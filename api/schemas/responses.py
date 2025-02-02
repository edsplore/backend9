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


class CreateSimulationResponse(BaseModel):
    id: str
    status: str
    prompt: str


class UpdateSimulationResponse(BaseModel):
    id: str
    status: str


class ListVoicesResponse(BaseModel):
    voices: List[dict]


class StartAudioSimulationPreviewResponse(BaseModel):
    access_token: str
