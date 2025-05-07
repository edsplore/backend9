from domain.services.azure_ai_llm_service import AzureAILLMService
from infrastructure.database import Database
from fastapi import HTTPException
import json
from api.schemas.responses import (KeywordScoreAnalysisScript, KeywordScoreAnalysisWithScriptResponse,
ContextualScoreAnalysisScript, ContextualScoreAnalysisWithScriptResponse, BehaviouralScoreAnalysis,
ChatTypeScoreResponse)
from typing import List
import math
import domain.utils.constants as constants

from utils.logger import Logger
logger = Logger.get_logger(__name__)

class ScoringService:
    def __init__(self):
        try:
            self.db = Database()
            logger.info("ScoringService initialized.")
        except Exception as e:
            logger.error("Failed to initialize database for ScoringService.")
            logger.exception(e)

    def clean_llm_response_string(self, response_string: str):
        return response_string.strip("`").replace("```json", "").replace("```", "").strip()

    def convert_string_to_response_dict(self, response_string: str):
        try:
            return json.loads(response_string)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response string.")
            return {}

    def get_keyword_analysis_response(self, keyword_analysis_list: List[KeywordScoreAnalysisScript]):
        try:
            if keyword_analysis_list:
                total_keywords = 0
                missing_keywords = 0
                for entry in keyword_analysis_list:
                    if entry.role == "Trainee" and entry.keyword_analysis:
                        total_keywords += entry.keyword_analysis.total_keywords
                        missing_keywords += entry.keyword_analysis.missing_keywords
            
                keyword_analysis_response = KeywordScoreAnalysisWithScriptResponse(
                    script=keyword_analysis_list,
                    total_keywords=total_keywords,
                    total_missing_keywords=missing_keywords,
                    keyword_score=math.ceil(((total_keywords - missing_keywords) / total_keywords) * 100)
                )
                return keyword_analysis_response
            else:
                return KeywordScoreAnalysisWithScriptResponse(
                    script=keyword_analysis_list,
                    total_keywords=0,
                    total_missing_keywords=0,
                    keyword_score=0
                )
        except Exception as e:
            logger.error("Failed to get keyword analysis response.")
            return KeywordScoreAnalysisWithScriptResponse(
                    script=keyword_analysis_list,
                    total_keywords=0,
                    total_missing_keywords=0,
                    keyword_score=0
                )
    
    async def get_keyword_score_analysis(self, inputScript, transcript)-> KeywordScoreAnalysisWithScriptResponse:
        try:
            system_message = constants.SYSTEM_PROMPT_KEYWORD_SCORING
            user_prompt = (
                "Here is the Input Original Script:\n"
                "{original_script}\n\n"
                "And here is the Input Transcript:\n"
                "{transcript}\n\n"
                "Please analyze the transcript against the original script based on the instructions provided earlier and give me the keywords analysis."
            )
            script_text = "[\n" + ",\n".join(
                json.dumps({
                    "role": each_sentence["role"],
                    "script_sentence": each_sentence["script_sentence"],
                    "keywords": [keyword["text"] for keyword in each_sentence["keywords"]]
                }, indent=2)
                for each_sentence in inputScript
            ) + "\n]"
            user_prompt = user_prompt.format(original_script=script_text, transcript=transcript)
            llm_service = AzureAILLMService(system_message)
            response = await llm_service.get_chat_completion(user_prompt)
            response_cleaned = self.clean_llm_response_string(str(response))
            response_object = self.convert_string_to_response_dict(response_cleaned)
            keyword_score_analysis_list: List[KeywordScoreAnalysisScript] = [KeywordScoreAnalysisScript(**entry) for entry in response_object]
            return self.get_keyword_analysis_response(keyword_score_analysis_list)
        except Exception as e:
            logger.error("Failed to calculate keyword score for attempt.")
            logger.exception(e)
            raise HTTPException(status_code=500, detail="Failed to calculate keyword score for attempt.")

    def get_context_score_response(self, context_score_analysis_list: List[ContextualScoreAnalysisScript])-> ContextualScoreAnalysisWithScriptResponse:
        try:
            if context_score_analysis_list:
                total_contextual_accuracy = 0
                trainee_script_count = 0
                for entry in context_score_analysis_list:
                    if entry.role == "Trainee":
                        trainee_script_count += 1
                        if entry.contextual_accuracy:
                            total_contextual_accuracy += entry.contextual_accuracy
                
                context_score_analysis_response = ContextualScoreAnalysisWithScriptResponse(
                    script=context_score_analysis_list,
                    overall_contextual_accuracy=math.ceil(total_contextual_accuracy / trainee_script_count)
                )
                return context_score_analysis_response
            else:
                return ContextualScoreAnalysisWithScriptResponse(
                    script=context_score_analysis_list,
                    overall_contextual_accuracy=0
                )
        except Exception as e:
            logger.error("Failed to get context score analysis with script response.")
            return ContextualScoreAnalysisWithScriptResponse(
                    script=context_score_analysis_list,
                    overall_contextual_accuracy=0
                )
    
    async def get_context_score_analysis(self, inputScript, transcript)-> ContextualScoreAnalysisWithScriptResponse:
        try:
            system_message = constants.SYSTEM_MESSAGE_CONTEXT_ACCURACY
            user_prompt = (
                "Here is the Input Original Script:\n"
                "{original_script}\n\n"
                "And here is the Input Transcript:\n"
                "{transcript}\n\n"
                "Analyze the Transcript against the Original Script based on the instructions provided earlier and give me the contextual score analysis."
            )
            script_text = "\n".join(
                f'{each_sentence["role"]}: {each_sentence["script_sentence"]}'
                for each_sentence in inputScript
            )
            user_prompt = user_prompt.format(original_script=script_text, transcript=transcript)
            llm_service = AzureAILLMService(system_message)
            response = await llm_service.get_chat_completion(user_prompt)
            response_cleaned = self.clean_llm_response_string(str(response))
            response_object = self.convert_string_to_response_dict(response_cleaned)
            context_score_analysis_list: List[ContextualScoreAnalysisScript] = [ContextualScoreAnalysisScript(**entry) for entry in response_object]
            return self.get_context_score_response(context_score_analysis_list)
        except Exception as e:
            logger.error("Failed to calculate context accuracy.")
            logger.exception(e)
            raise HTTPException(status_code=500, detail="Failed to calculate context accuracy.")

    async def get_behavioural_score_analysis(self, inputScript, transcript):
        try:
            system_message = constants.SYSTEM_MESSAGE_BEHAVIOURAL_SCORING
            user_prompt = (
                "Here is the Original Script Conversation:\n"
                "{original_script}\n\n"
                "And here is the Actual Script Conversation:\n"
                "{transcript}\n\n"
                "Please analyze the Actual Script Conversation against the Original Script Conversation based on the instructions provided earlier and give me the behavioural score analysis."
            )
            script_text = "\n".join(
                f'{each_sentence["role"]}: {each_sentence["script_sentence"]}'
                for each_sentence in inputScript
            )
            user_prompt = user_prompt.format(original_script=script_text, transcript=transcript)
            llm_service = AzureAILLMService(system_message)
            response = await llm_service.get_chat_completion(user_prompt)
            response_cleaned = self.clean_llm_response_string(str(response))
            response_object = self.convert_string_to_response_dict(response_cleaned)
            behavioural_score_analysis_list: BehaviouralScoreAnalysis = BehaviouralScoreAnalysis(**response_object)
            return behavioural_score_analysis_list
        except Exception as e:
            logger.error("Failed to calculate behavioural score for attempt.")
            logger.exception(e)
            raise HTTPException(status_code=500, detail="Failed to calculate behavioural score for attempt.")
    
    async def calculate_attempt_scores_chat_type(self, inputScript = None, transcript = None):
        try:  
            keyword_score_analysis: KeywordScoreAnalysisWithScriptResponse = await self.get_keyword_score_analysis(constants.testInputScript, constants.testScoringTranscript2)
            context_score_analysis: ContextualScoreAnalysisWithScriptResponse = await self.get_context_score_analysis(constants.testInputScript, constants.testScoringTranscript2)
            behavioural_score_analysis: BehaviouralScoreAnalysis = await self.get_behavioural_score_analysis(constants.testInputScript, constants.testScoringTranscript2)
            chat_score_analysis: ChatTypeScoreResponse = ChatTypeScoreResponse(
                keyword_accuracy=keyword_score_analysis,
                contextual_accuracy=context_score_analysis,
                confidence_accuracy=getattr(behavioural_score_analysis, 'confidence_score', None),
                concentration_accuracy=getattr(behavioural_score_analysis, 'concentration_score', None),
                energy_accuracy=getattr(behavioural_score_analysis, 'energy_score', None)
            )
            return chat_score_analysis
            
        except Exception as e:
            logger.error("Failed to get chat simulation score analysis for attempt.")
            logger.exception(e)
            raise HTTPException(status_code=500, detail="Failed to get chat simulation score analysis for attempt.")
        
                                
    