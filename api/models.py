from pydantic import BaseModel
from typing import Optional, List


class ParentCreate(BaseModel):
    full_name: str
    email: str
    consent_confirmed: bool = False


class ParentResponse(BaseModel):
    id: int
    full_name: str
    email: str
    consent_timestamp: str
    consent_confirmed: bool
    created_at: str


class AthleteCreate(BaseModel):
    parent_id: int
    first_name: str
    age: int
    gender: str  # Girl / Boy / Prefer not to say
    weight_lbs: float
    height_ft: int
    height_in: float
    position: Optional[str] = None  # Goalkeeper / Defender / Midfielder / Forward
    competition_level: Optional[str] = None  # Recreational / Club / Competitive / Elite
    sweat_profile: Optional[str] = None  # Light / Moderate / Heavy / Very Heavy
    allergies: Optional[str] = None
    dietary_restrictions: Optional[str] = None
    supplement_use: Optional[str] = None


class AthleteResponse(BaseModel):
    id: int
    parent_id: int
    first_name: str
    age: int
    gender: str
    weight_lbs: float
    height_ft: int
    height_in: float
    position: Optional[str]
    competition_level: Optional[str]
    sweat_profile: Optional[str]
    allergies: Optional[str]
    dietary_restrictions: Optional[str]
    supplement_use: Optional[str]
    created_at: str


class EventCreate(BaseModel):
    athlete_id: int
    event_name: str
    event_type: str
    event_date: str  # YYYY-MM-DD
    start_time: Optional[str] = None  # HH:MM
    duration_hours: Optional[float] = None
    city: Optional[str] = None


class EventResponse(BaseModel):
    id: int
    athlete_id: int
    event_name: str
    event_type: str
    event_date: str
    start_time: Optional[str]
    duration_hours: Optional[float]
    city: Optional[str]
    created_at: str


class MealLogCreate(BaseModel):
    athlete_id: int
    log_method: str  # photo / text / quick-select / restaurant / water
    description: Optional[str] = None
    calories: Optional[float] = None
    carbs_g: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    iron_mg: Optional[float] = None
    calcium_mg: Optional[float] = None
    water_oz: Optional[float] = None
    edamam_raw: Optional[str] = None


class MealLogResponse(BaseModel):
    id: int
    athlete_id: int
    logged_at: str
    log_method: str
    description: Optional[str]
    calories: Optional[float]
    carbs_g: Optional[float]
    protein_g: Optional[float]
    fat_g: Optional[float]
    iron_mg: Optional[float]
    calcium_mg: Optional[float]
    water_oz: Optional[float]


class SweatOutputRequest(BaseModel):
    athlete_id: int
    event_id: int
    city: str


class RecipeSwapRequest(BaseModel):
    athlete_id: int
    disliked_recipe: str
    meal_timing_category: str


class MealPlanSlotUpdate(BaseModel):
    plan_date: str
    slot_name: str
    recipe_id: str


class MealPlanLogSlot(BaseModel):
    plan_date: str
    slot_name: str


class MealPlanGenerateRequest(BaseModel):
    athlete_id: int
    week_start: str
    overwrite_existing: bool = False


class OTPRequest(BaseModel):
    email: str


class OTPVerify(BaseModel):
    email: str
    code: str
