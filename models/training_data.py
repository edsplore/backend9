from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class SimulationModel(BaseModel):
    simulation_id: str
    name: str
    type: str
    level: str
    est_time: int
    due_date: Optional[datetime]
    status: str
    highest_attempt_score: Optional[float] = None

class ModuleModel(BaseModel):
    id: str
    name: str
    total_simulations: int
    average_score: float
    due_date: Optional[datetime]
    status: str
    simulations: List[SimulationModel]

class TrainingPlanModel(BaseModel):
    id: str
    name: str
    completion_percentage: float
    total_modules: int
    total_simulations: int
    est_time: int
    average_sim_score: float
    due_date: Optional[datetime]
    status: str
    modules: List[ModuleModel]

class SimulationCompletionStats(BaseModel):
    total_simulations: int
    completed_simulations: int
    percentage: float

class TimelyCompletionStats(BaseModel):
    total_simulations: int
    completed_simulations: int
    percentage: float

class TrainingStats(BaseModel):
    simulation_completed: SimulationCompletionStats
    timely_completion: TimelyCompletionStats
    average_sim_score: float
    highest_sim_score: float

class TrainingDataResponse(BaseModel):
    training_plans: List[TrainingPlanModel]
    stats: TrainingStats