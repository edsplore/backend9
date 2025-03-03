from typing import Dict
from datetime import datetime
from infrastructure.database import Database
from api.schemas.requests import CreateAssignmentRequest
from fastapi import HTTPException


class AssignmentService:

    def __init__(self):
        self.db = Database()

    async def create_assignment(self,
                                request: CreateAssignmentRequest) -> Dict:
        """Create a new assignment"""
        try:
            # Create assignment document
            assignment_doc = {
                "assignmentName": request.assignment_name,
                "assignedItemType": request.assignment_type,
                "assignedItemId": request.assignment_id,
                "startDate": request.start_date,
                "endDate": request.end_date,
                "team": request.team,
                "trainee": request.trainee,
                "createdBy": request.user_id,
                "createdAt": datetime.utcnow(),
                "lastModifiedBy": request.user_id,
                "lastModifiedAt": datetime.utcnow(),
                "status": "assigned"
            }

            # Insert into database
            result = await self.db.assignments.insert_one(assignment_doc)

            return {"id": str(result.inserted_id), "status": "success"}

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error creating assignment: {str(e)}")
