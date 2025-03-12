from fastapi import APIRouter, HTTPException
from domain.services.list_service import ListService
from api.schemas.requests import ListItemsRequest
from api.schemas.responses import ListTrainingPlansResponse, ListModulesResponse, ListSimulationsResponse

router = APIRouter()


class ListController:

    def __init__(self):
        self.service = ListService()

    async def list_training_plans(
            self, request: ListItemsRequest) -> ListTrainingPlansResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")

        training_plans = await self.service.list_training_plans(request.user_id
                                                                )
        return ListTrainingPlansResponse(training_plans=training_plans)

    async def list_modules(self,
                           request: ListItemsRequest) -> ListModulesResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")

        modules = await self.service.list_modules(request.user_id)
        return ListModulesResponse(modules=modules)

    async def list_simulations(
            self, request: ListItemsRequest) -> ListSimulationsResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")

        simulations = await self.service.list_simulations(request.user_id)
        return ListSimulationsResponse(simulations=simulations)


controller = ListController()


@router.post("/list-training-plans", tags=["Read", "Training Plans"])
async def list_training_plans(
        request: ListItemsRequest) -> ListTrainingPlansResponse:
    """List all training plans with summary information"""
    return await controller.list_training_plans(request)


@router.post("/list-modules", tags=["Read", "Modules"])
async def list_modules(request: ListItemsRequest) -> ListModulesResponse:
    """List all modules with summary information"""
    return await controller.list_modules(request)


@router.post("/list-simulations", tags=["Read", "Simulations"])
async def list_simulations(
        request: ListItemsRequest) -> ListSimulationsResponse:
    """List all simulations with summary information"""
    return await controller.list_simulations(request)
