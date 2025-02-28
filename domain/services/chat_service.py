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


class ChatService:

    def __init__(self):
        self.db = Database()

        # Initialize Azure OpenAI chat completion
        self.kernel = Kernel()
        self.chat_completion = AzureChatCompletion(
            service_id="azure_gpt4",
            deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
            endpoint=AZURE_OPENAI_BASE_URL,
            api_key=AZURE_OPENAI_KEY)
        self.kernel.add_service(self.chat_completion)
        self.execution_settings = AzureChatPromptExecutionSettings(
            service_id="azure_gpt4",
            ai_model_id=AZURE_OPENAI_DEPLOYMENT_NAME,
            temperature=0.7,
            top_p=1.0,
            max_tokens=2000)

    async def start_chat(self,
                         user_id: str,
                         sim_id: str,
                         message: Optional[str] = None) -> Dict[str, str]:
        """Start a new chat session"""
        try:
            # Get simulation
            sim_id_object = ObjectId(sim_id)
            simulation = await self.db.simulations.find_one(
                {"_id": sim_id_object})

            if not simulation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            # Get simulation prompt
            prompt = simulation.get("prompt")
            if not prompt:
                raise HTTPException(
                    status_code=400,
                    detail="Simulation does not have a prompt configured")

            # Create chat history
            history = ChatHistory()

            # Add system message with simulation prompt
            history.add_system_message(
                f"You are an AI assistant trained to simulate a customer service scenario. "
                f"Here is your context and behavior guideline:\n\n{prompt}\n\n"
                f"Respond naturally as per this context. Be consistent with the scenario "
                f"and maintain the appropriate tone and style.")

            # If initial message provided, process it
            response = None
            if message:
                history.add_user_message(message)
                response = await self.chat_completion.complete_chat(
                    history, settings=self.execution_settings)

            # Create chat session document
            chat_doc = {
                "userId": user_id,
                "simulationId": sim_id,
                "history": [msg.dict() for msg in history.messages],
                "createdAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }

            # Insert into database
            result = await self.db.chat_sessions.insert_one(chat_doc)

            return {
                "chat_id": str(result.inserted_id),
                "response": str(response) if response else ""
            }

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error starting chat: {str(e)}")

    async def send_message(self, chat_id: str, message: str) -> str:
        """Send a message in an existing chat session"""
        try:
            # Get chat session
            chat_id_object = ObjectId(chat_id)
            chat_session = await self.db.chat_sessions.find_one(
                {"_id": chat_id_object})

            if not chat_session:
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

            # Get response
            response = await self.chat_completion.complete_chat(
                history, settings=self.execution_settings)

            # Add response to history
            history.add_assistant_message(str(response))

            # Update chat session
            await self.db.chat_sessions.update_one({"_id": chat_id_object}, {
                "$set": {
                    "history": [msg.dict() for msg in history.messages],
                    "lastModifiedAt": datetime.utcnow()
                }
            })

            return str(response)

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error sending message: {str(e)}")
