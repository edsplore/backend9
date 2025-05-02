from domain.services.azure_ai_llm_service import AzureAILLMService
from infrastructure.database import Database
from fastapi import HTTPException
import json
from api.schemas.responses import (KeywordScoreAnalysisScript, KeywordScoreAnalysisWithScriptResponse)
from typing import List
import math

from utils.logger import Logger
logger = Logger.get_logger(__name__)


SYSTEM_MESSAGE_KEYWORD_SCORING = (
    "You are an AI tasked with analyzing a customer service training conversation."
    "You will receive two inputs: \n\n"
    "1. Input Original Script: A structured set of lines, each representing one turn in the expected conversation. "
    "Each line has a role (either 'Trainee' or 'Customer') and an object with two fields: "
    "'script_sentence' (the exact sentence expected to be spoken) and 'keywords' (a list of keyword strings that are guaranteed to be present in the script_sentence). \n"
    "Example: \n"
    "{\n"
    "  \"Trainee\": {\"script_sentence\": \"How are you feeling today?\", \"keywords\": [\"feeling\", \"today\"]},\n"
    "  \"Customer\": {\"script_sentence\": \"I'm feeling a bit dizzy.\", \"keywords\": []}\n"
    "}\n\n"
    "2. Input Transcript: A single string simulating a real training session where the Trainee and Customer interact. "
    "Each line is prefixed with the role (e.g., 'Trainee:' or 'Customer:') followed by the sentence spoken. "
    "Example: \n"
    "\"Trainee: How are you feeling?\\nCustomer: I'm feeling a bit dizzy.\"\n\n"
    "Your task is to analyze only the Trainee's lines from the transcript. For each Trainee sentence, match it with the corresponding 'script_sentence' in the Original Script (order is always the same). "
    "Check which of the expected keywords are present in the spoken sentence. Matches must be case-insensitive and based on exact whole words (not partial substrings). \n"
    "For each matched Trainee line, return an object with the following fields:\n"
    "- 'role': the value 'Trainee'\n"
    "- 'script_sentence': the actual spoken sentence from the transcript\n"
    "- 'keyword_analysis': an object with:\n"
    "  - 'total_keywords': total number of keywords from the original script\n"
    "  - 'missing_keywords': number of keywords that were not present in the spoken sentence\n"
    "  - 'missing_keywords_list': list of the missing keywords\n\n"
    "For each Customer line, return an object with:\n"
    "- 'role': the value 'Customer'\n"
    "- 'script_sentence': the spoken sentence from the transcript\n"
    "- 'keywords': an empty object {}\n\n"
    "STRICT RULE - The final output must be a JSON array in the exact order as the transcript. "
    "STRICT RULE - Do not wrap the output in markdown or backticks. Only return a raw JSON array with no extra text or formatting.\n\n"
    "Example Output: \n"
    "[\n"
    "  {\n"
    "    \"role\": \"Trainee\",\n"
    "    \"script_sentence\": \"How are you feeling?\",\n"
    "    \"keyword_analysis\": {\n"
    "      \"total_keywords\": 2,\n"
    "      \"missing_keywords\": 1,\n"
    "      \"missing_keywords_list\": [\"today\"]\n"
    "    }\n"
    "  },\n"
    "  {\n"
    "    \"role\": \"Customer\",\n"
    "    \"script_sentence\": \"I'm feeling a bit dizzy.\",\n"
    "    \"keywords\": {}\n"
    "  }\n"
    "]"
)

