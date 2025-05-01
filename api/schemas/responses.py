from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from domain.models.training import TrainingDataModel
from domain.models.playback import SimulationAttemptModel, AttemptAnalyticsModel
from api.schemas.requests import SimulationScoringMetrics, SimulationPractice


class PaginationMetadata(BaseModel):
    total_count: int
    page: int
    pagesize: int
    total_pages: int


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




class UpdateSimulationResponse(BaseModel):
    id: str
    status: str
    document: Dict[str, Any]




class StartSimulationResponse(BaseModel):
    id: str
    status: str
    access_token: Optional[str] = None  # For audio simulations
    response: Optional[str] = None  # For chat simulations
    call_id: Optional[str] = None  # For simulations




class EndSimulationResponse(BaseModel):
    id: str
    status: str
    scores: Dict[str, float]
    duration: int
    transcript: str
    audio_url: str




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




class HotspotCoordinates(BaseModel):
    x: float
    y: float
    width: float
    height: float




class HotspotSettings(BaseModel):
    font: str
    fontSize: int
    buttonColor: str
    textColor: str
    timeoutDuration: int
    highlightField: bool
    enableHotkey: bool




class Hotspot(BaseModel):
    type: str
    id: str
    name: str
    hotspotType: str
    coordinates: HotspotCoordinates
    settings: HotspotSettings




class SlideSequence(BaseModel):
    type: str
    id: str
    name: Optional[str] = None
    hotspotType: Optional[str] = None
    coordinates: Optional[HotspotCoordinates] = None
    settings: Optional[Dict[str, Any]] = None
    role: Optional[str] = None
    text: Optional[str] = None
    options: Optional[List[str]] = None




class SlideImage(BaseModel):
    data: str  # Base64 encoded image data
    contentType: str  # e.g., "image/png", "image/jpeg"




class SlideData(BaseModel):
    imageId: str
    imageName: str
    imageUrl: Optional[str] = None  # URL for stored image
    imageData: Optional[SlideImage] = None  # Image data for upload
    sequence: Optional[List[SlideSequence]] = None




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
    voice_id: Optional[str] = None
    script: Optional[list[ScriptSentence]] = None
    slidesData: Optional[list[SlideData]] = None
    prompt: Optional[str] = None
    key_objectives: list[str] | None = None
    overview_video: str | None = None
    quick_tips: list[str] | None = None
    simulation_completion_repetition: int | None = None
    simulation_max_repetition: int | None = None
    final_simulation_score_criteria: str | None = None
    simulation_scoring_metrics: SimulationScoringMetrics | None = None
    sim_practice: SimulationPractice | None = None
    estimated_time_to_attempt_in_mins: int | None = None
    mood: str | None = None
    voice_speed: str | None = None




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
    scores: dict = {}
    highest_attempt_score: float = 0
    assignment_id: str




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




class SlideImageData(BaseModel):
    image_id: str
    image_data: bytes




class StartVisualAudioPreviewResponse(BaseModel):
    simulation: SimulationData
    images: List[SlideImageData] = []




class StartVisualChatPreviewResponse(BaseModel):
    simulation: SimulationData
    images: List[SlideImageData] = []




class StartVisualPreviewResponse(BaseModel):
    simulation: SimulationData
    images: List[SlideImageData] = []




class SimulationByIDResponse(BaseModel):
    simulation: SimulationData
    images: Optional[List[SlideImageData]] = None




class TagData(BaseModel):
    id: str
    name: str
    created_by: str
    created_at: str
    last_modified_by: str
    last_modified_at: str




class CreateTagResponse(BaseModel):
    id: str
    status: str




class FetchTagsResponse(BaseModel):
    tags: List[TagData]




class StartVisualAudioAttemptResponse(BaseModel):
    id: str
    status: str
    simulation: SimulationData
    images: List[SlideImageData] = []




class StartVisualChatAttemptResponse(BaseModel):
    id: str
    status: str
    simulation: SimulationData
    images: List[SlideImageData] = []




class StartVisualAttemptResponse(BaseModel):
    id: str
    status: str
    simulation: SimulationData
    images: List[SlideImageData] = []


class FetchManagerDashnoardTrainingPlansDetails(BaseModel):
    id: str
    name: str
    type: str
    start_date: str
    end_date: str
    team_id: List[str] = []
    trainee_id: List[str] = []
    created_by: str
    created_at: str
    last_modified_by: str
    last_modified_at: str
    status: str


