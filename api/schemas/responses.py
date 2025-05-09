from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
from domain.models.training import TrainingDataModel
from domain.models.playback import SimulationAttemptModel, AttemptAnalyticsModel
from api.schemas.requests import SimulationScoringMetrics, SimulationPractice, MetricWeightage


class PaginationMetadata(BaseModel):
    total_count: int
    page: int
    pagesize: int
    total_pages: int


class TrainingDataResponse(BaseModel):
    stats: dict


class AttemptsStatsResponse(BaseModel):

    class SimulationCompletion(BaseModel):
        completed: int
        total: int
        total_modules: int

    class OnTimeCompletion(BaseModel):
        completed: int
        total: int

    class Scores(BaseModel):
        percentage: int
        difference_from_last_week: int

    simultion_completion: SimulationCompletion
    ontime_completion: OnTimeCompletion
    average_sim_score: Scores
    highest_sim_score: Scores

    class Config:
        arbitrary_types_allowed = True


class AttemptsResponse(BaseModel):
    attempts: List[SimulationAttemptModel]
    total_attempts: int


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
    metric_weightage: MetricWeightage | None = None
    sim_practice: SimulationPractice | None = None
    estimated_time_to_attempt_in_mins: int | None = None
    mood: str | None = None
    voice_speed: str | None = None


class FetchSimulationsResponse(BaseModel):
    simulations: List[SimulationData]
    pagination: Optional[PaginationMetadata] = None


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
    pagination: Optional[PaginationMetadata] = None


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
    pagination: Optional[PaginationMetadata] = None


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
    pagination: Optional[PaginationMetadata] = None


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
    pagination: Optional[PaginationMetadata] = None


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


class SimulationDetailsByUser(BaseModel):
    simulation_id: str
    name: str
    type: str
    level: str
    est_time: int
    dueDate: str
    status: str = "not_started"
    highest_attempt_score: float = 0
    average_score: int = 0
    scores: dict = {}
    assignment_id: str
    user_id: str


class ModuleDetailsByUser(BaseModel):
    name: str
    total_simulations: int
    average_score: float = 0
    due_date: str
    status: str = "not_started"
    user_id: str
    completion_percentage: int = 0
    adherence_percentage: int = 0
    est_time: int = 0
    simulations: Optional[List[SimulationDetailsByUser]] = []


class TrainingPlanDetailsByUser(BaseModel):
    name: str
    completion_percentage: int = 0
    adherence_percentage: int = 0
    total_modules: int
    total_simulations: int
    est_time: int
    average_score: float = 0
    due_date: str
    status: str = "not_started"
    user_id: str
    modules: Optional[List[ModuleDetailsByUser]] = []
    simulations: Optional[List[SimulationDetailsByUser]] = []


class TrainingPlanDetailsMinimal(BaseModel):
    id: str
    name: str
    completion_percentage: float = 0
    average_score: float = 0
    user: List[TrainingPlanDetailsByUser]


class ModuleDetailsMinimal(BaseModel):
    id: str
    name: str
    completion_percentage: float = 0
    average_score: float = 0
    user: List[ModuleDetailsByUser]


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
    teams_stats: Optional[Dict[str,
                               List[Union[TrainingPlanDetailsByUser,
                                          ModuleDetailsByUser,
                                          SimulationDetailsByUser]]]] = None
    pagination: Optional[PaginationMetadata] = None


class TraineeAssignmentAttemptStatus(BaseModel):
    name: str
    classId: int
    status: str
    dueDate: str
    avgScore: Optional[int]


class TrainingEntity(BaseModel):
    id: str  # ID No.
    name: str  # TRP Name
    trainees: List['TraineeAssignmentAttemptStatus']
    completionRate: int
    adherenceRate: int
    avgScore: float
    estTime: int
    assignedTrainees: int


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
        trainees: List[
            'FetchManagerDashboardTrainingPlansResponse.TraineeStatus']
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


class ManagerDashboardTeamWiseAggregateMetrics(BaseModel):
    team: str
    score: int


class ManagerDashboardLeaderBoardsAggMetricWise(BaseModel):
    completion: List[ManagerDashboardTeamWiseAggregateMetrics]
    averageScore: List[ManagerDashboardTeamWiseAggregateMetrics]
    adherence: List[ManagerDashboardTeamWiseAggregateMetrics]


class ManagerDashboardAggregateDetails(BaseModel):
    assignmentCounts: ManagerDashboardAggregateAssignmentCounts
    completionRates: ManagerDashboardAggregateMetrics
    adherenceRates: ManagerDashboardAggregateMetrics
    averageScores: ManagerDashboardAggregateMetrics
    leaderBoards: ManagerDashboardLeaderBoardsAggMetricWise


class AdminDashboardUserActivityStatsUserType(BaseModel):

    class Breakdown(BaseModel):
        admin: int = 0
        manager: int = 0
        designer: int = 0
        trainees: int = 0

    total_users: int = 0
    breakdown: Breakdown = Breakdown()


class AdminDashboardUserActivityStatsResponse(BaseModel):
    new_users: AdminDashboardUserActivityStatsUserType
    active_users: AdminDashboardUserActivityStatsUserType
    deactivated_users: AdminDashboardUserActivityStatsUserType
    daily_active_users: AdminDashboardUserActivityStatsUserType
    weekly_active_users: AdminDashboardUserActivityStatsUserType
    monthly_active_users: AdminDashboardUserActivityStatsUserType


class AdminDashboardUserActivityResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    division: str
    department: str
    addedOn: str
    status: str
    assignedSimulations: int
    completionRate: int
    adherenceRate: int
    averageScore: int
    activatedOn: str
    deActivatedOn: str
    loginCount: int
    lastLoginOn: str
    lastSessionDuration: int


class KeywordAnalysis(BaseModel):
    total_keywords: int
    missing_keywords: int
    missing_keywords_list: List[str]


class KeywordScoreAnalysisScript(BaseModel):
    role: str
    script_sentence: Optional[str] = None
    actual_sentence: Optional[str] = None
    keyword_analysis: Optional[KeywordAnalysis | dict] = None


class KeywordScoreAnalysisWithScriptResponse(BaseModel):
    script: List[KeywordScoreAnalysisScript]
    total_keywords: int
    total_missing_keywords: int
    keyword_score: int


class CreateUserResponse(BaseModel):
    user_id: str


class ContextualScoreAnalysisScript(BaseModel):
    role: str
    scripted_text: Optional[str] = None
    actual_text: Optional[str] = None
    scripted_context: Optional[str] = None
    actual_context: Optional[str] = None
    summary_evaluation: Optional[str] = None
    contextual_accuracy: Optional[int] = None


class ContextualScoreAnalysisWithScriptResponse(BaseModel):
    script: List[ContextualScoreAnalysisScript]
    overall_contextual_accuracy: int


class IndividualBehaviouralScoreAnalysis(BaseModel):
    overall_score: int
    evaluation: str


class BehaviouralScoreAnalysis(BaseModel):
    confidence_score: IndividualBehaviouralScoreAnalysis
    concentration_score: IndividualBehaviouralScoreAnalysis
    energy_score: IndividualBehaviouralScoreAnalysis


class ChatTypeScoreResponse(BaseModel):
    keyword_accuracy: KeywordScoreAnalysisWithScriptResponse
    contextual_accuracy: ContextualScoreAnalysisWithScriptResponse
    confidence_accuracy: Optional[IndividualBehaviouralScoreAnalysis] = None
    concentration_accuracy: Optional[IndividualBehaviouralScoreAnalysis] = None
    energy_accuracy: Optional[IndividualBehaviouralScoreAnalysis] = None
