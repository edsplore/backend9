from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from infrastructure.database import Database
from api.schemas.requests import CreateTrainingPlanRequest, UpdateTrainingPlanRequest, CloneTrainingPlanRequest
from api.schemas.responses import TrainingPlanData
from fastapi import HTTPException

from utils.logger import Logger  # Ensure correct import path for your project
logger = Logger.get_logger(__name__)


class TrainingPlanService:

    def __init__(self):
        self.db = Database()
        logger.info("TrainingPlanService initialized.")

    async def create_training_plan(self, request: CreateTrainingPlanRequest) -> Dict:
        """Create a new training plan"""
        logger.info("Received request to create a training plan.")
        logger.debug(f"CreateTrainingPlanRequest data: {request.dict()}")
        try:
            # Validate added objects
            for obj in request.added_object:
                logger.debug(f"Validating added object with ID {obj.id} and type {obj.type}")
                if obj.type == "module":
                    module = await self.db.modules.find_one({"_id": ObjectId(obj.id)})
                    if not module:
                        logger.warning(f"Module with ID {obj.id} not found.")
                        raise HTTPException(
                            status_code=404,
                            detail=f"Module with id {obj.id} not found"
                        )
                elif obj.type == "simulation":
                    simulation = await self.db.simulations.find_one({"_id": ObjectId(obj.id)})
                    if not simulation:
                        logger.warning(f"Simulation with ID {obj.id} not found.")
                        raise HTTPException(
                            status_code=404,
                            detail=f"Simulation with id {obj.id} not found"
                        )
                else:
                    logger.warning(f"Invalid object type: {obj.type}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid object type: {obj.type}"
                    )

            training_plan_doc = {
                "name": request.training_plan_name,
                "tags": request.tags,
                "addedObject": [obj.dict() for obj in request.added_object],
                "createdBy": request.user_id,
                "createdAt": datetime.utcnow(),
                "lastModifiedBy": request.user_id,
                "lastModifiedAt": datetime.utcnow()
            }

            logger.debug(f"Inserting training plan document: {training_plan_doc}")
            result = await self.db.training_plans.insert_one(training_plan_doc)
            logger.info(f"Training plan created with ID: {result.inserted_id}")

            return {"id": str(result.inserted_id), "status": "success"}
        except HTTPException as he:
            logger.error(f"HTTPException in create_training_plan: {he.detail}", exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error creating training plan: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error creating training plan: {str(e)}"
            )

    async def clone_training_plan(self, request: CloneTrainingPlanRequest) -> Dict:
        """Clone an existing training plan"""
        logger.info("Received request to clone a training plan.")
        logger.debug(f"CloneTrainingPlanRequest data: {request.dict()}")
        try:
            plan_id_object = ObjectId(request.training_plan_id)
            existing_plan = await self.db.training_plans.find_one({"_id": plan_id_object})
            if not existing_plan:
                logger.warning(f"Training plan with ID {request.training_plan_id} not found for cloning.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Training plan with id {request.training_plan_id} not found"
                )

            new_plan = existing_plan.copy()
            new_plan.pop("_id")
            new_plan["name"] = f"{existing_plan['name']} (Copy)"
            new_plan["createdBy"] = request.user_id
            new_plan["createdAt"] = datetime.utcnow()
            new_plan["lastModifiedBy"] = request.user_id
            new_plan["lastModifiedAt"] = datetime.utcnow()

            logger.debug(f"Cloned training plan document: {new_plan}")
            result = await self.db.training_plans.insert_one(new_plan)
            logger.info(f"Training plan cloned successfully. New ID: {result.inserted_id}")

            return {"id": str(result.inserted_id), "status": "success"}
        except HTTPException as he:
            logger.error(f"HTTPException in clone_training_plan: {he.detail}", exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error cloning training plan: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error cloning training plan: {str(e)}"
            )

    async def update_training_plan(self, training_plan_id: str, request: UpdateTrainingPlanRequest) -> TrainingPlanData:
        """Update an existing training plan"""
        logger.info(f"Received request to update training plan with ID: {training_plan_id}")
        logger.debug(f"UpdateTrainingPlanRequest data: {request.dict()}")
        try:
            training_plan_id_object = ObjectId(training_plan_id)
            existing_plan = await self.db.training_plans.find_one({"_id": training_plan_id_object})
            if not existing_plan:
                logger.warning(f"Training plan with ID {training_plan_id} not found.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Training plan with id {training_plan_id} not found"
                )

            update_doc = {}

            if request.training_plan_name is not None:
                update_doc["name"] = request.training_plan_name
            if request.tags is not None:
                update_doc["tags"] = request.tags
            if request.added_object is not None:
                for obj in request.added_object:
                    logger.debug(f"Validating added object with ID {obj.id} and type {obj.type}")
                    if obj.type == "module":
                        module = await self.db.modules.find_one({"_id": ObjectId(obj.id)})
                        if not module:
                            logger.warning(f"Module with ID {obj.id} not found during update.")
                            raise HTTPException(
                                status_code=404,
                                detail=f"Module with id {obj.id} not found"
                            )
                    elif obj.type == "simulation":
                        simulation = await self.db.simulations.find_one({"_id": ObjectId(obj.id)})
                        if not simulation:
                            logger.warning(f"Simulation with ID {obj.id} not found during update.")
                            raise HTTPException(
                                status_code=404,
                                detail=f"Simulation with id {obj.id} not found"
                            )
                    else:
                        logger.warning(f"Invalid object type: {obj.type} during update.")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid object type: {obj.type}"
                        )

                update_doc["addedObject"] = [obj.dict() for obj in request.added_object]

            update_doc["lastModifiedBy"] = request.user_id
            update_doc["lastModifiedAt"] = datetime.utcnow()

            logger.debug(f"Update document for training plan {training_plan_id}: {update_doc}")
            result = await self.db.training_plans.update_one(
                {"_id": training_plan_id_object},
                {"$set": update_doc}
            )

            if result.modified_count == 0:
                logger.error("Failed to update training plan; no documents modified.")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update training plan"
                )

            updated_plan = await self.get_training_plan_by_id(training_plan_id)
            logger.info(f"Training plan {training_plan_id} updated successfully.")
            return updated_plan
        except HTTPException as he:
            logger.error(f"HTTPException in update_training_plan: {he.detail}", exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error updating training plan: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error updating training plan: {str(e)}"
            )

    async def fetch_training_plans(self, user_id: str) -> List[TrainingPlanData]:
        """Fetch all training plans"""
        logger.info(f"Fetching all training plans for user_id={user_id}.")
        try:
            cursor = self.db.training_plans.find({})
            training_plans = []

            async for doc in cursor:
                total_estimated_time = 0
                for obj in doc.get("addedObject", []):
                    try:
                        if obj["type"] == "module":
                            module = await self.db.modules.find_one({"_id": ObjectId(obj["id"])})
                            if module:
                                for sim_id in module.get("simulationIds", []):
                                    sim = await self.db.simulations.find_one({"_id": ObjectId(sim_id)})
                                    if sim and "estimatedTimeToAttemptInMins" in sim:
                                        total_estimated_time += sim["estimatedTimeToAttemptInMins"]
                        elif obj["type"] == "simulation":
                            sim = await self.db.simulations.find_one({"_id": ObjectId(obj["id"])})
                            if sim and "estimatedTimeToAttemptInMins" in sim:
                                total_estimated_time += sim["estimatedTimeToAttemptInMins"]
                    except Exception as ex:
                        logger.warning(f"Skipping invalid object {obj.get('id', 'unknown')} due to: {ex}")
                        continue

                training_plan = TrainingPlanData(
                    id=str(doc["_id"]),
                    name=doc.get("name", ""),
                    tags=doc.get("tags", []),
                    added_object=doc.get("addedObject", []),
                    created_by=doc.get("createdBy", ""),
                    created_at=doc.get("createdAt", datetime.utcnow()).isoformat(),
                    last_modified_by=doc.get("lastModifiedBy", ""),
                    last_modified_at=doc.get("lastModifiedAt", datetime.utcnow()).isoformat(),
                    estimated_time=total_estimated_time
                )
                training_plans.append(training_plan)

            logger.info(f"Total training plans fetched: {len(training_plans)}")
            return training_plans
        except Exception as e:
            logger.error(f"Error fetching training plans: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching training plans: {str(e)}"
            )

    async def get_training_plan_by_id(self, training_plan_id: str) -> Optional[TrainingPlanData]:
        """Fetch a single training plan by ID"""
        logger.info(f"Fetching training plan by ID: {training_plan_id}")
        try:
            training_plan_id_object = ObjectId(training_plan_id)
            doc = await self.db.training_plans.find_one({"_id": training_plan_id_object})
            if not doc:
                logger.warning(f"No training plan found for ID {training_plan_id}")
                return None

            total_estimated_time = 0
            for obj in doc.get("addedObject", []):
                try:
                    if obj["type"] == "module":
                        module = await self.db.modules.find_one({"_id": ObjectId(obj["id"])})
                        if module:
                            for sim_id in module.get("simulationIds", []):
                                sim = await self.db.simulations.find_one({"_id": ObjectId(sim_id)})
                                if sim and "estimatedTimeToAttemptInMins" in sim:
                                    total_estimated_time += sim["estimatedTimeToAttemptInMins"]
                    elif obj["type"] == "simulation":
                        sim = await self.db.simulations.find_one({"_id": ObjectId(obj["id"])})
                        if sim and "estimatedTimeToAttemptInMins" in sim:
                            total_estimated_time += sim["estimatedTimeToAttemptInMins"]
                except Exception as ex:
                    logger.warning(f"Skipping invalid object {obj.get('id', 'unknown')} due to: {ex}")
                    continue

            training_plan_data = TrainingPlanData(
                id=str(doc["_id"]),
                name=doc.get("name", ""),
                tags=doc.get("tags", []),
                added_object=doc.get("addedObject", []),
                created_by=doc.get("createdBy", ""),
                created_at=doc.get("createdAt", datetime.utcnow()).isoformat(),
                last_modified_by=doc.get("lastModifiedBy", ""),
                last_modified_at=doc.get("lastModifiedAt", datetime.utcnow()).isoformat(),
                estimated_time=total_estimated_time
            )
            logger.info(f"Training plan {training_plan_id} fetched successfully.")
            return training_plan_data
        except Exception as e:
            logger.error(f"Error fetching training plan by ID: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching training plan: {str(e)}"
            )