class ScoringService:
    def __init__(self):
        try:
            self.db = Database()
            logger.info("ScoringService initialized.")
        except Exception as e:
            logger.error("Failed to initialize database for ScoringService.")
            logger.exception(e)
    
    async def get_keyword_score_analysis(self, inputScript, transcript)-> KeywordScoreAnalysisWithScriptResponse:
        try:
            system_message = SYSTEM_MESSAGE_KEYWORD_SCORING
            user_prompt = (
                "Here is the Input Original Script:\n"
                "{original_script}\n\n"
                "And here is the Input Transcript:\n"
                "{transcript}\n\n"
                "Please analyze the transcript against the original script based on the instructions provided earlier and give me the keywords analysis."
            )
            script_text = "\n".join(
                f'{each_sentence["role"]}: {{"script_sentence": "{each_sentence["script_sentence"]}", keywords: {[keyword["text"] for keyword in each_sentence["keywords"]]}}}'
                for each_sentence in inputScript
            )
            script_text += "{\n" + script_text + "\n}"
            user_prompt = user_prompt.format(original_script=script_text, transcript=transcript)
            llm_service = AzureAILLMService(system_message)
            response = await llm_service.get_chat_completion(user_prompt)
            response_cleaned = self.clean_llm_response_string(str(response))
            response_object = self.convert_string_to_response_dict(response_cleaned)
            keyword_score_analysis_list: List[KeywordScoreAnalysisScript] = [KeywordScoreAnalysisScript(**entry) for entry in response_object]
            return self.get_keyword_analysis_with_script_response(keyword_score_analysis_list)
        except Exception as e:
            logger.error("Failed to calculate keyword score for attempt.")
            logger.exception(e)
            raise HTTPException(status_code=500, detail="Failed to calculate keyword score for attempt.")

    def clean_llm_response_string(self, response_string: str):
        return response_string.strip("`").replace("```json", "").replace("```", "").strip()

    def convert_string_to_response_dict(self, response_string: str):
        try:
            return json.loads(response_string)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response string.")
            return {}

    def get_keyword_analysis_with_script_response(self, keyword_analysis_list: List[KeywordScoreAnalysisScript]):
        try:
            if keyword_analysis_list:
                total_keywords = 0
                missing_keywords = 0
                for entry in keyword_analysis_list:
                    if entry.role == "Trainee":
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
            logger.error("Failed to get keyword analysis with script response.")
            return KeywordScoreAnalysisWithScriptResponse(
                    script=keyword_analysis_list,
                    total_keywords=0,
                    total_missing_keywords=0,
                    keyword_score=0
                )

    async def calculate_attempt_scores_chat_type(self, inputScript = None, transcript = None):
        try:
            testInputScript = [
                {
                "role": "Trainee",
                "script_sentence": "Thank you for calling Sunshine Pharmacy. My name is Sarah, and I’m here to assist you with your prescription needs. This call may be recorded for quality and training purposes. Before we proceed, may I have your full name, please?",
                "keywords": [
                    {
                    "text": "Sunshine Pharmacy",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    },
                    {
                    "text": "prescription",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    },
                    {
                    "text": "quality",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    },
                    {
                    "text": "training purposes",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    },
                    {
                    "text": "full name",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "customer",
                "script_sentence": "<p>Hi, Sarah. This is Emily Johnson.</p>",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "Trainee",
                "script_sentence": "Thank you, Ms. Johnson. To ensure the privacy and security of your health information in accordance with HIPAA regulations, I need to verify your identity. Can you please provide your date of birth and the phone number associated with your pharmacy account?",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "customer",
                "script_sentence": "<p>My date of birth is April 15, 1985, and my phone number is 555-123-4567.</p>",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "Trainee",
                "script_sentence": "Thank you. Let me verify that information. Your information matches our records. How may I assist you with your prescription today?",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "customer",
                "script_sentence": "<p>I need to check the status of a prescription and see if I can get it refilled.</p>",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "Trainee",
                "script_sentence": "I’d be happy to help with that. Can you please provide the prescription number, or if you don’t have it, the name of the medication and the prescribing physician?",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "customer",
                "script_sentence": "<p>I don’t have the prescription number, but the medication is Lisinopril, 10 mg, and it was prescribed by Dr. Michael Carter.</p>",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "Trainee",
                "script_sentence": "Thank you, Ms. Johnson. Let me look up that prescription. I’ve found your prescription for Lisinopril, 10 mg, prescribed by Dr. Michael Carter. It looks like you have one refill remaining, and the prescription is eligible for fulfillment. Would you like me to process the refill for you today?",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "customer",
                "script_sentence": "<p>Yes, please. Can you tell me when it will be ready?</p>",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "Trainee",
                "script_sentence": "Certainly. I’m processing the refill now. It should be ready for pickup at Sunshine Pharmacy by 3",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "customer",
                "script_sentence": "<p>I’d like delivery, please.</p>",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "Trainee",
                "script_sentence": "Great. Let me confirm your delivery address. Our records show your address as 123 Maple Street, Apartment 4B, Springfield, IL 62701. Is that correct?",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "customer",
                "script_sentence": "<p>Yes, that’s correct.</p>",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "Trainee",
                "script_sentence": "Perfect. The medication will be delivered to that address by tomorrow afternoon. You’ll receive a confirmation call or text when it’s on its way. The cost for the Lisinopril refill is $15. Would you like to use the card on file ending in 1234, or would you prefer another payment method?",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "customer",
                "script_sentence": "<p>The card on file is fine.</p>",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "Trainee",
                "script_sentence": "Thank you. I’ve processed the payment, and the refill order is confirmed. Before we conclude, I need to provide a few important reminders",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "customer",
                "script_sentence": "<p>No, that’s all. Thank you, Sarah.</p>",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "Trainee",
                "script_sentence": "You’re very welcome, Ms. Johnson. Thank you for choosing Sunshine Pharmacy. Have a great day!",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                },
                {
                "role": "customer",
                "script_sentence": "<p>You too. Goodbye.</p>",
                "keywords": [
                    {
                    "text": "",
                    "selectionIndex": "0",
                    "selectionLength": "0"
                    }
                ]
                }
            ]
            testTranscript = (
                "Trainee: Thank you for calling Sunshine Pharmacy. My name is Sarah, and I’m here to assist you with your prescription needs. This call may be recorded for quality purposes. Before we proceed, may I have your name, please?\n"
                "Customer: Hi, Sarah. This is Emily Johnson.\n"
                "Trainee: Thank you, Ms. Johnson. To ensure the privacy and security of your health information in accordance with HIPAA regulations, I need to verify your identity. Can you please provide your date of birth and the phone number associated with your pharmacy account?\n"
                "Customer: My date of birth is April 15, 1985, and my phone number is 555-123-4567.\n"
                "Trainee: Thank you. Let me verify that information. Your information matches our records. How may I assist you with your prescription today?\n"
                "Customer: I need to check the status of a prescription and see if I can get it refilled.\n"
                "Trainee: I’d be happy to help with that. Can you please provide the prescription number, or if you don’t have it, the name of the medication and the prescribing physician?\n"
                "Customer: I don’t have the prescription number, but the medication is Lisinopril, 10 mg, and it was prescribed by Dr. Michael Carter.\n"
                "Trainee: Thank you, Ms. Johnson. Let me look up that prescription. I’ve found your prescription for Lisinopril, 10 mg, prescribed by Dr. Michael Carter. It looks like you have one refill remaining, and the prescription is eligible for fulfillment. Would you like me to process the refill for you today?\n"
                "Customer: Yes, please. Can you tell me when it will be ready?\n"
                "Trainee: Certainly. I’m processing the refill now. It should be ready for pickup at Sunshine Pharmacy by 3\n"
                "Customer: I’d like delivery, please.\n"
                "Trainee: Great. Let me confirm your delivery address. Our records show your address as 123 Maple Street, Apartment 4B, Springfield, IL 62701. Is that correct?\n"
                "Customer: Yes, that’s correct.\n"
                "Trainee: Perfect. The medication will be delivered to that address by tomorrow afternoon. You’ll receive a confirmation call or text when it’s on its way. The cost for the Lisinopril refill is $15. Would you like to use the card on file ending in 1234, or would you prefer another payment method?\n"
                "Customer: The card on file is fine.\n"
                "Trainee: Thank you. I’ve processed the payment, and the refill order is confirmed. Before we conclude, I need to provide a few important reminders\n"
                "Customer: No, that’s all. Thank you, Sarah.\n"
                "Trainee: You’re very welcome, Ms. Johnson. Thank you for choosing Sunshine Pharmacy. Have a great day!\n"
                "Customer: You too. Goodbye."
            )
            keyword_score_analysis: KeywordScoreAnalysisWithScriptResponse = await self.get_keyword_score_analysis(testInputScript, testTranscript)
            return keyword_score_analysis
            
        except Exception as e:
            logger.error("Failed to get keyword score analysis for attempt.")
            logger.exception(e)
            raise HTTPException(status_code=500, detail="Failed to get keyword score analysis for attempt.")
        
                                
    