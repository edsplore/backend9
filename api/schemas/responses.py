from typing import List, Optional
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


class AssignmentData(BaseModel):
    id: str
    name: str
    type: str
    start_date: str
    end_date: str
    team_id: List[str]
    trainee_id: List[str]
    created_by: str
    created_at: str
    last_modified_by: str
    last_modified_at: str
    status: str


class FetchAssignmentsResponse(BaseModel):
    assignments: List[AssignmentData]


class SimulationDetails(BaseModel):
    simulation_id: str
    name: str
    type: str
    level: str
    estTime: int
    dueDate: str
    status: str = "not_started"
    highest_attempt_score: float = 0


class ModuleDetails(BaseModel):
    id: str
    name: str
    total_simulations: int
    average_score: float = 0
    due_date: str
    status: str = "not_started"
    simulations: List[SimulationDetails]


class TrainingPlanDetails(BaseModel):
    id: str
    name: str
    completion_percentage: float = 0
    total_modules: int
    total_simulations: int
    est_time: int
    average_sim_score: float = 0
    due_date: str
    status: str = "not_started"
    modules: List[ModuleDetails]


class StatsData(BaseModel):
    total_simulations: int
    completed_simulations: int
    percentage: float


class Stats(BaseModel):
    simulation_completed: StatsData
    timely_completion: StatsData
    average_sim_score: float = 0
    highest_sim_score: float = 0


class FetchAssignedPlansResponse(BaseModel):
    training_plans: List[TrainingPlanDetails]
    modules: List[ModuleDetails]
    simulations: List[SimulationDetails]
    stats: Stats
