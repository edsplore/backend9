from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class PaginationParams(BaseModel):
    page: int = 1
    pagesize: int = 50
    search: Optional[str] = None
    sortBy: Optional[str] = None
    sortDir: SortDirection = SortDirection.ASC
    tags: Optional[List[str]] = None
    division: Optional[str] = None
    department: Optional[str] = None
    status: Optional[List[str]] = None
    level: Optional[str] = None
    simType: Optional[str] = None
    createdBy: Optional[str] = None
    modifiedBy: Optional[str] = None
    createdFrom: Optional[datetime] = None
    createdTo: Optional[datetime] = None
    modifiedFrom: Optional[datetime] = None
    modifiedTo: Optional[datetime] = None


class ChatHistoryItem(BaseModel):
    sentence: str
    role: str


class TrainingDataRequest(BaseModel):
    user_id: str


class AttemptsRequest(BaseModel):
    user_id: str


class AttemptRequest(BaseModel):
    user_id: str
    attempt_id: str


class AudioToScriptRequest(BaseModel):
    user_id: str


class TextToScriptRequest(BaseModel):
    user_id: str
    prompt: str


class FileToScriptRequest(BaseModel):
    user_id: str


class StartSimulationRequest(BaseModel):
    user_id: str
    sim_id: str
    assignment_id: str


class EndAudioSimulationRequest(BaseModel):
    user_id: str
    simulation_id: str
    usersimulationprogress_id: str
    call_id: str


class EndChatSimulationRequest(BaseModel):
    user_id: str
    simulation_id: str
    usersimulationprogress_id: str
    chat_history: List[ChatHistoryItem]


class ListVoicesRequest(BaseModel):
    user_id: str


class StartChatPreviewRequest(BaseModel):
    user_id: str
    sim_id: str
    message: str | None = None
    usersimulationprogress_id: Optional[str] = None


class StartChatSimulationRequest(BaseModel):
    user_id: str
    sim_id: str
    assignment_id: str
    message: Optional[str] = None
    usersimulationprogress_id: Optional[str] = None


class ScriptSentence(BaseModel):
    script_sentence: str
    role: str
    keywords: list[str]


