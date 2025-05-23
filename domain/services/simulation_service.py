import asyncio
from typing import Any, Dict, List, Optional
import json
import aiohttp
import base64
from datetime import datetime
from bson import ObjectId
import traceback
import re
from config import (AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_KEY,
                    AZURE_OPENAI_BASE_URL, RETELL_API_KEY)
from infrastructure.database import Database
from api.schemas.requests import (CreateSimulationRequest,
                                  UpdateSimulationRequest,
                                  CloneSimulationRequest, PaginationParams,
                                  SimulationScoringMetrics, MetricWeightage,
                                  AttemptModel, ChatHistoryItem)
from api.schemas.responses import SimulationByIDResponse, SimulationData
from fastapi import HTTPException, UploadFile
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings, )
from api.schemas.requests import UpdateImageMaskingObjectRequest

from api.schemas.responses import (StartVisualAudioPreviewResponse,
                                   StartVisualChatPreviewResponse,
                                   StartVisualPreviewResponse, SimulationData,
                                   SimulationByIDResponse,
                                   EndSimulationResponse,
                                   SimulationByIDResponse, EndSimulationResponse, UpdateImageMaskingObjectResponse)

from domain.services.scoring_service import ScoringService

from bson import ObjectId

from utils.logger import Logger

# Add after imports
logger = Logger.get_logger(__name__)

COPY_PREFIX = "Copy "


