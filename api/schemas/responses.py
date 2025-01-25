from typing import List
from pydantic import BaseModel
from domain.models.training import TrainingDataModel
from domain.models.playback import SimulationAttemptModel, AttemptAnalyticsModel

class TrainingDataResponse(BaseModel):
    training_plans: List[TrainingDataModel]
    stats: dict

class AttemptsResponse(BaseModel):
    attempts: List[SimulationAttemptModel]

class AttemptResponse(BaseModel):
    attempt: AttemptAnalyticsModel

class ScriptResponse(BaseModel):
    script: List[dict]