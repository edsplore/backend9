from pydantic import BaseModel

class TrainingDataRequest(BaseModel):
    user_id: str

class AttemptsRequest(BaseModel):
    user_id: str

class AttemptRequest(BaseModel):
    user_id: str
    attempt_id: str