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
from api.schemas.requests import CreateSimulationRequest, UpdateSimulationRequest, CloneSimulationRequest
from api.schemas.responses import SimulationByIDResponse, SimulationData
from fastapi import HTTPException, UploadFile
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings, )

from api.schemas.responses import StartVisualAudioPreviewResponse, StartVisualChatPreviewResponse, StartVisualPreviewResponse, SimulationData, SimulationByIDResponse
from bson import ObjectId


class SimulationService:

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
            temperature=0.1,
            top_p=1.0,
            max_tokens=4096)

    async def _store_slide_file(self, slide_data: dict,
                                file: UploadFile) -> dict:
        """Store slide file in MongoDB and return updated slide data"""
        try:
            print(
                f"DEBUG: Attempting to store slide file for slide with imageId: {slide_data.get('imageId')}"
            )
            file_bytes = await file.read()
            print(
                f"DEBUG: Read {len(file_bytes)} bytes from file '{file.filename}'"
            )

            # Build the document to insert
            image_doc = {
                "imageId": slide_data["imageId"],
                "name": slide_data.get("imageName", file.filename),
                "contentType": file.content_type,
                "data": file_bytes,
                "uploadedAt": datetime.utcnow()
            }
            print("DEBUG: Inserting image document into MongoDB:", image_doc)

            # Insert into the images collection
            result = await self.db.images.insert_one(image_doc)
            print("DEBUG: Image inserted with id:", result.inserted_id)

            # Build the image URL
            image_url = f"/api/images/{result.inserted_id}"

            # Update slide data with the image URL
            slide_data_copy = slide_data.copy()
            slide_data_copy["imageUrl"] = image_url
            return slide_data_copy

        except Exception as e:
            print("DEBUG: Exception in _store_slide_file:")
            traceback.print_exc(
            )  # Print full traceback to help diagnose the error
            raise HTTPException(status_code=500,
                                detail=f"Error storing slide file: {str(e)}")

    async def _store_slide_image(self, slide_data: dict) -> dict:
        """Store image data in MongoDB and return updated slide data"""
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
                del slide_data_copy[
                    "imageData"]  # Remove the image data after storing

            return slide_data_copy

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error storing image: {str(e)}")

    async def create_simulation(self,
                                request: CreateSimulationRequest) -> Dict:
        """Create a new simulation"""
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
            return {"id": str(result.inserted_id), "status": "success"}

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error creating simulation: {str(e)}")

    async def clone_simulation(self, request: CloneSimulationRequest) -> Dict:
        """Clone an existing simulation"""
        try:
            # Get existing simulation
            sim_id_object = ObjectId(request.simulation_id)
            existing_sim = await self.db.simulations.find_one(
                {"_id": sim_id_object})

            if not existing_sim:
                raise HTTPException(
                    status_code=404,
                    detail=
                    f"Simulation with id {request.simulation_id} not found")

            # Create new simulation document with data from existing one
            new_sim = existing_sim.copy()

            # Remove _id so a new one will be generated
            new_sim.pop("_id")

            # Update metadata
            new_sim["name"] = f"{existing_sim['name']} (Copy)"
            new_sim["createdBy"] = request.user_id
            new_sim["createdOn"] = datetime.utcnow()
            new_sim["lastModifiedBy"] = request.user_id
            new_sim["lastModified"] = datetime.utcnow()
            new_sim["status"] = "draft"

            # Insert new simulation
            result = await self.db.simulations.insert_one(new_sim)

            return {"id": str(result.inserted_id), "status": "success"}

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error cloning simulation: {str(e)}")

    async def update_simulation(
        self,
        sim_id: str,
        request: UpdateSimulationRequest,
        slides_files: Dict[str, UploadFile] = None,
    ) -> Dict:
        """Update an existing simulation (service)."""
        try:
            from bson import ObjectId

            sim_id_object = ObjectId(sim_id)
            existing_sim = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not existing_sim:
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            # Build update_doc
            update_doc = {}

            # Helper to add fields if they exist
            def add_if_exists(field_name: str, doc_field: str | None = None):
                value = getattr(request, field_name)
                if value is not None:
                    update_doc[doc_field or field_name] = value

            # Field mappings from request -> doc
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

            # Determine final sim type (existing or from request)
            sim_type = request.type if request.type else existing_sim.get(
                "type")

            # Handle script/prompt generation for audio/chat
            if request.script is not None:
                update_doc["script"] = [s.dict() for s in request.script]
                if sim_type in ["audio", "chat"]:
                    prompt = await self._generate_simulation_prompt(
                        request.script)
                    update_doc["prompt"] = prompt

            # Modified section for slidesData processing
            if request.slidesData is not None and sim_type in [
                    "visual-audio",
                    "visual-chat",
                    "visual",
            ]:
                processed_slides = []

                # Make sure we have some files to process
                if slides_files and len(slides_files) > 0:
                    for slide in request.slidesData:
                        slide_dict = slide.dict()
                        # Remove base64 so we rely on the actual file upload
                        slide_dict.pop("imageData", None)

                        # Check if we have a file for this slide's imageId
                        image_id = slide_dict.get("imageId")
                        if image_id in slides_files:
                            # Process the updated file
                            file_obj = slides_files[image_id]
                            processed_slide = await self._store_slide_file(
                                slide_dict, file_obj)
                            processed_slides.append(processed_slide)
                        else:
                            # No file update for this slide, just use the existing data
                            processed_slides.append(slide_dict)
                else:
                    # No files to update, just use the slidesData as is
                    processed_slides = [
                        slide.dict() for slide in request.slidesData
                    ]
                    for slide_dict in processed_slides:
                        slide_dict.pop("imageData", None)

                update_doc["slidesData"] = processed_slides

            if request.lvl1 is not None:
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

            # Handle simulation_scoring_metrics
            if request.simulation_scoring_metrics is not None:
                update_doc["simulationScoringMetrics"] = {
                    "isEnabled": request.simulation_scoring_metrics.is_enabled,
                    "keywordScore":
                    request.simulation_scoring_metrics.keyword_score,
                    "clickScore":
                    request.simulation_scoring_metrics.click_score,
                }

            # Handle sim_practice
            if request.sim_practice is not None:
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

            # Handle voice settings for audio
            if sim_type == "audio":
                if request.voice_id is not None:
                    update_doc["voiceId"] = request.voice_id

                if request.voice_speed is not None:
                    update_doc["voice_speed"] = request.voice_speed

                # If prompt is updated, recreate LLM + Agent
                if "prompt" in update_doc:
                    llm_response = await self._create_retell_llm(
                        update_doc["prompt"])
                    update_doc["llmId"] = llm_response["llm_id"]

                    agent_voice_id = request.voice_id or "11labs-Adrian"
                    agent_response = await self._create_retell_agent(
                        llm_response["llm_id"], agent_voice_id)
                    update_doc["agentId"] = agent_response["agent_id"]

            # lastModified & lastModifiedBy
            update_doc["lastModified"] = datetime.utcnow()
            update_doc["lastModifiedBy"] = request.user_id

            # Perform the DB update
            result = await self.db.simulations.update_one(
                {"_id": sim_id_object}, {"$set": update_doc})

            if result.modified_count == 0:
                raise HTTPException(status_code=500,
                                    detail="Failed to update simulation")

            # Fetch the updated document
            updated_simulation = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            updated_simulation["_id"] = str(updated_simulation["_id"])

            return {
                "id": sim_id,
                "status": "success",
                "document": updated_simulation
            }

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error updating simulation: {str(e)}")

    async def start_visual_audio_preview(
            self, sim_id: str,
            user_id: str) -> StartVisualAudioPreviewResponse:
        try:
            sim_id_object = ObjectId(sim_id)

            simulation_doc = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation_doc:
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            # 🧠 Normalize fields for Pydantic model
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

            # 🖼️ Collect any referenced images from slides
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
                            print(
                                f"⚠️ Failed to load image for slide: {image_err}"
                            )

            return StartVisualAudioPreviewResponse(simulation=simulation,
                                                   images=images)

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error starting visual-audio preview: {str(e)}")

    async def start_visual_chat_preview(
            self, sim_id: str, user_id: str) -> StartVisualChatPreviewResponse:
        try:
            sim_id_object = ObjectId(sim_id)

            simulation_doc = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation_doc:
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            # 🧠 Normalize fields for Pydantic model
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

            # 🖼️ Collect any referenced images from slides
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
                            print(
                                f"⚠️ Failed to load image for slide: {image_err}"
                            )

            return StartVisualChatPreviewResponse(simulation=simulation,
                                                  images=images)

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error starting visual-chat preview: {str(e)}")

    async def start_visual_preview(self, sim_id: str,
                                   user_id: str) -> StartVisualPreviewResponse:
        try:
            sim_id_object = ObjectId(sim_id)

            simulation_doc = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation_doc:
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            # 🧠 Normalize fields for Pydantic model
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

            # 🖼️ Collect any referenced images from slides
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
                            print(
                                f"⚠️ Failed to load image for slide: {image_err}"
                            )

            return StartVisualPreviewResponse(simulation=simulation,
                                              images=images)

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error starting visual preview: {str(e)}")

    async def _create_retell_llm(self, prompt: str) -> Dict:
        """Create a new Retell LLM"""
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
                        raise HTTPException(
                            status_code=response.status,
                            detail="Failed to create Retell LLM")

                    return await response.json()

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error creating Retell LLM: {str(e)}")

    async def _create_retell_agent(self, llm_id: str, voice_id: str) -> Dict:
        """Create a new Retell Agent"""
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
                        raise HTTPException(
                            status_code=response.status,
                            detail="Failed to create Retell Agent")

                    return await response.json()

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating Retell Agent: {str(e)}")

    async def _generate_simulation_prompt(self, script: List[Dict]) -> str:
        """Generate simulation prompt using Azure OpenAI"""
        try:
            history = ChatHistory()
            print(history)

            # First, add the system prompt
            system_message = (
                "Create a detailed prompt for an AI agent. You will be given a script of a dialog between a customer "
                "and a customer service agent. You need to create a prompt so that the AI should play the role of the customer. "
                "Make sure that in the prompt you mention that the AI needs to follow the script exactly verbatim. In other words, "
                "include the complete verbatim script in your response. If the user gives an input that is not included in the script "
                "then the AI should invent details and answer smartly.")
            history.add_system_message(system_message)

            # Then, add the user message with the conversation script
            conversation = "\n".join(
                [f"{s.role}: {s.script_sentence}" for s in script])
            inputprompt = f"Script: {conversation}"

            print("input", inputprompt)

            # Add user content
            history.add_user_message(inputprompt)

            print("input prompt pushed")

            # Get response from Azure OpenAI
            result = await self.chat_completion.get_chat_message_content(
                history, settings=self.execution_settings)

            print("result", result)

            return str(result)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating simulation prompt: {str(e)}")

    async def start_audio_simulation_preview(self, sim_id: str,
                                             user_id: str) -> Dict:
        """Start an audio simulation preview"""
        try:
            # Convert string ID to ObjectId
            sim_id_object = ObjectId(sim_id)

            # Get simulation
            simulation = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            # Get agent_id
            agent_id = simulation.get("agentId")
            if not agent_id:
                raise HTTPException(
                    status_code=400,
                    detail="Simulation does not have an agent configured")

            # Create web call
            web_call = await self._create_web_call(agent_id)

            return {"access_token": web_call["access_token"]}

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error starting audio simulation preview: {str(e)}")

    async def _create_web_call(self, agent_id: str) -> Dict:
        """Create a web call using Retell API"""
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
                        raise HTTPException(status_code=response.status,
                                            detail="Failed to create web call")

                    return await response.json()

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error creating web call: {str(e)}")

    async def fetch_simulations(self, user_id: str) -> List[SimulationData]:
        """Fetch all simulations"""
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

            return simulations

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error fetching simulations: {str(e)}")

    # async def get_simulation_by_id(
    #         self, simulation_id: str) -> Optional[SimulationData]:
    #     """Fetch a single simulation by ID"""
    #     try:
    #         # Convert string ID to ObjectId
    #         simulation_id_object = ObjectId(simulation_id)

    #         # Find the simulation
    #         doc = await self.db.simulations.find_one(
    #             {"_id": simulation_id_object})

    #         if not doc:
    #             return None

    #         return SimulationData(
    #             id=str(doc["_id"]),
    #             sim_name=doc.get("name", ""),
    #             version=str(doc.get("version", "1")),
    #             lvl1=doc.get("lvl1", {}),
    #             lvl2=doc.get("lvl2", {}),
    #             lvl3=doc.get("lvl3", {}),
    #             sim_type=doc.get("type", ""),
    #             status=doc.get("status", ""),
    #             tags=doc.get("tags", []),
    #             est_time=str(doc.get("estimatedTimeToAttemptInMins", "")),
    #             last_modified=doc.get("lastModified",
    #                                   datetime.utcnow()).isoformat(),
    #             modified_by=doc.get("lastModifiedBy", ""),
    #             created_on=doc.get("createdOn", datetime.utcnow()).isoformat(),
    #             created_by=doc.get("createdBy", ""),
    #             islocked=doc.get("isLocked", False),
    #             division_id=doc.get("divisionId", ""),
    #             department_id=doc.get("departmentId", ""),
    #             script=doc.get("script", None),
    #             slidesData=doc.get("slidesData", None))

    #     except Exception as e:
    #         raise HTTPException(status_code=500,
    #                             detail=f"Error fetching simulation: {str(e)}")

    async def get_simulation_by_id(self,
                                   sim_id: str) -> SimulationByIDResponse:
        try:
            sim_id_object = ObjectId(sim_id)

            simulation_doc = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation_doc:
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {sim_id} not found")

            # 🧠 Normalize fields for Pydantic model
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

            # 🖼️ Collect any referenced images from slides
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
                            print(
                                f"⚠️ Failed to load image for slide: {image_err}"
                            )

            return SimulationByIDResponse(simulation=simulation, images=images)

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error starting visual preview: {str(e)}")