class TrainingPlanDetailsByUser(BaseModel):
    completion_percentage: float = 0
    total_modules: int
    total_simulations: int
    est_time: int
    average_sim_score: float = 0
    due_date: str
    status: str = "not_started"
    user_id: str
    modules: List[ModuleDetails]


class TrainingPlanDetailsMinimal(BaseModel):
    id: str
    name: str
    completion_percentage: float = 0
    average_score: float = 0
    user: List[TrainingPlanDetailsByUser]


class ModuleDetailsByUser(BaseModel):
    total_simulations: int
    average_score: float = 0
    due_date: str
    status: str = "not_started"
    user_id: str
    simulations: List[SimulationDetails]
   


class ModuleDetailsMinimal(BaseModel):
    id: str
    name: str
    completion_percentage: float = 0
    average_score: float = 0
    user: List[ModuleDetailsByUser]


class SimulationDetailsByUser(BaseModel):
    simulation_id: str
    name: str
    type: str
    level: str
    estTime: int
    dueDate: str
    status: str = "not_started"
    highest_attempt_score: float = 0
    scores: dict = {}
    assignment_id: str
    user_id: str
   
class SimulationDetailsMinimal(BaseModel):
    id: str
    name: str
    completion_percentage: float = 0
    average_score: float = 0
    user: List[SimulationDetailsByUser]


class FetchManagerDashboardResponse(BaseModel):
    training_plans: List[TrainingPlanDetailsMinimal]
    modules: List[ModuleDetailsMinimal]
    simulations: List[SimulationDetailsMinimal]
    pagination: Optional[PaginationMetadata] = None

class TraineeAssignmentAttemptStatus(BaseModel):
    name: str
    class_id: int
    status: str
    due_date: str
    avg_score: Optional[str]  

class TrainingEntity(BaseModel):
    id: str  # ID No.
    name: str  # TRP Name
    trainees: List['TraineeAssignmentAttemptStatus']
    completion_rate: str
    adherence_rate: str
    avg_score: float
    est_time: str

class ManagerDashboardTrainingEntityTableResponse(BaseModel):
    training_entity: List[TrainingEntity]
    pagination: Optional[PaginationMetadata] = None

class FetchManagerDashboardTrainingPlansResponse(BaseModel):
    class TraineeStatus(BaseModel):
        name: str
        class_id: int
        status: str
        due_date: str
        avg_score: Optional[str]  # "NA" or a percentage


    class TrainingPlan(BaseModel):
        id: str  # ID No.
        name: str  # TRP Name
        trainees: List['FetchManagerDashboardTrainingPlansResponse.TraineeStatus']
        completion_rate: str
        adherence_rate: str
        avg_score: float
        est_time: str


    training_plans: List[TrainingPlan]




class FetchManagerDashboardModulesResponse(BaseModel):
    class TraineeStatus(BaseModel):
        name: str
        class_id: int
        status: str
        due_date: str
        avg_score: Optional[str]


    class Module(BaseModel):
        id: str
        name: str
        trainees: List['FetchManagerDashboardModulesResponse.TraineeStatus']
        completion_rate: str
        adherence_rate: str
        avg_score: float
        est_time: str


    modules: List[Module]


class FetchManagerDashboardSimultaionResponse(BaseModel):
    class TraineeStatus(BaseModel):
        name: str
        class_id: int
        status: str
        due_date: str
        avg_score: Optional[str]


    class Simulation(BaseModel):
        id: str
        name: str
        trainees: List['FetchManagerDashboardSimultaionResponse.TraineeStatus']
        completion_rate: str
        adherence_rate: str
        avg_score: float
        est_time: str


    simulations: List[Simulation]




class ManagerDashboardAssignmentCounts(BaseModel):
    total: int = 0,
    completed: int = 0,
    inProgress: int = 0,
    notStarted: int = 0,
    overdue: int = 0


class ManagerDashboardAggregateAssignmentCounts(BaseModel):
    trainingPlans: ManagerDashboardAssignmentCounts
    modules: ManagerDashboardAssignmentCounts
    simulations: ManagerDashboardAssignmentCounts


class ManagerDashboardAggregateMetrics(BaseModel):
    trainingPlans: int = 0
    modules: int = 0
    simulations: int = 0


class ManagerDashboardAggregateDetails(BaseModel):
    assignmentCounts: ManagerDashboardAggregateAssignmentCounts
    completionRates: ManagerDashboardAggregateMetrics
    adherenceRates: ManagerDashboardAggregateMetrics
    averageScores: ManagerDashboardAggregateMetrics

