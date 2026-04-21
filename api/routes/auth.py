import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone

from core.config import settings

router = APIRouter()

FIREBASE_AUTH = "https://identitytoolkit.googleapis.com/v1/accounts"


class AuthRequest(BaseModel):
    email: str
    password: str


def _init_firebase():
    import json
    import firebase_admin
    from firebase_admin import credentials
    if not firebase_admin._apps:
        if settings.firebase_service_account_json:
            cred = credentials.Certificate(json.loads(settings.firebase_service_account_json))
        else:
            cred = credentials.Certificate(settings.firebase_service_account_path)
        firebase_admin.initialize_app(cred)


def _get_firestore():
    _init_firebase()
    from firebase_admin import firestore
    return firestore.client()


def _firebase_error(message: str) -> str:
    mapping = {
        "EMAIL_EXISTS": "email-already-in-use",
        "INVALID_EMAIL": "invalid-email",
        "WEAK_PASSWORD": "weak-password",
        "EMAIL_NOT_FOUND": "user-not-found",
        "INVALID_PASSWORD": "wrong-password",
        "INVALID_LOGIN_CREDENTIALS": "invalid-credential",
        "USER_DISABLED": "user-disabled",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "too-many-requests",
        "OPERATION_NOT_ALLOWED": "operation-not-allowed",
    }
    for key, code in mapping.items():
        if key in message:
            return code
    return "unknown"


async def _get_custom_token(uid: str) -> str:
    _init_firebase()
    from firebase_admin import auth as admin_auth
    try:
        token_bytes = admin_auth.create_custom_token(uid)
        return token_bytes.decode("utf-8")
    except Exception as e:
        print(f"[AUTH] Custom token hatası uid={uid}: {e}")
        raise HTTPException(status_code=500, detail="token-error")


@router.post("/register")
async def register(req: AuthRequest):
    print(f"[AUTH] Kayıt isteği: {req.email}")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FIREBASE_AUTH}:signUp?key={settings.firebase_web_api_key}",
            json={"email": req.email, "password": req.password, "returnSecureToken": True},
            timeout=15,
        )
    data = resp.json()

    if "error" in data:
        raw = data["error"]["message"]
        code = _firebase_error(raw)
        print(f"[AUTH] Kayıt hatası ({req.email}): {raw} → {code}")
        raise HTTPException(status_code=400, detail=code)

    uid = data["localId"]
    email = data["email"]
    print(f"[AUTH] Firebase kullanıcı oluşturuldu: uid={uid}")

    try:
        db = _get_firestore()
        db.collection("users").document(uid).set({
            "uid": uid,
            "email": email,
            "provider": "email",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }, merge=True)
        print(f"[AUTH] Firestore kaydı oluşturuldu: uid={uid}")
    except Exception as e:
        print(f"[AUTH] Firestore yazma hatası uid={uid}: {e}")
        raise HTTPException(status_code=500, detail="firestore-error")

    custom_token = await _get_custom_token(uid)
    print(f"[AUTH] Kayıt başarılı: {email}")
    return {"customToken": custom_token, "uid": uid, "email": email}


@router.post("/login")
async def login(req: AuthRequest):
    print(f"[AUTH] Giriş isteği: {req.email}")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FIREBASE_AUTH}:signInWithPassword?key={settings.firebase_web_api_key}",
            json={"email": req.email, "password": req.password, "returnSecureToken": True},
            timeout=15,
        )
    data = resp.json()

    if "error" in data:
        raw = data["error"]["message"]
        code = _firebase_error(raw)
        print(f"[AUTH] Giriş hatası ({req.email}): {raw} → {code}")
        raise HTTPException(status_code=400, detail=code)

    uid = data["localId"]
    print(f"[AUTH] Firebase doğrulandı: uid={uid}")

    try:
        db = _get_firestore()
        user_doc = db.collection("users").document(uid).get()
        if not user_doc.exists:
            print(f"[AUTH] Firestore'da kayıt yok: uid={uid}")
            raise HTTPException(status_code=403, detail="user-not-registered")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Firestore okuma hatası uid={uid}: {e}")
        raise HTTPException(status_code=500, detail="firestore-error")

    custom_token = await _get_custom_token(uid)
    print(f"[AUTH] Giriş başarılı: {req.email}")
    return {"customToken": custom_token, "uid": uid, "email": data["email"]}
