from typing import Dict, List, Optional
from fastapi import HTTPException
import aiohttp
import json
import math
import re
import asyncio
import numpy as np
from datetime import datetime
from rank_bm25 import BM25Okapi
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import librosa
import pyworld as pw
import tempfile
import os

# Configuration - should be moved to config.py
QWEN_API_URL = "https://eu2simudal001.eastus2.cloudapp.azure.com/qwen/chat"
SBERT_SIMILARITY_URL = "https://eu2simudal001.eastus2.cloudapp.azure.com/sbert/similarity"
SBERT_ENCODE_URL = "https://eu2simudal001.eastus2.cloudapp.azure.com/sbert/encode"
SBERT_BATCH_SIMILARITY_URL = "https://eu2simudal001.eastus2.cloudapp.azure.com/sbert/batch_similarity"

from infrastructure.database import Database
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class AdvancedScoringService:
    # Configurable scoring thresholds and weights
    SCORING_CONFIG = {
        "confidence": {
            "information_accuracy": {
                "weight": 0.30,
                "bm25_threshold": 0.7,
                "normalization_factor": 15.0  # For BM25 score normalization
            },
            "speech_clarity": {
                "weight": 0.20,
                "enabled": True,
                "filler_words": [
                    "um", "uh", "er", "ah", "like", "you know", "sort of", "kind of",
                    "actually", "basically", "literally", "obviously", "seriously",
                    "honestly", "frankly", "personally", "generally", "totally",
                    "absolutely", "definitely", "probably", "supposedly", "apparently"
                ],
                # Scoring scale: (max_filler_words, max_pause_seconds, score)
                "scoring_scale": [
                    (2, 5, 80),    # 0-2 filler words, pause < 5 seconds = 80%
                    (5, 10, 60),   # 3-5 filler words, pause 5-10 seconds = 60%
                    (10, 15, 40),  # 6-10 filler words, pause 10-15 seconds = 40%
                    (15, 20, 20),  # 11-15 filler words, pause 15-20 seconds = 20%
                    (float('inf'), float('inf'), 10)  # More than 15 filler words or >20s pause = 10%
                ],
                "pause_threshold": 2.0,  # Minimum pause duration to be considered significant (seconds)
                "normal_pause_max": 3.0  # Normal conversation pause max (seconds)
            },
            "objection_handling": {
                "weight": 0.20,
                "enabled": True,
                "effectiveness_weight": 0.85,  # 85% for handling quality
                "timing_weight": 0.15,  # 15% for response time
                "sbert_objection_threshold": 0.7,  # Similarity threshold for objection detection
                "context_sentences_before": 2,  # Sentences to include before objection
                "context_sentences_after": 3,  # Sentences to include after objection
                "max_response_time": 10.0,  # Max response time for scoring (seconds)
                "ideal_response_time": 3.0,  # Ideal response time (seconds)
                # Common objection patterns to help SBERT identify objections
                "objection_patterns": [
                    "That's too expensive",
                    "I don't think this will work",
                    "I'm not sure about this",
                    "This seems complicated",
                    "I've had bad experience before",
                    "Your competitor offers better",
                    "I need to think about it",
                    "I don't have time for this",
                    "This is not what I expected",
                    "I'm not convinced",
                    "I have concerns about",
                    "But what if it doesn't work",
                    "I'm worried about"
                ]
            },
            "tone_volume": {
                "weight": 0.15,
                "enabled": True,
                "audio_required": True,  # Only works with audio files
                # Pitch variance scoring thresholds (standard deviation)
                "scoring_thresholds": {
                    "low_deviation": 50.0,    # Below this = 100% score
                    "medium_deviation": 100.0,  # Below this = 66% score
                    "high_deviation": 150.0,   # Below this = 33% score
                    # Above high_deviation = 10% score
                },
                "scores": {
                    "low": 100.0,
                    "medium": 66.0,
                    "high": 33.0,
                    "very_high": 10.0
                },
                # Audio processing parameters
                "sample_rate": 16000,  # Default sample rate for processing
                "hop_length": 256,     # Frame hop length for WORLD analysis
                "frame_period": 5.0,   # Frame period in milliseconds
                # Voice filtering parameters
                "min_f0": 70.0,        # Minimum F0 (pitch) in Hz
                "max_f0": 400.0,       # Maximum F0 (pitch) in Hz
                "voiced_threshold": 0.5  # Threshold for voiced detection
            },
            "consistency": {
                "weight": 0.15,
                "enabled": True,
                "analysis_prompt_template": """
                Analyze the following conversation for consistency in messaging and information provided by the agent/trainee.

                Evaluate these aspects:
                1. **Information Consistency**: Check if the agent provides contradictory information during the call
                2. **Solution Consistency**: Verify that multiple solutions or steps offered are coherent and don't conflict
                3. **Message Coherence**: Ensure the agent maintains consistent messaging throughout the conversation
                4. **Policy Adherence**: Check if the agent consistently follows the original script/policy guidelines

                Original Script:
                {original_script}

                Actual Conversation:
                {transcript}

                Rate the consistency on a scale of 0-100, where:
                - 90-100: Excellent consistency with no contradictions
                - 70-89: Good consistency with minor inconsistencies
                - 50-69: Moderate consistency with some contradictory information
                - 30-49: Poor consistency with multiple contradictions
                - 0-29: Very poor consistency with major contradictions

                Focus only on the agent/trainee responses. Ignore customer statements.

                **Important**: Provide ONLY a numeric score between 0 and 100. Do not include any explanation or additional text.
                """,
                "retry_attempts": 3,
                "timeout": 30,
                "default_score": 50.0  # Fallback score if analysis fails
            }
        },
        "bm25": {
            "top_score_percentage": 0.7,  # Use top 70% of scores
            "min_token_length": 2  # Minimum token length
        },
        "llm": {
            "timeout": 30,  # API timeout in seconds
            "retry_attempts": 3,
            "default_score": 50.0  # Fallback score if LLM fails
        }
    }

    def __init__(self):
        self.db = Database()
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')
        logger.info("AdvancedScoringService initialized.")

    async def calculate_confidence_score(self, original_script: List[Dict], transcript: str, user_simulation_progress_id: str, audio_url: Optional[str] = None, transcript_object: Optional[List[Dict]] = None, simulation_type: str = "audio") -> Dict[str, float]:
        """
        Calculate overall confidence score based on multiple components
        This method is designed to be called asynchronously without blocking the main workflow

        Args:
            original_script: List of script dictionaries with 'script_sentence', 'role', etc.
            transcript: The actual conversation transcript
            user_simulation_progress_id: ID to store results against
            audio_url: Optional URL to audio file for future analysis
            transcript_object: Optional transcript object with timing information (for audio simulations)
            simulation_type: Type of simulation ("audio", "chat", "visual-chat", etc.)

        Returns:
            Dictionary containing component scores and total confidence score
        """
        # Validate inputs
        if not original_script or not isinstance(original_script, list):
            logger.error(f"Invalid original_script provided: {type(original_script)}")
            await self._store_error(user_simulation_progress_id, "Invalid original script format")
            return self._get_default_scores()

        if not transcript or not isinstance(transcript, str):
            logger.error(f"Invalid transcript provided: {type(transcript)}")
            await self._store_error(user_simulation_progress_id, "Invalid transcript format")
            return self._get_default_scores()

        if not user_simulation_progress_id:
            logger.error("No user simulation progress ID provided")
            return self._get_default_scores()

        try:
            logger.info(f"Starting confidence score calculation for progress ID: {user_simulation_progress_id}")

            # Calculate information accuracy score (30%)
            info_accuracy_score = await self._calculate_information_accuracy(original_script, transcript)

            # Calculate speech clarity score (20%)
            speech_clarity_score = 0.0
            if self.SCORING_CONFIG["confidence"]["speech_clarity"]["enabled"]:
                speech_clarity_score = await self._calculate_speech_clarity(transcript, transcript_object, simulation_type)

            # Calculate objection handling score (20%)
            objection_handling_score = 0.0
            if self.SCORING_CONFIG["confidence"]["objection_handling"]["enabled"]:
                objection_handling_score = await self._calculate_objection_handling(
                    original_script, transcript, transcript_object, simulation_type
                )

            # Calculate tone and volume score (15%)
            tone_volume_score = 0.0
            if (self.SCORING_CONFIG["confidence"]["tone_volume"]["enabled"] and 
                simulation_type == "audio" and audio_url):
                tone_volume_score = await self._calculate_tone_volume(audio_url, transcript_object)

            # Calculate consistency score (15%)
            consistency_score = 0.0
            if self.SCORING_CONFIG["confidence"]["consistency"]["enabled"]:
                consistency_score = await self._calculate_consistency(original_script, transcript)

            # Calculate total confidence score with all implemented components
            scores = {
                "information_accuracy": info_accuracy_score,
                "speech_clarity": speech_clarity_score,
                "objection_handling": objection_handling_score,
                "tone_volume": tone_volume_score,
                "consistency": consistency_score,
                "total_confidence": (
                    info_accuracy_score * self.SCORING_CONFIG["confidence"]["information_accuracy"]["weight"] +
                    speech_clarity_score * self.SCORING_CONFIG["confidence"]["speech_clarity"]["weight"] +
                    objection_handling_score * self.SCORING_CONFIG["confidence"]["objection_handling"]["weight"] +
                    tone_volume_score * self.SCORING_CONFIG["confidence"]["tone_volume"]["weight"] +
                    consistency_score * self.SCORING_CONFIG["confidence"]["consistency"]["weight"]
                )
            }

            # Store the scores in the database asynchronously
            await self._store_confidence_scores(user_simulation_progress_id, scores)

            logger.info(f"Confidence score calculation completed for progress ID: {user_simulation_progress_id}")
            return scores

        except Exception as e:
            logger.error(f"Error calculating confidence score for progress ID {user_simulation_progress_id}: {str(e)}", exc_info=True)
            # Don't raise the exception since this is a background task
            # Store the error in database for later review
            await self._store_error(user_simulation_progress_id, f"Confidence score calculation failed: {str(e)}")
            return self._get_default_scores()

    def _get_default_scores(self) -> Dict[str, float]:
        """Return default scores when calculation fails"""
        return {
            "information_accuracy": 0.0,
            "speech_clarity": 0.0,
            "objection_handling": 0.0,
            "tone_volume": 0.0,
            "consistency": 0.0,
            "total_confidence": 0.0
        }

    def _preprocess_text(self, text: str) -> List[str]:
        """
        Preprocess text for BM25 scoring
        """
        if not isinstance(text, str) or not text.strip():
            return []

        try:
            # Tokenize
            tokens = word_tokenize(text.lower())
            # Remove stopwords and punctuation
            stop_words = set(stopwords.words('english'))
            min_length = self.SCORING_CONFIG["bm25"]["min_token_length"]
            tokens = [token for token in tokens 
                     if token.isalnum() 
                     and token not in stop_words 
                     and len(token) >= min_length]
            return tokens
        except Exception as e:
            logger.error(f"Error preprocessing text: {str(e)}", exc_info=True)
            return []

    async def _calculate_information_accuracy(self, original_script: List[Dict], transcript: str) -> float:
        """
        Calculate information accuracy score using BM25 and LLM
        """
        try:
            # First try BM25 matching
            bm25_score = await self._calculate_bm25_score(original_script, transcript)

            # If BM25 score is below threshold, use LLM
            if bm25_score < self.SCORING_CONFIG["confidence"]["information_accuracy"]["bm25_threshold"]:
                return await self._calculate_llm_accuracy_score(original_script, transcript)

            return bm25_score * 100  # Convert to 0-100 scale
        except Exception as e:
            logger.error(f"Error calculating information accuracy: {str(e)}", exc_info=True)
            raise

    async def _calculate_speech_clarity(self, transcript: str, transcript_object: Optional[List[Dict]] = None, simulation_type: str = "audio") -> float:
        """
        Calculate speech clarity and fluency score based on filler words and pauses

        Args:
            transcript: The conversation transcript text
            transcript_object: Optional transcript object with timing information
            simulation_type: Type of simulation to determine available data

        Returns:
            Speech clarity score (0-100)
        """
        try:
            # Count filler words in transcript
            filler_count = self._count_filler_words(transcript)

            # Calculate pause metrics (only for audio simulations with transcript object)
            max_pause_duration = 0.0
            if simulation_type == "audio" and transcript_object:
                max_pause_duration = self._calculate_max_pause_duration(transcript_object)

            # Apply scoring scale
            score = self._apply_speech_clarity_scale(filler_count, max_pause_duration)

            logger.debug(f"Speech clarity: {filler_count} filler words, {max_pause_duration:.2f}s max pause, score: {score}")
            return score

        except Exception as e:
            logger.error(f"Error calculating speech clarity: {str(e)}", exc_info=True)
            return 0.0

    async def _calculate_consistency(self, original_script: List[Dict], transcript: str) -> float:
        """
        Calculate consistency score using QWEN LLM analysis

        Args:
            original_script: List of script dictionaries
            transcript: The conversation transcript text

        Returns:
            Consistency score (0-100)
        """
        try:
            # Format original script for better readability
            formatted_script = self._format_script_for_analysis(original_script)

            # Prepare prompt using template
            config = self.SCORING_CONFIG["confidence"]["consistency"]
            prompt = config["analysis_prompt_template"].format(
                original_script=formatted_script,
                transcript=transcript
            )

            # Analyze consistency using QWEN LLM with retry logic
            retry_attempts = config["retry_attempts"]
            timeout = config["timeout"]

            for attempt in range(retry_attempts):
                try:
                    timeout_config = aiohttp.ClientTimeout(total=timeout)
                    async with aiohttp.ClientSession(timeout=timeout_config) as session:
                        async with session.post(
                            QWEN_API_URL,
                            json={"message": prompt},
                            headers={"Content-Type": "application/json"}
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                response_text = result["response"]

                                # Extract numeric score from response
                                score = self._extract_numeric_score(response_text)
                                if score is not None:
                                    logger.debug(f"Consistency score: {score:.2f}")
                                    return score
                                else:
                                    logger.warning(f"Could not extract score from response: {response_text}")
                                    if attempt < retry_attempts - 1:
                                        await asyncio.sleep(1)
                                        continue
                                    return config["default_score"]
                            else:
                                logger.warning(f"QWEN API returned status {response.status}, attempt {attempt + 1}/{retry_attempts}")
                                if attempt < retry_attempts - 1:
                                    await asyncio.sleep(2 ** attempt)
                                    continue

                except asyncio.TimeoutError:
                    logger.error(f"Timeout on attempt {attempt + 1}/{retry_attempts} for consistency analysis")
                    if attempt < retry_attempts - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue

            # All retries exhausted
            logger.error("All retry attempts exhausted for consistency analysis")
            return config["default_score"]

        except Exception as e:
            logger.error(f"Error calculating consistency: {str(e)}", exc_info=True)
            return self.SCORING_CONFIG["confidence"]["consistency"]["default_score"]

    def _format_script_for_analysis(self, original_script: List[Dict]) -> str:
        """
        Format original script for better LLM analysis

        Args:
            original_script: List of script dictionaries

        Returns:
            Formatted script text
        """
        try:
            formatted_lines = []
            for item in original_script:
                if isinstance(item, dict):
                    role = item.get("role", "Unknown")
                    sentence = item.get("script_sentence", "")

                    # Remove HTML tags if present
                    import re
                    cleaned_sentence = re.sub(r'<.*?>', '', sentence)

                    formatted_lines.append(f"{role}: {cleaned_sentence}")
                else:
                    formatted_lines.append(str(item))

            return "\n".join(formatted_lines)

        except Exception as e:
            logger.error(f"Error formatting script: {str(e)}", exc_info=True)
            return ""

    def _extract_numeric_score(self, response_text: str) -> Optional[float]:
        """
        Extract numeric score from LLM response

        Args:
            response_text: The LLM response text

        Returns:
            Extracted score or None if not found
        """
        try:
            # Try to extract number from the response
            import re

            # Look for numbers (including decimals)
            numbers = re.findall(r'\d+(?:\.\d+)?', response_text)
            if numbers:
                score = float(numbers[0])
                # Ensure score is within valid range
                return min(max(score, 0), 100)

            # If no numbers found, look for written numbers
            written_numbers = {
                'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
                'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90, 'hundred': 100
            }

            response_lower = response_text.lower()
            for word, value in written_numbers.items():
                if word in response_lower:
                    return float(value)

            return None

        except Exception as e:
            logger.error(f"Error extracting numeric score: {str(e)}", exc_info=True)
            return None

    async def _calculate_objection_handling(self, original_script: List[Dict], transcript: str, 
                                          transcript_object: Optional[List[Dict]] = None, 
                                          simulation_type: str = "audio") -> float:
        """
        Calculate objection handling effectiveness score

        Args:
            original_script: List of script dictionaries
            transcript: The conversation transcript text
            transcript_object: Optional transcript object with timing information
            simulation_type: Type of simulation

        Returns:
            Objection handling score (0-100)
        """
        try:
            # Parse transcript into structured format
            parsed_transcript = self._parse_transcript_to_segments(transcript)

            # Detect objections using SBERT
            objections = await self._detect_objections(parsed_transcript)

            if not objections:
                # No objections found, return perfect score
                logger.debug("No objections detected in transcript")
                return 100.0

            handling_scores = []
            for objection in objections:
                # Get context around the objection
                context = self._get_objection_context(parsed_transcript, objection)

                # Analyze handling effectiveness using LLM
                effectiveness_score = await self._analyze_objection_handling(context)

                # Calculate response time if transcript object is available
                timing_score = 100.0  # Default if no timing available
                if simulation_type == "audio" and transcript_object:
                    timing_score = self._calculate_objection_response_time(
                        objection, transcript_object, parsed_transcript
                    )

                # Combine effectiveness and timing scores
                config = self.SCORING_CONFIG["confidence"]["objection_handling"]
                combined_score = (
                    effectiveness_score * config["effectiveness_weight"] +
                    timing_score * config["timing_weight"]
                )
                handling_scores.append(combined_score)

            # Return average score across all objections
            final_score = sum(handling_scores) / len(handling_scores)
            logger.debug(f"Objection handling: {len(objections)} objections, average score: {final_score:.2f}")
            return final_score

        except Exception as e:
            logger.error(f"Error calculating objection handling: {str(e)}", exc_info=True)
            return 0.0

    def _parse_transcript_to_segments(self, transcript: str) -> List[Dict]:
        """
        Parse transcript text into structured segments

        Args:
            transcript: Raw transcript text

        Returns:
            List of segments with role and content
        """
        try:
            segments = []
            lines = transcript.split('\n')

            for i, line in enumerate(lines):
                if line.strip():
                    # Extract role and content
                    if ':' in line:
                        role, content = line.split(':', 1)
                        segments.append({
                            'index': i,
                            'role': role.strip().lower(),
                            'content': content.strip(),
                            'full_line': line.strip()
                        })

            return segments
        except Exception as e:
            logger.error(f"Error parsing transcript: {str(e)}", exc_info=True)
            return []

    async def _detect_objections(self, segments: List[Dict]) -> List[Dict]:
        """
        Detect objections in transcript segments using SBERT

        Args:
            segments: List of transcript segments

        Returns:
            List of objection segments
        """
        try:
            objections = []
            objection_patterns = self.SCORING_CONFIG["confidence"]["objection_handling"]["objection_patterns"]
            threshold = self.SCORING_CONFIG["confidence"]["objection_handling"]["sbert_objection_threshold"]

            # Filter customer/user segments only
            customer_segments = [s for s in segments if s['role'] in ['customer', 'user']]

            if not customer_segments:
                return objections

            # Prepare sentences for batch comparison
            customer_sentences = [s['content'] for s in customer_segments]

            # Use SBERT batch similarity to compare with objection patterns
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    SBERT_BATCH_SIMILARITY_URL,
                    json={
                        "sentences1": customer_sentences,
                        "sentences2": objection_patterns
                    },
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        similarities = result.get("similarities", [])

                        # Check each customer sentence for objections
                        for i, sentence_similarities in enumerate(similarities):
                            max_similarity = max(sentence_similarities)
                            if max_similarity > threshold:
                                objection_segment = customer_segments[i].copy()
                                objection_segment['similarity_score'] = max_similarity
                                objection_segment['matched_pattern'] = objection_patterns[
                                    sentence_similarities.index(max_similarity)
                                ]
                                objections.append(objection_segment)
                    else:
                        logger.warning(f"SBERT API returned status {response.status}")

            return objections

        except Exception as e:
            logger.error(f"Error detecting objections: {str(e)}", exc_info=True)
            return []

    def _get_objection_context(self, segments: List[Dict], objection: Dict) -> Dict:
        """
        Get context around an objection (sentences before and after)

        Args:
            segments: All transcript segments
            objection: The objection segment

        Returns:
            Context dictionary with before, objection, and after segments
        """
        try:
            objection_index = objection['index']
            config = self.SCORING_CONFIG["confidence"]["objection_handling"]

            # Find the objection in segments
            segment_indices = [s['index'] for s in segments]
            if objection_index not in segment_indices:
                return {"before": [], "objection": objection, "after": []}

            current_pos = segment_indices.index(objection_index)

            # Get context before and after
            before_start = max(0, current_pos - config["context_sentences_before"])
            after_end = min(len(segments), current_pos + 1 + config["context_sentences_after"])

            context = {
                "before": segments[before_start:current_pos],
                "objection": objection,
                "after": segments[current_pos + 1:after_end]
            }

            return context

        except Exception as e:
            logger.error(f"Error getting objection context: {str(e)}", exc_info=True)
            return {"before": [], "objection": objection, "after": []}

    async def _analyze_objection_handling(self, context: Dict) -> float:
        """
        Analyze how effectively an objection was handled using LLM

        Args:
            context: Context around the objection

        Returns:
            Effectiveness score (0-100)
        """
        try:
            # Construct context text
            context_text = ""
            for segment in context["before"]:
                context_text += f"{segment['role'].title()}: {segment['content']}\n"

            context_text += f"**OBJECTION** {context['objection']['role'].title()}: {context['objection']['content']}\n"

            for segment in context["after"]:
                context_text += f"{segment['role'].title()}: {segment['content']}\n"

            # Create prompt for LLM analysis
            prompt = f"""
            Analyze the following conversation where a customer raises an objection and evaluate how effectively the agent handled it.

            Consider these criteria:
            1. Response time/speed (immediate vs delayed)
            2. Clarity and assertiveness of the response
            3. Avoiding hedging language ("maybe", "I think", "possibly")
            4. Providing specific solutions or explanations
            5. Maintaining confidence and professionalism
            6. Addressing the objection directly

            Conversation:
            {context_text}

            Rate the objection handling effectiveness on a scale of 0-100, where:
            - 90-100: Excellent handling with immediate, clear, assertive response
            - 70-89: Good handling with mostly clear response
            - 50-69: Adequate handling but could be better
            - 30-49: Poor handling with hesitation or unclear response
            - 0-29: Very poor handling or no proper response

            Provide ONLY a numeric score between 0 and 100.
            """

            # Retry logic for LLM API calls
            retry_attempts = self.SCORING_CONFIG["llm"]["retry_attempts"]
            timeout = self.SCORING_CONFIG["llm"]["timeout"]

            for attempt in range(retry_attempts):
                try:
                    timeout_config = aiohttp.ClientTimeout(total=timeout)
                    async with aiohttp.ClientSession(timeout=timeout_config) as session:
                        async with session.post(
                            QWEN_API_URL,
                            json={"message": prompt},
                            headers={"Content-Type": "application/json"}
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                response_text = result["response"]

                                # Extract numeric score
                                import re
                                numbers = re.findall(r'\d+(?:\.\d+)?', response_text)
                                if numbers:
                                    score = float(numbers[0])
                                    return min(max(score, 0), 100)
                                else:
                                    logger.warning(f"No numeric score found in LLM response: {response_text}")
                                    if attempt < retry_attempts - 1:
                                        await asyncio.sleep(1)
                                        continue
                                    return self.SCORING_CONFIG["llm"]["default_score"]
                            else:
                                logger.warning(f"Qwen API returned status {response.status}, attempt {attempt + 1}/{retry_attempts}")
                                if attempt < retry_attempts - 1:
                                    await asyncio.sleep(2 ** attempt)
                                    continue
                except asyncio.TimeoutError:
                    logger.error(f"Timeout on attempt {attempt + 1}/{retry_attempts}")
                    if attempt < retry_attempts - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue

            # All retries exhausted
            return self.SCORING_CONFIG["llm"]["default_score"]

        except Exception as e:
            logger.error(f"Error analyzing objection handling: {str(e)}", exc_info=True)
            return self.SCORING_CONFIG["llm"]["default_score"]

    def _calculate_objection_response_time(self, objection: Dict, transcript_object: List[Dict], 
                                         segments: List[Dict]) -> float:
        """
        Calculate response time between objection and agent response

        Args:
            objection: The objection segment
            transcript_object: Transcript with timing information
            segments: All transcript segments

        Returns:
            Timing score (0-100)
        """
        try:
            config = self.SCORING_CONFIG["confidence"]["objection_handling"]

            # Find objection in transcript object
            objection_end_time = None
            agent_start_time = None

            # Search for the objection in transcript object
            for segment in transcript_object:
                if segment.get("content", "").strip() == objection['content'].strip():
                    words = segment.get("words", [])
                    if words:
                        objection_end_time = words[-1].get("end", 0)
                    break

            if objection_end_time is None:
                logger.warning("Could not find objection in transcript object")
                return 100.0  # Default to perfect score if timing not available

            # Find next agent/trainee response
            objection_index = objection['index']
            for segment in segments:
                if (segment['index'] > objection_index and 
                    segment['role'] in ['agent', 'trainee']):
                    # Find this segment in transcript object
                    for to_segment in transcript_object:
                        if to_segment.get("content", "").strip() == segment['content'].strip():
                            words = to_segment.get("words", [])
                            if words:
                                agent_start_time = words[0].get("start", 0)
                            break
                    break

            if agent_start_time is None:
                logger.warning("Could not find agent response after objection")
                return 50.0  # Moderate score if no response found

            # Calculate response time
            response_time = agent_start_time - objection_end_time

            # Score based on response time
            if response_time <= config["ideal_response_time"]:
                return 100.0
            elif response_time <= config["max_response_time"]:
                # Linear interpolation between ideal and max
                score = 100 - ((response_time - config["ideal_response_time"]) / 
                              (config["max_response_time"] - config["ideal_response_time"]) * 50)
                return max(score, 50.0)
            else:
                # Very poor timing
                return 10.0

        except Exception as e:
            logger.error(f"Error calculating objection response time: {str(e)}", exc_info=True)
            return 50.0  # Default moderate score on error

    async def _calculate_tone_volume(self, audio_url: str, transcript_object: Optional[List[Dict]] = None) -> float:
        """
        Calculate tone and volume score using pitch analysis with pyworld

        Args:
            audio_url: URL of the audio file
            transcript_object: Transcript with timing information to focus on agent speech

        Returns:
            Tone and volume score (0-100)
        """
        try:
            # Download and process audio file
            audio_file_path = await self._download_audio_file(audio_url)

            # Load audio with librosa
            y, sr = librosa.load(audio_file_path, sr=self.SCORING_CONFIG["confidence"]["tone_volume"]["sample_rate"])

            # Extract agent speech segments if transcript object is available
            agent_segments = []
            if transcript_object:
                agent_segments = self._extract_agent_speech_segments(transcript_object, len(y), sr)

            # Calculate pitch variance for agent speech
            if agent_segments:
                pitch_variance = await self._calculate_agent_pitch_variance(y, sr, agent_segments)
            else:
                # Analyze entire audio if no transcript timing available
                pitch_variance = await self._calculate_pitch_variance(y, sr)

            # Convert variance to score
            score = self._variance_to_score(pitch_variance)

            # Clean up temporary file
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)

            logger.debug(f"Tone and volume: pitch variance = {pitch_variance:.2f}, score = {score:.2f}")
            return score

        except Exception as e:
            logger.error(f"Error calculating tone and volume: {str(e)}", exc_info=True)
            return 0.0

    async def _download_audio_file(self, audio_url: str) -> str:
        """
        Download audio file from URL to temporary location

        Args:
            audio_url: URL of the audio file

        Returns:
            Path to temporary audio file
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                temp_path = tmp.name

            # Download audio file
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(temp_path, 'wb') as f:
                            f.write(content)
                        return temp_path
                    else:
                        raise HTTPException(status_code=response.status, detail="Failed to download audio file")

        except Exception as e:
            logger.error(f"Error downloading audio file: {str(e)}", exc_info=True)
            raise

    def _extract_agent_speech_segments(self, transcript_object: List[Dict], audio_length_samples: int, sample_rate: int) -> List[tuple]:
        """
        Extract time segments where agent/trainee is speaking

        Args:
            transcript_object: Transcript with timing information
            audio_length_samples: Total length of audio in samples
            sample_rate: Audio sample rate

        Returns:
            List of (start_sample, end_sample) tuples for agent speech
        """
        try:
            agent_segments = []

            for segment in transcript_object:
                if segment.get("role", "").lower() in ["agent", "trainee"]:
                    words = segment.get("words", [])
                    if words:
                        # Get start and end times for this segment
                        start_time = words[0].get("start", 0)
                        end_time = words[-1].get("end", 0)

                        # Convert to sample indices
                        start_sample = int(start_time * sample_rate)
                        end_sample = int(end_time * sample_rate)

                        # Ensure within bounds
                        start_sample = max(0, start_sample)
                        end_sample = min(audio_length_samples - 1, end_sample)

                        if start_sample < end_sample:
                            agent_segments.append((start_sample, end_sample))

            return agent_segments

        except Exception as e:
            logger.error(f"Error extracting agent speech segments: {str(e)}", exc_info=True)
            return []

    async def _calculate_agent_pitch_variance(self, y: np.ndarray, sr: int, agent_segments: List[tuple]) -> float:
        """
        Calculate pitch variance for agent speech segments

        Args:
            y: Audio signal
            sr: Sample rate
            agent_segments: List of (start, end) sample indices for agent speech

        Returns:
            Pitch variance (standard deviation)
        """
        try:
            all_f0_values = []
            config = self.SCORING_CONFIG["confidence"]["tone_volume"]

            for start_sample, end_sample in agent_segments:
                # Extract audio segment
                segment = y[start_sample:end_sample]

                if len(segment) > 0:
                    # Calculate pitch for this segment
                    f0, _ = self._extract_pitch_pyworld(segment, sr)

                    # Filter out unvoiced frames and outliers
                    valid_f0 = f0[(f0 > config["min_f0"]) & (f0 < config["max_f0"])]

                    if len(valid_f0) > 0:
                        all_f0_values.extend(valid_f0)

            if len(all_f0_values) > 1:
                return float(np.std(all_f0_values))
            else:
                logger.warning("No valid pitch values found in agent speech")
                return 0.0

        except Exception as e:
            logger.error(f"Error calculating agent pitch variance: {str(e)}", exc_info=True)
            return 0.0

    async def _calculate_pitch_variance(self, y: np.ndarray, sr: int) -> float:
        """
        Calculate pitch variance for entire audio signal

        Args:
            y: Audio signal
            sr: Sample rate

        Returns:
            Pitch variance (standard deviation)
        """
        try:
            config = self.SCORING_CONFIG["confidence"]["tone_volume"]

            # Extract pitch using pyworld
            f0, _ = self._extract_pitch_pyworld(y, sr)

            # Filter out unvoiced frames and outliers
            valid_f0 = f0[(f0 > config["min_f0"]) & (f0 < config["max_f0"])]

            if len(valid_f0) > 1:
                return float(np.std(valid_f0))
            else:
                logger.warning("No valid pitch values found in audio")
                return 0.0

        except Exception as e:
            logger.error(f"Error calculating pitch variance: {str(e)}", exc_info=True)
            return 0.0

    def _extract_pitch_pyworld(self, y: np.ndarray, sr: int) -> tuple:
        """
        Extract pitch (F0) using pyworld

        Args:
            y: Audio signal
            sr: Sample rate

        Returns:
            Tuple of (f0, time_axis)
        """
        try:
            config = self.SCORING_CONFIG["confidence"]["tone_volume"]

            # Convert to double precision for pyworld
            x = y.astype(np.float64)

            # Perform pyworld analysis
            _f0, t = pw.dio(x, sr, frame_period=config["frame_period"])  # Raw F0 estimation
            f0 = pw.stonemask(x, _f0, t, sr)  # Refined F0 estimation

            return f0, t

        except Exception as e:
            logger.error(f"Error extracting pitch with pyworld: {str(e)}", exc_info=True)
            return np.array([]), np.array([])

    def _variance_to_score(self, variance: float) -> float:
        """
        Convert pitch variance to score based on thresholds

        Args:
            variance: Pitch variance (standard deviation)

        Returns:
            Score (0-100)
        """
        try:
            config = self.SCORING_CONFIG["confidence"]["tone_volume"]
            thresholds = config["scoring_thresholds"]
            scores = config["scores"]

            if variance <= thresholds["low_deviation"]:
                return scores["low"]  # 100%
            elif variance <= thresholds["medium_deviation"]:
                return scores["medium"]  # 66%
            elif variance <= thresholds["high_deviation"]:
                return scores["high"]  # 33%
            else:
                return scores["very_high"]  # 10%

        except Exception as e:
            logger.error(f"Error converting variance to score: {str(e)}", exc_info=True)
            return 0.0

    def _count_filler_words(self, transcript: str) -> int:
        """
        Count filler words in the transcript

        Args:
            transcript: The conversation transcript

        Returns:
            Number of filler words found
        """
        try:
            # Get filler words list
            filler_words = self.SCORING_CONFIG["confidence"]["speech_clarity"]["filler_words"]

            # Convert transcript to lowercase and extract only agent/trainee parts
            lines = transcript.split('\n')
            agent_text = ""

            for line in lines:
                if line.strip():
                    # Check if line contains agent/trainee content
                    if any(role in line.lower() for role in ['agent:', 'trainee:']):
                        # Extract the spoken content after the role indicator
                        if ':' in line:
                            content = line.split(':', 1)[1].strip().lower()
                            agent_text += " " + content

            # Count filler words
            filler_count = 0
            for filler in filler_words:
                # Count occurrences of each filler word
                if filler in agent_text:
                    # Use word boundaries to avoid partial matches
                    import re
                    pattern = r'\b' + re.escape(filler) + r'\b'
                    matches = re.findall(pattern, agent_text)
                    filler_count += len(matches)

            return filler_count

        except Exception as e:
            logger.error(f"Error counting filler words: {str(e)}", exc_info=True)
            return 0

    def _calculate_max_pause_duration(self, transcript_object: List[Dict]) -> float:
        """
        Calculate the maximum pause duration from transcript object

        Args:
            transcript_object: List of transcript segments with timing information

        Returns:
            Maximum pause duration in seconds
        """
        try:
            max_pause = 0.0
            pause_threshold = self.SCORING_CONFIG["confidence"]["speech_clarity"]["pause_threshold"]

            previous_end_time = None

            for segment in transcript_object:
                # Only analyze agent/trainee segments
                if segment.get("role", "").lower() in ["agent", "trainee"]:
                    words = segment.get("words", [])

                    if words:
                        # Get the start time of first word in this segment
                        segment_start = words[0].get("start", 0)

                        # Calculate pause between segments
                        if previous_end_time is not None:
                            pause_duration = segment_start - previous_end_time
                            if pause_duration > pause_threshold:
                                max_pause = max(max_pause, pause_duration)

                        # Update previous end time with last word's end time
                        if words:
                            previous_end_time = words[-1].get("end", segment_start)

                        # Check for pauses within the segment (between words)
                        for i in range(1, len(words)):
                            prev_word_end = words[i-1].get("end", 0)
                            curr_word_start = words[i].get("start", 0)
                            pause_duration = curr_word_start - prev_word_end

                            if pause_duration > pause_threshold:
                                max_pause = max(max_pause, pause_duration)

            return max_pause

        except Exception as e:
            logger.error(f"Error calculating pause duration: {str(e)}", exc_info=True)
            return 0.0

    def _apply_speech_clarity_scale(self, filler_count: int, max_pause_duration: float) -> float:
        """
        Apply the scoring scale based on filler words and pause duration

        Args:
            filler_count: Number of filler words
            max_pause_duration: Maximum pause duration in seconds

        Returns:
            Speech clarity score (0-100)
        """
        try:
            scoring_scale = self.SCORING_CONFIG["confidence"]["speech_clarity"]["scoring_scale"]

            for max_fillers, max_pause, score in scoring_scale:
                if filler_count <= max_fillers and max_pause_duration <= max_pause:
                    return float(score)

            # If no scale matches, return the lowest score
            return float(scoring_scale[-1][2])

        except Exception as e:
            logger.error(f"Error applying speech clarity scale: {str(e)}", exc_info=True)
            return 0.0

    async def _calculate_bm25_score(self, original_script: List[Dict], transcript: str) -> float:
        """
        Calculate BM25 similarity score between original script and transcript
        """
        try:
            # Extract script sentences, handling potential nested data structures
            original_sentences = []
            for item in original_script:
                if isinstance(item, dict):
                    script_sentence = item.get("script_sentence", "")
                    # Remove HTML tags if present
                    import re
                    script_sentence = re.sub(r'<.*?>', '', script_sentence)
                    original_sentences.append(script_sentence)
                else:
                    original_sentences.append(str(item))

            # Preprocess original script sentences
            original_tokens = [self._preprocess_text(sent) for sent in original_sentences if sent.strip()]

            if not original_tokens:
                logger.warning("No valid original script sentences found")
                return 0.0

            # Create BM25 model
            bm25 = BM25Okapi(original_tokens)

            # Split transcript into lines and preprocess
            transcript_lines = [line.strip() for line in transcript.split('\n') if line.strip()]

            # Extract the actual spoken content, handling different formats
            processed_lines = []
            for line in transcript_lines:
                if ':' in line:
                    # Format: "Role: Content"
                    content = line.split(':', 1)[1].strip()
                    processed_lines.append(content)
                else:
                    # Direct content
                    processed_lines.append(line)

            # Tokenize processed lines
            transcript_tokens = [self._preprocess_text(line) for line in processed_lines if line.strip()]

            if not transcript_tokens:
                logger.warning("No valid transcript lines found")
                return 0.0

            # Calculate BM25 scores for each transcript line against all original sentences
            scores = []
            for query_tokens in transcript_tokens:
                if query_tokens:  # Skip empty token lists
                    line_scores = bm25.get_scores(query_tokens)
                    scores.append(max(line_scores) if line_scores.size > 0 else 0.0)

            # Calculate final score using appropriate aggregation
            if scores:
                # Use mean of the top 70% of scores to reduce impact of outliers
                sorted_scores = sorted(scores, reverse=True)
                top_scores = sorted_scores[:int(len(sorted_scores) * 0.7) or 1]
                final_score = sum(top_scores) / len(top_scores)
            else:
                final_score = 0.0

            # Normalize to 0-1 range (BM25 scores typically range from 0 to ~20)
            normalized_score = min(1.0, final_score / 15.0)

            logger.debug(f"BM25 score: {final_score:.3f}, normalized: {normalized_score:.3f}")
            return normalized_score

        except Exception as e:
            logger.error(f"Error calculating BM25 score: {str(e)}", exc_info=True)
            raise

    async def _calculate_llm_accuracy_score(self, original_script: List[Dict], transcript: str) -> float:
        """
        Calculate accuracy score using Qwen LLM
        """
        try:
            # Format original script for better comparison
            formatted_script = "\n".join([
                f"{item.get('role', 'Unknown')}: {item.get('script_sentence', '')}"
                for item in original_script
            ])

            # Prepare prompt for LLM
            prompt = (
                "Compare the following original script and actual transcript for factual accuracy. "
                "Focus on product details, policy information, and resolution steps. "
                "Return ONLY a numeric value between 0 and 100 where 100 means perfect accuracy.\n\n"
                f"Original Script:\n{formatted_script}\n\n"
                f"Actual Transcript:\n{transcript}\n\n"
                "Please provide only a number (0-100) representing the accuracy score."
            )

            # Retry logic for LLM API calls
            retry_attempts = self.SCORING_CONFIG["llm"]["retry_attempts"]
            timeout = self.SCORING_CONFIG["llm"]["timeout"]

            for attempt in range(retry_attempts):
                try:
                    timeout_config = aiohttp.ClientTimeout(total=timeout)
                    async with aiohttp.ClientSession(timeout=timeout_config) as session:
                        async with session.post(
                            QWEN_API_URL,
                            json={"message": prompt},
                            headers={"Content-Type": "application/json"}
                        ) as response:
                            if response.status == 200:
                                result = await response.json()

                                # Extract numeric score from response
                                try:
                                    response_text = result["response"]
                                    logger.debug(f"Qwen response: {response_text}")

                                    # Try to extract number from the response
                                    numbers = re.findall(r'\d+(?:\.\d+)?', response_text)
                                    if numbers:
                                        score = float(numbers[0])
                                        return min(max(score, 0), 100)  # Ensure score is between 0 and 100
                                    else:
                                        logger.warning(f"No numeric value found in Qwen response: {response_text}")
                                        if attempt < retry_attempts - 1:
                                            await asyncio.sleep(1)  # Wait before retry
                                            continue
                                        return self.SCORING_CONFIG["llm"]["default_score"]
                                except (KeyError, ValueError, TypeError) as e:
                                    logger.error(f"Error parsing LLM response: {str(e)}, response: {result}", exc_info=True)
                                    if attempt < retry_attempts - 1:
                                        await asyncio.sleep(1)  # Wait before retry
                                        continue
                                    return self.SCORING_CONFIG["llm"]["default_score"]
                            else:
                                logger.warning(f"Qwen API returned status {response.status}, attempt {attempt + 1}/{retry_attempts}")
                                if attempt < retry_attempts - 1:
                                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                    continue
                                else:
                                    raise HTTPException(
                                        status_code=response.status,
                                        detail=f"Failed to get response from Qwen API after {retry_attempts} attempts"
                                    )
                except asyncio.TimeoutError:
                    logger.error(f"Timeout on attempt {attempt + 1}/{retry_attempts}")
                    if attempt < retry_attempts - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        logger.error("All retry attempts exhausted")
                        return self.SCORING_CONFIG["llm"]["default_score"]

        except Exception as e:
            logger.error(f"Error calculating LLM accuracy score: {str(e)}", exc_info=True)
            raise

    async def _store_confidence_scores(self, user_simulation_progress_id: str, scores: Dict[str, float]) -> None:
        """
        Store confidence scores in the database
        """
        try:
            # Update the user simulation progress document with advanced scores
            from bson import ObjectId

            update_doc = {
                "advancedScores.confidence": scores,
                "advancedScores.lastUpdated": datetime.utcnow()
            }

            await self.db.user_sim_progress.update_one(
                {"_id": ObjectId(user_simulation_progress_id)},
                {"$set": update_doc}
            )

            # Also store in a separate collection for analytics
            await self.db.advanced_scoring_results.insert_one({
                "userSimulationProgressId": user_simulation_progress_id,
                "scoreType": "confidence",
                "scores": scores,
                "timestamp": datetime.utcnow()
            })

            logger.info(f"Confidence scores stored successfully for progress ID: {user_simulation_progress_id}")

        except Exception as e:
            logger.error(f"Error storing confidence scores for progress ID {user_simulation_progress_id}: {str(e)}", exc_info=True)
            # Don't raise the exception since this is a background task

    async def _store_error(self, user_simulation_progress_id: str, error_message: str) -> None:
        """
        Store error information in the database
        """
        try:
            await self.db.advanced_scoring_errors.insert_one({
                "userSimulationProgressId": user_simulation_progress_id,
                "error": error_message,
                "timestamp": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Error storing error message: {str(e)}", exc_info=True)