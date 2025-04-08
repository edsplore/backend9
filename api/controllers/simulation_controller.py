from fastapi import APIRouter, HTTPException, File, UploadFile, Request
from typing import Dict, List
from bson import ObjectId
from datetime import datetime
import aiohttp
from domain.services.simulation_service import SimulationService
from infrastructure.database import Database
from domain.services.chat_service import ChatService
from api.schemas.requests import (
    CreateSimulationRequest, UpdateSimulationRequest,
    StartAudioSimulationPreviewRequest, StartChatPreviewRequest,
    StartAudioSimulationRequest, StartChatSimulationRequest,
    EndAudioSimulationRequest, EndChatSimulationRequest,
    FetchSimulationsRequest, StartVisualAudioPreviewRequest,
    StartVisualChatPreviewRequest, StartVisualPreviewRequest)
from api.schemas.responses import (
    CreateSimulationResponse, UpdateSimulationResponse,
    StartAudioSimulationPreviewResponse, StartChatPreviewResponse,
    StartSimulationResponse, EndSimulationResponse, FetchSimulationsResponse,
    StartVisualAudioPreviewResponse, SlideImageData, SimulationByIDResponse,
    StartVisualChatPreviewResponse, StartVisualPreviewResponse, SimulationData)
from config import RETELL_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_KEY, AZURE_OPENAI_BASE_URL
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import AzureChatPromptExecutionSettings

router = APIRouter()


