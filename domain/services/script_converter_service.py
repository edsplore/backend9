import json
import io
import docx
import PyPDF2
import aiohttp

from fastapi import UploadFile, HTTPException
from typing import List, Dict, Optional
from datetime import datetime

from config import (DEEPGRAM_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME,
                    AZURE_OPENAI_KEY, AZURE_OPENAI_BASE_URL)
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings, )
from domain.plugins.deepgram_plugin import DeepgramPlugin
from typing import List
from pydantic import BaseModel

from utils.logger import Logger  # Make sure the path is correct for your project

logger = Logger.get_logger(__name__)


class ScriptItem(BaseModel):
    role: str
    message: str


class MyResponseSchema(BaseModel):
    script: List[ScriptItem]


class ScriptConverterService:

    def __init__(self):
        logger.info("Initializing ScriptConverterService.")
        # Initialize Semantic Kernel
        self.kernel = Kernel()

        # Add Azure OpenAI service
        self.chat_completion = AzureChatCompletion(
            service_id="azure_gpt4",
            deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
            endpoint=AZURE_OPENAI_BASE_URL,
            api_key=AZURE_OPENAI_KEY,
            api_version="2025-01-01-preview")
        self.kernel.add_service(self.chat_completion)
        logger.info("Azure OpenAI service added to kernel.")

        # Add Deepgram plugin
        self.deepgram_plugin = DeepgramPlugin(DEEPGRAM_API_KEY)
        self.kernel.add_plugin(self.deepgram_plugin, "DeepgramPlugin")
        logger.info("Deepgram plugin added to kernel.")

        # Configure execution settings
        self.execution_settings = AzureChatPromptExecutionSettings(
            service_id="azure_gpt4",
            ai_model_id=AZURE_OPENAI_DEPLOYMENT_NAME,
            temperature=0.7,
            top_p=1.0,
            max_tokens=2000,
            response_format=MyResponseSchema)
        logger.info("ScriptConverterService initialized successfully.")

    async def convert_audio_to_script(
            self, user_id: str,
            audio_file: UploadFile) -> List[Dict[str, str]]:
        """
        Convert audio to script using Deepgram plugin.
        """
        logger.info("Converting audio to script.")
        logger.debug(
            f"user_id={user_id}, filename={audio_file.filename if audio_file else 'None'}"
        )
        try:
            audio_content = await audio_file.read()
            logger.debug("Audio file content read successfully.")

            transcribe_function = self.kernel.plugins["DeepgramPlugin"][
                "transcribe_audio"]
            transcript = await self.deepgram_plugin.transcribe_audio(
                audio_content)
            logger.debug(f"Transcript received from Deepgram: {transcript}")

            script_data = await self._convert_transcript_to_conversation_format(
                str(transcript))
            logger.info("Audio converted to conversation format successfully.")
            return script_data
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error processing audio: {str(e)}")

    async def convert_text_to_script(self, user_id: str,
                                     prompt: str) -> List[Dict[str, str]]:
        """
        Convert text to conversation script using Azure OpenAI.
        """
        logger.info("Converting text prompt to script.")
        logger.debug(f"user_id={user_id}, prompt_length={len(prompt)}")
        try:
            script_data = await self._convert_prompt_to_conversation_format(
                prompt)
            logger.info("Text converted to conversation format successfully.")
            return script_data
        except Exception as e:
            logger.error(f"Error converting text to script: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error converting text to script: {str(e)}")

    async def convert_file_to_script(self, user_id: str,
                                     file: UploadFile) -> List[Dict[str, str]]:
        """
        Convert file content to conversation script using Azure OpenAI.
        """
        logger.info("Converting file content to script.")
        logger.debug(
            f"user_id={user_id}, filename={file.filename if file else 'None'}")
        try:
            content = await self._extract_text_from_file(file)
            logger.debug("File content extracted successfully.")
            script_data = await self._convert_prompt_to_conversation_format(
                content)
            logger.info(
                "File content converted to conversation format successfully.")
            return script_data
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error processing file: {str(e)}")

    async def _extract_text_from_file(self, file: UploadFile) -> str:
        """
        Extract text content from different file types
        """
        logger.debug(
            f"Extracting text from file with content_type={file.content_type}")
        content = await file.read()
        try:
            if file.content_type == 'text/plain':
                text_data = content.decode('utf-8')
                logger.debug("Extracted text from plain text file.")
                return text_data
            elif file.content_type == 'application/pdf':
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                extracted_text = ' '.join(page.extract_text()
                                          for page in pdf_reader.pages)
                logger.debug("Extracted text from PDF.")
                return extracted_text
            elif file.content_type in [
                    'application/msword',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ]:
                doc_data = docx.Document(io.BytesIO(content))
                extracted_text = ' '.join(paragraph.text
                                          for paragraph in doc_data.paragraphs)
                logger.debug("Extracted text from Word document.")
                return extracted_text
            else:
                logger.warning(f"Unsupported file type: {file.content_type}")
                raise HTTPException(status_code=400,
                                    detail="Unsupported file type")
        except Exception as ex:
            logger.error(f"Error extracting text from file: {ex}",
                         exc_info=True)
            raise

    async def _convert_prompt_to_conversation_format(
            self, content: str) -> List[Dict[str, str]]:
        """
        Convert content to conversation format using Azure OpenAI
        """
        logger.info(
            "Converting prompt to conversation format via Azure OpenAI.")
        logger.debug(f"Prompt length: {len(content)}")
        try:
            history = ChatHistory()

            history.add_system_message(
                "Convert the following text into a natural conversation between a user and an assistant. "
                "Return the result as a JSON object with a 'script' array containing objects with 'role' and "
                "'message' fields. The conversation should flow naturally and make sense. There are only two "
                "roles 'Customer' and 'Trainee' in the conversation. The conversation should mostly start with the Trainee. "
                "Something like, 'Thanks for calling, how can I help you today?'"
            )
            history.add_user_message(content)
            logger.debug(
                f"Chat history created. System + user messages added: {history}"
            )

            result = await self.chat_completion.get_chat_message_content(
                history, settings=self.execution_settings)
            logger.debug(f"Azure OpenAI raw response: {result}")

            try:
                conversation = json.loads(str(result))
                script = conversation.get('script', [])
                logger.debug("Parsed JSON response from OpenAI successfully.")
                return script
            except json.JSONDecodeError as jde:
                logger.error("Failed to parse Azure OpenAI response.",
                             exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to parse Azure OpenAI response")
        except Exception as e:
            logger.error(f"Error converting to conversation format: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error converting to conversation format: {str(e)}")

    async def _convert_transcript_to_conversation_format(
            self, content: str) -> List[Dict[str, str]]:
        """
        Convert transcript to conversation format using Azure OpenAI
        """
        logger.info(
            "Converting transcript to conversation format via Azure OpenAI.")
        logger.debug(f"Transcript length: {len(content)}")
        try:
            history = ChatHistory()

            history.add_system_message(
                "Convert the following phoneCall transcript of two callers marked as Speaker 0 and Speaker 1 "
                "into a conversation between a Customer and Trainee. Return the result as a JSON object with "
                "a 'script' array containing objects with 'role' and 'message' fields. Also, do not add "
                "conversation from your end. As per transcript you can start conversation with either Customer "
                "or Trainee. Do not miss any important line from transcript.")
            history.add_user_message(content)
            logger.debug(f"Chat history created for transcript: {history}")

            result = await self.chat_completion.get_chat_message_content(
                history, settings=self.execution_settings)
            logger.debug(f"Azure OpenAI raw response for transcript: {result}")

            try:
                conversation = json.loads(str(result))
                script = conversation.get('script', [])
                logger.debug(
                    "Parsed JSON response from OpenAI for transcript successfully."
                )
                return script
            except json.JSONDecodeError as jde:
                logger.error(
                    "Failed to parse Azure OpenAI response for transcript.",
                    exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to parse Azure OpenAI response")
        except Exception as e:
            logger.error(f"Error converting transcript: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error converting to conversation format: {str(e)}")
