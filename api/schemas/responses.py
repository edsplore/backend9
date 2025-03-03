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


class StartChatPreviewResponse(BaseModel):
    chat_id: str
    response: str


class ScriptSentence(BaseModel):
    script_sentence: str
    role: str
    keywords: list[str]


class SimulationData(BaseModel):
    id: str
    sim_name: str
    version: str
    lvl1: dict = {}
    lvl2: dict = {}
    lvl3: dict = {}
    sim_type: str
    status: str
    tags: List[str] = []
    est_time: str
    last_modified: str
    modified_by: str
    created_on: str
    created_by: str
    islocked: bool
    division_id: str
    department_id: str
    script: list[ScriptSentence]


class FetchSimulationsResponse(BaseModel):
    simulations: List[SimulationData]


class CreateModuleResponse(BaseModel):
    id: str
    status: str


class ModuleData(BaseModel):
    id: str
    name: str
    tags: List[str]
    simulations_id: List[str]
    created_by: str
    created_at: str
    last_modified_by: str
    last_modified_at: str
    estimated_time: int = 0


class FetchModulesResponse(BaseModel):
    modules: List[ModuleData]


class CreateTrainingPlanResponse(BaseModel):
    id: str
    status: str


class TrainingPlanData(BaseModel):
    id: str
    name: str
    tags: List[str]
    added_object: List[dict[str, str]]
    created_by: str
    created_at: str
    last_modified_by: str
    last_modified_at: str
    estimated_time: int = 0


class FetchTrainingPlansResponse(BaseModel):
    training_plans: List[TrainingPlanData]


# New response models
class ListItemData(BaseModel):
    name: str
    id: str
    type: str
    sims: int = 0


class ListTrainingPlansResponse(BaseModel):
    training_plans: List[ListItemData]


class ListModulesResponse(BaseModel):
    modules: List[ListItemData]


class ListSimulationsResponse(BaseModel):
    simulations: List[ListItemData]


class CreateAssignmentResponse(BaseModel):
    id: str
    status: str
