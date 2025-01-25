# api/controllers/simulation_controller.py
from fastapi import APIRouter, HTTPException
from typing import Dict
from domain.services.simulation_service import SimulationService
from api.schemas.requests import CreateSimulationRequest

router = APIRouter()

class SimulationController:
    def __init__(self):
        self.service = SimulationService()

    async def create_simulation(self, request: CreateSimulationRequest) -> Dict:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.name:
            raise HTTPException(status_code=400, detail="Missing 'name'")
        if not request.division_id:
            raise HTTPException(status_code=400, detail="Missing 'divisionId'")
        if not request.department_id:
            raise HTTPException(status_code=400, detail="Missing 'departmentId'")
        if not request.script:
            raise HTTPException(status_code=400, detail="Missing 'script'")

        simulation_id = await self.service.create_simulation(request)
        return {"id": simulation_id, "status": "success"}

controller = SimulationController()

@router.post("/simulations/create")
async def create_simulation(request: CreateSimulationRequest) -> Dict:
    return await controller.create_simulation(request)