class SimulationService:

    def __init__(self):
        logger.info("Initializing SimulationService...")

        try:
            logger.debug("Connecting to database...")
            self.db = Database()
            logger.info("Database initialized successfully.")

            self.scoring_service = ScoringService()
        except Exception as e:
            logger.error("Failed to initialize database.")
            logger.exception(e)

        try:
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

        logger.info("SimulationService initialized.")

    async def _store_slide_file(self, slide_data: dict,
                                file: UploadFile) -> dict:
        """Store slide file in MongoDB and return updated slide data"""
        logger.info("Storing slide file in MongoDB.")
        logger.debug(f"Slide data: {slide_data}, File: {file.filename}")
        try:
            file_bytes = await file.read()
            # Build the document to insert
            image_doc = {
                "imageId": slide_data["imageId"],
                "name": slide_data.get("imageName", file.filename),
                "contentType": file.content_type,
                "data": file_bytes,
                "uploadedAt": datetime.utcnow()
            }

            logger.debug(f"Image doc being inserted: {image_doc}")

            # Insert into the images collection
            result = await self.db.images.insert_one(image_doc)

            logger.info(
                f"Image inserted successfully, id={result.inserted_id}")

            # Build the image URL
            image_url = f"/api/images/{result.inserted_id}"

            # Update slide data with the image URL
            slide_data_copy = slide_data.copy()
            slide_data_copy["imageUrl"] = image_url
            return slide_data_copy

        except Exception as e:
            logger.error(f"Error in _store_slide_file: {str(e)}",
                         exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error storing slide file: {str(e)}")

    async def _store_slide_image(self, slide_data: dict) -> dict:
        """Store image data in MongoDB and return updated slide data"""
        logger.info("Storing slide image in MongoDB.")
        logger.debug(f"Slide data: {slide_data}")
        if not slide_data.get("imageData"):
            return slide_data

        try:
            # Decode base64 image data
            image_data = base64.b64decode(slide_data["imageData"]["data"])

            # Create image document
            image_doc = {
                "imageId": slide_data["imageId"],
                "name": slide_data["imageName"],
                "contentType": slide_data["imageData"]["contentType"],
                "data": image_data,
                "uploadedAt": datetime.utcnow()
            }

            # Store in images collection
            result = await self.db.images.insert_one(image_doc)

            # Create image URL
            image_url = f"/api/images/{result.inserted_id}"

            # Update slide data
            slide_data_copy = slide_data.copy()
            slide_data_copy["imageUrl"] = image_url
            if "imageData" in slide_data_copy:
                del slide_data_copy["imageData"]

            logger.info(
                f"Slide image stored successfully, id={result.inserted_id}")
            return slide_data_copy

        except Exception as e:
            logger.error(f"Error storing image data: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error storing image: {str(e)}")

    # New method in your service class
    async def simulation_name_exists(self, name: str, workspace: str) -> bool:
        """Check if a simulation with the given name already exists in the workspace"""
        logger.info(f"Checking if simulation name '{name}' exists in workspace {workspace}")
        try:
            # Query the database for simulations with the same name in the workspace
            count = await self.db.simulations.count_documents({
                "name": name,
                "workspace": workspace
            })
            return count > 0
        except Exception as e:
            logger.error(f"Error checking simulation name existence: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error checking simulation name: {str(e)}")

    # Modified create_simulation method
    async def create_simulation(self,
                                request: CreateSimulationRequest,
                                workspace: str) -> Dict:
        """Create a new simulation"""
        logger.info(f"Creating new simulation for user: {request.user_id} in workspace: {workspace}")
        logger.debug(f"CreateSimulationRequest data: {request.dict()}")
        try:
            # Check if a simulation with this name already exists in the workspace
            name_exists = await self.simulation_name_exists(request.name, workspace)
            if name_exists:
                logger.warning(
                    f"Simulation with name '{request.name}' already exists in workspace {workspace}")
                # Return a specific error for duplicate names
                return {
                    "status": "error",
                    "message": "Simulation with this name already exists",
                }

            # Create simulation document (existing code)
            simulation_doc = {
                "name": request.name,
                "divisionId": request.division_id,
                "departmentId": request.department_id,
                "type": request.type,
                "lastModifiedBy": request.user_id,
                "lastModified": datetime.utcnow(),
                "createdBy": request.user_id,
                "createdOn": datetime.utcnow(),
                "status": "draft",
                "version": 1,
                "tags": request.tags,
                "workspace": workspace  # Add workspace field
            }
            # Insert into database
            result = await self.db.simulations.insert_one(simulation_doc)
            logger.info(
                f"Successfully created simulation with ID: {result.inserted_id}")
            return {"id": str(result.inserted_id), "status": "success"}
        except Exception as e:
            logger.error(f"Error creating simulation: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error creating simulation: {str(e)}")

    async def _next_copy_name(self, base_name: str, workspace: str) -> str:
        """
        Given the *current* simulation name, return the correctly
        incremented 'Copy … N' name.
        """
        # 1.  Build the prefix (note the trailing space)
        prefix = f"{COPY_PREFIX}{base_name} "
        # 2.  Regex for "Copy <base_name> <number>"  (anchors ^…$ guarantee an exact match)
        pattern = f"^{re.escape(prefix)}(\\d+)$"

        # 3.  Pull any existing copies and collect the numeric suffixes
        cursor = self.db.simulations.find(  # projection keeps query light
            {
                "name": {"$regex": pattern},
                "workspace": workspace  # Add workspace filter
            },
            {
                "_id": 0,
                "name": 1
            },
        )

        max_n = 0
        async for doc in cursor:
            m = re.match(pattern, doc["name"])
            if m:
                max_n = max(max_n, int(m.group(1)))

        # 4.  Next copy gets +1
        return f"{prefix}{max_n + 1}"

    async def clone_simulation(self, request: CloneSimulationRequest, workspace: str) -> Dict:
        """Clone an existing simulation with proper naming."""
        logger.info(
            "Cloning simulation for user=%s, sim_id=%s, workspace=%s",
            request.user_id,
            request.simulation_id,
            workspace
        )
        try:
            sim_id_object = ObjectId(request.simulation_id)
            existing_sim = await self.db.simulations.find_one({
                "_id": sim_id_object,
                "workspace": workspace
            })

            if not existing_sim:
                raise HTTPException(
                    status_code=404,
                    detail=
                    f"Simulation with id {request.simulation_id} not found in workspace {workspace}",
                )

            # ------------------------------------------------------------------
            # 👇 calculate the new name *before* inserting
            new_name = await self._next_copy_name(existing_sim["name"], workspace)
            # ------------------------------------------------------------------

            new_sim = existing_sim.copy()
            new_sim.pop("_id")

            new_sim.update({
                "name": new_name,
                "createdBy": request.user_id,
                "createdOn": datetime.utcnow(),
                "lastModifiedBy": request.user_id,
                "lastModified": datetime.utcnow(),
                "status": "draft",
                "workspace": workspace  # Ensure workspace is set
            })

            result = await self.db.simulations.insert_one(new_sim)
            logger.info("Simulation cloned successfully → %s",
                        result.inserted_id)
            return {"id": str(result.inserted_id), "status": "success"}

        except HTTPException:
            # Let FastAPI propagate the original error & traceback
            raise
        except Exception as e:
            logger.exception("Error cloning simulation")
            raise HTTPException(status_code=500,
                                detail=f"Error cloning simulation: {e}")

    async def update_simulation(
        self,
        sim_id: str,
        request: UpdateSimulationRequest,
        slides_files: Dict[str, UploadFile] = None,
    ) -> Dict:
        """Update an existing simulation (service)."""
        logger.info(
            f"Updating simulation {sim_id} for user: {request.user_id}")
        logger.debug(
            f"UpdateSimulationRequest data: {request.dict()}, slides_files keys={list(slides_files.keys()) if slides_files else 'No Files'}"
        )
        try:
            from bson import ObjectId

            sim_id_object = ObjectId(sim_id)
            existing_sim = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not existing_sim:
                logger.warning(f"Simulation {sim_id} not found during update.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            update_doc = {}

            def add_if_exists(field_name: str,
                              doc_field: Optional[str] = None):
                value = getattr(request, field_name)
                if value is not None:
                    update_doc[doc_field or field_name] = value

            field_mappings = {
                "name": "name",
                "division_id": "divisionId",
                "department_id": "departmentId",
                "type": "type",
                "tags": "tags",
                "status": "status",
                "estimated_time_to_attempt_in_mins":
                "estimatedTimeToAttemptInMins",
                "key_objectives": "keyObjectives",
                "overview_video": "overviewVideo",
                "quick_tips": "quickTips",
                "language": "language",
                "mood": "mood",
                "prompt": "prompt",
                "simulation_completion_repetition":
                "simulationCompletionRepetition",
                "simulation_max_repetition": "simulationMaxRepetition",
                "final_simulation_score_criteria":
                "finalSimulationScoreCriteria",
                "is_locked": "isLocked",
                "version": "version",
                "assistant_id": "assistantId",
                "slides": "slides",
                "voice_id": "voiceId",
            }
            for field, doc_field in field_mappings.items():
                add_if_exists(field, doc_field)

            sim_type = request.type if request.type else existing_sim.get(
                "type")

            if request.script is not None:
                logger.debug("Updating script.")
                update_doc["script"] = [s.dict() for s in request.script]
                if sim_type in ["audio", "chat"]:
                    prompt = await self.generate_simulation_prompt(
                        request.script)
                    update_doc["prompt"] = prompt

            if request.slidesData is not None and sim_type in [
                    "visual-audio",
                    "visual-chat",
                    "visual",
            ]:
                processed_slides = []
                logger.debug("Processing slidesData for visual simulation.")

                if slides_files and len(slides_files) > 0:
                    for slide in request.slidesData:
                        slide_dict = slide.dict()
                        slide_dict.pop("imageData", None)
                        image_id = slide_dict.get("imageId")
                        if image_id in slides_files:
                            file_obj = slides_files[image_id]
                            processed_slide = await self._store_slide_file(
                                slide_dict, file_obj)
                            processed_slides.append(processed_slide)
                        else:
                            processed_slides.append(slide_dict)
                else:
                    processed_slides = [
                        slide.dict() for slide in request.slidesData
                    ]
                    for slide_dict in processed_slides:
                        slide_dict.pop("imageData", None)

                update_doc["slidesData"] = processed_slides

            if request.lvl1 is not None:
                logger.debug("Updating lvl1 configuration.")
                update_doc["lvl1"] = {
                    "isEnabled":
                    request.lvl1.is_enabled,
                    "enablePractice":
                    request.lvl1.enable_practice,
                    "hideAgentScript":
                    request.lvl1.hide_agent_script,
                    "hideCustomerScript":
                    request.lvl1.hide_customer_script,
                    "hideKeywordScores":
                    request.lvl1.hide_keyword_scores,
                    "hideSentimentScores":
                    request.lvl1.hide_sentiment_scores,
                    "hideHighlights":
                    request.lvl1.hide_highlights,
                    "hideCoachingTips":
                    request.lvl1.hide_coaching_tips,
                    "enablePostSimulationSurvey":
                    request.lvl1.enable_post_simulation_survey,
                    "aiPoweredPausesAndFeedback":
                    request.lvl1.ai_powered_pauses_and_feedback,
                }

            if request.lvl2 is not None:
                logger.debug("Updating lvl2 configuration.")
                update_doc["lvl2"] = {
                    "isEnabled":
                    request.lvl2.is_enabled,
                    "enablePractice":
                    request.lvl2.enable_practice,
                    "hideAgentScript":
                    request.lvl2.hide_agent_script,
                    "hideCustomerScript":
                    request.lvl2.hide_customer_script,
                    "hideKeywordScores":
                    request.lvl2.hide_keyword_scores,
                    "hideSentimentScores":
                    request.lvl2.hide_sentiment_scores,
                    "hideHighlights":
                    request.lvl2.hide_highlights,
                    "hideCoachingTips":
                    request.lvl2.hide_coaching_tips,
                    "enablePostSimulationSurvey":
                    request.lvl2.enable_post_simulation_survey,
                    "aiPoweredPausesAndFeedback":
                    request.lvl2.ai_powered_pauses_and_feedback,
                }

            if request.lvl3 is not None:
                logger.debug("Updating lvl3 configuration.")
                update_doc["lvl3"] = {
                    "isEnabled":
                    request.lvl3.is_enabled,
                    "enablePractice":
                    request.lvl3.enable_practice,
                    "hideAgentScript":
                    request.lvl3.hide_agent_script,
                    "hideCustomerScript":
                    request.lvl3.hide_customer_script,
                    "hideKeywordScores":
                    request.lvl3.hide_keyword_scores,
                    "hideSentimentScores":
                    request.lvl3.hide_sentiment_scores,
                    "hideHighlights":
                    request.lvl3.hide_highlights,
                    "hideCoachingTips":
                    request.lvl3.hide_coaching_tips,
                    "enablePostSimulationSurvey":
                    request.lvl3.enable_post_simulation_survey,
                    "aiPoweredPausesAndFeedback":
                    request.lvl3.ai_powered_pauses_and_feedback,
                }

            if request.simulation_scoring_metrics is not None:
                logger.debug("Updating simulation scoring metrics.")
                update_doc["simulationScoringMetrics"] = {
                    "isEnabled":
                    request.simulation_scoring_metrics.is_enabled,
                    "keywordScore":
                    request.simulation_scoring_metrics.keyword_score,
                    "clickScore":
                    request.simulation_scoring_metrics.click_score,
                    "pointsPerKeyword":
                    request.simulation_scoring_metrics.points_per_keyword,
                    "pointsPerClick":
                    request.simulation_scoring_metrics.points_per_click,
                }

            if request.metric_weightage is not None:
                logger.debug("Updating metric weightage.")
                update_doc["metricWeightage"] = {
                    "clickAccuracy":
                    request.metric_weightage.click_accuracy,
                    "keywordAccuracy":
                    request.metric_weightage.keyword_accuracy,
                    "dataEntryAccuracy":
                    request.metric_weightage.data_entry_accuracy,
                    "contextualAccuracy":
                    request.metric_weightage.contextual_accuracy,
                    "sentimentMeasures":
                    request.metric_weightage.sentiment_measures,
                }

            if request.sim_practice is not None:
                logger.debug("Updating sim practice configuration.")
                update_doc["simPractice"] = {
                    "isUnlimited": request.sim_practice.is_unlimited,
                    "preRequisiteLimit":
                    request.sim_practice.pre_requisite_limit,
                }

            update_doc[
                "simulationCompletionRepetition"] = request.simulation_completion_repetition
            update_doc[
                "simulationMaxRepetition"] = request.simulation_max_repetition
            update_doc[
                "finalSimulationScoreCriteria"] = request.final_simulation_score_criteria

            if sim_type == "audio":
                if request.voice_id is not None:
                    logger.debug(f"Setting voice_id to {request.voice_id}")
                    update_doc["voiceId"] = request.voice_id

                if request.voice_speed is not None:
                    logger.debug(
                        f"Setting voice_speed to {request.voice_speed}")
                    update_doc["voice_speed"] = request.voice_speed

                # In the update_simulation function, where you call _create_retell_llm:
                if "prompt" in update_doc and sim_type == "audio":
                    logger.debug("Creating Retell LLM due to updated prompt.")

                    # Check if the first script element has a role of "trainee"
                    assistant_first = False
                    if update_doc.get("script") and len(
                            update_doc["script"]) > 0:
                        first_role = update_doc["script"][0].get("role",
                                                                 "").lower()
                        assistant_first = (first_role == "assistant"
                                           or first_role == "customer")
                        logger.debug(
                            f"First script role is {first_role}, assistant_first={assistant_first}"
                        )

                    llm_response = await self._create_retell_llm(
                        update_doc["prompt"], assistant_first)
                    update_doc["llmId"] = llm_response["llm_id"]

                    agent_voice_id = request.voice_id or "11labs-Adrian"
                    agent_response = await self._create_retell_agent(
                        llm_response["llm_id"], agent_voice_id)
                    update_doc["agentId"] = agent_response["agent_id"]

            update_doc["lastModified"] = datetime.utcnow()
            update_doc["lastModifiedBy"] = request.user_id

            logger.debug(
                f"Final update document for simulation {sim_id}: {update_doc}")
            result = await self.db.simulations.update_one(
                {"_id": sim_id_object}, {"$set": update_doc})

            if result.modified_count == 0:
                logger.error(
                    "Failed to update simulation; no documents modified.")
                raise HTTPException(status_code=500,
                                    detail="Failed to update simulation")

            updated_simulation = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            updated_simulation["_id"] = str(updated_simulation["_id"])
            logger.info(f"Simulation {sim_id} updated successfully.")
            return {
                "id": sim_id,
                "status": "success",
                "document": updated_simulation
            }

        except HTTPException as he:
            logger.error(f"HTTPException in update_simulation: {he.detail}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error updating simulation: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error updating simulation: {str(e)}")

    async def start_visual_audio_preview(
            self, sim_id: str,
            user_id: str) -> StartVisualAudioPreviewResponse:
        logger.info(f"Starting visual-audio preview for simulation {sim_id}")
        try:
            sim_id_object = ObjectId(sim_id)

            simulation_doc = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation_doc:
                logger.warning(
                    f"Simulation {sim_id} not found for visual-audio preview.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            # Extract simulation scoring metrics with new fields
            simulation_scoring_metrics = None
            if simulation_doc.get("simulationScoringMetrics"):
                sim_metrics = simulation_doc.get("simulationScoringMetrics",
                                                 {})
                simulation_scoring_metrics = SimulationScoringMetrics(
                    is_enabled=sim_metrics.get("isEnabled", False),
                    keyword_score=sim_metrics.get("keywordScore", 0),
                    click_score=sim_metrics.get("clickScore", 0),
                    points_per_keyword=sim_metrics.get("pointsPerKeyword", 1),
                    points_per_click=sim_metrics.get("pointsPerClick", 1),
                )

            # Extract metric weightage
            metric_weightage = None
            if simulation_doc.get("metricWeightage"):
                metric_weights = simulation_doc.get("metricWeightage", {})
                metric_weightage = MetricWeightage(
                    click_accuracy=metric_weights.get("clickAccuracy", 0),
                    keyword_accuracy=metric_weights.get("keywordAccuracy", 0),
                    data_entry_accuracy=metric_weights.get(
                        "dataEntryAccuracy", 0),
                    contextual_accuracy=metric_weights.get(
                        "contextualAccuracy", 0),
                    sentiment_measures=metric_weights.get(
                        "sentimentMeasures", 0),
                )

            simulation = SimulationData(
                id=str(simulation_doc["_id"]),
                sim_name=simulation_doc.get("name", ""),
                version=str(simulation_doc.get("version", "1")),
                sim_type=simulation_doc.get("type", ""),
                status=simulation_doc.get("status", ""),
                tags=simulation_doc.get("tags", []),
                est_time=""
                if simulation_doc.get("estimatedTimeToAttemptInMins") in [
                    0, "0", None, ""
                ] else str(simulation_doc.get("estimatedTimeToAttemptInMins")),
                last_modified=simulation_doc.get(
                    "lastModified", datetime.utcnow()).isoformat(),
                modified_by=simulation_doc.get("lastModifiedBy", ""),
                created_on=simulation_doc.get("createdOn",
                                              datetime.utcnow()).isoformat(),
                created_by=simulation_doc.get("createdBy", ""),
                islocked=simulation_doc.get("isLocked", False),
                division_id=simulation_doc.get("divisionId", ""),
                department_id=simulation_doc.get("departmentId", ""),
                script=simulation_doc.get("script", []),
                voice_id=simulation_doc.get("voiceId", "11labs-Adrian"),
                lvl1=simulation_doc.get("lvl1", {}),
                lvl2=simulation_doc.get("lvl2", {}),
                lvl3=simulation_doc.get("lvl3", {}),
                slidesData=simulation_doc.get("slidesData", []),
                simulation_scoring_metrics=simulation_scoring_metrics,
                metric_weightage=metric_weightage,
            )

            images = []
            if simulation_doc.get("slidesData"):
                for slide in simulation_doc["slidesData"]:
                    if slide.get("imageId"):
                        try:
                            image_id = slide["imageId"]
                            image_doc = await self.db.images.find_one(
                                {"imageId": image_id})
                            if image_doc:
                                images.append({
                                    "image_id":
                                    slide["imageId"],
                                    "image_data":
                                    base64.b64encode(
                                        image_doc["data"]).decode("utf-8"),
                                })
                        except Exception as image_err:
                            logger.warning(
                                f"Failed to load image for slide: {image_err}")

            logger.info(
                f"Visual-audio preview for sim {sim_id} prepared successfully.")
            return StartVisualAudioPreviewResponse(simulation=simulation,
                                                   images=images)

        except HTTPException as he:
            logger.error(
                f"HTTPException in start_visual_audio_preview: {he.detail}",
                exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error starting visual-audio preview: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error starting visual-audio preview: {str(e)}")

    async def start_visual_chat_preview(
            self, sim_id: str, user_id: str) -> StartVisualChatPreviewResponse:
        logger.info(f"Starting visual-chat preview for simulation {sim_id}")
        try:
            sim_id_object = ObjectId(sim_id)

            simulation_doc = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation_doc:
                logger.warning(
                    f"Simulation {sim_id} not found for visual-chat preview.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            # Extract simulation scoring metrics with new fields
            simulation_scoring_metrics = None
            if simulation_doc.get("simulationScoringMetrics"):
                sim_metrics = simulation_doc.get("simulationScoringMetrics",
                                                 {})
                simulation_scoring_metrics = SimulationScoringMetrics(
                    is_enabled=sim_metrics.get("isEnabled", False),
                    keyword_score=sim_metrics.get("keywordScore", 0),
                    click_score=sim_metrics.get("clickScore", 0),
                    points_per_keyword=sim_metrics.get("pointsPerKeyword", 1),
                    points_per_click=sim_metrics.get("pointsPerClick", 1),
                )

            # Extract metric weightage
            metric_weightage = None
            if simulation_doc.get("metricWeightage"):
                metric_weights = simulation_doc.get("metricWeightage", {})
                metric_weightage = MetricWeightage(
                    click_accuracy=metric_weights.get("clickAccuracy", 0),
                    keyword_accuracy=metric_weights.get("keywordAccuracy", 0),
                    data_entry_accuracy=metric_weights.get(
                        "dataEntryAccuracy", 0),
                    contextual_accuracy=metric_weights.get(
                        "contextualAccuracy", 0),
                    sentiment_measures=metric_weights.get(
                        "sentimentMeasures", 0),
                )

            simulation = SimulationData(
                id=str(simulation_doc["_id"]),
                sim_name=simulation_doc.get("name", ""),
                version=str(simulation_doc.get("version", "1")),
                sim_type=simulation_doc.get("type", ""),
                status=simulation_doc.get("status", ""),
                tags=simulation_doc.get("tags", []),
                est_time=""
                if simulation_doc.get("estimatedTimeToAttemptInMins") in [
                    0, "0", None, ""
                ] else str(simulation_doc.get("estimatedTimeToAttemptInMins")),
                last_modified=simulation_doc.get(
                    "lastModified", datetime.utcnow()).isoformat(),
                modified_by=simulation_doc.get("lastModifiedBy", ""),
                created_on=simulation_doc.get("createdOn",
                                              datetime.utcnow()).isoformat(),
                created_by=simulation_doc.get("createdBy", ""),
                islocked=simulation_doc.get("isLocked", False),
                division_id=simulation_doc.get("divisionId", ""),
                department_id=simulation_doc.get("departmentId", ""),
                script=simulation_doc.get("script", []),
                lvl1=simulation_doc.get("lvl1", {}),
                lvl2=simulation_doc.get("lvl2", {}),
                lvl3=simulation_doc.get("lvl3", {}),
                slidesData=simulation_doc.get("slidesData", []),
                simulation_scoring_metrics=simulation_scoring_metrics,
                metric_weightage=metric_weightage,
            )

            images = []
            if simulation_doc.get("slidesData"):
                for slide in simulation_doc["slidesData"]:
                    if slide.get("imageId"):
                        try:
                            image_id = slide["imageId"]
                            image_doc = await self.db.images.find_one(
                                {"imageId": image_id})
                            if image_doc:
                                images.append({
                                    "image_id":
                                    slide["imageId"],
                                    "image_data":
                                    base64.b64encode(
                                        image_doc["data"]).decode("utf-8"),
                                })
                        except Exception as image_err:
                            logger.warning(
                                f"Failed to load image for slide: {image_err}")

            logger.info(
                f"Visual-chat preview for sim {sim_id} prepared successfully.")
            return StartVisualChatPreviewResponse(simulation=simulation,
                                                  images=images)

        except HTTPException as he:
            logger.error(
                f"HTTPException in start_visual_chat_preview: {he.detail}",
                exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error starting visual-chat preview: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error starting visual-chat preview: {str(e)}")

    async def start_visual_preview(self, sim_id: str,
                                   user_id: str) -> StartVisualPreviewResponse:
        logger.info(f"Starting visual preview for simulation {sim_id}")
        try:
            sim_id_object = ObjectId(sim_id)

            simulation_doc = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation_doc:
                logger.warning(
                    f"Simulation {sim_id} not found for visual preview.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            # Extract simulation scoring metrics with new fields
            simulation_scoring_metrics = None
            if simulation_doc.get("simulationScoringMetrics"):
                sim_metrics = simulation_doc.get("simulationScoringMetrics",
                                                 {})
                simulation_scoring_metrics = SimulationScoringMetrics(
                    is_enabled=sim_metrics.get("isEnabled", False),
                    keyword_score=sim_metrics.get("keywordScore", 0),
                    click_score=sim_metrics.get("clickScore", 0),
                    points_per_keyword=sim_metrics.get("pointsPerKeyword", 1),
                    points_per_click=sim_metrics.get("pointsPerClick", 1),
                )

            # Extract metric weightage
            metric_weightage = None
            if simulation_doc.get("metricWeightage"):
                metric_weights = simulation_doc.get("metricWeightage", {})
                metric_weightage = MetricWeightage(
                    click_accuracy=metric_weights.get("clickAccuracy", 0),
                    keyword_accuracy=metric_weights.get("keywordAccuracy", 0),
                    data_entry_accuracy=metric_weights.get(
                        "dataEntryAccuracy", 0),
                    contextual_accuracy=metric_weights.get(
                        "contextualAccuracy", 0),
                    sentiment_measures=metric_weights.get(
                        "sentimentMeasures", 0),
                )

            simulation = SimulationData(
                id=str(simulation_doc["_id"]),
                sim_name=simulation_doc.get("name", ""),
                version=str(simulation_doc.get("version", "1")),
                sim_type=simulation_doc.get("type", ""),
                status=simulation_doc.get("status", ""),
                tags=simulation_doc.get("tags", []),
                est_time=""
                if simulation_doc.get("estimatedTimeToAttemptInMins") in [
                    0, "0", None, ""
                ] else str(simulation_doc.get("estimatedTimeToAttemptInMins")),
                last_modified=simulation_doc.get(
                    "lastModified", datetime.utcnow()).isoformat(),
                modified_by=simulation_doc.get("lastModifiedBy", ""),
                created_on=simulation_doc.get("createdOn",
                                              datetime.utcnow()).isoformat(),
                created_by=simulation_doc.get("createdBy", ""),
                islocked=simulation_doc.get("isLocked", False),
                division_id=simulation_doc.get("divisionId", ""),
                department_id=simulation_doc.get("departmentId", ""),
                script=simulation_doc.get("script", []),
                lvl1=simulation_doc.get("lvl1", {}),
                lvl2=simulation_doc.get("lvl2", {}),
                lvl3=simulation_doc.get("lvl3", {}),
                slidesData=simulation_doc.get("slidesData", []),
                simulation_scoring_metrics=simulation_scoring_metrics,
                metric_weightage=metric_weightage,
            )

            images = []
            if simulation_doc.get("slidesData"):
                for slide in simulation_doc["slidesData"]:
                    if slide.get("imageId"):
                        try:
                            image_id = slide["imageId"]
                            image_doc = await self.db.images.find_one(
                                {"imageId": image_id})
                            if image_doc:
                                images.append({
                                    "image_id":
                                    slide["imageId"],
                                    "image_data":
                                    base64.b64encode(
                                        image_doc["data"]).decode("utf-8"),
                                })
                        except Exception as image_err:
                            logger.warning(
                                f"Failed to load image for slide: {image_err}")

            logger.info(
                f"Visual preview for sim {sim_id} prepared successfully.")
            return StartVisualPreviewResponse(simulation=simulation,
                                              images=images)

        except HTTPException as he:
            logger.error(f"HTTPException in start_visual_preview: {he.detail}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error starting visual preview: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error starting visual preview: {str(e)}")

    async def _create_retell_llm(self,
                                 prompt: str,
                                 assistant_first: bool = False) -> Dict:
        """Create a new Retell LLM"""
        logger.info("Creating Retell LLM.")
        logger.debug(f"Prompt: {prompt[:100]}...")  # Show first 100 chars
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {RETELL_API_KEY}',
                    'Content-Type': 'application/json'
                }
                data = {"general_prompt": prompt, "model": "gpt-4.1"}

                # Add begin_message field if trainee speaks first
                if assistant_first:
                    data["begin_message"] = ""

                async with session.post(
                        'https://api.retellai.com/create-retell-llm',
                        headers=headers,
                        json=data) as response:
                    if response.status != 201:
                        logger.error(
                            f"Failed to create Retell LLM. Status: {response.status}"
                        )
                        raise HTTPException(
                            status_code=response.status,
                            detail="Failed to create Retell LLM")
                    resp_json = await response.json()
                    logger.info("Retell LLM created successfully.")
                    return resp_json
        except Exception as e:
            logger.error(f"Error creating Retell LLM: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error creating Retell LLM: {str(e)}")

    async def _create_retell_agent(self, llm_id: str, voice_id: str) -> Dict:
        """Create a new Retell Agent"""
        logger.info("Creating Retell Agent.")
        logger.debug(f"LLM ID: {llm_id}, Voice ID: {voice_id}")
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {RETELL_API_KEY}',
                    'Content-Type': 'application/json'
                }

                data = {
                    "response_engine": {
                        "llm_id": llm_id,
                        "type": "retell-llm"
                    },
                    "voice_id": voice_id
                }

                async with session.post(
                        'https://api.retellai.com/create-agent',
                        headers=headers,
                        json=data) as response:
                    if response.status != 201:
                        logger.error(
                            f"Failed to create Retell Agent. Status: {response.status}"
                        )
                        raise HTTPException(
                            status_code=response.status,
                            detail="Failed to create Retell Agent")

                    resp_json = await response.json()
                    logger.info("Retell Agent created successfully.")
                    return resp_json

        except Exception as e:
            logger.error(f"Error creating Retell Agent: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error creating Retell Agent: {str(e)}")

    async def generate_simulation_prompt(self, script: List[Dict]) -> str:
        """Generate simulation prompt using the template without Azure OpenAI"""
        logger.info("Generating simulation prompt from script.")
        logger.debug(f"Script length: {len(script)} items.")
        try:
            # Build the conversation string from the script
            conversation = "\n".join(
                [f"{s.role}: {s.script_sentence}" for s in script])

            # Use the provided prompt template and insert the script
            prompt_template = """**Instructions**
    You are playing the role of a CUSTOMER interacting with a customer service representative. Follow these guidelines exactly:
    1. You will ONLY play the customer role. NEVER switch to playing the customer service representative under any circumstances.
    2. When the human provides a line that matches the customer service agent's dialogue in the script, respond ONLY with the customer's next line EXACTLY as written in the script below.
    3. If the human says something that doesn't match the script exactly, or if they ask a question not in the script:
       * Stay in character as the customer
       * Improvise a response that aligns with your character's situation and concerns
       * Keep your improvised response brief and focused on getting back to the script
       * NEVER take on the role of the customer service representative
    4. Your goal is to realistically portray the customer's side of this conversation, following the script precisely when applicable.
    5. If the conversation reaches the end of the script, continue to respond as the customer would, maintaining the same tone and concerns established in the script.
    **Your Character**
    You are a customer with the specific concerns and personality shown in the script. Maintain this characterization throughout the entire conversation.
    **Important**
    * You are ONLY the CUSTOMER
    * The human is ALWAYS the customer service representative
    * NEVER provide both sides of the conversation
    * NEVER explain that you're following a script
    * NEVER break character
    **Script**
    {script}
    Remember: You are ONLY the customer. The human is playing the customer service representative. Follow the script exactly when applicable, and stay in character when improvising."""

            # Insert the actual script into the template
            result = prompt_template.format(script=conversation)

            logger.info("Simulation prompt generated successfully.")
            return result
        except Exception as e:
            logger.error(f"Error generating simulation prompt: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error generating simulation prompt: {str(e)}")

    async def _generate_simulation_prompt(self, script: List[Dict]) -> str:
        """Generate simulation prompt using Azure OpenAI"""
        logger.info("Generating simulation prompt from script.")
        logger.debug(f"Script length: {len(script)} items.")
        try:
            history = ChatHistory()

            system_message = (
                "Create a detailed prompt for an AI agent. You will be given a script of a dialog between a customer "
                "and a customer service agent. You need to create a prompt so that the AI should play the role of the customer. "
                "Make sure that in the prompt you mention that the AI needs to follow the script exactly verbatim. In other words, "
                "include the complete verbatim script in your response. If the user gives an input that is not included in the script "
                "then the AI should invent details and answer smartly.")
            history.add_system_message(system_message)

            conversation = "\n".join(
                [f"{s.role}: {s.script_sentence}" for s in script])
            inputprompt = f"Script: {conversation}"
            history.add_user_message(inputprompt)

            result = await self.chat_completion.get_chat_message_content(
                history, settings=self.execution_settings)
            logger.info("Simulation prompt generated successfully.")
            return str(result)

        except Exception as e:
            logger.error(f"Error generating simulation prompt: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error generating simulation prompt: {str(e)}")

    async def start_audio_simulation_preview(self, sim_id: str,
                                             user_id: str) -> Dict:
        """Start an audio simulation preview"""
        logger.info(
            f"Starting audio simulation preview for sim_id={sim_id}, user_id={user_id}"
        )
        try:
            sim_id_object = ObjectId(sim_id)
            simulation = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation:
                logger.warning(
                    f"Simulation {sim_id} not found for audio preview.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")
            agent_id = simulation.get("agentId")
            if not agent_id:
                logger.warning(
                    "Simulation does not have an agent configured for audio preview."
                )
                raise HTTPException(
                    status_code=400,
                    detail="Simulation does not have an agent configured")

            web_call = await self._create_web_call(agent_id)

            # Extract simulation details for response (same as in start_audio_simulation)
            sim_details = {
                "sim_name":
                simulation.get("name", ""),
                "version":
                simulation.get("version", ""),
                "lvl1":
                simulation.get("lvl1", {}),
                "lvl2":
                simulation.get("lvl2", {}),
                "lvl3":
                simulation.get("lvl3", {}),
                "sim_type":
                simulation.get("type", ""),
                "status":
                simulation.get("status", ""),
                "tags":
                simulation.get("tags", []),
                "est_time":
                simulation.get("est_time", ""),
                "last_modified":
                simulation.get("last_modified", ""),
                "modified_by":
                simulation.get("modified_by", ""),
                "created_on":
                simulation.get("created_on", ""),
                "created_by":
                simulation.get("created_by", ""),
                "islocked":
                simulation.get("islocked", False),
                "division_id":
                simulation.get("divisionId", ""),
                "department_id":
                simulation.get("departmentId", ""),
                "voice_id":
                simulation.get("voice_id"),
                "script":
                simulation.get("script"),
                "slidesData":
                simulation.get("slidesData"),
                "prompt":
                simulation.get("prompt"),
                "key_objectives":
                simulation.get("keyObjectives"),
                "overview_video":
                simulation.get("overviewVideo"),
                "quick_tips":
                simulation.get("quickTips"),
                "simulation_completion_repetition":
                simulation.get("simulationCompletionRepetition"),
                "simulation_max_repetition":
                simulation.get("simulation_max_repetition"),
                "final_simulation_score_criteria":
                simulation.get("finalSimulationScoreCriteria"),
                "simulation_scoring_metrics":
                simulation.get("simulation_scoring_metrics"),
                "metric_weightage":
                simulation.get("metric_weightage"),
                "sim_practice":
                simulation.get("simPractice"),
                "estimated_time_to_attempt_in_mins":
                simulation.get("estimatedTimeToAttemptInMins"),
                "mood":
                simulation.get("mood"),
                "voice_speed":
                simulation.get("voice_speed"),
            }

            logger.info(
                f"Audio simulation preview created. Access token: {web_call['access_token']}"
            )
            return {
                "access_token": web_call["access_token"],
                "simulation_details": sim_details,
            }
        except HTTPException as he:
            logger.error(
                f"HTTPException in start_audio_simulation_preview: {he.detail}",
                exc_info=True,
            )
            raise he
        except Exception as e:
            logger.error(f"Error starting audio simulation preview: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error starting audio simulation preview: {str(e)}")

    async def _create_web_call(self, agent_id: str) -> Dict:
        """Create a web call using Retell API"""
        logger.info(f"Creating web call for agent_id={agent_id}")
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {RETELL_API_KEY}',
                    'Content-Type': 'application/json'
                }

                data = {"agent_id": agent_id}

                async with session.post(
                        'https://api.retellai.com/v2/create-web-call',
                        headers=headers,
                        json=data) as response:
                    if response.status != 201:
                        logger.error(
                            f"Failed to create web call. Status: {response.status}"
                        )
                        raise HTTPException(status_code=response.status,
                                            detail="Failed to create web call")

                    resp_json = await response.json()
                    logger.info("Web call created successfully.")
                    return resp_json

        except Exception as e:
            logger.error(f"Error creating web call: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error creating web call: {str(e)}")

    async def fetch_simulations(
            self,
            user_id: str,
            workspace: str,
            pagination: Optional[PaginationParams] = None) -> Dict[str, any]:
        """Fetch all simulations with pagination and filtering

        Returns a dictionary with:
        - simulations: List of SimulationData objects
        - total_count: Total number of simulations matching the query
        """
        logger.info(
            f"Fetching simulations for user_id={user_id} in workspace={workspace} with pagination")
        try:
            # Build query filter based on pagination parameters
            query = {"workspace": workspace}  # Add workspace filter

            if pagination:
                logger.debug(f"Applying pagination parameters: {pagination}")

                # Apply search filter if provided
                if pagination.search:
                    search_regex = {
                        "$regex": pagination.search,
                        "$options": "i"
                    }
                    query["$or"] = [{
                        "name": search_regex
                    }, {
                        "tags": search_regex
                    }]

                # Apply tag filter if provided
                if pagination.tags and len(pagination.tags) > 0:
                    query["tags"] = {"$in": pagination.tags}

                # Apply division filter if provided
                if pagination.division:
                    query["divisionId"] = pagination.division

                # Apply department filter if provided
                if pagination.department:
                    query["departmentId"] = pagination.department

                # Apply status filter if provided
                if pagination.status and len(pagination.status) > 0:
                    query["status"] = {"$in": pagination.status}

                # Apply simulation type filter if provided
                if pagination.simType:
                    query["type"] = pagination.simType

                # Apply created by filter if provided
                if pagination.createdBy:
                    query["createdBy"] = pagination.createdBy

                # Apply modified by filter if provided
                if pagination.modifiedBy:
                    query["lastModifiedBy"] = pagination.modifiedBy

                # Apply created date range filters if provided
                date_filter = {}
                if pagination.createdFrom:
                    date_filter["$gte"] = pagination.createdFrom
                if pagination.createdTo:
                    date_filter["$lte"] = pagination.createdTo
                if date_filter:
                    query["createdOn"] = date_filter

                # Apply modified date range filters if provided
                modified_date_filter = {}
                if pagination.modifiedFrom:
                    modified_date_filter["$gte"] = pagination.modifiedFrom
                if pagination.modifiedTo:
                    modified_date_filter["$lte"] = pagination.modifiedTo
                if modified_date_filter:
                    query["lastModified"] = modified_date_filter

            # Determine sort options
            sort_options = []
            if pagination and pagination.sortBy:
                # Convert camelCase sort field to database field name if needed
                sort_field_mapping = {
                    "simName": "name",
                    "simType": "type",
                    "lastModified": "lastModified",
                    "createdOn": "createdOn",
                    "modifiedBy": "lastModifiedBy",
                    "createdBy": "createdBy",
                    # Add other mappings as needed
                }
                db_field = sort_field_mapping.get(pagination.sortBy,
                                                  pagination.sortBy)
                sort_direction = 1 if pagination.sortDir == "asc" else -1
                sort_options.append((db_field, sort_direction))
            else:
                # Default sort by lastModified
                sort_options.append(("lastModified", -1))

            # Calculate pagination
            skip = 0
            limit = 50  # Default limit

            if pagination:
                limit = pagination.pagesize
                skip = (pagination.page - 1) * limit

            logger.debug(f"Query filter: {query}")
            logger.debug(f"Sort options: {sort_options}")
            logger.debug(f"Skip: {skip}, Limit: {limit}")

            # Execute the query with pagination
            cursor = (self.db.simulations.find(query).sort(sort_options).skip(
                skip).limit(limit))
            simulations = []

            async for doc in cursor:
                # Extract simulation scoring metrics with new fields
                simulation_scoring_metrics = None
                if doc.get("simulationScoringMetrics"):
                    sim_metrics = doc.get("simulationScoringMetrics", {})
                    simulation_scoring_metrics = SimulationScoringMetrics(
                        is_enabled=sim_metrics.get("isEnabled", False),
                        keyword_score=sim_metrics.get("keywordScore", 0),
                        click_score=sim_metrics.get("clickScore", 0),
                        points_per_keyword=sim_metrics.get(
                            "pointsPerKeyword", 1),
                        points_per_click=sim_metrics.get("pointsPerClick", 1),
                    )

                # Extract metric weightage
                metric_weightage = None
                if doc.get("metricWeightage"):
                    metric_weights = doc.get("metricWeightage", {})
                    metric_weightage = MetricWeightage(
                        click_accuracy=metric_weights.get("clickAccuracy", 0),
                        keyword_accuracy=metric_weights.get(
                            "keywordAccuracy", 0),
                        data_entry_accuracy=metric_weights.get(
                            "dataEntryAccuracy", 0),
                        contextual_accuracy=metric_weights.get(
                            "contextualAccuracy", 0),
                        sentiment_measures=metric_weights.get(
                            "sentimentMeasures", 0),
                    )

                simulation = SimulationData(
                    id=str(doc["_id"]),
                    sim_name=doc.get("name", ""),
                    version=str(doc.get("version", "1")),
                    lvl1=doc.get("lvl1", {}),
                    lvl2=doc.get("lvl2", {}),
                    lvl3=doc.get("lvl3", {}),
                    sim_type=doc.get("type", ""),
                    status=doc.get("status", ""),
                    tags=doc.get("tags", []),
                    est_time="" if doc.get("estimatedTimeToAttemptInMins") in [
                        0, "0", None, ""
                    ] else str(doc.get("estimatedTimeToAttemptInMins")),
                    last_modified=doc.get("lastModified",
                                          datetime.utcnow()).isoformat(),
                    modified_by=doc.get("lastModifiedBy", ""),
                    created_on=doc.get("createdOn",
                                       datetime.utcnow()).isoformat(),
                    created_by=doc.get("createdBy", ""),
                    islocked=doc.get("isLocked", False),
                    division_id=doc.get("divisionId", ""),
                    department_id=doc.get("departmentId", ""),
                    script=doc.get("script", None),
                    slidesData=doc.get("slidesData", None),
                    simulation_scoring_metrics=simulation_scoring_metrics,
                    metric_weightage=metric_weightage,
                )
                simulations.append(simulation)

            # Get total count for pagination metadata
            total_count = await self.db.simulations.count_documents(query)

            logger.info(
                f"Total simulations fetched: {len(simulations)}, Total count: {total_count}"
            )
            return {"simulations": simulations, "total_count": total_count}

        except Exception as e:
            logger.error(f"Error fetching simulations: {str(e)}",
                         exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error fetching simulations: {str(e)}")

    async def get_simulation_by_id(self,
                                   sim_id: str,
                                   workspace: str) -> SimulationByIDResponse:
        logger.info(f"Fetching simulation by ID: {sim_id} in workspace {workspace}")
        try:
            sim_id_object = ObjectId(sim_id)

            simulation_doc = await self.db.simulations.find_one({
                "_id": sim_id_object,
                "workspace": workspace
            })
            if not simulation_doc:
                logger.warning(
                    f"Simulation {sim_id} not found when fetching by ID in workspace {workspace}.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found in workspace {workspace}")

            # Extract simulation scoring metrics with new fields
            simulation_scoring_metrics = None
            if simulation_doc.get("simulationScoringMetrics"):
                sim_metrics = simulation_doc.get("simulationScoringMetrics",
                                                 {})
                simulation_scoring_metrics = SimulationScoringMetrics(
                    is_enabled=sim_metrics.get("isEnabled", False),
                    keyword_score=sim_metrics.get("keywordScore", 0),
                    click_score=sim_metrics.get("clickScore", 0),
                    points_per_keyword=sim_metrics.get("pointsPerKeyword", 1),
                    points_per_click=sim_metrics.get("pointsPerClick", 1),
                )

            # Extract metric weightage
            metric_weightage = None
            if simulation_doc.get("metricWeightage"):
                metric_weights = simulation_doc.get("metricWeightage", {})
                metric_weightage = MetricWeightage(
                    click_accuracy=metric_weights.get("clickAccuracy", 0),
                    keyword_accuracy=metric_weights.get("keywordAccuracy", 0),
                    data_entry_accuracy=metric_weights.get(
                        "dataEntryAccuracy", 0),
                    contextual_accuracy=metric_weights.get(
                        "contextualAccuracy", 0),
                    sentiment_measures=metric_weights.get(
                        "sentimentMeasures", 0),
                )

            simulation = SimulationData(
                id=str(simulation_doc["_id"]),
                sim_name=simulation_doc.get("name", ""),
                version=str(simulation_doc.get("version", "1")),
                sim_type=simulation_doc.get("type", ""),
                status=simulation_doc.get("status", ""),
                tags=simulation_doc.get("tags", []),
                est_time=""
                if simulation_doc.get("estimatedTimeToAttemptInMins") in [
                    0, "0", None, ""
                ] else str(simulation_doc.get("estimatedTimeToAttemptInMins")),
                last_modified=simulation_doc.get(
                    "lastModified", datetime.utcnow()).isoformat(),
                modified_by=simulation_doc.get("lastModifiedBy", ""),
                created_on=simulation_doc.get("createdOn",
                                              datetime.utcnow()).isoformat(),
                created_by=simulation_doc.get("createdBy", ""),
                islocked=simulation_doc.get("isLocked", False),
                division_id=simulation_doc.get("divisionId", ""),
                department_id=simulation_doc.get("departmentId", ""),
                script=simulation_doc.get("script", []),
                voice_id=simulation_doc.get("voiceId", "11labs-Adrian"),
                lvl1=simulation_doc.get("lvl1", {}),
                lvl2=simulation_doc.get("lvl2", {}),
                lvl3=simulation_doc.get("lvl3", {}),
                slidesData=simulation_doc.get("slidesData", []),
                key_objectives=simulation_doc.get("keyObjectives", []),
                overview_video=simulation_doc.get("overviewVideo", ""),
                quick_tips=simulation_doc.get("quickTips", []),
                final_simulation_score_criteria=simulation_doc.get(
                    "finalSimulationScoreCriteria", ""),
                simulation_completion_repetition=simulation_doc.get(
                    "simulationCompletionRepetition", 1),
                simulation_max_repetition=simulation_doc.get(
                    "simulationMaxRepetition", 1),
                simulation_scoring_metrics=simulation_scoring_metrics,
                metric_weightage=metric_weightage,
                sim_practice=simulation_doc.get("simPractice", {}),
                prompt=simulation_doc.get("prompt", ""),
            )

            images = []
            if simulation_doc.get("slidesData"):
                for slide in simulation_doc["slidesData"]:
                    if slide.get("imageId"):
                        try:
                            image_id = slide["imageId"]
                            image_doc = await self.db.images.find_one(
                                {"imageId": image_id})
                            if image_doc:
                                images.append({
                                    "image_id":
                                    slide["imageId"],
                                    "image_data":
                                    base64.b64encode(
                                        image_doc["data"]).decode("utf-8"),
                                })
                        except Exception as image_err:
                            logger.warning(
                                f"Failed to load image for slide: {image_err}")

            logger.info(f"Simulation {sim_id} fetched successfully.")
            return SimulationByIDResponse(simulation=simulation, images=images)

        except HTTPException as he:
            logger.error(f"HTTPException in get_simulation_by_id: {he.detail}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error fetching simulation by ID: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching simulation by ID: {str(e)}")

    async def _get_simulation_by_id_internal(self, sim_id: str) -> SimulationByIDResponse:
        """Internal method to get simulation by ID without workspace filtering"""
        logger.info(f"Fetching simulation by ID internally: {sim_id}")
        try:
            sim_id_object = ObjectId(sim_id)

            simulation_doc = await self.db.simulations.find_one({"_id": sim_id_object})
            if not simulation_doc:
                logger.warning(f"Simulation {sim_id} not found when fetching by ID internally.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            # Extract simulation scoring metrics with new fields
            simulation_scoring_metrics = None
            if simulation_doc.get("simulationScoringMetrics"):
                sim_metrics = simulation_doc.get("simulationScoringMetrics", {})
                simulation_scoring_metrics = SimulationScoringMetrics(
                    is_enabled=sim_metrics.get("isEnabled", False),
                    keyword_score=sim_metrics.get("keywordScore", 0),
                    click_score=sim_metrics.get("clickScore", 0),
                    points_per_keyword=sim_metrics.get("pointsPerKeyword", 1),
                    points_per_click=sim_metrics.get("pointsPerClick", 1),
                )

            # Extract metric weightage
            metric_weightage = None
            if simulation_doc.get("metricWeightage"):
                metric_weights = simulation_doc.get("metricWeightage", {})
                metric_weightage = MetricWeightage(
                    click_accuracy=metric_weights.get("clickAccuracy", 0),
                    keyword_accuracy=metric_weights.get("keywordAccuracy", 0),
                    data_entry_accuracy=metric_weights.get("dataEntryAccuracy", 0),
                    contextual_accuracy=metric_weights.get("contextualAccuracy", 0),
                    sentiment_measures=metric_weights.get("sentimentMeasures", 0),
                )

            simulation = SimulationData(
                id=str(simulation_doc["_id"]),
                sim_name=simulation_doc.get("name", ""),
                version=str(simulation_doc.get("version", "1")),
                sim_type=simulation_doc.get("type", ""),
                status=simulation_doc.get("status", ""),
                tags=simulation_doc.get("tags", []),
                est_time=""
                if simulation_doc.get("estimatedTimeToAttemptInMins") in [0, "0", None, ""]
                else str(simulation_doc.get("estimatedTimeToAttemptInMins")),
                last_modified=simulation_doc.get("lastModified", datetime.utcnow()).isoformat(),
                modified_by=simulation_doc.get("lastModifiedBy", ""),
                created_on=simulation_doc.get("createdOn", datetime.utcnow()).isoformat(),
                created_by=simulation_doc.get("createdBy", ""),
                islocked=simulation_doc.get("isLocked", False),
                division_id=simulation_doc.get("divisionId", ""),
                department_id=simulation_doc.get("departmentId", ""),
                script=simulation_doc.get("script", []),
                voice_id=simulation_doc.get("voiceId", "11labs-Adrian"),
                lvl1=simulation_doc.get("lvl1", {}),
                lvl2=simulation_doc.get("lvl2", {}),
                lvl3=simulation_doc.get("lvl3", {}),
                slidesData=simulation_doc.get("slidesData", []),
                key_objectives=simulation_doc.get("keyObjectives", []),
                overview_video=simulation_doc.get("overviewVideo", ""),
                quick_tips=simulation_doc.get("quickTips", []),
                final_simulation_score_criteria=simulation_doc.get("finalSimulationScoreCriteria", ""),
                simulation_completion_repetition=simulation_doc.get("simulationCompletionRepetition", 1),
                simulation_max_repetition=simulation_doc.get("simulationMaxRepetition", 1),
                simulation_scoring_metrics=simulation_scoring_metrics,
                metric_weightage=metric_weightage,
                sim_practice=simulation_doc.get("simPractice", {}),
                prompt=simulation_doc.get("prompt", ""),
            )

            images = []
            if simulation_doc.get("slidesData"):
                for slide in simulation_doc["slidesData"]:
                    if slide.get("imageId"):
                        try:
                            image_id = slide["imageId"]
                            image_doc = await self.db.images.find_one({"imageId": image_id})
                            if image_doc:
                                images.append({
                                    "image_id": slide["imageId"],
                                    "image_data": base64.b64encode(image_doc["data"]).decode("utf-8"),
                                })
                        except Exception as image_err:
                            logger.warning(f"Failed to load image for slide: {image_err}")

            logger.info(f"Simulation {sim_id} fetched successfully.")
            return SimulationByIDResponse(simulation=simulation, images=images)

        except HTTPException as he:
            logger.error(f"HTTPException in _get_simulation_by_id_internal: {he.detail}", exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error fetching simulation by ID internally: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching simulation by ID: {str(e)}")

    async def end_visual_audio_attempt(
            self, user_id: str, simulation_id: str,
            usersimulationprogress_id: str,
            userAttemptSequence: List[AttemptModel], slides_data: Optional[List[Dict[str, Any]]]) -> EndSimulationResponse:
        logger.info(f"Ending Visual Audio Attempt: {simulation_id}")
        try:

            scores = {
                'SimAccuracy': 0,
                'KeywordScore': 0,
                'ClickScore': 0,
                'Confidence': 0,
                'Energy': 0,
                'Concentration': 0
            }

            # Use internal method that doesn't require workspace
            simulation: SimulationByIDResponse = await self._get_simulation_by_id_internal(simulation_id)

            # Keyword Scores
            # Extract transcript from slides_data if available
            transcript = ""
            if slides_data:
                transcript_parts = []

                # Iterate through slides and extract message transcriptions
                for slide in slides_data:
                    if "sequence" in slide and slide["sequence"]:
                        for item in slide["sequence"]:
                            if item.get("type") == "message":
                                # Format as "Role: Text"
                                role = item.get("role", "")
                                text = item.get("text", "")
                                if role and text:
                                    transcript_parts.append(f"{role}: {text}")

                # Join all messages into a single transcript
                if transcript_parts:
                    transcript = "\n".join(transcript_parts)
            

                original_script = [{
                    **s.dict(), "script_sentence":
                    re.sub('<.*?>', '', s.script_sentence)
                } for s in simulation.simulation.script]

                keyword_score = await self.scoring_service.get_keyword_score_analysis_regex(
                    original_script, transcript)
                if keyword_score:
                    scores['KeywordScore'] = keyword_score.keyword_score

            #Click Accurracy
            wrong_click = sum(
                len(userAttempt.wrong_clicks)
                for userAttempt in userAttemptSequence
                if userAttempt.wrong_clicks)
            correct_click = sum(
                1 for userAttempt in userAttemptSequence
                if userAttempt.type == 'hotspot' and userAttempt.isClicked)
            total_clicks = wrong_click + correct_click
            click_score = (correct_click /
                           total_clicks) * 100 if total_clicks > 0 else 0
            scores['ClickScore'] = click_score

            update_doc = {
                "status":
                "completed",
                "transcript":
                "",
                "audioUrl":
                "",
                "duration":
                0,
                "scores":
                scores,
                "completedAt":
                datetime.utcnow(),
                "lastModifiedAt":
                datetime.utcnow(),
                "userAttemptSequence":
                [attempt.dict() for attempt in userAttemptSequence],
                "transcription_data": slides_data
            }

            response = await self.db.user_sim_progress.update_one(
                {"_id": ObjectId(usersimulationprogress_id)},
                {"$set": update_doc})

            print("response ====== ", response)

            return EndSimulationResponse(id=usersimulationprogress_id,
                                         status="success",
                                         scores={},
                                         duration=0,
                                         transcript="",
                                         audio_url="")
        except Exception as e:
            logger.error(f"Error End Visual Audio Attempt by ID: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error End Visual Audio Attempt by ID: {str(e)}")

    async def end_visual_chat_attempt(
            self, user_id: str, simulation_id: str,
            usersimulationprogress_id: str,
            userAttemptSequence: List[AttemptModel]) -> EndSimulationResponse:
        logger.info(f"Ending Visual Chat Attempt: {simulation_id}")
        try:

            transcript = ""
            scores = {
                'SimAccuracy': 0,
                'KeywordScore': 0,
                'ClickScore': 0,
                'DataAccuracy': 0,
                'Confidence': 0,
                'Energy': 0,
                'Concentration': 0
            }

            # Filter message entries
            messages = [
                item for item in userAttemptSequence if item.type == "message"
            ]

            for message in messages:
                role = message.role if message.role is not None else "Unknown"
                user_text = message.userText.strip()
                if user_text:
                    transcript = transcript + (f"{role}: {user_text}\n")

            # Use internal method that doesn't require workspace
            simulation: SimulationByIDResponse = await self._get_simulation_by_id_internal(simulation_id)
            main_script = simulation.simulation.script
            slide_data_script = []
            data_accuracy_script = {}

            for slide in simulation.simulation.slidesData:
                for seq in slide.sequence:
                    if seq.type == 'message':
                        slide_data_script.append({
                            'script_sentence': seq.text,
                            'role': seq.role,
                            'keywords': []
                        })
                    if seq.type == 'hotspot' and (
                            seq.hotspotType == 'textfield'
                            or seq.hotspotType == 'dropdown'):
                        data_accuracy_script[seq.id] = seq

            for index, slide_script in enumerate(slide_data_script):
                for script in main_script:
                    if slide_script['script_sentence'].strip() == re.sub(
                            '<.*?>', '', script.script_sentence).strip():
                        if script.keywords:
                            slide_data_script[index][
                                'keywords'] = script.keywords.copy()

            keyword_score = await self.scoring_service.get_keyword_score_analysis_regex(
                slide_data_script, transcript)
            if keyword_score:
                scores['KeywordScore'] = keyword_score.keyword_score

            #Click Accurracy
            wrong_click = sum(
                len(userAttempt.wrong_clicks)
                for userAttempt in userAttemptSequence
                if userAttempt.wrong_clicks)
            correct_click = sum(
                1 for userAttempt in userAttemptSequence
                if userAttempt.type == 'hotspot' and userAttempt.isClicked)
            total_clicks = wrong_click + correct_click
            click_score = (correct_click /
                           total_clicks) * 100 if total_clicks > 0 else 0
            scores['ClickScore'] = click_score

            #DataAccuracy - get hotspot with textField
            textfield_hotspots = [
                item for item in userAttemptSequence
                if item.type == "hotspot" and (
                    item.hotspotType == 'textfield'
                    or item.hotspotType == 'dropdown')
            ]
            correct_data = sum(
                1 for textfield_hotspot in textfield_hotspots
                if textfield_hotspot.userInput == data_accuracy_script[
                    textfield_hotspot.id].settings["expectedValue"])
            wrong_data = len(textfield_hotspots) - correct_data
            total_data = correct_data + wrong_data
            data_accuracy_score = (correct_data /
                                   total_data) * 100 if total_data > 0 else 0
            scores['DataAccuracy'] = data_accuracy_score

            update_doc = {
                "status":
                "completed",
                "transcript":
                transcript,
                "chatHistory": [],
                "duration":
                0,
                "scores":
                scores,
                "completedAt":
                datetime.utcnow(),
                "lastModifiedAt":
                datetime.utcnow(),
                "userAttemptSequence":
                [attempt.dict() for attempt in userAttemptSequence]
            }

            await self.db.user_sim_progress.update_one(
                {"_id": ObjectId(usersimulationprogress_id)},
                {"$set": update_doc})

            return EndSimulationResponse(id=usersimulationprogress_id,
                                         status="success",
                                         scores=scores,
                                         duration=0,
                                         transcript=transcript,
                                         audio_url="")
        except Exception as e:
            logger.error(f"Error ending Visual Chat Attempt by ID: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error ending Visual Chat Attempt by ID: {str(e)}")

    async def end_chat_simulation(
            self, user_id: str, simulation_id: str,
            usersimulationprogress_id: str,
            chat_history: List[ChatHistoryItem]) -> EndSimulationResponse:
        try:
            # Use internal method that doesn't require workspace
            sim: SimulationByIDResponse = await self._get_simulation_by_id_internal(simulation_id)
            if not sim:
                logger.warning(
                    f"Simulation {simulation_id} not found for end_chat_simulation."
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {simulation_id} not found")

            scores = {
                'SimAccuracy': 0,
                'KeywordScore': 0,
                'ClickScore': 0,
                'Confidence': 0,
                'Energy': 0,
                'Concentration': 0
            }

            original_script = [{
                **s.dict(), "script_sentence":
                re.sub('<.*?>', '', s.script_sentence)
            } for s in sim.simulation.script]

            transcript = "\n".join(f"{msg.role}: {msg.sentence}"
                                   for msg in chat_history)

            keyword_score = await self.scoring_service.get_keyword_score_analysis_regex(
                original_script, transcript)
            if keyword_score:
                scores['KeywordScore'] = keyword_score.keyword_score

            duration = 300  # 5 minutes default for chat simulations

            update_doc = {
                "status": "completed",
                "transcript": transcript,
                "chatHistory": [msg.dict() for msg in chat_history],
                "duration": duration,
                "scores": scores,
                "completedAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }

            await self.db.user_sim_progress.update_one(
                {"_id": ObjectId(usersimulationprogress_id)},
                {"$set": update_doc})

            logger.info(
                f"Chat simulation ended. ID={usersimulationprogress_id}")
            return EndSimulationResponse(id=usersimulationprogress_id,
                                         status="success",
                                         scores=scores,
                                         duration=duration,
                                         transcript=transcript,
                                         audio_url="")
        except Exception as e:
            logger.error(f"Error ending Chat Attempt by ID: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error ending Chat Attempt by ID: {str(e)}")

    async def end_audio_simulation(self, user_id: str, simulation_id: str,
                                   usersimulationprogress_id: str,
                                   call_id: str) -> EndSimulationResponse:
        try:
            await asyncio.sleep(15)
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {RETELL_API_KEY}"}
                url = f"https://api.retellai.com/v2/get-call/{call_id}"

                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(
                            f"Failed to fetch call details. Status: {response.status}"
                        )
                        raise HTTPException(
                            status_code=response.status,
                            detail="Failed to fetch call details from Retell AI"
                        )
                    call_data = await response.json()

            # Use internal method that doesn't require workspace
            sim: SimulationByIDResponse = await self._get_simulation_by_id_internal(simulation_id)
            if not sim:
                logger.warning(
                    f"Simulation {simulation_id} not found for end_chat_simulation."
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {simulation_id} not found")

            scores = {
                'SimAccuracy': 0,
                'KeywordScore': 0,
                'ClickScore': 0,
                'Confidence': 0,
                'Energy': 0,
                'Concentration': 0
            }
            original_script = [{
                **s.dict(), "script_sentence":
                re.sub('<.*?>', '', s.script_sentence)
            } for s in sim.simulation.script]
            transcript = call_data.get("transcript", "").replace(
                "User", "Customer").replace("Agent", "Trainee")

            keyword_score = await self.scoring_service.get_keyword_score_analysis_regex(
                original_script, transcript)
            if keyword_score:
                scores['KeywordScore'] = keyword_score.keyword_score

            transcriptObject = call_data.get("transcript_object", {})
            duration = (call_data.get("end_timestamp", 0) -
                        call_data.get("start_timestamp", 0)) // 1000

            update_doc = {
                "status": "completed",
                "transcript": transcript,
                "transcriptObject": transcriptObject,
                "audioUrl": call_data.get("recording_url", ""),
                "duration": duration,
                "scores": scores,
                "completedAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }

            await self.db.user_sim_progress.update_one(
                {"_id": ObjectId(usersimulationprogress_id)},
                {"$set": update_doc})

            logger.info(
                f"Audio simulation ended. ID={usersimulationprogress_id}")
            return EndSimulationResponse(id=usersimulationprogress_id,
                                         status="success",
                                         scores=scores,
                                         duration=duration,
                                         transcript=transcript,
                                         audio_url=call_data.get(
                                             "recording_url", ""))
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error ending audio simulation: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error ending audio simulation: {str(e)}")

    async def end_visual_attempt(
            self, user_id: str, simulation_id: str,
            usersimulationprogress_id: str,
            userAttemptSequence: List[AttemptModel]) -> EndSimulationResponse:
        try:
            scores = {
                'SimAccuracy': 0,
                'KeywordScore': 0,
                'ClickScore': 0,
                'Confidence': 0,
                'Energy': 0,
                'Concentration': 0
            }

            #Click Accurracy
            wrong_click = sum(
                len(userAttempt.wrong_clicks)
                for userAttempt in userAttemptSequence
                if userAttempt.wrong_clicks)
            correct_click = sum(
                1 for userAttempt in userAttemptSequence
                if userAttempt.type == 'hotspot' and userAttempt.isClicked)
            total_clicks = wrong_click + correct_click
            click_score = (correct_click /
                           total_clicks) * 100 if total_clicks > 0 else 0
            scores['ClickScore'] = click_score

            update_doc = {
                "status": "completed",
                "duration": 0,
                "scores": scores,
                "completedAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }

            await self.db.user_sim_progress.update_one(
                {"_id": ObjectId(usersimulationprogress_id)},
                {"$set": update_doc})

            return EndSimulationResponse(id=usersimulationprogress_id,
                                         status="success",
                                         scores={},
                                         duration=0,
                                         transcript="",
                                         audio_url="")
        except Exception as e:
            logger.error(f"[end_visual_attempt] {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail="Internal server error")

    async def update_image_mask(self, sim_id: str, image_id: str, masking_list: List[Dict]):
        try:
            filter_query = { "_id": ObjectId(sim_id) }
            update_query = {
                "$set": {
                    "slidesData.$[elem].masking": masking_list
                }
            }
            array_filters = [{"elem.imageId": image_id}]

            result = await self.db.simulations.update_one(filter_query, update_query, array_filters=array_filters)

            if result: 
                if result.matched_count == 0:
                    return UpdateImageMaskingObjectResponse(
                        status="failed",
                        message=f"No document found with sim_id '{sim_id}' and image_id '{image_id}'"
                    )

                return UpdateImageMaskingObjectResponse(
                    status="success",
                    message=f"Masking data updated successfully for image_id '{image_id}'."
                )
            return UpdateImageMaskingObjectResponse(
                status="failed",
                message="Failed to update masking data"
            )
                
        except Exception as e:
            logger.error(f"[update_image_masking_object] {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail="Internal server error")
        