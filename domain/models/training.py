from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

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

class TrainingDataModel(BaseModel):
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