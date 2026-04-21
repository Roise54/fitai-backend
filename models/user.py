from pydantic import BaseModel
from typing import Optional

class UserProfile(BaseModel):
    age: int
    height_cm: float
    weight_kg: float
    gender: str  # male / female
    goal: str    # lose_fat / build_muscle / recomp

class BodyAnalysisResult(BaseModel):
    fat_percentage: str
    muscle_level: str
    fitness_level: str
    kg_to_goal: float
    estimated_months: int
    first_actions: list[str]

class FoodAnalysisResult(BaseModel):
    analysis: str
    decision: str        # ye / azalt / değiştir / kaçın
    impact: str          # düşük / orta / yüksek
    alternative: str

class DailyScore(BaseModel):
    score: int
    feedback: str
    top_recommendation: str
