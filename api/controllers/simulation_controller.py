from fastapi import APIRouter, HTTPException
from typing import Dict
from domain.services.simulation_service import SimulationService
from api.schemas.requests import CreateSimulationRequest, UpdateSimulationRequest
from api.schemas.responses import CreateSimulationResponse, UpdateSimulationResponse
from api.schemas.requests import StartAudioSimulationPreviewRequest
from api.schemas.responses import StartAudioSimulationPreviewResponse

router = APIRouter()


class SimulationController:

    def __init__(self):
        self.service = SimulationService()

    async def create_simulation(
            self,
            request: CreateSimulationRequest) -> CreateSimulationResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.name:
            raise HTTPException(status_code=400, detail="Missing 'name'")
        if not request.division_id:
            raise HTTPException(status_code=400, detail="Missing 'divisionId'")
        if not request.department_id:
            raise HTTPException(status_code=400,
                                detail="Missing 'departmentId'")
        if not request.script:
            raise HTTPException(status_code=400, detail="Missing 'script'")

        result = await self.service.create_simulation(request)
        return CreateSimulationResponse(id=result["id"],
                                        status=result["status"],
                                        prompt=result["prompt"])

    async def update_simulation(
            self, sim_id: str,
            request: UpdateSimulationRequest) -> UpdateSimulationResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")

        result = await self.service.update_simulation(sim_id, request)
        return UpdateSimulationResponse(id=result["id"],
                                        status=result["status"])

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


controller = SimulationController()


@router.post("/simulations/create")
async def create_simulation(
        request: CreateSimulationRequest) -> CreateSimulationResponse:
    return await controller.create_simulation(request)


@router.put("/simulations/{sim_id}/update")
async def update_simulation(
        sim_id: str,
        request: UpdateSimulationRequest) -> UpdateSimulationResponse:
    return await controller.update_simulation(sim_id, request)


@router.post("/simulations/start-audio-preview")
async def start_audio_simulation_preview(
    request: StartAudioSimulationPreviewRequest
) -> StartAudioSimulationPreviewResponse:
    return await controller.start_audio_simulation_preview(request)
