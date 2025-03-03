from fastapi import APIRouter, HTTPException
from domain.services.assignment_service import AssignmentService
from api.schemas.requests import CreateAssignmentRequest
from api.schemas.responses import CreateAssignmentResponse

router = APIRouter()


class AssignmentController:

    def __init__(self):
        self.service = AssignmentService()

    async def create_assignment(
            self,
            request: CreateAssignmentRequest) -> CreateAssignmentResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.assignment_name:
            raise HTTPException(status_code=400,
                                detail="Missing 'assignment_name'")
        if not request.assignment_type:
            raise HTTPException(status_code=400,
                                detail="Missing 'assignment_type'")
        if not request.assignment_id:
            raise HTTPException(status_code=400,
                                detail="Missing 'assignment_id'")
        if not request.start_date:
            raise HTTPException(status_code=400, detail="Missing 'start_date'")
        if not request.end_date:
            raise HTTPException(status_code=400, detail="Missing 'end_date'")

        result = await self.service.create_assignment(request)
        return CreateAssignmentResponse(id=result["id"],
                                        status=result["status"])


controller = AssignmentController()


@router.post("/create-assignment")
async def create_assignment(
        request: CreateAssignmentRequest) -> CreateAssignmentResponse:
    """Create a new assignment"""
    return await controller.create_assignment(request)
