from config import (AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_KEY, AZURE_OPENAI_BASE_URL)
from fastapi import HTTPException
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings)

from infrastructure.database import Database
from utils.logger import Logger
logger = Logger.get_logger(__name__)

class AzureAILLMService:
    def __init__(self, system_prompt: str):
        try:
            logger.info("AzureAILLMService initialized.")
            self.db = Database()
            self.system_prompt = system_prompt
            logger.debug("Initializing Semantic Kernel...")
            self.kernel = Kernel()

            logger.debug("Setting up AzureChatCompletion service...")
            self.chat_completion = AzureChatCompletion(
                service_id="azure_gpt4",
                deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
                endpoint=AZURE_OPENAI_BASE_URL,
                api_key=AZURE_OPENAI_KEY,
                api_version="2025-01-01-preview")

            logger.debug("Adding AzureChatCompletion to Kernel...")
            self.kernel.add_service(self.chat_completion)
            logger.info("AzureChatCompletion added to Kernel successfully.")

            logger.debug("Configuring execution settings...")
            self.execution_settings = AzureChatPromptExecutionSettings(
                service_id="azure_gpt4",
                ai_model_id=AZURE_OPENAI_DEPLOYMENT_NAME,
                temperature=0.1,
                top_p=1.0,
                max_tokens=4096)
            logger.info("Execution settings configured successfully.")

        except Exception as e:
            logger.error(
                "Error during Semantic Kernel or AzureChatCompletion setup.")
            logger.exception(e)

        logger.info("AzureAILLMService initialized.")
    
    @property
    def system_prompt(self):
        """Getter method for system_prompt"""
        return self._system_prompt
    
    @system_prompt.setter
    def system_prompt(self, _system_prompt):
        """Setter method for system_prompt"""
        self._system_prompt = _system_prompt

    def get_chat_completion(self, user_prompt: Optional[str] = None):
        try:
            history = ChatHistory()
            history.add_system_message(self.system_prompt)
            if user_prompt:
                history.add_user_message(user_prompt)
            return self.chat_completion.get_chat_message_content(history, settings=self.execution_settings)
        except Exception as e:
            logger.error("Error during chat completion.")
            logger.exception(e)
            raise HTTPException(status_code=500, detail="Error during chat completion.")
    