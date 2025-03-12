from typing import Dict, List
from datetime import datetime
from infrastructure.database import Database
from api.schemas.requests import CreateAssignmentRequest
from api.schemas.responses import AssignmentData
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
                "name": request.name,
                "type": request.type,
                "startDate": request.start_date,
                "endDate": request.end_date,
                "teamId": request.team_id,
                "traineeId": request.trainee_id,
                "createdBy": request.user_id,
                "createdAt": datetime.utcnow(),
                "lastModifiedBy": request.user_id,
                "lastModifiedAt": datetime.utcnow(),
                "status": "active"
            }

            # Insert into database
            result = await self.db.assignments.insert_one(assignment_doc)

            return {"id": str(result.inserted_id), "status": "success"}

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error creating assignment: {str(e)}")

    async def fetch_assignments(self) -> List[AssignmentData]:
        """Fetch all assignments"""
        try:
            cursor = self.db.assignments.find({})
            assignments = []

            async for doc in cursor:
                assignment = AssignmentData(
                    id=str(doc["_id"]),
                    name=doc.get("name", ""),
                    type=doc.get("type", ""),
                    start_date=doc.get("startDate", ""),
                    end_date=doc.get("endDate", ""),
                    team_id=doc.get("teamId", []),
                    trainee_id=doc.get("traineeId", []),
                    created_by=doc.get("createdBy", ""),
                    created_at=doc.get("createdAt",
                                       datetime.utcnow()).isoformat(),
                    last_modified_by=doc.get("lastModifiedBy", ""),
                    last_modified_at=doc.get("lastModifiedAt",
                                             datetime.utcnow()).isoformat(),
                    status=doc.get("status", ""))
                assignments.append(assignment)

            return assignments

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error fetching assignments: {str(e)}")
