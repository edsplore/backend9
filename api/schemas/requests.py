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

class ScriptSentence(BaseModel):
    script_sentence: str
    role: str  
    keywords: list[str]

class CreateSimulationRequest(BaseModel):
    user_id: str
    name: str
    division_id: str
    department_id: str
    type: str
    script: list[ScriptSentence]
    tags: list[str]
