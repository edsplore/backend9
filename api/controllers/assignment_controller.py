from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from domain.services.assignment_service import AssignmentService
from api.schemas.requests import (CreateAssignmentRequest,
                                  FetchAssignedPlansRequest, PaginationParams)
from utils.logger import Logger
from api.schemas.responses import (CreateAssignmentResponse,
                                   FetchAssignmentsResponse,
                                   FetchAssignedPlansResponse,
                                   PaginationMetadata)

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
                    
            logger.info(f"Assignment created successfully: {result}")
            return CreateAssignmentResponse(id=result["id"],
                                            status=result["status"])
        except Exception as e:
            logger.error(f"Error while creating assignment: {str(e)}",
                         exc_info=True)
            raise

    async def fetch_assignments(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> FetchAssignmentsResponse:
        logger.info("Fetching all assignments.")
        try:
            # Pass the pagination parameters to the service layer
            result = await self.service.fetch_assignments(pagination)

            assignments = result["assignments"]
            total_count = result["total_count"]

            # Create pagination metadata if pagination was requested
            pagination_metadata = None
            if pagination:
                page = pagination.page
                pagesize = pagination.pagesize
                total_pages = (total_count + pagesize -
                               1) // pagesize  # Ceiling division

                pagination_metadata = PaginationMetadata(
                    total_count=total_count,
                    page=page,
                    pagesize=pagesize,
                    total_pages=total_pages)

            logger.debug(
                f"Assignments fetched: {len(assignments)} out of {total_count} total"
            )
            return FetchAssignmentsResponse(assignments=assignments,
                                            pagination=pagination_metadata)
        except Exception as e:
            logger.error(f"Error fetching assignments: {str(e)}",
                         exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error fetching assignments: {str(e)}")

    async def fetch_assigned_plans(
            self,
            request: FetchAssignedPlansRequest) -> FetchAssignedPlansResponse:
        logger.info(f"Fetching assigned plans for user_id={request.user_id}")
        try:
            # Pass the pagination parameters to the service layer
            result = await self.service.fetch_assigned_plans(
                request.user_id, pagination=request.pagination)

            response_data = result["data"]
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

            # Add pagination metadata to the response
            response_data.pagination = pagination_metadata

            logger.debug(
                f"Assigned plans fetched with pagination: {pagination_metadata}"
            )
            return response_data
        except Exception as e:
            logger.error(f"Error fetching assigned plans: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching assigned plans: {str(e)}")


controller = AssignmentController()


@router.post("/create-assignment", tags=["Assignments", "Create"])
async def create_assignment(
        request: CreateAssignmentRequest) -> CreateAssignmentResponse:
    """Create a new assignment"""
    return await controller.create_assignment(request)


@router.post("/fetch-assignments", tags=["Assignments", "Read"])
async def fetch_assignments(request: dict = None) -> FetchAssignmentsResponse:
    """Fetch all assignments with optional pagination"""
    pagination = None
    if request and "pagination" in request:
        pagination = PaginationParams(**request["pagination"])
    return await controller.fetch_assignments(pagination)


@router.post("/fetch-assigned-plans", tags=["Assignments", "Read"])
async def fetch_assigned_plans(
        request: FetchAssignedPlansRequest) -> FetchAssignedPlansResponse:
    """Fetch assigned training plans with nested details"""
    return await controller.fetch_assigned_plans(request)