class HotspotCoordinates(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Hotspot(BaseModel):
    type: str
    id: str
    name: str
    hotspotType: str
    coordinates: HotspotCoordinates
    settings: Dict[str, Any]
    options: Optional[List[str]] = None


class SlideSequence(BaseModel):
    type: str
    id: str
    name: Optional[str] = None
    hotspotType: Optional[str] = None
    coordinates: Optional[HotspotCoordinates] = None
    settings: Optional[Dict[str, Any]] = None
    options: Optional[List[str]] = None
    role: Optional[str] = None
    text: Optional[str] = None


class SlideImage(BaseModel):
    data: str  # Base64 encoded image data
    contentType: str  # e.g., "image/png", "image/jpeg"


class SlideData(BaseModel):
    imageId: str
    imageName: str
    imageUrl: Optional[str] = None  # URL for stored image
    imageData: Optional[SlideImage] = None  # Image data for upload
    sequence: List[SlideSequence]


class SimulationLevel(BaseModel):
    is_enabled: bool = False
    enable_practice: bool = False
    hide_agent_script: bool = False
    hide_customer_script: bool = False
    hide_keyword_scores: bool = False
    hide_sentiment_scores: bool = False
    hide_highlights: bool = False
    hide_coaching_tips: bool = False
    enable_post_simulation_survey: bool = False
    ai_powered_pauses_and_feedback: bool = False


class SimulationScoringMetrics(BaseModel):
    is_enabled: bool = False
    keyword_score: int = 0
    click_score: int = 0


class SimulationPractice(BaseModel):
    is_unlimited: bool = False
    pre_requisite_limit: int = 0


class CreateSimulationRequest(BaseModel):
    user_id: str
    name: str
    division_id: str
    department_id: str
    type: str
    tags: list[str]


class UpdateSimulationRequest(BaseModel):
    user_id: str
    name: str | None = None
    division_id: str | None = None
    department_id: str | None = None
    type: str | None = None
    script: Optional[list[ScriptSentence]] | None = None
    tags: list[str] | None = None
    status: str | None = None
    lvl1: SimulationLevel | None = None
    lvl2: SimulationLevel | None = None
    lvl3: SimulationLevel | None = None
    estimated_time_to_attempt_in_mins: int | None = None
    key_objectives: list[str] | None = None
    overview_video: str | None = None
    quick_tips: list[str] | None = None
    voice_id: str | None = None
    language: str | None = None
    mood: str | None = None
    voice_speed: str | None = None
    prompt: str | None = None
    simulation_completion_repetition: int | None = None
    simulation_max_repetition: int | None = None
    final_simulation_score_criteria: str | None = None
    simulation_scoring_metrics: SimulationScoringMetrics | None = None
    sim_practice: SimulationPractice | None = None
    is_locked: bool | None = None
    version: int | None = None
    agent_id: str | None = None
    llm_id: str | None = None
    assistant_id: str | None = None
    slides: dict | None = None
    slidesData: Optional[List[SlideData]] = None


class StartAudioSimulationPreviewRequest(BaseModel):
    user_id: str
    sim_id: str


class StartAudioSimulationRequest(BaseModel):
    user_id: str
    sim_id: str
    assignment_id: str


class FetchSimulationsRequest(BaseModel):
    user_id: str
    pagination: Optional[PaginationParams] = None


class CreateModuleRequest(BaseModel):
    user_id: str
    module_name: str
    tags: list[str]
    simulations: list[str]


class UpdateModuleRequest(BaseModel):
    user_id: str
    module_name: Optional[str] = None
    tags: Optional[list[str]] = None
    simulations: Optional[list[str]] = None


class FetchModulesRequest(BaseModel):
    user_id: str
    pagination: Optional[PaginationParams] = None


class AddedObject(BaseModel):
    type: str
    id: str


class CreateTrainingPlanRequest(BaseModel):
    user_id: str
    training_plan_name: str
    tags: list[str]
    added_object: list[AddedObject]


class UpdateTrainingPlanRequest(BaseModel):
    user_id: str
    training_plan_name: Optional[str] = None
    tags: Optional[list[str]] = None
    added_object: Optional[list[AddedObject]] = None


class FetchTrainingPlansRequest(BaseModel):
    user_id: str
    pagination: Optional[PaginationParams] = None


class ListItemsRequest(BaseModel):
    user_id: str


class TeamMember(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    email: str
    phone_no: str
    fullName: str


class TeamLeader(TeamMember):
    pass


class Team(BaseModel):
    team_id: str
    name: str
    leader: TeamLeader
    team_members: List[TeamMember]
    status: str


class CreateAssignmentRequest(BaseModel):
    id: str
    user_id: str
    name: str
    type: str
    start_date: str
    end_date: str
    team_id: List[Team]
    trainee_id: List[str] = []


class CloneSimulationRequest(BaseModel):
    user_id: str
    simulation_id: str


class CloneTrainingPlanRequest(BaseModel):
    user_id: str
    training_plan_id: str


class CloneModuleRequest(BaseModel):
    user_id: str
    module_id: str


class FetchAssignedPlansRequest(BaseModel):
    user_id: str


class StartVisualAudioPreviewRequest(BaseModel):
    user_id: str
    sim_id: str


class StartVisualChatPreviewRequest(BaseModel):
    user_id: str
    sim_id: str


class StartVisualPreviewRequest(BaseModel):
    user_id: str
    sim_id: str


class CreateTagRequest(BaseModel):
    user_id: str
    name: str


class FetchTagsRequest(BaseModel):
    user_id: str


class StartVisualAudioAttemptRequest(BaseModel):
    user_id: str
    sim_id: str
    assignment_id: str


class StartVisualChatAttemptRequest(BaseModel):
    user_id: str
    sim_id: str
    assignment_id: str


class StartVisualAttemptRequest(BaseModel):
    user_id: str
    sim_id: str
    assignment_id: str


class EndVisualAudioAttemptRequest(BaseModel):
    user_id: str
    simulation_id: str
    usersimulationprogress_id: str


class EndVisualChatAttemptRequest(BaseModel):
    user_id: str
    simulation_id: str
    usersimulationprogress_id: str


class EndVisualAttemptRequest(BaseModel):
    user_id: str
    simulation_id: str
    usersimulationprogress_id: str

class FetchManagerDashboardTrainingPlansRequest(BaseModel):
    user_id: str
