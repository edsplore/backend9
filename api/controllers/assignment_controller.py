from fastapi import APIRouter, HTTPException
from domain.services.assignment_service import AssignmentService
from api.schemas.requests import CreateAssignmentRequest, FetchAssignedPlansRequest
from utils.logger import Logger
from api.schemas.responses import (CreateAssignmentResponse,
                                   FetchAssignmentsResponse,
                                   FetchAssignedPlansResponse)

router = APIRouter()
logger = Logger.get_logger(__name__)

class AssignmentController:

    def __init__(self):
        self.service = AssignmentService()
        logger.info("AssignmentController initialized.")
    
    async def create_assignment(
            self,
            request: CreateAssignmentRequest) -> CreateAssignmentResponse:
        logger.info("Received request to create assignment.")
        logger.debug(f"Request data: {request.dict()}")
        try:
    
            result = await self.service.create_assignment(request)
            logger.info(f"Assignment created successfully: {result}")
            return CreateAssignmentResponse(id=result["id"],
                                            status=result["status"])
        except Exception as e:
            logger.error(f"Error while creating assignment: {str(e)}", exc_info=True)
            raise
    
    async def fetch_assignments(self) -> FetchAssignmentsResponse:
        logger.info("Fetching all assignments.")
        try:
            assignments = await self.service.fetch_assignments()
            logger.debug(f"Assignments fetched: {assignments}")
            return FetchAssignmentsResponse(assignments=assignments)
        except Exception as e:
            logger.error(f"Error fetching assignments: {str(e)}", exc_info=True)
            raise
    
    async def fetch_assigned_plans(
            self,
            request: FetchAssignedPlansRequest) -> FetchAssignedPlansResponse:
        logger.info(f"Fetching assigned plans for user_id={request.user_id}")
        try:
            response = await self.service.fetch_assigned_plans(request.user_id)
            logger.debug(f"Assigned plans: {response}")
            return response
        except Exception as e:
            logger.error(f"Error fetching assigned plans: {str(e)}", exc_info=True)
            raise

controller = AssignmentController()

@router.post("/create-assignment", tags=["Assignments", "Create"])
async def create_assignment(
        request: CreateAssignmentRequest) -> CreateAssignmentResponse:
    """Create a new assignment"""
    return await controller.create_assignment(request)


@router.get("/fetch-assignments", tags=["Assignments", "Read"])
async def fetch_assignments() -> FetchAssignmentsResponse:
    """Fetch all assignments"""
    return await controller.fetch_assignments()


@router.post("/fetch-assigned-plans", tags=["Assignments", "Read"])
async def fetch_assigned_plans(
        request: FetchAssignedPlansRequest) -> FetchAssignedPlansResponse:
    """Fetch assigned training plans with nested details"""
    return await controller.fetch_assigned_plans(request)
