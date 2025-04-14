from fastapi import APIRouter, HTTPException
from domain.services.training_plan_service import TrainingPlanService
from api.schemas.requests import CreateTrainingPlanRequest, FetchTrainingPlansRequest, CloneTrainingPlanRequest, UpdateTrainingPlanRequest
from api.schemas.responses import CreateTrainingPlanResponse, FetchTrainingPlansResponse, TrainingPlanData


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

    async def get_training_plan_by_id(self, training_plan_id: str) -> TrainingPlanData:
        if not training_plan_id:
            raise HTTPException(status_code=400, detail="Missing 'id'")

        training_plan = await self.service.get_training_plan_by_id(training_plan_id)
        if not training_plan:
            raise HTTPException(
                status_code=404,
                detail=f"Training plan with id {training_plan_id} not found")
        return training_plan

    async def clone_training_plan(self, request: CloneTrainingPlanRequest) -> CreateTrainingPlanResponse:
        """Clone an existing training plan"""
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.training_plan_id:
            raise HTTPException(status_code=400, detail="Missing 'trainingPlanId'")

        result = await self.service.clone_training_plan(request)
        return CreateTrainingPlanResponse(id=result["id"], status=result["status"])

    async def update_training_plan(self, training_plan_id: str, request: UpdateTrainingPlanRequest) -> TrainingPlanData:
        """Update an existing training plan"""
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")

        result = await self.service.update_training_plan(training_plan_id, request)
        return result


controller = TrainingPlanController()


@router.post("/training-plans/create", tags=["Training Plans", "Create"])
async def create_training_plan(
        request: CreateTrainingPlanRequest) -> CreateTrainingPlanResponse:
    return await controller.create_training_plan(request)


@router.post("/training-plans/clone", tags=["Training Plans", "Create"])
async def clone_training_plan(request: CloneTrainingPlanRequest) -> CreateTrainingPlanResponse:
    """Clone an existing training plan"""
    return await controller.clone_training_plan(request)


@router.put("/training-plans/{training_plan_id}/update", tags=["Training Plans", "Update"])
async def update_training_plan(training_plan_id: str, request: UpdateTrainingPlanRequest) -> TrainingPlanData:
    """Update an existing training plan"""
    return await controller.update_training_plan(training_plan_id, request)


@router.post("/training-plans/fetch", tags=["Training Plans", "Read"])
async def fetch_training_plans(
        request: FetchTrainingPlansRequest) -> FetchTrainingPlansResponse:
    return await controller.fetch_training_plans(request)


@router.get("/training-plans/fetch/{training_plan_id}", tags=["Training Plans", "Read"])
async def get_training_plan_by_id(training_plan_id: str) -> TrainingPlanData:
    """Get a single training plan by ID"""
    return await controller.get_training_plan_by_id(training_plan_id)