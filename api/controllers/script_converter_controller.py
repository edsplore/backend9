from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Dict, List
from domain.services.script_converter_service import ScriptConverterService
from api.schemas.requests import AudioToScriptRequest, TextToScriptRequest, FileToScriptRequest
from api.schemas.responses import ScriptResponse

router = APIRouter()

class ScriptConverterController:
    def __init__(self):
        self.service = ScriptConverterService()

    async def convert_audio_to_script(self, user_id: str, audio_file: UploadFile) -> ScriptResponse:
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not audio_file:
            raise HTTPException(status_code=400, detail="Missing audio file")

        # Validate audio file type
        print(audio_file.content_type)
        # if not audio_file.content_type.startswith('audio/'):
        #     raise HTTPException(status_code=400, detail="File must be an audio file")

        script = await self.service.convert_audio_to_script(user_id, audio_file)
        return ScriptResponse(script=script)

    async def convert_text_to_script(self, user_id: str, prompt: str) -> ScriptResponse:
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not prompt:
            raise HTTPException(status_code=400, detail="Missing 'prompt'")

        script = await self.service.convert_text_to_script(user_id, prompt)
        return ScriptResponse(script=script)

    async def convert_file_to_script(self, user_id: str, file: UploadFile) -> ScriptResponse:
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not file:
            raise HTTPException(status_code=400, detail="Missing file")

        # Validate file type (e.g., txt, doc, pdf)
        allowed_types = ['text/plain', 'application/pdf', 'application/msword', 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        script = await self.service.convert_file_to_script(user_id, file)
        return ScriptResponse(script=script)

controller = ScriptConverterController()

@router.post("/convert/audio-to-script")
async def audio_to_script(
    user_id: str = Form(...),
    audio_file: UploadFile = File(...)
) -> ScriptResponse:
    return await controller.convert_audio_to_script(user_id, audio_file)

@router.post("/convert/text-to-script")
async def text_to_script(request: TextToScriptRequest) -> ScriptResponse:
    return await controller.convert_text_to_script(request.user_id, request.prompt)

@router.post("/convert/file-to-script")
async def file_to_script(
    user_id: str = Form(...),
    file: UploadFile = File(...)
) -> ScriptResponse:
    return await controller.convert_file_to_script(user_id, file)