from typing import List, Optional
from pydantic import BaseModel

class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float

class TranscriptSegment(BaseModel):
    role: str
    content: str
    words: List[WordTimestamp]

class KeywordAnalysis(BaseModel):
    spokenSentence: str
    scriptSentence: str
    role: str
    simAccuracy: float
    keywordScore: float
    hitKeywordArray: List[str]
    missedKeywordArray: List[str]

class AttemptAnalytics(BaseModel):
    sentencewiseAnalytics: List[KeywordAnalysis]
    audioUrl: str
    transcript: str
    transcriptObject: List[TranscriptSegment]
    timeTakenSeconds: int
    clickScore: float
    textFieldKeywordScore: float
    keywordScore: float
    simAccuracyScore: float
    confidence: float
    energy: float
    concentration: float
    minPassingScore: float

class SimulationAttempt(BaseModel):
    attemptId: str
    trainingPlan: str
    moduleName: str
    simId: str
    simName: str
    simType: str
    simLevel: str
    score: float
    timeTaken: int
    dueDate: Optional[str]
    attemptType: str
    estTime: int
    attemptCount: int