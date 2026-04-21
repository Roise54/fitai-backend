import re
from fastapi import HTTPException

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_TEXT_LENGTH = 100
MAX_QUESTION_LENGTH = 500
MAX_FOOD_DECISIONS = 20

ALLOWED_GOALS = {"lose_fat", "build_muscle", "recomp"}
ALLOWED_GENDERS = {"male", "female"}

# Prompt injection'a karşı izin verilen karakterler: harf, rakam, boşluk, Türkçe harfler
_SAFE_TEXT_RE = re.compile(r"[^\w\s\u00C0-\u024F\u011E\u011F\u0130\u0131\u015E\u015F\u00D6\u00F6\u00DC\u00FC\u00C7\u00E7\-']", re.UNICODE)


def sanitize_name(value: str) -> str:
    """İsim alanını temizle: özel karakterleri sil, kırp, uzunluk sınırla."""
    value = _SAFE_TEXT_RE.sub("", value.strip())
    return value[:50]


def sanitize_text(value: str, max_len: int = MAX_TEXT_LENGTH) -> str:
    """Genel metin temizleme."""
    value = _SAFE_TEXT_RE.sub("", value.strip())
    return value[:max_len]


def sanitize_question(value: str) -> str:
    """Chat sorusu: biraz daha geniş karakter kümesi, ama uzunluk kısıtlı."""
    # Sadece tehlikeli prompt injection karakterlerini kaldır
    value = re.sub(r"[<>{}\[\]\\]", "", value.strip())
    return value[:MAX_QUESTION_LENGTH]


def validate_goal(goal: str) -> str:
    if goal not in ALLOWED_GOALS:
        raise HTTPException(status_code=422, detail="Geçersiz hedef değeri")
    return goal


def validate_gender(gender: str) -> str:
    if gender not in ALLOWED_GENDERS:
        raise HTTPException(status_code=422, detail="Geçersiz cinsiyet değeri")
    return gender


def validate_image_bytes(data: bytes, field_name: str = "Görsel") -> None:
    """Boyut ve magic bytes ile görsel doğrulama."""
    if not data:
        raise HTTPException(status_code=422, detail=f"{field_name} boş olamaz")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f"{field_name} 5MB sınırını aşıyor")

    is_jpeg = data[:3] == b'\xff\xd8\xff'
    is_png = data[:8] == b'\x89PNG\r\n\x1a\n'
    is_webp = len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP'
    # HEIC: 'ftyp' alanı offset 4'te bulunur
    is_heic = len(data) >= 12 and data[4:8] == b'ftyp'

    if not (is_jpeg or is_png or is_webp or is_heic):
        raise HTTPException(status_code=422, detail=f"{field_name} desteklenmeyen format (JPEG/PNG/WebP/HEIC bekleniyor)")


def validate_profile_numbers(age: int, height_cm: float, weight_kg: float) -> None:
    if not (5 <= age <= 120):
        raise HTTPException(status_code=422, detail="Geçersiz yaş değeri")
    if not (50.0 <= height_cm <= 250.0):
        raise HTTPException(status_code=422, detail="Geçersiz boy değeri")
    if not (20.0 <= weight_kg <= 500.0):
        raise HTTPException(status_code=422, detail="Geçersiz kilo değeri")


def validate_food_decisions(decisions: list) -> list:
    if len(decisions) > MAX_FOOD_DECISIONS:
        raise HTTPException(status_code=422, detail="Çok fazla yemek kararı")
    return [sanitize_text(str(d), 200) for d in decisions]


def validate_week_number(week: int) -> int:
    if not (1 <= week <= 52):
        raise HTTPException(status_code=422, detail="Geçersiz hafta numarası")
    return week
