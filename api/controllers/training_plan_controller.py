from fastapi import APIRouter, HTTPException
from domain.services.training_plan_service import TrainingPlanService
from api.schemas.requests import (
    CreateTrainingPlanRequest,
    FetchTrainingPlansRequest,
    CloneTrainingPlanRequest,
    UpdateTrainingPlanRequest
)
from api.schemas.responses import (
    CreateTrainingPlanResponse,
    FetchTrainingPlansResponse,
    TrainingPlanData
)
from utils.logger import Logger

logger = Logger.get_logger(__name__)
router = APIRouter()


class TrainingPlanController:

    def __init__(self):
        self.service = TrainingPlanService()
        logger.info("TrainingPlanController initialized.")

    async def create_training_plan(
            self,
            request: CreateTrainingPlanRequest) -> CreateTrainingPlanResponse:
        logger.info("Received request to create training plan.")
        logger.debug(f"Request: {request.dict()}")

        try:
            if not request.user_id:
                logger.warning("Missing 'userId' in create_training_plan request.")
                raise HTTPException(status_code=400, detail="Missing 'userId'")
            if not request.training_plan_name:
                logger.warning("Missing 'trainingPlanName' in request.")
                raise HTTPException(status_code=400, detail="Missing 'trainingPlanName'")
            if not request.added_object:
                logger.warning("Missing 'addedObject' in request.")
                raise HTTPException(status_code=400, detail="Missing 'addedObject'")

            result = await self.service.create_training_plan(request)
            logger.info(f"Training plan created with ID: {result['id']}")
            return CreateTrainingPlanResponse(id=result["id"], status=result["status"])
        except Exception as e:
            logger.error(f"Error creating training plan: {str(e)}", exc_info=True)
            raise

    async def fetch_training_plans(
            self,
            request: FetchTrainingPlansRequest) -> FetchTrainingPlansResponse:
        logger.info(f"Fetching training plans for user_id: {request.user_id}")
        try:
            if not request.user_id:
                logger.warning("Missing 'userId' in fetch_training_plans request.")
                raise HTTPException(status_code=400, detail="Missing 'userId'")

            training_plans = await self.service.fetch_training_plans(request.user_id)
            logger.info(f"Fetched {len(training_plans)} training plans.")
            return FetchTrainingPlansResponse(training_plans=training_plans)
        except Exception as e:
            logger.error(f"Error fetching training plans: {str(e)}", exc_info=True)
            raise

    async def get_training_plan_by_id(self, training_plan_id: str) -> TrainingPlanData:
        logger.info(f"Fetching training plan by ID: {training_plan_id}")
        try:
            if not training_plan_id:
                logger.warning("Missing 'id' in get_training_plan_by_id request.")
                raise HTTPException(status_code=400, detail="Missing 'id'")

            training_plan = await self.service.get_training_plan_by_id(training_plan_id)
            if not training_plan:
                logger.warning(f"Training plan with ID {training_plan_id} not found.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Training plan with id {training_plan_id} not found"
                )

            logger.info(f"Training plan {training_plan_id} retrieved successfully.")
            return training_plan
        except Exception as e:
            logger.error(f"Error fetching training plan by ID: {str(e)}", exc_info=True)
            raise

    async def clone_training_plan(self, request: CloneTrainingPlanRequest) -> CreateTrainingPlanResponse:
        logger.info("Received request to clone training plan.")
        logger.debug(f"Request: {request.dict()}")

        try:
            if not request.user_id:
                logger.warning("Missing 'userId' in clone_training_plan request.")
                raise HTTPException(status_code=400, detail="Missing 'userId'")
            if not request.training_plan_id:
                logger.warning("Missing 'trainingPlanId' in request.")
                raise HTTPException(status_code=400, detail="Missing 'trainingPlanId'")

            result = await self.service.clone_training_plan(request)
            logger.info(f"Training plan cloned. New ID: {result['id']}")
            return CreateTrainingPlanResponse(id=result["id"], status=result["status"])
        except Exception as e:
            logger.error(f"Error cloning training plan: {str(e)}", exc_info=True)
            raise

    async def update_training_plan(self, training_plan_id: str, request: UpdateTrainingPlanRequest) -> TrainingPlanData:
        logger.info(f"Received request to update training plan ID: {training_plan_id}")
        logger.debug(f"Update data: {request.dict()}")

        try:
            if not request.user_id:
                logger.warning("Missing 'userId' in update_training_plan request.")
                raise HTTPException(status_code=400, detail="Missing 'userId'")

            result = await self.service.update_training_plan(training_plan_id, request)
            logger.info(f"Training plan {training_plan_id} updated successfully.")
            return result
        except Exception as e:
            logger.error(f"Error updating training plan: {str(e)}", exc_info=True)
            raise


controller = TrainingPlanController()


@router.post("/training-plans/create", tags=["Training Plans", "Create"])
async def create_training_plan(
        request: CreateTrainingPlanRequest) -> CreateTrainingPlanResponse:
    logger.info("API called: /training-plans/create")
    return await controller.create_training_plan(request)


@router.post("/training-plans/clone", tags=["Training Plans", "Create"])
async def clone_training_plan(request: CloneTrainingPlanRequest) -> CreateTrainingPlanResponse:
    logger.info("API called: /training-plans/clone")
    return await controller.clone_training_plan(request)


@router.put("/training-plans/{training_plan_id}/update", tags=["Training Plans", "Update"])
async def update_training_plan(training_plan_id: str, request: UpdateTrainingPlanRequest) -> TrainingPlanData:
    logger.info(f"API called: /training-plans/{training_plan_id}/update")
    return await controller.update_training_plan(training_plan_id, request)


@router.post("/training-plans/fetch", tags=["Training Plans", "Read"])
async def fetch_training_plans(
        request: FetchTrainingPlansRequest) -> FetchTrainingPlansResponse:
    logger.info("API called: /training-plans/fetch")
    return await controller.fetch_training_plans(request)


@router.get("/training-plans/fetch/{training_plan_id}", tags=["Training Plans", "Read"])
async def get_training_plan_by_id(training_plan_id: str) -> TrainingPlanData:
    logger.info(f"API called: /training-plans/fetch/{training_plan_id}")
    return await controller.get_training_plan_by_id(training_plan_id)
