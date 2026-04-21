import json
import asyncio
import logging
from pathlib import Path
from urllib.parse import quote
import httpx
from core.config import settings

logger = logging.getLogger(__name__)

_CACHE_FILE = Path(__file__).parent.parent / "exercise_gif_cache.json"
_cache: dict[str, dict] = {}


def _load_cache() -> None:
    global _cache
    if _CACHE_FILE.exists():
        try:
            _cache = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            _cache = {}


def _save_cache() -> None:
    try:
        _CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


_load_cache()


async def fetch_exercise_data(english_name: str) -> dict:
    """ExerciseDB'den egzersiz verisi çek — target, secondary muscles, instructions dahil."""
    if not settings.rapidapi_key:
        return {}

    key = english_name.lower().strip()
    if not key:
        return {}

    if key in _cache and _cache[key]:
        return _cache[key]

    encoded = quote(key)
    url = f"https://exercisedb.p.rapidapi.com/exercises/name/{encoded}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url,
                params={"limit": "1", "offset": "0"},
                headers={
                    "X-RapidAPI-Key": settings.rapidapi_key,
                    "X-RapidAPI-Host": "exercisedb.p.rapidapi.com",
                },
            )

        logger.info("ExerciseDB [%s] → %s", key, resp.status_code)

        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                ex = data[0]
                result = {
                    "target_muscle": ex.get("target", ""),
                    "secondary_muscles": ex.get("secondaryMuscles", []),
                    "instructions": ex.get("instructions", []),
                    "difficulty": ex.get("difficulty", ""),
                    "body_part": ex.get("bodyPart", ""),
                }
                _cache[key] = result
                _save_cache()
                return result
        else:
            logger.error("ExerciseDB hata [%s]: %s", key, resp.text[:200])

    except Exception as exc:
        logger.error("ExerciseDB isteği başarısız [%s]: %s", key, exc)

    return {}


async def enrich_exercises(plan: dict) -> dict:
    """Plan içindeki tüm egzersizlere paralel olarak ExerciseDB verisi ekle."""
    pairs: list[tuple[dict, asyncio.Task]] = []

    for day in plan.get("days", []):
        if day.get("is_rest"):
            continue
        for exercise in day.get("exercises", []):
            english = exercise.get("english_name", "")
            task = asyncio.create_task(fetch_exercise_data(english))
            pairs.append((exercise, task))

    for exercise, task in pairs:
        try:
            data = await task
            exercise["target_muscle"] = data.get("target_muscle", "")
            exercise["secondary_muscles"] = data.get("secondary_muscles", [])
            exercise["instructions"] = data.get("instructions", [])
            exercise["difficulty"] = data.get("difficulty", "")
        except Exception:
            exercise["target_muscle"] = ""
            exercise["secondary_muscles"] = []
            exercise["instructions"] = []
            exercise["difficulty"] = ""

    return plan


# Eski isim — geriye dönük uyumluluk
enrich_plan_with_gifs = enrich_exercises
