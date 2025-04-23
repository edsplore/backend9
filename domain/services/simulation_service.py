from typing import Dict, List, Optional
import json
import aiohttp
import base64
from datetime import datetime
from bson import ObjectId
import traceback
from config import (AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_KEY,
                    AZURE_OPENAI_BASE_URL, RETELL_API_KEY)
from infrastructure.database import Database
from api.schemas.requests import (CreateSimulationRequest,
                                  UpdateSimulationRequest,
                                  CloneSimulationRequest)
from api.schemas.responses import SimulationByIDResponse, SimulationData
from fastapi import HTTPException, UploadFile
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings, )

from api.schemas.responses import (StartVisualAudioPreviewResponse,
                                   StartVisualChatPreviewResponse,
                                   StartVisualPreviewResponse, SimulationData,
                                   SimulationByIDResponse)
from bson import ObjectId

from utils.logger import Logger

# Add after imports
logger = Logger.get_logger(__name__)


class SimulationService:

    # def __init__(self):
    #     self.db = Database()
    #     # Initialize Azure OpenAI chat completion
    #     self.kernel = Kernel()
    #     self.chat_completion = AzureChatCompletion(
    #         service_id="azure_gpt4",
    #         deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
    #         endpoint=AZURE_OPENAI_BASE_URL,
    #         api_key=AZURE_OPENAI_KEY)
    #     self.kernel.add_service(self.chat_completion)
    #     self.execution_settings = AzureChatPromptExecutionSettings(
    #         service_id="azure_gpt4",
    #         ai_model_id=AZURE_OPENAI_DEPLOYMENT_NAME,
    #         temperature=0.1,
    #         top_p=1.0,
    #         max_tokens=4096)

    def __init__(self):
        logger.info("Initializing SimulationService...")

        try:
            logger.debug("Connecting to database...")
            self.db = Database()
            logger.info("Database initialized successfully.")
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

    async def create_simulation(self,
                                request: CreateSimulationRequest) -> Dict:
        """Create a new simulation"""
        logger.info(f"Creating new simulation for user: {request.user_id}")
        logger.debug(f"CreateSimulationRequest data: {request.dict()}")
        try:
            # Create simulation document
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
                "tags": request.tags
            }

            # Insert into database
            result = await self.db.simulations.insert_one(simulation_doc)
            logger.info(
                f"Successfully created simulation with ID: {result.inserted_id}"
            )
            return {"id": str(result.inserted_id), "status": "success"}

        except Exception as e:
            logger.error(f"Error creating simulation: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error creating simulation: {str(e)}")

    async def clone_simulation(self, request: CloneSimulationRequest) -> Dict:
        """Clone an existing simulation"""
        logger.info(
            f"Cloning simulation for user: {request.user_id}, sim_id={request.simulation_id}"
        )
        logger.debug(f"CloneSimulationRequest data: {request.dict()}")
        try:
            # Get existing simulation
            sim_id_object = ObjectId(request.simulation_id)
            existing_sim = await self.db.simulations.find_one(
                {"_id": sim_id_object})

            if not existing_sim:
                logger.warning(
                    f"Simulation {request.simulation_id} not found for cloning."
                )
                raise HTTPException(
                    status_code=404,
                    detail=
                    f"Simulation with id {request.simulation_id} not found")

            new_sim = existing_sim.copy()
            new_sim.pop("_id")

            new_sim["name"] = f"{existing_sim['name']} (Copy)"
            new_sim["createdBy"] = request.user_id
            new_sim["createdOn"] = datetime.utcnow()
            new_sim["lastModifiedBy"] = request.user_id
            new_sim["lastModified"] = datetime.utcnow()
            new_sim["status"] = "draft"

            result = await self.db.simulations.insert_one(new_sim)
            logger.info(
                f"Simulation cloned successfully. New ID: {result.inserted_id}"
            )
            return {"id": str(result.inserted_id), "status": "success"}

        except HTTPException as he:
            logger.error(f"HTTPException in clone_simulation: {he.detail}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error cloning simulation: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error cloning simulation: {str(e)}")

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
                "voice_id": "voice_id",
            }
            for field, doc_field in field_mappings.items():
                add_if_exists(field, doc_field)

            sim_type = request.type if request.type else existing_sim.get(
                "type")

            if request.script is not None:
                logger.debug("Updating script.")
                update_doc["script"] = [s.dict() for s in request.script]
                if sim_type in ["audio", "chat"]:
                    prompt = await self._generate_simulation_prompt(
                        request.script)
                    update_doc["prompt"] = prompt

            if request.slidesData is not None and sim_type in [
                    "visual-audio", "visual-chat", "visual"
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
                    "isEnabled": request.simulation_scoring_metrics.is_enabled,
                    "keywordScore":
                    request.simulation_scoring_metrics.keyword_score,
                    "clickScore":
                    request.simulation_scoring_metrics.click_score,
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

                if "prompt" in update_doc:
                    logger.debug("Creating Retell LLM due to updated prompt.")
                    llm_response = await self._create_retell_llm(
                        update_doc["prompt"])
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

            simulation = SimulationData(
                id=str(simulation_doc["_id"]),
                sim_name=simulation_doc.get("name", ""),
                version=str(simulation_doc.get("version", "1")),
                sim_type=simulation_doc.get("type", ""),
                status=simulation_doc.get("status", ""),
                tags=simulation_doc.get("tags", []),
                est_time=str(
                    simulation_doc.get("estimatedTimeToAttemptInMins", "")),
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
                voice_id=simulation_doc.get("voice_id", "11labs-Adrian"),
                lvl1=simulation_doc.get("lvl1", {}),
                lvl2=simulation_doc.get("lvl2", {}),
                lvl3=simulation_doc.get("lvl3", {}),
                slidesData=simulation_doc.get("slidesData", []))

            images = []
            if simulation_doc.get("slidesData"):
                for slide in simulation_doc["slidesData"]:
                    if slide.get("imageUrl"):
                        try:
                            image_id = slide["imageUrl"].split("/")[-1]
                            image_doc = await self.db.images.find_one(
                                {"_id": ObjectId(image_id)})
                            if image_doc:
                                images.append({
                                    "image_id":
                                    slide["imageId"],
                                    "image_data":
                                    base64.b64encode(
                                        image_doc["data"]).decode("utf-8")
                                })
                        except Exception as image_err:
                            logger.warning(
                                f"Failed to load image for slide: {image_err}")

            logger.info(
                f"Visual-audio preview for sim {sim_id} prepared successfully."
            )
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

            simulation = SimulationData(
                id=str(simulation_doc["_id"]),
                sim_name=simulation_doc.get("name", ""),
                version=str(simulation_doc.get("version", "1")),
                sim_type=simulation_doc.get("type", ""),
                status=simulation_doc.get("status", ""),
                tags=simulation_doc.get("tags", []),
                est_time=str(
                    simulation_doc.get("estimatedTimeToAttemptInMins", "")),
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
                slidesData=simulation_doc.get("slidesData", []))

            images = []
            if simulation_doc.get("slidesData"):
                for slide in simulation_doc["slidesData"]:
                    if slide.get("imageUrl"):
                        try:
                            image_id = slide["imageUrl"].split("/")[-1]
                            image_doc = await self.db.images.find_one(
                                {"_id": ObjectId(image_id)})
                            if image_doc:
                                images.append({
                                    "image_id":
                                    slide["imageId"],
                                    "image_data":
                                    base64.b64encode(
                                        image_doc["data"]).decode("utf-8")
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

            simulation = SimulationData(
                id=str(simulation_doc["_id"]),
                sim_name=simulation_doc.get("name", ""),
                version=str(simulation_doc.get("version", "1")),
                sim_type=simulation_doc.get("type", ""),
                status=simulation_doc.get("status", ""),
                tags=simulation_doc.get("tags", []),
                est_time=str(
                    simulation_doc.get("estimatedTimeToAttemptInMins", "")),
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
                slidesData=simulation_doc.get("slidesData", []))

            images = []
            if simulation_doc.get("slidesData"):
                for slide in simulation_doc["slidesData"]:
                    if slide.get("imageUrl"):
                        try:
                            image_id = slide["imageUrl"].split("/")[-1]
                            image_doc = await self.db.images.find_one(
                                {"_id": ObjectId(image_id)})
                            if image_doc:
                                images.append({
                                    "image_id":
                                    slide["imageId"],
                                    "image_data":
                                    base64.b64encode(
                                        image_doc["data"]).decode("utf-8")
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

    async def _create_retell_llm(self, prompt: str) -> Dict:
        """Create a new Retell LLM"""
        logger.info("Creating Retell LLM.")
        logger.debug(f"Prompt: {prompt[:100]}...")  # Show first 100 chars
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {RETELL_API_KEY}',
                    'Content-Type': 'application/json'
                }

                data = {"general_prompt": prompt}

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
            logger.info(
                f"Audio simulation preview created. Access token: {web_call['access_token']}"
            )
            return {"access_token": web_call["access_token"]}

        except HTTPException as he:
            logger.error(
                f"HTTPException in start_audio_simulation_preview: {he.detail}",
                exc_info=True)
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

    async def fetch_simulations(self, user_id: str) -> List[SimulationData]:
        """Fetch all simulations"""
        logger.info(f"Fetching all simulations for user_id={user_id}")
        try:
            cursor = self.db.simulations.find({})
            simulations = []

            async for doc in cursor:
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
                    est_time=str(doc.get("estimatedTimeToAttemptInMins", "")),
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
                    slidesData=doc.get("slidesData", None))
                simulations.append(simulation)

            logger.info(f"Total simulations fetched: {len(simulations)}")
            return simulations

        except Exception as e:
            logger.error(f"Error fetching simulations: {str(e)}",
                         exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error fetching simulations: {str(e)}")

    async def get_simulation_by_id(self,
                                   sim_id: str) -> SimulationByIDResponse:
        logger.info(f"Fetching simulation by ID: {sim_id}")
        try:
            sim_id_object = ObjectId(sim_id)

            simulation_doc = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation_doc:
                logger.warning(
                    f"Simulation {sim_id} not found when fetching by ID.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            simulation = SimulationData(
                id=str(simulation_doc["_id"]),
                sim_name=simulation_doc.get("name", ""),
                version=str(simulation_doc.get("version", "1")),
                sim_type=simulation_doc.get("type", ""),
                status=simulation_doc.get("status", ""),
                tags=simulation_doc.get("tags", []),
                est_time=str(
                    simulation_doc.get("estimatedTimeToAttemptInMins", "")),
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
                voice_id=simulation_doc.get("voice_id", "11labs-Adrian"),
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
                simulation_scoring_metrics=simulation_doc.get(
                    "simulationScoringMetrics", {}),
                sim_practice=simulation_doc.get("simPractice", {}),
                prompt=simulation_doc.get("prompt", ""))

            images = []
            if simulation_doc.get("slidesData"):
                for slide in simulation_doc["slidesData"]:
                    if slide.get("imageUrl"):
                        try:
                            image_id = slide["imageUrl"].split("/")[-1]
                            image_doc = await self.db.images.find_one(
                                {"_id": ObjectId(image_id)})
                            if image_doc:
                                images.append({
                                    "image_id":
                                    slide["imageId"],
                                    "image_data":
                                    base64.b64encode(
                                        image_doc["data"]).decode("utf-8")
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
                detail=f"Error starting visual preview: {str(e)}")
