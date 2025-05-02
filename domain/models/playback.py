from typing import List, Optional
from pydantic import BaseModel

class WordTimestampModel(BaseModel):
    word: str
    start: float
    end: float

class TranscriptSegmentModel(BaseModel):
    role: str
    content: str
    words: List[WordTimestampModel]

class KeywordAnalysisModel(BaseModel):
    spokenSentence: str
    scriptSentence: str
    role: str
    simAccuracy: float
    keywordScore: float
    hitKeywordArray: List[str]
    missedKeywordArray: List[str]

class AttemptAnalyticsModel(BaseModel):
    id: str;
    sentencewiseAnalytics: List[KeywordAnalysisModel]
    audioUrl: str
    transcript: str
    transcriptObject: List[TranscriptSegmentModel]
    timeTakenSeconds: int
    clickScore: float
    textFieldKeywordScore: float
    keywordScore: float
    simAccuracyScore: float
    confidence: float
    energy: float
    concentration: float
    minPassingScore: float
    name: str
    completedAt: str
    type: str
    simLevel: str

class SimulationAttemptModel(BaseModel):
    id: str
    trainingPlan: str
    moduleName: str
    simId: str
    simName: str
    simType: str
    simLevel: str
    score: float
    status: str
    timeTaken: int
    dueDate: Optional[str]
    attemptType: str
    estTime: int
    attemptCount: int

class SimulationAttemptDetailModel(BaseModel):
    id: str
    assignmentId: str
    type: str
    simulationId: str
    status: str
    score: str
    createdAt: str
    lastModifiedAt: str
    estTime: str
   