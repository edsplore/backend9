from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Dict, List
from domain.services.script_converter_service import ScriptConverterService
from api.schemas.requests import AudioToScriptRequest, TextToScriptRequest, FileToScriptRequest
from api.schemas.responses import ScriptResponse

from utils.logger import Logger

logger = Logger.get_logger(__name__)

router = APIRouter()


class ScriptConverterController:

    def __init__(self):
        self.service = ScriptConverterService()
        logger.info("ScriptConverterController initialized.")

    async def convert_audio_to_script(
            self, user_id: str, audio_file: UploadFile) -> ScriptResponse:
        logger.info("Received request to convert audio to script.")
        logger.debug(
            f"user_id: {user_id}, filename: {audio_file.filename if audio_file else 'None'}"
        )

        try:

            script = await self.service.convert_audio_to_script(
                user_id, audio_file)
            logger.info(
                f"Successfully converted audio to script for user_id: {user_id}"
            )
            return ScriptResponse(script=script)
        except Exception as e:
            logger.error(f"Error converting audio to script: {str(e)}",
                         exc_info=True)
            raise

    async def convert_text_to_script(self, user_id: str,
                                     prompt: str) -> ScriptResponse:
        logger.info("Received request to convert text to script.")
        logger.debug(f"user_id: {user_id}, prompt: {prompt[:50]}...")

        try:

            script = await self.service.convert_text_to_script(user_id, prompt)
            logger.info(
                f"Successfully converted text to script for user_id: {user_id}"
            )
            return ScriptResponse(script=script)
        except Exception as e:
            logger.error(f"Error converting text to script: {str(e)}",
                         exc_info=True)
            raise

    async def convert_file_to_script(self, user_id: str,
                                     file: UploadFile) -> ScriptResponse:
        logger.info("Received request to convert file to script.")
        logger.debug(
            f"user_id: {user_id}, filename: {file.filename if file else 'None'}"
        )

        try:

            script = await self.service.convert_file_to_script(user_id, file)
            logger.info(
                f"Successfully converted file to script for user_id: {user_id}"
            )
            return ScriptResponse(script=script)
        except Exception as e:
            logger.error(f"Error converting file to script: {str(e)}",
                         exc_info=True)
            raise

    async def convert_audio_to_text(self, user_id: str,
                                    audio_file: UploadFile) -> Dict[str, str]:
        """Convert audio to text using Deepgram"""
        logger.info("Received request to convert audio to text.")
        logger.debug(
            f"user_id: {user_id}, filename: {audio_file.filename if audio_file else 'None'}"
        )

        try:
            audio_content = await audio_file.read()
            transcript = await self.service.deepgram_plugin.transcribe_audio_visual(
                audio_content)
            logger.info(
                f"Successfully converted audio to text for user_id: {user_id}")
            return {"text": transcript}
        except Exception as e:
            logger.error(f"Error converting audio to text: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error converting audio to text: {str(e)}")


controller = ScriptConverterController()


@router.post("/convert/audio-to-script", tags=["Script", "Create", "Audio"])
async def audio_to_script(user_id: str = Form(...),
                          audio_file: UploadFile = File(
                              ...)) -> ScriptResponse:
    return await controller.convert_audio_to_script(user_id, audio_file)


@router.post("/convert/text-to-script", tags=["Script", "Create", "Prompt"])
async def text_to_script(request: TextToScriptRequest) -> ScriptResponse:
    return await controller.convert_text_to_script(request.user_id,
                                                   request.prompt)


@router.post("/convert/file-to-script", tags=["Script", "Create", "File"])
async def file_to_script(user_id: str = Form(...),
                         file: UploadFile = File(...)) -> ScriptResponse:
    return await controller.convert_file_to_script(user_id, file)


@router.post("/convert/audio-to-text", tags=["Script", "Create", "Audio"])
async def audio_to_text(user_id: str = Form(...),
                        audio_file: UploadFile = File(...)) -> Dict[str, str]:
    """Convert audio to text using Deepgram"""
    return await controller.convert_audio_to_text(user_id, audio_file)
