from typing import Dict, List
from datetime import datetime
from infrastructure.database import Database
from api.schemas.requests import CreateAssignmentRequest
from api.schemas.responses import AssignmentData
from fastapi import HTTPException
from bson import ObjectId


class AssignmentService:

    def __init__(self):
        self.db = Database()

    async def create_assignment(self,
                                request: CreateAssignmentRequest) -> Dict:
        """Create a new assignment"""
        try:
            # Create assignment document
            assignment_doc = {
                "id": request.id,
                "name": request.name,
                "type": request.type,
                "startDate": request.start_date,
                "endDate": request.end_date,
                "teamId": [team.dict() for team in request.team_id],
                "traineeId": request.trainee_id,
                "createdBy": request.user_id,
                "createdAt": datetime.utcnow(),
                "lastModifiedBy": request.user_id,
                "lastModifiedAt": datetime.utcnow(),
                "status": "active"
            }

            # Insert into database
            result = await self.db.assignments.insert_one(assignment_doc)
            assignment_id = str(result.inserted_id)

            # Process trainee IDs
            for trainee_id in request.trainee_id:
                await self._process_user_assignment(trainee_id, assignment_id)

            # Process team members
            for team in request.team_id:
                # Process team leader
                if team.leader and team.leader.user_id:
                    await self._process_user_assignment(
                        team.leader.user_id, assignment_id, team.leader.dict())

                # Process team members
                if team.team_members:
                    for member in team.team_members:
                        if member.user_id:
                            await self._process_user_assignment(
                                member.user_id, assignment_id, member.dict())

            return {"id": assignment_id, "status": "success"}

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error creating assignment: {str(e)}")

    async def _process_user_assignment(self,
                                       user_id: str,
                                       assignment_id: str,
                                       user_data: Dict = None) -> None:
        """Process user document creation or update for assignments"""
        try:
            # Check if user exists
            existing_user = await self.db.users.find_one({"_id": user_id})

            if existing_user:
                # Update existing user's assignments array
                update_doc = {"$addToSet": {"assignments": assignment_id}}

                # Update user data if provided
                if user_data:
                    update_doc["$set"] = {
                        "first_name": user_data.get("first_name"),
                        "last_name": user_data.get("last_name"),
                        "email": user_data.get("email"),
                        "phone_no": user_data.get("phone_no"),
                        "fullName": user_data.get("fullName"),
                        "lastModifiedAt": datetime.utcnow()
                    }

                await self.db.users.update_one({"_id": user_id}, update_doc)
            else:
                # Create new user document
                new_user = {
                    "_id": user_id,
                    "assignments": [assignment_id],
                    "createdAt": datetime.utcnow(),
                    "lastModifiedAt": datetime.utcnow()
                }

                # Add user data if provided
                if user_data:
                    new_user.update({
                        "first_name": user_data.get("first_name"),
                        "last_name": user_data.get("last_name"),
                        "email": user_data.get("email"),
                        "phone_no": user_data.get("phone_no"),
                        "fullName": user_data.get("fullName")
                    })

                await self.db.users.insert_one(new_user)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing user assignment: {str(e)}")

    async def fetch_assignments(self) -> List[AssignmentData]:
        """Fetch all assignments"""
        try:
            cursor = self.db.assignments.find({})
            assignments = []

            async for doc in cursor:
                assignment = AssignmentData(
                    id=doc.get("id", ""),
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
