from fastapi import APIRouter, HTTPException, File, UploadFile, Request
from typing import Dict, List
from bson import ObjectId
from datetime import datetime
import aiohttp
from utils.logger import Logger  # <-- Added import for Logger
from domain.services.simulation_service import SimulationService
from infrastructure.database import Database
from domain.services.chat_service import ChatService

from api.schemas.requests import (
    CreateSimulationRequest,
    UpdateSimulationRequest,
    StartAudioSimulationPreviewRequest,
    StartChatPreviewRequest,
    StartAudioSimulationRequest,
    StartChatSimulationRequest,
    EndAudioSimulationRequest,
    EndChatSimulationRequest,
    FetchSimulationsRequest,
    StartVisualAudioPreviewRequest,
    StartVisualChatPreviewRequest,
    StartVisualPreviewRequest,
    CloneSimulationRequest,
    StartVisualAudioAttemptRequest,
    StartVisualChatAttemptRequest,
    StartVisualAttemptRequest,
    EndVisualAudioAttemptRequest,
    EndVisualChatAttemptRequest,
    EndVisualAttemptRequest,
)
from api.schemas.responses import (
    CreateSimulationResponse, UpdateSimulationResponse,
    StartAudioSimulationPreviewResponse, StartChatPreviewResponse,
    StartSimulationResponse, EndSimulationResponse, FetchSimulationsResponse,
    StartVisualAudioPreviewResponse, SlideImageData, SimulationByIDResponse,
    StartVisualChatPreviewResponse, StartVisualPreviewResponse, SimulationData,
    StartVisualAttemptResponse, StartVisualAudioAttemptResponse,
    StartVisualChatAttemptResponse)
from config import (RETELL_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME,
                    AZURE_OPENAI_KEY, AZURE_OPENAI_BASE_URL)
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings, )

logger = Logger.get_logger(__name__)  # <-- Initialize logger
router = APIRouter()


