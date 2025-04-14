from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from infrastructure.database import Database
from api.schemas.requests import CreateTrainingPlanRequest, UpdateTrainingPlanRequest, CloneTrainingPlanRequest
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

    async def clone_training_plan(self, request: CloneTrainingPlanRequest) -> Dict:
        """Clone an existing training plan"""
        try:
            # Get existing training plan
            plan_id_object = ObjectId(request.training_plan_id)
            existing_plan = await self.db.training_plans.find_one({"_id": plan_id_object})

            if not existing_plan:
                raise HTTPException(
                    status_code=404,
                    detail=f"Training plan with id {request.training_plan_id} not found"
                )

            # Create new training plan document with data from existing one
            new_plan = existing_plan.copy()

            # Remove _id so a new one will be generated
            new_plan.pop("_id")

            # Update metadata
            new_plan["name"] = f"{existing_plan['name']} (Copy)"
            new_plan["createdBy"] = request.user_id
            new_plan["createdAt"] = datetime.utcnow()
            new_plan["lastModifiedBy"] = request.user_id
            new_plan["lastModifiedAt"] = datetime.utcnow()

            # Insert new training plan
            result = await self.db.training_plans.insert_one(new_plan)

            return {"id": str(result.inserted_id), "status": "success"}

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error cloning training plan: {str(e)}"
            )

    async def update_training_plan(self, training_plan_id: str, request: UpdateTrainingPlanRequest) -> TrainingPlanData:
        """Update an existing training plan"""
        try:
            # Convert string ID to ObjectId
            training_plan_id_object = ObjectId(training_plan_id)

            # Get existing training plan
            existing_plan = await self.db.training_plans.find_one({"_id": training_plan_id_object})
            if not existing_plan:
                raise HTTPException(
                    status_code=404,
                    detail=f"Training plan with id {training_plan_id} not found")

            # Build update document
            update_doc = {}

            if request.training_plan_name is not None:
                update_doc["name"] = request.training_plan_name

            if request.tags is not None:
                update_doc["tags"] = request.tags

            if request.added_object is not None:
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

                update_doc["addedObject"] = [obj.dict() for obj in request.added_object]

            # Add metadata
            update_doc["lastModifiedBy"] = request.user_id
            update_doc["lastModifiedAt"] = datetime.utcnow()

            # Update database
            result = await self.db.training_plans.update_one(
                {"_id": training_plan_id_object}, {"$set": update_doc})

            if result.modified_count == 0:
                raise HTTPException(status_code=500,
                                    detail="Failed to update training plan")

            # Get updated training plan
            updated_plan = await self.get_training_plan_by_id(training_plan_id)
            return updated_plan

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error updating training plan: {str(e)}")

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