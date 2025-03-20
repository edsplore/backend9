from pydantic import BaseModel


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


class ListVoicesRequest(BaseModel):
    user_id: str


class StartChatPreviewRequest(BaseModel):
    user_id: str
    sim_id: str
    message: str | None = None


class ScriptSentence(BaseModel):
    script_sentence: str
    role: str
    keywords: list[str]


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
    script: list[ScriptSentence]
    tags: list[str]


class UpdateSimulationRequest(BaseModel):
    user_id: str
    name: str | None = None
    division_id: str | None = None
    department_id: str | None = None
    type: str | None = None
    script: list[ScriptSentence] | None = None
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


class StartAudioSimulationPreviewRequest(BaseModel):
    user_id: str
    sim_id: str


class FetchSimulationsRequest(BaseModel):
    user_id: str


class CreateModuleRequest(BaseModel):
    user_id: str
    module_name: str
    tags: list[str]
    simulations: list[str]


class FetchModulesRequest(BaseModel):
    user_id: str


class AddedObject(BaseModel):
    type: str
    id: str


class CreateTrainingPlanRequest(BaseModel):
    user_id: str
    training_plan_name: str
    tags: list[str]
    added_object: list[AddedObject]


class FetchTrainingPlansRequest(BaseModel):
    user_id: str


# New request models
class ListItemsRequest(BaseModel):
    user_id: str


class CreateAssignmentRequest(BaseModel):
    id: str
    user_id: str
    name: str
    type: str
    start_date: str
    end_date: str
    team_id: list[str] = []
    trainee_id: list[str] = []
