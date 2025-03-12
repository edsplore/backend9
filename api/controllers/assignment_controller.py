from fastapi import APIRouter, HTTPException
from domain.services.assignment_service import AssignmentService
from api.schemas.requests import CreateAssignmentRequest
from api.schemas.responses import CreateAssignmentResponse, FetchAssignmentsResponse

router = APIRouter()


class AssignmentController:

    def __init__(self):
        self.service = AssignmentService()

    async def create_assignment(
            self,
            request: CreateAssignmentRequest) -> CreateAssignmentResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.name:
            raise HTTPException(status_code=400, detail="Missing 'name'")
        if not request.type:
            raise HTTPException(status_code=400, detail="Missing 'type'")
        if not request.start_date:
            raise HTTPException(status_code=400, detail="Missing 'start_date'")
        if not request.end_date:
            raise HTTPException(status_code=400, detail="Missing 'end_date'")

        result = await self.service.create_assignment(request)
        return CreateAssignmentResponse(id=result["id"],
                                        status=result["status"])

    async def fetch_assignments(self) -> FetchAssignmentsResponse:
        assignments = await self.service.fetch_assignments()
        return FetchAssignmentsResponse(assignments=assignments)


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
