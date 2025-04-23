from typing import Dict, Optional
from datetime import datetime
from bson import ObjectId
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings, )
from config import (AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_KEY,
                    AZURE_OPENAI_BASE_URL)
from infrastructure.database import Database
from fastapi import HTTPException

from utils.logger import Logger  # <-- Import your custom logger

logger = Logger.get_logger(__name__)


class ChatService:

    def __init__(self):
        self.db = Database()
        logger.info("ChatService initialized.")

        # Initialize Azure OpenAI chat completion
        self.kernel = Kernel()
        self.chat_completion = AzureChatCompletion(
            service_id="azure_gpt4",
            deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
            endpoint=AZURE_OPENAI_BASE_URL,
            api_key=AZURE_OPENAI_KEY,
        api_version="2025-01-01-preview")
        self.kernel.add_service(self.chat_completion)
        self.execution_settings = AzureChatPromptExecutionSettings(
            service_id="azure_gpt4",
            ai_model_id=AZURE_OPENAI_DEPLOYMENT_NAME,
            temperature=0.7,
            top_p=1.0,
            max_tokens=2000)
        logger.info(
            "Azure OpenAI chat completion initialized for ChatService.")

    async def start_chat(self,
                         user_id: str,
                         sim_id: str,
                         message: Optional[str] = None) -> Dict[str, str]:
        """Start a new chat session"""
        logger.info("Starting a new chat session.")
        logger.debug(
            f"user_id={user_id}, sim_id={sim_id}, initial_message={message}")
        try:
            sim_id_object = ObjectId(sim_id)
            simulation = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation:
                logger.warning(f"Simulation with id {sim_id} not found.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            prompt = simulation.get("prompt")
            if not prompt:
                logger.warning(
                    f"Simulation {sim_id} does not have a prompt configured.")
                raise HTTPException(
                    status_code=400,
                    detail="Simulation does not have a prompt configured")

            history = ChatHistory()
            system_message = (
                "You are an AI assistant trained to simulate a customer service scenario. "
                "Here is your context and behavior guideline:\n\n"
                f"{prompt}\n\n"
                "Respond naturally as per this context. Be consistent with the scenario "
                "and maintain the appropriate tone and style.")
            history.add_system_message(system_message)
            logger.debug(
                f"System message added to chat history: {system_message}")

            response = None
            if message:
                logger.debug(
                    "Initial user message detected, requesting AzureChatCompletion."
                )
                history.add_user_message(message)
                response = await self.chat_completion.get_chat_message_content(
                    history, settings=self.execution_settings)

            logger.info("Chat session started successfully.")
            return {"response": str(response) if response else ""}
        except HTTPException as he:
            logger.error(f"HTTP error in start_chat: {str(he.detail)}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error starting chat: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error starting chat: {str(e)}")

    async def send_message(self, chat_id: str, message: str) -> str:
        """Send a message in an existing chat session"""
        logger.info(f"Sending message to chat session {chat_id}.")
        logger.debug(f"Message content: {message}")
        try:
            chat_id_object = ObjectId(chat_id)
            chat_session = await self.db.chat_sessions.find_one(
                {"_id": chat_id_object})
            if not chat_session:
                logger.warning(f"Chat session with id {chat_id} not found.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Chat session with id {chat_id} not found")

            # Recreate chat history
            history = ChatHistory()
            for msg in chat_session["history"]:
                if msg["role"] == "system":
                    history.add_system_message(msg["content"])
                elif msg["role"] == "assistant":
                    history.add_assistant_message(msg["content"])
                elif msg["role"] == "user":
                    history.add_user_message(msg["content"])

            # Add new message
            history.add_user_message(message)
            logger.debug(
                "New user message added to history. Requesting AzureChatCompletion..."
            )

            # Get response
            response = await self.chat_completion.get_chat_message_content(
                history, settings=self.execution_settings)
            logger.debug(f"AzureChatCompletion returned: {response}")

            # Add assistant response to history
            history.add_assistant_message(str(response))

            # Update chat session
            await self.db.chat_sessions.update_one({"_id": chat_id_object}, {
                "$set": {
                    "history": [msg.dict() for msg in history.messages],
                    "lastModifiedAt": datetime.utcnow()
                }
            })
            logger.info(
                f"Message sent to chat session {chat_id} successfully.")

            return str(response)
        except HTTPException as he:
            logger.error(f"HTTP error in send_message: {str(he.detail)}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error sending message: {str(e)}")
