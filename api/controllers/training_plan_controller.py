from fastapi import APIRouter, HTTPException, Request
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
            self, request: CreateTrainingPlanRequest,
            workspace: str) -> CreateTrainingPlanResponse:
        logger.info(
            f"Received request to create training plan in workspace {workspace}."
        )
        logger.debug(f"Request: {request.dict()}")

        try:

            result = await self.service.create_training_plan(
                request, workspace)

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

            logger.info(
                f"Training plan created with ID: {result['id']} in workspace {workspace}"
            )
            return CreateTrainingPlanResponse(id=result["id"],
                                              status=result["status"])
        except Exception as e:
            logger.error(f"Error creating training plan: {str(e)}",
                         exc_info=True)
            raise

    async def fetch_training_plans(
            self, request: FetchTrainingPlansRequest,
            workspace: str) -> FetchTrainingPlansResponse:
        logger.info(
            f"Fetching training plans for user_id: {request.user_id} in workspace {workspace}"
        )
        try:
            # Pass the pagination parameters and workspace to the service layer
            result = await self.service.fetch_training_plans(
                request.user_id, workspace, pagination=request.pagination)

            training_plans = result["training_plans"]
            total_count = result["total_count"]

            # Create pagination metadata if pagination was requested
            pagination_metadata = None
            if request.pagination:
                page = request.pagination.page
                pagesize = request.pagination.pagesize
                total_pages = (total_count + pagesize -
                               1) // pagesize  # Ceiling division

                pagination_metadata = PaginationMetadata(
                    total_count=total_count,
                    page=page,
                    pagesize=pagesize,
                    total_pages=total_pages)

            logger.info(
                f"Fetched {len(training_plans)} training plan(s) out of {total_count} total."
            )
            return FetchTrainingPlansResponse(training_plans=training_plans,
                                              pagination=pagination_metadata)
        except Exception as e:
            logger.error(f"Error fetching training plans: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching training plans: {str(e)}")

    async def get_training_plan_by_id(self, training_plan_id: str,
                                      workspace: str) -> TrainingPlanData:
        logger.info(
            f"Fetching training plan by ID: {training_plan_id} in workspace {workspace}"
        )
        try:

            training_plan = await self.service.get_training_plan_by_id(
                training_plan_id, workspace)
            if not training_plan:
                logger.warning(
                    f"Training plan with ID {training_plan_id} not found in workspace {workspace}."
                )
                raise HTTPException(
                    status_code=404,
                    detail=
                    f"Training plan with id {training_plan_id} not found in workspace {workspace}"
                )

            logger.info(
                f"Training plan {training_plan_id} retrieved successfully.")
            return training_plan
        except Exception as e:
            logger.error(f"Error fetching training plan by ID: {str(e)}",
                         exc_info=True)
            raise

    async def clone_training_plan(
            self, request: CloneTrainingPlanRequest,
            workspace: str) -> CreateTrainingPlanResponse:
        logger.info(
            f"Received request to clone training plan in workspace {workspace}."
        )
        logger.debug(f"Request: {request.dict()}")

        try:

            result = await self.service.clone_training_plan(request, workspace)
            logger.info(f"Training plan cloned. New ID: {result['id']}")
            return CreateTrainingPlanResponse(id=result["id"],
                                              status=result["status"])
        except Exception as e:
            logger.error(f"Error cloning training plan: {str(e)}",
                         exc_info=True)
            raise

    async def update_training_plan(self, training_plan_id: str,
                                   request: UpdateTrainingPlanRequest,
                                   workspace: str) -> TrainingPlanData:
        logger.info(
            f"Received request to update training plan ID: {training_plan_id} in workspace {workspace}"
        )
        logger.debug(f"Update data: {request.dict()}")

        try:

            result = await self.service.update_training_plan(
                training_plan_id, request, workspace)
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
        request: CreateTrainingPlanRequest,
        current_request: Request) -> CreateTrainingPlanResponse:
    logger.info("API called: /training-plans/create")
    workspace = current_request.headers.get('x-workspace-id')
    if not workspace:
        raise HTTPException(status_code=400, detail="Workspace ID is required")
    return await controller.create_training_plan(request, workspace)


@router.post("/training-plans/clone", tags=["Training Plans", "Create"])
async def clone_training_plan(
        request: CloneTrainingPlanRequest,
        current_request: Request) -> CreateTrainingPlanResponse:
    logger.info("API called: /training-plans/clone")
    workspace = current_request.headers.get('x-workspace-id')
    if not workspace:
        raise HTTPException(status_code=400, detail="Workspace ID is required")
    return await controller.clone_training_plan(request, workspace)


@router.put("/training-plans/{training_plan_id}/update",
            tags=["Training Plans", "Update"])
async def update_training_plan(training_plan_id: str,
                               request: UpdateTrainingPlanRequest,
                               current_request: Request) -> TrainingPlanData:
    logger.info(f"API called: /training-plans/{training_plan_id}/update")
    workspace = current_request.headers.get('x-workspace-id')
    if not workspace:
        raise HTTPException(status_code=400, detail="Workspace ID is required")
    return await controller.update_training_plan(training_plan_id, request,
                                                 workspace)


@router.post("/training-plans/fetch", tags=["Training Plans", "Read"])
async def fetch_training_plans(
        request: FetchTrainingPlansRequest,
        current_request: Request) -> FetchTrainingPlansResponse:
    logger.info("API called: /training-plans/fetch")
    workspace = current_request.headers.get('x-workspace-id')
    if not workspace:
        raise HTTPException(status_code=400, detail="Workspace ID is required")
    return await controller.fetch_training_plans(request, workspace)


@router.get("/training-plans/fetch/{training_plan_id}",
            tags=["Training Plans", "Read"])
async def get_training_plan_by_id(
        training_plan_id: str, current_request: Request) -> TrainingPlanData:
    logger.info(f"API called: /training-plans/fetch/{training_plan_id}")
    workspace = current_request.headers.get('x-workspace-id')
    if not workspace:
        raise HTTPException(status_code=400, detail="Workspace ID is required")
    return await controller.get_training_plan_by_id(training_plan_id,
                                                    workspace)
