from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from infrastructure.database import Database
from api.schemas.requests import CreateTrainingPlanRequest
from api.schemas.responses import TrainingPlanData
from fastapi import HTTPException


class TrainingPlanService:

    def __init__(self):
        self.db = Database()

    async def create_training_plan(self,
                                   request: CreateTrainingPlanRequest) -> Dict:
        """Create a new training plan"""
        try:
            # Validate added objects
            for obj in request.added_object:
                if obj.type == "module":
                    module = await self.db.modules.find_one(
                        {"_id": ObjectId(obj.id)})
                    if not module:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Module with id {obj.id} not found")
                elif obj.type == "simulation":
                    simulation = await self.db.simulations.find_one(
                        {"_id": ObjectId(obj.id)})
                    if not simulation:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Simulation with id {obj.id} not found")
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid object type: {obj.type}")

            # Create training plan document
            training_plan_doc = {
                "name": request.training_plan_name,
                "tags": request.tags,
                "addedObject": [obj.dict() for obj in request.added_object],
                "createdBy": request.user_id,
                "createdAt": datetime.utcnow(),
                "lastModifiedBy": request.user_id,
                "lastModifiedAt": datetime.utcnow()
            }

            # Insert into database
            result = await self.db.training_plans.insert_one(training_plan_doc)

            return {"id": str(result.inserted_id), "status": "success"}

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating training plan: {str(e)}")

    async def fetch_training_plans(self,
                                   user_id: str) -> List[TrainingPlanData]:
        """Fetch all training plans"""
        try:
            cursor = self.db.training_plans.find({})
            training_plans = []

            async for doc in cursor:
                # Calculate total estimated time from all objects
                total_estimated_time = 0

                for obj in doc.get("addedObject", []):
                    try:
                        if obj["type"] == "module":
                            # Get module's simulations and their times
                            module = await self.db.modules.find_one(
                                {"_id": ObjectId(obj["id"])})
                            if module:
                                for sim_id in module.get("simulationIds", []):
                                    sim = await self.db.simulations.find_one(
                                        {"_id": ObjectId(sim_id)})
                                    if sim and "estimatedTimeToAttemptInMins" in sim:
                                        total_estimated_time += sim[
                                            "estimatedTimeToAttemptInMins"]
                        elif obj["type"] == "simulation":
                            # Get simulation time directly
                            sim = await self.db.simulations.find_one(
                                {"_id": ObjectId(obj["id"])})
                            if sim and "estimatedTimeToAttemptInMins" in sim:
                                total_estimated_time += sim[
                                    "estimatedTimeToAttemptInMins"]
                    except Exception:
                        # Skip if object not found or invalid ID
                        continue

                training_plan = TrainingPlanData(
                    id=str(doc["_id"]),
                    name=doc.get("name", ""),
                    tags=doc.get("tags", []),
                    added_object=doc.get("addedObject", []),
                    created_by=doc.get("createdBy", ""),
                    created_at=doc.get("createdAt",
                                       datetime.utcnow()).isoformat(),
                    last_modified_by=doc.get("lastModifiedBy", ""),
                    last_modified_at=doc.get("lastModifiedAt",
                                             datetime.utcnow()).isoformat(),
                    estimated_time=total_estimated_time)
                training_plans.append(training_plan)

            return training_plans

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching training plans: {str(e)}")

    async def get_training_plan_by_id(self, training_plan_id: str) -> Optional[TrainingPlanData]:
        """Fetch a single training plan by ID"""
        try:
            # Convert string ID to ObjectId
            training_plan_id_object = ObjectId(training_plan_id)

            # Find the training plan
            doc = await self.db.training_plans.find_one({"_id": training_plan_id_object})

            if not doc:
                return None

            # Calculate total estimated time from all objects
            total_estimated_time = 0

            for obj in doc.get("addedObject", []):
                try:
                    if obj["type"] == "module":
                        # Get module's simulations and their times
                        module = await self.db.modules.find_one(
                            {"_id": ObjectId(obj["id"])})
                        if module:
                            for sim_id in module.get("simulationIds", []):
                                sim = await self.db.simulations.find_one(
                                    {"_id": ObjectId(sim_id)})
                                if sim and "estimatedTimeToAttemptInMins" in sim:
                                    total_estimated_time += sim[
                                        "estimatedTimeToAttemptInMins"]
                    elif obj["type"] == "simulation":
                        # Get simulation time directly
                        sim = await self.db.simulations.find_one(
                            {"_id": ObjectId(obj["id"])})
                        if sim and "estimatedTimeToAttemptInMins" in sim:
                            total_estimated_time += sim[
                                "estimatedTimeToAttemptInMins"]
                except Exception:
                    # Skip if object not found or invalid ID
                    continue

            return TrainingPlanData(
                id=str(doc["_id"]),
                name=doc.get("name", ""),
                tags=doc.get("tags", []),
                added_object=doc.get("addedObject", []),
                created_by=doc.get("createdBy", ""),
                created_at=doc.get("createdAt", datetime.utcnow()).isoformat(),
                last_modified_by=doc.get("lastModifiedBy", ""),
                last_modified_at=doc.get("lastModifiedAt",
                                         datetime.utcnow()).isoformat(),
                estimated_time=total_estimated_time)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching training plan: {str(e)}")