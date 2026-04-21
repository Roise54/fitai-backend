from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.limiter import limiter
from api.routes import body, food, score, diet, quote, body_progress, workout, auth

# ─── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="FitAI API",
    docs_url=None,   # Swagger UI'yi production'da kapat
    redoc_url=None,
)

# ─── Rate limiter ────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── Request body boyut sınırı (10 MB) ───────────────────────────────────────

class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    MAX_BODY = 10 * 1024 * 1024  # 10 MB

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY:
            return JSONResponse(status_code=413, content={"detail": "İstek boyutu 10MB sınırını aşıyor"})
        return await call_next(request)

app.add_middleware(MaxBodySizeMiddleware)

# ─── CORS ────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ─── Global hata yakalayıcı (backend detayı sızdırmaz) ───────────────────────

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Sunucu hatası. Lütfen tekrar deneyin."},
    )

# ─── Router'lar ──────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(body.router, prefix="/body", tags=["body"])
app.include_router(body_progress.router, prefix="/body-progress", tags=["body-progress"])
app.include_router(food.router, prefix="/food", tags=["food"])
app.include_router(score.router, prefix="/score", tags=["score"])
app.include_router(diet.router, prefix="/diet", tags=["diet"])
app.include_router(quote.router, prefix="/quote", tags=["quote"])
app.include_router(workout.router, prefix="/workout", tags=["workout"])

# ─── Health check (route listesi yok) ────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok"}
