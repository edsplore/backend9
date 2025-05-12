from typing import Dict, List, Optional
from fastapi import HTTPException
import aiohttp
import json
import math
import re
import asyncio
from datetime import datetime
from rank_bm25 import BM25Okapi
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Configuration - should be moved to config.py
QWEN_API_URL = "https://eu2simudal001.eastus2.cloudapp.azure.com/qwen/chat"

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
                "enabled": False  # TODO: Implement
            },
            "tone_volume": {
                "weight": 0.15,
                "enabled": False  # TODO: Implement
            },
            "consistency": {
                "weight": 0.15,
                "enabled": False  # TODO: Implement
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

            # For now, we calculate information accuracy and speech clarity
            # TODO: Implement other components (objection handling, tone/volume, consistency)
            scores = {
                "information_accuracy": info_accuracy_score,
                "speech_clarity": speech_clarity_score,
                "objection_handling": 0.0,  # Placeholder for future implementation
                "tone_volume": 0.0,  # Placeholder for future implementation
                "consistency": 0.0,  # Placeholder for future implementation
                "total_confidence": (
                    info_accuracy_score * self.SCORING_CONFIG["confidence"]["information_accuracy"]["weight"] +
                    speech_clarity_score * self.SCORING_CONFIG["confidence"]["speech_clarity"]["weight"]
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