class SimulationController:

    def __init__(self):
        self.service = SimulationService()
        self.chat_service = ChatService()
        self.db = Database()

        # Initialize Azure OpenAI for scoring
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

    async def create_simulation(
            self,
            request: CreateSimulationRequest) -> CreateSimulationResponse:
        """Create a new simulation"""
        try:
            result = await self.service.create_simulation(request)
            return CreateSimulationResponse(id=result["id"],
                                            status=result["status"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def update_simulation(
            self,
            sim_id: str,
            request: UpdateSimulationRequest,
            slides: List[UploadFile] = None) -> UpdateSimulationResponse:
        """
        Update an existing simulation (controller).
        """
        result = await self.service.update_simulation(sim_id, request, slides)
        return UpdateSimulationResponse(id=result["id"],
                                        status=result["status"],
                                        document=result["document"])

    async def start_audio_simulation_preview(
        self, request: StartAudioSimulationPreviewRequest
    ) -> StartAudioSimulationPreviewResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.sim_id:
            raise HTTPException(status_code=400, detail="Missing 'simId'")
        result = await self.service.start_audio_simulation_preview(
            request.sim_id, request.user_id)
        return StartAudioSimulationPreviewResponse(
            access_token=result["access_token"])

    async def start_visual_audio_preview(
        self, request: StartVisualAudioPreviewRequest
    ) -> StartVisualAudioPreviewResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.sim_id:
            raise HTTPException(status_code=400, detail="Missing 'simId'")

        result = await self.service.start_visual_audio_preview(
            request.sim_id, request.user_id)

        print(result.simulation)

        return StartVisualAudioPreviewResponse(
            simulation=result.simulation,
            images=[
                SlideImageData(image_id=img.image_id,
                               image_data=img.image_data)
                for img in result.images
            ])

    async def start_visual_chat_preview(
        self, request: StartVisualChatPreviewRequest
    ) -> StartVisualChatPreviewResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.sim_id:
            raise HTTPException(status_code=400, detail="Missing 'simId'")

        result = await self.service.start_visual_chat_preview(
            request.sim_id, request.user_id)

        print(result.simulation)

        return StartVisualChatPreviewResponse(
            simulation=result.simulation,
            images=[
                SlideImageData(image_id=img.image_id,
                               image_data=img.image_data)
                for img in result.images
            ])

    async def start_visual_preview(
            self,
            request: StartVisualPreviewRequest) -> StartVisualPreviewResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.sim_id:
            raise HTTPException(status_code=400, detail="Missing 'simId'")

        result = await self.service.start_visual_preview(
            request.sim_id, request.user_id)

        print(result.simulation)

        return StartVisualPreviewResponse(simulation=result.simulation,
                                          images=[
                                              SlideImageData(
                                                  image_id=img.image_id,
                                                  image_data=img.image_data)
                                              for img in result.images
                                          ])

    async def start_chat_preview(
            self,
            request: StartChatPreviewRequest) -> StartChatPreviewResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.sim_id:
            raise HTTPException(status_code=400, detail="Missing 'simId'")
        if request.message == "":
            sim_id_object = ObjectId(request.sim_id)
            simulation = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {request.sim_id} not found")
            script = simulation.get("script", [])
            if script and len(script) > 0:
                first_entry = script[0]
                if first_entry.get("role").lower() == "customer":
                    return StartChatPreviewResponse(
                        response=first_entry.get("script_sentence", ""))
            return StartChatPreviewResponse(response="")
        else:
            result = await self.chat_service.start_chat(
                request.user_id, request.sim_id, request.message)
            return StartChatPreviewResponse(response=result["response"])

    async def start_audio_simulation(
            self,
            request: StartAudioSimulationRequest) -> StartSimulationResponse:
        """Start an audio simulation and create progress record"""
        try:
            # Get simulation
            sim_id_object = ObjectId(request.sim_id)
            simulation = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {request.sim_id} not found")

            # Get agent_id
            agent_id = simulation.get("agentId")
            if not agent_id:
                raise HTTPException(
                    status_code=400,
                    detail="Simulation does not have an agent configured")

            # Create web call
            web_call = await self._create_web_call(agent_id)

            # Create progress document
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

            # Insert into database
            result = await self.db.user_sim_progress.insert_one(progress_doc)

            return StartSimulationResponse(
                id=str(result.inserted_id),
                status="success",
                access_token=web_call["access_token"],
                call_id=web_call["call_id"])

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error starting audio simulation: {str(e)}")

    async def start_chat_simulation(
            self,
            request: StartChatSimulationRequest) -> StartSimulationResponse:
        """Start a chat simulation and create/update progress record"""
        try:
            # Get simulation
            sim_id_object = ObjectId(request.sim_id)
            simulation = await self.db.simulations.find_one(
                {"_id": sim_id_object})
            if not simulation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Simulation with id {request.sim_id} not found")

            # Get initial chat response if message provided
            chat_response = None
            if request.message is not None:  # Handle empty string case
                chat_response = await self.chat_service.start_chat(
                    request.user_id, request.sim_id, request.message)

            if request.usersimulationprogress_id:
                # Update existing progress document
                progress_id_object = ObjectId(
                    request.usersimulationprogress_id)
                progress_doc = await self.db.user_sim_progress.find_one(
                    {"_id": progress_id_object})

                if not progress_doc:
                    raise HTTPException(
                        status_code=404,
                        detail=
                        f"Progress document with id {request.usersimulationprogress_id} not found"
                    )

                # Update chat history if message provided
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

                # Update document
                await self.db.user_sim_progress.update_one(
                    {"_id": progress_id_object}, {"$set": update_doc})

                return StartSimulationResponse(
                    id=request.usersimulationprogress_id,
                    status="success",
                    response=chat_response["response"]
                    if chat_response else None)
            else:
                # Create new progress document
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

                # Add initial messages if provided
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

                # Insert into database
                result = await self.db.user_sim_progress.insert_one(
                    progress_doc)

                return StartSimulationResponse(
                    id=str(result.inserted_id),
                    status="success",
                    response=chat_response["response"]
                    if chat_response else None)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error starting chat simulation: {str(e)}")

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

    async def end_audio_simulation(
            self, request: EndAudioSimulationRequest) -> EndSimulationResponse:
        try:
            # Get call details from Retell AI
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {RETELL_API_KEY}'}
                url = f'https://api.retellai.com/v2/get-call/{request.call_id}'

                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail="Failed to fetch call details from Retell AI"
                        )

                    call_data = await response.json()

            # Get simulation details
            sim = await self.db.simulations.find_one(
                {"_id": ObjectId(request.simulation_id)})
            if not sim:
                raise HTTPException(
                    status_code=404,
                    detail=
                    f"Simulation with id {request.simulation_id} not found")

            # Calculate scores using Azure OpenAI
            transcript = call_data.get("transcript", "")
            scores = await self._calculate_scores(sim, transcript)

            transcriptObject = call_data.get("transcript_object", {})

            # Calculate duration in seconds
            duration = (call_data.get("end_timestamp", 0) -
                        call_data.get("start_timestamp", 0)) // 1000

            # Update user simulation progress
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
            raise HTTPException(
                status_code=500,
                detail=f"Error ending audio simulation: {str(e)}")

    async def end_chat_simulation(
            self, request: EndChatSimulationRequest) -> EndSimulationResponse:
        try:
            # Get simulation details
            sim = await self.db.simulations.find_one(
                {"_id": ObjectId(request.simulation_id)})
            if not sim:
                raise HTTPException(
                    status_code=404,
                    detail=
                    f"Simulation with id {request.simulation_id} not found")

            # Convert chat history to transcript format
            transcript = "\n".join(f"{msg.role}: {msg.sentence}"
                                   for msg in request.chat_history)

            # Calculate scores using Azure OpenAI
            scores = await self._calculate_scores(sim, transcript)

            # Calculate duration (for chat, we'll use a default or estimated value)
            duration = 300  # 5 minutes default for chat simulations

            # Update user simulation progress
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

            return EndSimulationResponse(id=request.usersimulationprogress_id,
                                         status="success",
                                         scores=scores,
                                         duration=duration,
                                         transcript=transcript,
                                         audio_url="")

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error ending chat simulation: {str(e)}")

    async def _calculate_scores(self, simulation: Dict,
                                transcript: str) -> Dict[str, float]:
        """Calculate simulation scores using Azure OpenAI"""
        try:
            history = ChatHistory()

            # Add system message with scoring instructions
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

            # Add conversation context
            script_text = "\n".join(f"{s['role']}: {s['script_sentence']}"
                                    for s in simulation['script'])

            context = (f"Expected Script:\n{script_text}\n\n"
                       f"Actual Conversation:\n{transcript}")
            history.add_user_message(context)

            # Get scores from Azure OpenAI
            result = await self.chat_completion.get_chat_message_content(
                history, settings=self.execution_settings)

            # Parse scores from response
            scores = eval(str(result))  # Convert string response to dict
            return scores

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error calculating scores: {str(e)}")

    async def fetch_simulations(
            self,
            request: FetchSimulationsRequest) -> FetchSimulationsResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        simulations = await self.service.fetch_simulations(request.user_id)
        return FetchSimulationsResponse(simulations=simulations)

    async def get_simulation_by_id(
            self, simulation_id: str) -> SimulationByIDResponse:
        """Get a single simulation by ID"""
        if not simulation_id:
            raise HTTPException(status_code=400, detail="Missing 'id'")

        simulation = await self.service.get_simulation_by_id(simulation_id)
        if not simulation:
            raise HTTPException(
                status_code=404,
                detail=f"Simulation with id {simulation_id} not found")
        return simulation


controller = SimulationController()


@router.put("/simulations/{sim_id}/update", tags=["Simulations", "Update"])
async def update_simulation(
    sim_id: str, req: Request, slides: List[UploadFile] = File(None)
) -> UpdateSimulationResponse:
    """
    Update an existing simulation.
    Can handle both JSON (no files) and multipart/form-data (with files).
    """
    content_type = req.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        # JSON body
        data = await req.json()
        slides_files = []
    else:
        # Multipart/form-data
        form_data = await req.form()
        data = dict(form_data)

        # Fields that might be JSON strings (list/array, dict/object).
        # Adjust as needed for your specific model fields.
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

        import json
        for field_name in json_fields:
            if field_name in data and isinstance(data[field_name], str):
                try:
                    data[field_name] = json.loads(data[field_name])
                except Exception as e:
                    print(f"DEBUG: Could not parse '{field_name}': {e}")

        # Extract slides files from keys like slides[0], slides[1], etc.
        slides_files = []
        for key, value in form_data.multi_items():
            if key.startswith("slides["):
                slides_files.append(value)

    # Parse into Pydantic model
    from api.schemas.requests import UpdateSimulationRequest
    try:
        update_request = UpdateSimulationRequest.parse_obj(data)
    except Exception as e:
        print("DEBUG: Error parsing UpdateSimulationRequest:", e)
        raise HTTPException(status_code=422, detail="Request validation error")

    # Forward to controller
    return await controller.update_simulation(sim_id, update_request,
                                              slides_files)


@router.post("/simulations/start-audio-preview", tags=["Simulations", "Audio"])
async def start_audio_simulation_preview(
    request: StartAudioSimulationPreviewRequest
) -> StartAudioSimulationPreviewResponse:
    return await controller.start_audio_simulation_preview(request)


@router.post("/simulations/start-chat-preview", tags=["Simulations", "Chat"])
async def start_chat_preview(
        request: StartChatPreviewRequest) -> StartChatPreviewResponse:
    return await controller.start_chat_preview(request)


@router.post("/simulations/start-audio", tags=["Simulations", "Start"])
async def start_audio_simulation(
        request: StartAudioSimulationRequest) -> StartSimulationResponse:
    """Start an audio simulation"""
    return await controller.start_audio_simulation(request)


@router.post("/simulations/start-chat", tags=["Simulations", "Start"])
async def start_chat_simulation(
        request: StartChatSimulationRequest) -> StartSimulationResponse:
    """Start a chat simulation"""
    print("test")
    return await controller.start_chat_simulation(request)


@router.post("/simulations/end-audio", tags=["Simulations", "End"])
async def end_audio_simulation(
        request: EndAudioSimulationRequest) -> EndSimulationResponse:
    return await controller.end_audio_simulation(request)


@router.post("/simulations/end-chat", tags=["Simulations", "End"])
async def end_chat_simulation(
        request: EndChatSimulationRequest) -> EndSimulationResponse:
    return await controller.end_chat_simulation(request)


@router.post("/simulations/fetch", tags=["Simulations", "Read"])
async def fetch_simulations(
        request: FetchSimulationsRequest) -> FetchSimulationsResponse:
    return await controller.fetch_simulations(request)


@router.post("/simulations/start-visual-audio-preview",
             tags=["Simulations", "Visual Audio"])
async def start_visual_audio_preview(
    request: StartVisualAudioPreviewRequest
) -> StartVisualAudioPreviewResponse:
    """Start a visual-audio simulation preview"""
    return await controller.start_visual_audio_preview(request)


@router.post("/simulations/start-visual-chat-preview",
             tags=["Simulations", "Visual Chat"])
async def start_visual_chat_preview(
        request: StartVisualChatPreviewRequest
) -> StartVisualChatPreviewResponse:
    """Start a visual-chat simulation preview"""
    return await controller.start_visual_chat_preview(request)


@router.post("/simulations/start-visual-preview",
             tags=["Simulations", "Visual"])
async def start_visual_preview(
        request: StartVisualPreviewRequest) -> StartVisualPreviewResponse:
    """Start a visual-chat simulation preview"""
    return await controller.start_visual_preview(request)


@router.get("/simulations/fetch/{simulation_id}", tags=["Simulations", "Read"])
async def get_simulation_by_id(simulation_id: str) -> SimulationByIDResponse:
    """Get a single simulation by ID"""
    return await controller.get_simulation_by_id(simulation_id)


@router.post("/simulations/create", tags=["Simulations", "Create"])
async def create_simulation(
        request: CreateSimulationRequest) -> CreateSimulationResponse:
    """Create a new simulation"""
    return await controller.create_simulation(request)
