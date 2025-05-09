from typing import Optional, List, Literal
from pydantic import BaseModel

from pydantic import BaseModel
from typing import Optional, List, Literal, Union


class CoordinatesModel(BaseModel):
    x: float
    y: float
    width: float
    height: float


class SettingsModel(BaseModel):
    timeoutDuration: int
    highlightColor: Optional[str] = None
    font: Optional[str] = None
    fontSize: Optional[int] = None
    buttonColor: Optional[str] = None
    textColor: Optional[str] = None
    highlightField: Optional[bool] = None
    enableHotkey: Optional[bool] = None
    placeholder: Optional[str] = None


class WrongClickModel(BaseModel):
    x_cordinates: float
    y_cordinates: float


class AttemptModel(BaseModel):
    id: str
    type: Literal["hotspot", "message"]
    name: Optional[str] = None
    role: Optional[str] = None
    hotspotType: Optional[Literal["button", "textfield", 'dropdown']] = None
    coordinates: Optional[CoordinatesModel] = None
    text: Optional[str] = None
    userText: Optional[str] = None
    userMessageId: Optional[str] = None
    timestamp: Optional[str] = None
    options: Optional[List] = None
    settings: Optional[SettingsModel] = None
    wrong_clicks: Optional[List[WrongClickModel]] = None
    isClicked: Optional[bool] = None
    userInput: Optional[str] = None

