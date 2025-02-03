from fastapi import APIRouter, HTTPException
from domain.services.training_plan_service import TrainingPlanService
from api.schemas.requests import CreateTrainingPlanRequest, FetchTrainingPlansRequest
from api.schemas.responses import CreateTrainingPlanResponse, FetchTrainingPlansResponse

router = APIRouter()


class TrainingPlanController:

    def __init__(self):
        self.service = TrainingPlanService()

    async def create_training_plan(
            self,
            request: CreateTrainingPlanRequest) -> CreateTrainingPlanResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.training_plan_name:
            raise HTTPException(status_code=400,
                                detail="Missing 'trainingPlanName'")
        if not request.added_object:
            raise HTTPException(status_code=400,
                                detail="Missing 'addedObject'")

        result = await self.service.create_training_plan(request)
        return CreateTrainingPlanResponse(id=result["id"],
                                          status=result["status"])

    async def fetch_training_plans(
            self,
            request: FetchTrainingPlansRequest) -> FetchTrainingPlansResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")

        training_plans = await self.service.fetch_training_plans(
            request.user_id)
        return FetchTrainingPlansResponse(training_plans=training_plans)


controller = TrainingPlanController()


@router.post("/training-plans/create")
async def create_training_plan(
        request: CreateTrainingPlanRequest) -> CreateTrainingPlanResponse:
    return await controller.create_training_plan(request)


@router.post("/training-plans/fetch")
async def fetch_training_plans(
        request: FetchTrainingPlansRequest) -> FetchTrainingPlansResponse:
    return await controller.fetch_training_plans(request)