class SimulationController:

    def __init__(self):
        logger.info("Initializing SimulationController.")
        self.service = SimulationService()
        self.chat_service = ChatService()
        self.db = Database()

        # Initialize Azure OpenAI for scoring
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
        logger.info("SimulationController initialized successfully.")

    async def create_simulation(
            self,
            request: CreateSimulationRequest) -> CreateSimulationResponse:
        """Create a new simulation"""
        logger.info("Received request to create a new simulation.")
        try:
            result = await self.service.create_simulation(request)
            logger.info(f"Simulation created with ID: {result['id']}")
            return CreateSimulationResponse(id=result["id"],
                                            status=result["status"])
        except Exception as e:
            logger.error(f"Error creating simulation: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def clone_simulation(
            self, request: CloneSimulationRequest) -> CreateSimulationResponse:
        """Clone an existing simulation"""
        logger.info("Received request to clone a simulation.")
        try:

            result = await self.service.clone_simulation(request)
            logger.info(f"Simulation cloned. New ID: {result['id']}")
            return CreateSimulationResponse(id=result["id"],
                                            status=result["status"])
        except Exception as e:
            logger.error(f"Error cloning simulation: {e}", exc_info=True)
            raise

    async def update_simulation(
            self,
            sim_id: str,
            request: UpdateSimulationRequest,
            slides: List[UploadFile] = None) -> UpdateSimulationResponse:
        """Update an existing simulation"""

        logger.info(f"Received request to update simulation with ID: {sim_id}")
        try:

            result = await self.service.update_simulation(
                sim_id, request, slides)
            logger.info(f"Simulation {sim_id} updated successfully.")
            return UpdateSimulationResponse(id=result["id"],
                                            status=result["status"],
                                            document=result["document"])
        except Exception as e:
            logger.error(f"Error updating simulation: {e}", exc_info=True)
            raise

    async def start_audio_simulation_preview(
        self, request: StartAudioSimulationPreviewRequest
    ) -> StartAudioSimulationPreviewResponse:

        logger.info("Received request to start audio simulation preview.")
        try:

            result = await self.service.start_audio_simulation_preview(
                request.sim_id, request.user_id)
            logger.info(
                f"Audio simulation preview started. Access token: {result['access_token']}"
            )
            return StartAudioSimulationPreviewResponse(
                access_token=result["access_token"])
        except Exception as e:
            logger.error(f"Error starting audio simulation preview: {e}",
                         exc_info=True)
            raise

    async def start_visual_audio_preview(
        self, request: StartVisualAudioPreviewRequest
    ) -> StartVisualAudioPreviewResponse:

        logger.info("Received request to start visual-audio preview.")
        try:

            result = await self.service.start_visual_audio_preview(
                request.sim_id, request.user_id)
            logger.info("Visual-audio preview started successfully.")
            return StartVisualAudioPreviewResponse(
                simulation=result.simulation,
                images=[
                    SlideImageData(image_id=img.image_id,
                                   image_data=img.image_data)
                    for img in result.images
                ])
        except Exception as e:
            logger.error(f"Error starting visual-audio preview: {e}",
                         exc_info=True)
            raise

    async def start_visual_chat_preview(
        self, request: StartVisualChatPreviewRequest
    ) -> StartVisualChatPreviewResponse:
        logger.info("Received request to start visual-chat preview.")
        try:

            result = await self.service.start_visual_chat_preview(
                request.sim_id, request.user_id)
            logger.info("Visual-chat preview started successfully.")
            return StartVisualChatPreviewResponse(
                simulation=result.simulation,
                images=[
                    SlideImageData(image_id=img.image_id,
                                   image_data=img.image_data)
                    for img in result.images
                ])
        except Exception as e:
            logger.error(f"Error starting visual-chat preview: {e}",
                         exc_info=True)
            raise

    async def start_visual_preview(
            self,
            request: StartVisualPreviewRequest) -> StartVisualPreviewResponse:

        logger.info("Received request to start visual preview.")
        try:

            result = await self.service.start_visual_preview(
                request.sim_id, request.user_id)
            logger.info("Visual preview started successfully.")
            return StartVisualPreviewResponse(
                simulation=result.simulation,
                images=[
                    SlideImageData(image_id=img.image_id,
                                   image_data=img.image_data)
                    for img in result.images
                ])
        except Exception as e:
            logger.error(f"Error starting visual preview: {e}", exc_info=True)
            raise

    async def start_chat_preview(
            self,
            request: StartChatPreviewRequest) -> StartChatPreviewResponse:

        logger.info("Received request to start chat preview.")
        try:

            if request.message == "":
                logger.debug(
                    "Message is empty. Checking simulation script for first entry."
                )
                sim_id_object = ObjectId(request.sim_id)
                simulation = await self.db.simulations.find_one(
                    {"_id": sim_id_object})
                if not simulation:
                    logger.warning(
                        f"Simulation with id {request.sim_id} not found.")
                    raise HTTPException(
                        status_code=404,
                        detail=f"Simulation with id {request.sim_id} not found"
                    )
                script = simulation.get("script", [])
                if script and len(script) > 0:
                    first_entry = script[0]
                    if first_entry.get("role").lower() == "customer":
                        logger.debug(
                            "Returning first script sentence for 'customer' role."
                        )
                        return StartChatPreviewResponse(
                            response=first_entry.get("script_sentence", ""))
                return StartChatPreviewResponse(response="")
            else:
                result = await self.chat_service.start_chat(
                    request.user_id, request.sim_id, request.message)
                logger.info("Chat preview started with custom message.")
                return StartChatPreviewResponse(response=result["response"])
        except Exception as e:
            logger.error(f"Error starting chat preview: {e}", exc_info=True)
            raise

    async def start_audio_simulation(
            self,
            request: StartAudioSimulationRequest) -> StartSimulationResponse:
        """Start an audio simulation and create progress record"""
        logger.info("Received request to start audio simulation.")
        try:
            sim_id_object = ObjectId(request.sim_id)
            simulation = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation:
                logger.warning(
                    f"Simulation with id {request.sim_id} not found.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {request.sim_id} not found")

            agent_id = simulation.get("agentId")
            if not agent_id:
                logger.warning("Simulation does not have an agent configured.")
                raise HTTPException(
                    status_code=400,
                    detail="Simulation does not have an agent configured")

            web_call = await self._create_web_call(agent_id)
            progress_doc = {
                "userId": request.user_id,
                "simulationId": request.sim_id,
                "assignmentId": request.assignment_id,
                "type": "audio",
                "status": "in_progress",
                "callId": web_call.get("call_id"),
                "accessToken": web_call.get("access_token"),
                "createdAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }
            result = await self.db.user_sim_progress.insert_one(progress_doc)

            logger.info(
                f"Audio simulation started. call_id={web_call['call_id']}")
            return StartSimulationResponse(
                id=str(result.inserted_id),
                status="success",
                access_token=web_call["access_token"],
                call_id=web_call["call_id"])
        except Exception as e:
            logger.error(f"Error starting audio simulation: {e}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error starting audio simulation: {str(e)}")

    async def start_chat_simulation(
            self,
            request: StartChatSimulationRequest) -> StartSimulationResponse:
        """Start a chat simulation and create/update progress record"""
        logger.info("Received request to start chat simulation.")
        try:
            sim_id_object = ObjectId(request.sim_id)
            simulation = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation:
                logger.warning(
                    f"Simulation with id {request.sim_id} not found.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {request.sim_id} not found")

            chat_response = None
            if request.message is not None:
                logger.debug(
                    f"Starting initial chat with message: {request.message}")
                chat_response = await self.chat_service.start_chat(
                    request.user_id, request.sim_id, request.message)

            if request.usersimulationprogress_id:
                logger.info("Updating existing user simulation progress.")
                progress_id_object = ObjectId(
                    request.usersimulationprogress_id)
                progress_doc = await self.db.user_sim_progress.find_one(
                    {"_id": progress_id_object})
                if not progress_doc:
                    logger.warning(
                        f"Progress document {request.usersimulationprogress_id} not found."
                    )
                    raise HTTPException(
                        status_code=404,
                        detail=
                        (f"Progress document with id {request.usersimulationprogress_id} not found"
                         ))

                update_doc = {"lastModifiedAt": datetime.utcnow()}
                if request.message is not None:
                    chat_history = progress_doc.get("chatHistory", [])
                    chat_history.append({
                        "role": "Customer",
                        "sentence": request.message
                    })
                    if chat_response and chat_response.get("response"):
                        chat_history.append({
                            "role":
                            "Assistant",
                            "sentence":
                            chat_response["response"]
                        })
                    update_doc["chatHistory"] = chat_history

                await self.db.user_sim_progress.update_one(
                    {"_id": progress_id_object}, {"$set": update_doc})
                logger.info("User simulation progress updated successfully.")
                return StartSimulationResponse(
                    id=request.usersimulationprogress_id,
                    status="success",
                    response=chat_response["response"]
                    if chat_response else None)
            else:
                logger.info("Creating new user simulation progress.")
                progress_doc = {
                    "userId": request.user_id,
                    "simulationId": request.sim_id,
                    "assignmentId": request.assignment_id,
                    "type": "chat",
                    "status": "in_progress",
                    "chatHistory": [],
                    "createdAt": datetime.utcnow(),
                    "lastModifiedAt": datetime.utcnow()
                }

                if request.message is not None:
                    progress_doc["chatHistory"] = [{
                        "role": "Customer",
                        "sentence": request.message
                    }]
                    if chat_response and chat_response.get("response"):
                        progress_doc["chatHistory"].append({
                            "role":
                            "Assistant",
                            "sentence":
                            chat_response["response"]
                        })

                result = await self.db.user_sim_progress.insert_one(
                    progress_doc)
                logger.info(
                    "New user simulation progress created successfully.")
                return StartSimulationResponse(
                    id=str(result.inserted_id),
                    status="success",
                    response=chat_response["response"]
                    if chat_response else None)
        except Exception as e:
            logger.error(f"Error starting chat simulation: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error starting chat simulation: {str(e)}")

    async def _create_web_call(self, agent_id: str) -> Dict:
        """Create a web call using Retell API"""
        logger.debug(f"Creating web call with agent_id={agent_id}")
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {RETELL_API_KEY}",
                    "Content-Type": "application/json"
                }
                data = {"agent_id": agent_id}

                async with session.post(
                        "https://api.retellai.com/v2/create-web-call",
                        headers=headers,
                        json=data) as response:
                    if response.status != 201:
                        logger.warning(
                            f"Failed to create web call. Status: {response.status}"
                        )
                        raise HTTPException(status_code=response.status,
                                            detail="Failed to create web call")
                    resp_json = await response.json()
                    logger.debug(f"Web call created successfully: {resp_json}")
                    return resp_json
        except Exception as e:
            logger.error(f"Error creating web call: {e}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error creating web call: {str(e)}")

    async def end_audio_simulation(
            self, request: EndAudioSimulationRequest) -> EndSimulationResponse:
        logger.info("Received request to end audio simulation.")
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {RETELL_API_KEY}"}
                url = f"https://api.retellai.com/v2/get-call/{request.call_id}"

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

            sim = await self.db.simulations.find_one(
                {"_id": ObjectId(request.simulation_id)})
            if not sim:
                logger.warning(
                    f"Simulation {request.simulation_id} not found for end_audio_simulation."
                )
                raise HTTPException(
                    status_code=404,
                    detail=
                    f"Simulation with id {request.simulation_id} not found")

            transcript = call_data.get("transcript", "")
            scores = await self._calculate_scores(sim, transcript)
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
                {"_id": ObjectId(request.usersimulationprogress_id)},
                {"$set": update_doc})

            logger.info(
                f"Audio simulation ended. ID={request.usersimulationprogress_id}"
            )
            return EndSimulationResponse(id=request.usersimulationprogress_id,
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

    async def end_chat_simulation(
            self, request: EndChatSimulationRequest) -> EndSimulationResponse:
        logger.info("Received request to end chat simulation.")
        try:
            sim = await self.db.simulations.find_one(
                {"_id": ObjectId(request.simulation_id)})
            if not sim:
                logger.warning(
                    f"Simulation {request.simulation_id} not found for end_chat_simulation."
                )
                raise HTTPException(
                    status_code=404,
                    detail=
                    f"Simulation with id {request.simulation_id} not found")

            transcript = "\n".join(f"{msg.role}: {msg.sentence}"
                                   for msg in request.chat_history)
            scores = await self._calculate_scores(sim, transcript)
            duration = 300  # 5 minutes default for chat simulations

            update_doc = {
                "status": "completed",
                "transcript": transcript,
                "chatHistory": [msg.dict() for msg in request.chat_history],
                "duration": duration,
                "scores": scores,
                "completedAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }

            await self.db.user_sim_progress.update_one(
                {"_id": ObjectId(request.usersimulationprogress_id)},
                {"$set": update_doc})

            logger.info(
                f"Chat simulation ended. ID={request.usersimulationprogress_id}"
            )
            return EndSimulationResponse(id=request.usersimulationprogress_id,
                                         status="success",
                                         scores=scores,
                                         duration=duration,
                                         transcript=transcript,
                                         audio_url="")
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error ending chat simulation: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error ending chat simulation: {str(e)}")

    async def _calculate_scores(self, simulation: Dict,
                                transcript: str) -> Dict[str, float]:
        """Calculate simulation scores using Azure OpenAI"""
        logger.debug("Calculating scores with Azure OpenAI.")
        try:
            history = ChatHistory()
            system_message = (
                "You are an AI scoring system. Analyze the following conversation between a customer "
                "and a trainee based on the given script and criteria. Provide scores for:\n"
                "1. Sim Accuracy (0-100): How well the trainee followed the script\n"
                "2. Keyword Score (0-100): Usage of required keywords\n"
                "3. Click Score (0-100): Effectiveness of interaction points\n"
                "4. Confidence (0-100): Trainee's confidence level\n"
                "5. Energy (0-100): Trainee's energy and enthusiasm\n"
                "6. Concentration (0-100): Trainee's focus and attention\n\n"
                "Return ONLY a JSON object with these scores as numbers.")
            history.add_system_message(system_message)

            script_text = "\n".join(f"{s['role']}: {s['script_sentence']}"
                                    for s in simulation['script'])
            context = f"Expected Script:\n{script_text}\n\nActual Conversation:\n{transcript}"
            history.add_user_message(context)

            result = await self.chat_completion.get_chat_message_content(
                history, settings=self.execution_settings)
            logger.debug(f"OpenAI raw score response: {result}")
            scores = eval(str(result))  # Convert string response to dict
            logger.debug(f"Scores parsed successfully: {scores}")
            return scores
        except Exception as e:
            logger.error(f"Error calculating scores: {e}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error calculating scores: {str(e)}")

    async def fetch_simulations(
            self,
            request: FetchSimulationsRequest) -> FetchSimulationsResponse:

        logger.info("Received request to fetch simulations.")
        try:

            simulations = await self.service.fetch_simulations(request.user_id)
            logger.info(f"Fetched {len(simulations)} simulation(s).")
            return FetchSimulationsResponse(simulations=simulations)
        except Exception as e:
            logger.error(f"Error fetching simulations: {e}", exc_info=True)
            raise

    async def get_simulation_by_id(
            self, simulation_id: str) -> SimulationByIDResponse:
        """Get a single simulation by ID"""
        logger.info(
            f"Received request to get simulation by ID: {simulation_id}")
        try:

            simulation = await self.service.get_simulation_by_id(simulation_id)
            if not simulation:
                logger.warning(
                    f"Simulation with id {simulation_id} not found.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {simulation_id} not found")
            logger.info(f"Simulation {simulation_id} retrieved successfully.")
            return simulation
        except Exception as e:
            logger.error(f"Error getting simulation by ID: {e}", exc_info=True)
            raise

    async def start_visual_audio_attempt(
            self, sim_id: str, user_id: str,
            assignment_id: str) -> StartVisualAudioAttemptResponse:
        try:
            progress_doc = {
                "userId": user_id,
                "simulationId": sim_id,
                "assignmentId": assignment_id,
                "type": "visual_audio",
                "status": "in_progress",
                "createdAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }

            result = await self.db.user_sim_progress.insert_one(progress_doc)
            return StartVisualAudioAttemptResponse(id=str(result.inserted_id),
                                                   status="in_progress")
        except Exception as e:
            logger.error(f"[start_visual_audio_attempt] {str(e)}",
                         exc_info=True)
            raise HTTPException(status_code=500,
                                detail="Internal server error")

    async def start_visual_chat_attempt(
            self, sim_id: str, user_id: str,
            assignment_id: str) -> StartVisualChatAttemptResponse:
        try:
            progress_doc = {
                "userId": user_id,
                "simulationId": sim_id,
                "assignmentId": assignment_id,
                "type": "visual_chat",
                "status": "in_progress",
                "createdAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }

            result = await self.db.user_sim_progress.insert_one(progress_doc)
            return StartVisualChatAttemptResponse(id=str(result.inserted_id),
                                                  status="in_progress")
        except Exception as e:
            logger.error(f"[start_visual_chat_attempt] {str(e)}",
                         exc_info=True)
            raise HTTPException(status_code=500,
                                detail="Internal server error")

    async def start_visual_attempt(
            self, sim_id: str, user_id: str,
            assignment_id: str) -> StartVisualAttemptResponse:
        try:
            progress_doc = {
                "userId": user_id,
                "simulationId": sim_id,
                "assignmentId": assignment_id,
                "type": "visual",
                "status": "in_progress",
                "createdAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }

            result = await self.db.user_sim_progress.insert_one(progress_doc)
            return StartVisualAttemptResponse(id=str(result.inserted_id),
                                              status="in_progress")
        except Exception as e:
            logger.error(f"[start_visual_attempt] {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail="Internal server error")

    async def end_visual_audio_attempt(
            self,
            request: EndVisualAudioAttemptRequest) -> EndSimulationResponse:
        try:
            update_doc = {
                "status": "completed",
                "transcript": "",
                "audioUrl": "",
                "duration": 0,
                "scores": {},
                "completedAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }

            await self.db.user_sim_progress.update_one(
                {"_id": ObjectId(request.usersimulationprogress_id)},
                {"$set": update_doc})

            return EndSimulationResponse(id=request.usersimulationprogress_id,
                                         status="success",
                                         scores={},
                                         duration=0,
                                         transcript="",
                                         audio_url="")
        except Exception as e:
            logger.error(f"[end_visual_audio_attempt] {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail="Internal server error")

    async def end_visual_chat_attempt(
            self,
            request: EndVisualChatAttemptRequest) -> EndSimulationResponse:
        try:
            transcript = ""
            scores = {}

            update_doc = {
                "status": "completed",
                "transcript": transcript,
                "chatHistory": [],
                "duration": 0,
                "scores": scores,
                "completedAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }

            await self.db.user_sim_progress.update_one(
                {"_id": ObjectId(request.usersimulationprogress_id)},
                {"$set": update_doc})

            return EndSimulationResponse(id=request.usersimulationprogress_id,
                                         status="success",
                                         scores=scores,
                                         duration=0,
                                         transcript=transcript,
                                         audio_url="")
        except Exception as e:
            logger.error(f"[end_visual_chat_attempt] {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail="Internal server error")

    async def end_visual_attempt(
            self, request: EndVisualAttemptRequest) -> EndSimulationResponse:
        try:
            update_doc = {
                "status": "completed",
                "duration": 0,
                "scores": {},
                "completedAt": datetime.utcnow(),
                "lastModifiedAt": datetime.utcnow()
            }

            await self.db.user_sim_progress.update_one(
                {"_id": ObjectId(request.usersimulationprogress_id)},
                {"$set": update_doc})

            return EndSimulationResponse(id=request.usersimulationprogress_id,
                                         status="success",
                                         scores={},
                                         duration=0,
                                         transcript="",
                                         audio_url="")
        except Exception as e:
            logger.error(f"[end_visual_attempt] {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail="Internal server error")


controller = SimulationController()


@router.put("/simulations/{sim_id}/update", tags=["Simulations", "Update"])
async def update_simulation(
    sim_id: str, req: Request, slides: List[UploadFile] = File(None)
) -> UpdateSimulationResponse:
    """
    Update an existing simulation.
    Can handle both JSON (no files) and multipart/form-data (with files).
    """
    logger.info(f"API endpoint called: PUT /simulations/{sim_id}/update")
    content_type = req.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        data = await req.json()
        slides_files = {}
    else:
        form_data = await req.form()
        data = dict(form_data)
        import json
        json_fields = [
            "script",
            "slidesData",
            "tags",
            "quick_tips",
            "key_objectives",
            "lvl1",
            "lvl2",
            "lvl3",
            "simulation_scoring_metrics",
            "sim_practice",
        ]
        for field_name in json_fields:
            if field_name in data and isinstance(data[field_name], str):
                try:
                    data[field_name] = json.loads(data[field_name])
                except Exception as e:
                    logger.debug(f"Could not parse '{field_name}': {e}")

        slides_files = {}
        for key, value in form_data.multi_items():
            if key.startswith("slide_"):
                image_id = key[6:]
                slides_files[image_id] = value
                logger.debug(
                    f"Found file for image ID {image_id}: {value.filename}")

    from api.schemas.requests import UpdateSimulationRequest
    try:
        update_request = UpdateSimulationRequest.parse_obj(data)
    except Exception as e:
        logger.error("Error parsing UpdateSimulationRequest", exc_info=True)
        raise HTTPException(status_code=422, detail="Request validation error")

    logger.info(
        f"Forwarding update simulation request to controller for sim_id={sim_id}"
    )
    return await controller.update_simulation(sim_id, update_request,
                                              slides_files)


@router.post("/simulations/start-audio-preview", tags=["Simulations", "Audio"])
async def start_audio_simulation_preview(
    request: StartAudioSimulationPreviewRequest
) -> StartAudioSimulationPreviewResponse:
    logger.info("API endpoint called: POST /simulations/start-audio-preview")
    return await controller.start_audio_simulation_preview(request)


@router.post("/simulations/start-chat-preview", tags=["Simulations", "Chat"])
async def start_chat_preview(
        request: StartChatPreviewRequest) -> StartSimulationResponse:
    logger.info("API endpoint called: POST /simulations/start-chat-preview")

    chat_request_data = {
        "user_id": request.user_id,
        "sim_id": request.sim_id,
        "assignment_id": 'preview',
        "message": request.message,
    }

    if request.usersimulationprogress_id:
        chat_request_data[
            "usersimulationprogress_id"] = request.usersimulationprogress_id

    chat_request = StartChatSimulationRequest(**chat_request_data)

    response = await controller.start_chat_simulation(chat_request)
    return response


@router.post("/simulations/start-audio", tags=["Simulations", "Start"])
async def start_audio_simulation(
        request: StartAudioSimulationRequest) -> StartSimulationResponse:
    """Start an audio simulation"""
    logger.info("API endpoint called: POST /simulations/start-audio")
    return await controller.start_audio_simulation(request)


@router.post("/simulations/start-chat", tags=["Simulations", "Start"])
async def start_chat_simulation(
        request: StartChatSimulationRequest) -> StartSimulationResponse:
    """Start a chat simulation"""
    logger.info("API endpoint called: POST /simulations/start-chat")
    return await controller.start_chat_simulation(request)


@router.post("/simulations/end-audio", tags=["Simulations", "End"])
async def end_audio_simulation(
        request: EndAudioSimulationRequest) -> EndSimulationResponse:
    logger.info("API endpoint called: POST /simulations/end-audio")
    return await controller.end_audio_simulation(request)


@router.post("/simulations/end-chat", tags=["Simulations", "End"])
async def end_chat_simulation(
        request: EndChatSimulationRequest) -> EndSimulationResponse:
    logger.info("API endpoint called: POST /simulations/end-chat")
    return await controller.end_chat_simulation(request)


@router.post("/simulations/fetch", tags=["Simulations", "Read"])
async def fetch_simulations(
        request: FetchSimulationsRequest) -> FetchSimulationsResponse:
    logger.info("API endpoint called: POST /simulations/fetch")
    return await controller.fetch_simulations(request)


@router.post("/simulations/start-visual-audio-preview",
             tags=["Simulations", "Visual Audio"])
async def start_visual_audio_preview(
    request: StartVisualAudioPreviewRequest
) -> StartVisualAudioPreviewResponse:
    """Start a visual-audio simulation preview"""
    logger.info(
        "API endpoint called: POST /simulations/start-visual-audio-preview")
    return await controller.start_visual_audio_preview(request)


@router.post("/simulations/start-visual-chat-preview",
             tags=["Simulations", "Visual Chat"])
async def start_visual_chat_preview(
        request: StartVisualChatPreviewRequest
) -> StartVisualChatPreviewResponse:
    """Start a visual-chat simulation preview"""
    logger.info(
        "API endpoint called: POST /simulations/start-visual-chat-preview")
    return await controller.start_visual_chat_preview(request)


@router.post("/simulations/start-visual-preview",
             tags=["Simulations", "Visual"])
async def start_visual_preview(
        request: StartVisualPreviewRequest) -> StartVisualPreviewResponse:
    """Start a visual-chat simulation preview"""
    logger.info("API endpoint called: POST /simulations/start-visual-preview")
    return await controller.start_visual_preview(request)


@router.get("/simulations/fetch/{simulation_id}", tags=["Simulations", "Read"])
async def get_simulation_by_id(simulation_id: str) -> SimulationByIDResponse:
    """Get a single simulation by ID"""
    logger.info(f"API endpoint called: GET /simulations/fetch/{simulation_id}")
    return await controller.get_simulation_by_id(simulation_id)


@router.post("/simulations/create", tags=["Simulations", "Create"])
async def create_simulation(
        request: CreateSimulationRequest) -> CreateSimulationResponse:
    """Create a new simulation"""
    logger.info("API endpoint called: POST /simulations/create")
    return await controller.create_simulation(request)


@router.post("/simulations/clone", tags=["Simulations", "Create"])
async def clone_simulation(
        request: CloneSimulationRequest) -> CreateSimulationResponse:
    """Clone an existing simulation"""
    logger.info("API endpoint called: POST /simulations/clone")
    return await controller.clone_simulation(request)


@router.post("/simulations/start-visual-audio-attempt",
             tags=["Simulations", "Visual Audio"])
async def start_visual_audio_attempt(
    request: StartVisualAudioAttemptRequest
) -> StartVisualAudioAttemptResponse:
    """Start a visual-audio simulation attempt"""
    logger.info(
        "API endpoint called: POST /simulations/start-visual-audio-attempt")
    return await controller.start_visual_audio_attempt(request.sim_id,
                                                       request.user_id,
                                                       request.assignment_id)


@router.post("/simulations/start-visual-chat-attempt",
             tags=["Simulations", "Visual Chat"])
async def start_visual_chat_attempt(
        request: StartVisualChatAttemptRequest
) -> StartVisualChatAttemptResponse:
    """Start a visual-chat simulation attempt"""
    logger.info(
        "API endpoint called: POST /simulations/start-visual-chat-attempt")
    return await controller.start_visual_chat_attempt(request.sim_id,
                                                      request.user_id,
                                                      request.assignment_id)


@router.post("/simulations/start-visual-attempt",
             tags=["Simulations", "Visual"])
async def start_visual_attempt(
        request: StartVisualAttemptRequest) -> StartVisualAttemptResponse:
    """Start a visual simulation attempt"""
    logger.info("API endpoint called: POST /simulations/start-visual-attempt")
    return await controller.start_visual_attempt(request.sim_id,
                                                 request.user_id,
                                                 request.assignment_id)


@router.post("/simulations/end-visual-audio-attempt",
             tags=["Simulations", "End"])
async def end_visual_audio_attempt(
        request: EndVisualAudioAttemptRequest) -> EndSimulationResponse:
    """End a visual-audio simulation attempt"""
    logger.info(
        "API endpoint called: POST /simulations/end-visual-audio-attempt")
    return await controller.end_visual_audio_attempt(request)


@router.post("/simulations/end-visual-chat-attempt",
             tags=["Simulations", "End"])
async def end_visual_chat_attempt(
        request: EndVisualChatAttemptRequest) -> EndSimulationResponse:
    """End a visual-chat simulation attempt"""
    logger.info(
        "API endpoint called: POST /simulations/end-visual-chat-attempt")
    return await controller.end_visual_chat_attempt(request)


@router.post("/simulations/end-visual-attempt", tags=["Simulations", "End"])
async def end_visual_attempt(
        request: EndVisualAttemptRequest) -> EndSimulationResponse:
    """End a visual simulation attempt"""
    logger.info("API endpoint called: POST /simulations/end-visual-attempt")
    return await controller.end_visual_attempt(request)
