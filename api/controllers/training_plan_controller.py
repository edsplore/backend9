from fastapi import APIRouter, HTTPException
from domain.services.training_plan_service import TrainingPlanService
from api.schemas.requests import (CreateTrainingPlanRequest,
                                  FetchTrainingPlansRequest,
                                  CloneTrainingPlanRequest,
                                  UpdateTrainingPlanRequest, PaginationParams)
from api.schemas.responses import (CreateTrainingPlanResponse,
                                   FetchTrainingPlansResponse,
                                   TrainingPlanData, PaginationMetadata)
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

            result = await self.service.create_training_plan(request)

            # Check for duplicate name error
            if result.get("status") == "error":
                # Return a 409 Conflict for duplicate names
                if "already exists" in result.get("message", ""):
                    raise HTTPException(status_code=409,
                                        detail=result["message"])
                # Handle other errors with a 400 Bad Request
                else:
                    raise HTTPException(status_code=400,
                                        detail=result["message"])
                    
            logger.info(f"Training plan created with ID: {result['id']}")
            return CreateTrainingPlanResponse(id=result["id"],
                                              status=result["status"])
        except Exception as e:
            logger.error(f"Error creating training plan: {str(e)}",
                         exc_info=True)
            raise

    async def fetch_training_plans(
        self,
        request: FetchTrainingPlansRequest) -> FetchTrainingPlansResponse:
        logger.info(f"Fetching training plans for user_id: {request.user_id}")
        try:
            # Pass the pagination parameters to the service layer
            result = await self.service.fetch_training_plans(
                request.user_id, 
                pagination=request.pagination
            )
    
            training_plans = result["training_plans"]
            total_count = result["total_count"]
    
            # Create pagination metadata if pagination was requested
            pagination_metadata = None
            if request.pagination:
                page = request.pagination.page
                pagesize = request.pagination.pagesize
                total_pages = (total_count + pagesize - 1) // pagesize  # Ceiling division
    
                pagination_metadata = PaginationMetadata(
                    total_count=total_count,
                    page=page,
                    pagesize=pagesize,
                    total_pages=total_pages
                )
    
            logger.info(f"Fetched {len(training_plans)} training plan(s) out of {total_count} total.")
            return FetchTrainingPlansResponse(
                training_plans=training_plans,
                pagination=pagination_metadata
            )
        except Exception as e:
            logger.error(f"Error fetching training plans: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching training plans: {str(e)}")

    async def get_training_plan_by_id(
            self, training_plan_id: str) -> TrainingPlanData:
        logger.info(f"Fetching training plan by ID: {training_plan_id}")
        try:

            training_plan = await self.service.get_training_plan_by_id(
                training_plan_id)
            if not training_plan:
                logger.warning(
                    f"Training plan with ID {training_plan_id} not found.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Training plan with id {training_plan_id} not found"
                )

            logger.info(
                f"Training plan {training_plan_id} retrieved successfully.")
            return training_plan
        except Exception as e:
            logger.error(f"Error fetching training plan by ID: {str(e)}",
                         exc_info=True)
            raise

    async def clone_training_plan(
            self,
            request: CloneTrainingPlanRequest) -> CreateTrainingPlanResponse:
        logger.info("Received request to clone training plan.")
        logger.debug(f"Request: {request.dict()}")

        try:

            result = await self.service.clone_training_plan(request)
            logger.info(f"Training plan cloned. New ID: {result['id']}")
            return CreateTrainingPlanResponse(id=result["id"],
                                              status=result["status"])
        except Exception as e:
            logger.error(f"Error cloning training plan: {str(e)}",
                         exc_info=True)
            raise

    async def update_training_plan(
            self, training_plan_id: str,
            request: UpdateTrainingPlanRequest) -> TrainingPlanData:
        logger.info(
            f"Received request to update training plan ID: {training_plan_id}")
        logger.debug(f"Update data: {request.dict()}")

        try:

            result = await self.service.update_training_plan(
                training_plan_id, request)
            logger.info(
                f"Training plan {training_plan_id} updated successfully.")
            return result
        except Exception as e:
            logger.error(f"Error updating training plan: {str(e)}",
                         exc_info=True)
            raise


controller = TrainingPlanController()


@router.post("/training-plans/create", tags=["Training Plans", "Create"])
async def create_training_plan(
        request: CreateTrainingPlanRequest) -> CreateTrainingPlanResponse:
    logger.info("API called: /training-plans/create")
    return await controller.create_training_plan(request)


@router.post("/training-plans/clone", tags=["Training Plans", "Create"])
async def clone_training_plan(
        request: CloneTrainingPlanRequest) -> CreateTrainingPlanResponse:
    logger.info("API called: /training-plans/clone")
    return await controller.clone_training_plan(request)


@router.put("/training-plans/{training_plan_id}/update",
            tags=["Training Plans", "Update"])
async def update_training_plan(
        training_plan_id: str,
        request: UpdateTrainingPlanRequest) -> TrainingPlanData:
    logger.info(f"API called: /training-plans/{training_plan_id}/update")
    return await controller.update_training_plan(training_plan_id, request)


@router.post("/training-plans/fetch", tags=["Training Plans", "Read"])
async def fetch_training_plans(
        request: FetchTrainingPlansRequest) -> FetchTrainingPlansResponse:
    logger.info("API called: /training-plans/fetch")
    return await controller.fetch_training_plans(request)


@router.get("/training-plans/fetch/{training_plan_id}",
            tags=["Training Plans", "Read"])
async def get_training_plan_by_id(training_plan_id: str) -> TrainingPlanData:
    logger.info(f"API called: /training-plans/fetch/{training_plan_id}")
    return await controller.get_training_plan_by_id(training_plan_id)
