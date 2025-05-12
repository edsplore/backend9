from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from infrastructure.database import Database
from api.schemas.requests import (CreateTrainingPlanRequest,
                                  UpdateTrainingPlanRequest,
                                  CloneTrainingPlanRequest, PaginationParams)
from api.schemas.responses import TrainingPlanData, PaginationMetadata
from fastapi import HTTPException

from utils.logger import Logger  # Ensure correct import path for your project

logger = Logger.get_logger(__name__)


class TrainingPlanService:

    def __init__(self):
        self.db = Database()
        logger.info("TrainingPlanService initialized.")

    async def training_plan_name_exists(self, name: str,
                                        workspace: str) -> bool:
        """Check if a training plan with the given name already exists in the workspace"""
        logger.info(
            f"Checking if training plan name '{name}' exists in workspace {workspace}"
        )
        try:
            # Query the database for training plan with the same name in the workspace
            count = await self.db.training_plans.count_documents({
                "name":
                name,
                "workspace":
                workspace
            })
            return count > 0
        except Exception as e:
            logger.error(
                f"Error checking training plan name existence: {str(e)}",
                exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error checking training plan name: {str(e)}")

    async def create_training_plan(self, request: CreateTrainingPlanRequest,
                                   workspace: str) -> Dict:
        """Create a new training plan"""
        logger.info(
            f"Received request to create a training plan in workspace {workspace}."
        )
        logger.debug(f"CreateTrainingPlanRequest data: {request.dict()}")
        try:
            # Check if a training plan with this name already exists in the workspace
            name_exists = await self.training_plan_name_exists(
                request.training_plan_name, workspace)
            if name_exists:
                logger.warning(
                    f"Training Plan with name '{request.training_plan_name}' already exists in workspace {workspace}"
                )
                # Return a specific error for duplicate names
                return {
                    "status": "error",
                    "message": "Training Plan with this name already exists",
                }

            # Validate added objects in the same workspace
            for obj in request.added_object:
                logger.debug(
                    f"Validating added object with ID {obj.id} and type {obj.type}"
                )
                if obj.type == "module":
                    module = await self.db.modules.find_one({
                        "_id":
                        ObjectId(obj.id),
                        "workspace":
                        workspace
                    })
                    if not module:
                        logger.warning(
                            f"Module with ID {obj.id} not found in workspace {workspace}."
                        )
                        raise HTTPException(
                            status_code=404,
                            detail=
                            f"Module with id {obj.id} not found in workspace {workspace}"
                        )
                elif obj.type == "simulation":
                    simulation = await self.db.simulations.find_one({
                        "_id":
                        ObjectId(obj.id),
                        "workspace":
                        workspace
                    })
                    if not simulation:
                        logger.warning(
                            f"Simulation with ID {obj.id} not found in workspace {workspace}."
                        )
                        raise HTTPException(
                            status_code=404,
                            detail=
                            f"Simulation with id {obj.id} not found in workspace {workspace}"
                        )
                else:
                    logger.warning(f"Invalid object type: {obj.type}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid object type: {obj.type}")

            training_plan_doc = {
                "name": request.training_plan_name,
                "tags": request.tags,
                "addedObject": [obj.dict() for obj in request.added_object],
                "createdBy": request.user_id,
                "createdAt": datetime.utcnow(),
                "lastModifiedBy": request.user_id,
                "lastModifiedAt": datetime.utcnow(),
                "workspace": workspace  # Add workspace field
            }

            logger.debug(
                f"Inserting training plan document: {training_plan_doc}")
            result = await self.db.training_plans.insert_one(training_plan_doc)
            logger.info(f"Training plan created with ID: {result.inserted_id}")

            return {"id": str(result.inserted_id), "status": "success"}
        except HTTPException as he:
            logger.error(f"HTTPException in create_training_plan: {he.detail}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error creating training plan: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error creating training plan: {str(e)}")

    async def clone_training_plan(self, request: CloneTrainingPlanRequest,
                                  workspace: str) -> Dict:
        """Clone an existing training plan"""
        logger.info(
            f"Received request to clone a training plan in workspace {workspace}."
        )
        logger.debug(f"CloneTrainingPlanRequest data: {request.dict()}")

        try:
            plan_id_object = ObjectId(request.training_plan_id)
            existing_plan = await self.db.training_plans.find_one({
                "_id":
                plan_id_object,
                "workspace":
                workspace
            })
            if not existing_plan:
                logger.warning(
                    f"Training plan with ID {request.training_plan_id} not found for cloning in workspace {workspace}."
                )
                raise HTTPException(
                    status_code=404,
                    detail=
                    f"Training plan with id {request.training_plan_id} not found in workspace {workspace}"
                )

            # Generate new name with (Copy) suffix
            base_name = existing_plan['name']
            new_name = f"Copy {base_name}"

            # Check if the name with (Copy) exists in the same workspace
            name_exists = await self.training_plan_name_exists(
                new_name, workspace)
            counter = 0

            # If name exists, append a number until we find a unique name
            while name_exists:
                counter += 1
                new_name = f"Copy {base_name} {counter}"
                name_exists = await self.training_plan_name_exists(
                    new_name, workspace)

            new_plan = existing_plan.copy()
            new_plan.pop("_id")
            new_plan["name"] = new_name
            new_plan["createdBy"] = request.user_id
            new_plan["createdAt"] = datetime.utcnow()
            new_plan["lastModifiedBy"] = request.user_id
            new_plan["lastModifiedAt"] = datetime.utcnow()
            new_plan["workspace"] = workspace  # Ensure workspace is set

            logger.debug(f"Cloned training plan document: {new_plan}")
            result = await self.db.training_plans.insert_one(new_plan)
            logger.info(
                f"Training plan cloned successfully. New ID: {result.inserted_id}"
            )

            return {"id": str(result.inserted_id), "status": "success"}
        except HTTPException as he:
            logger.error(f"HTTPException in clone_training_plan: {he.detail}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error cloning training plan: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error cloning training plan: {str(e)}")

    async def update_training_plan(self, training_plan_id: str,
                                   request: UpdateTrainingPlanRequest,
                                   workspace: str) -> TrainingPlanData:
        """Update an existing training plan"""
        logger.info(
            f"Received request to update training plan with ID: {training_plan_id} in workspace {workspace}"
        )
        logger.debug(f"UpdateTrainingPlanRequest data: {request.dict()}")
        try:
            training_plan_id_object = ObjectId(training_plan_id)
            existing_plan = await self.db.training_plans.find_one({
                "_id":
                training_plan_id_object,
                "workspace":
                workspace
            })
            if not existing_plan:
                logger.warning(
                    f"Training plan with ID {training_plan_id} not found in workspace {workspace}."
                )
                raise HTTPException(
                    status_code=404,
                    detail=
                    f"Training plan with id {training_plan_id} not found in workspace {workspace}"
                )

            update_doc = {}

            if request.training_plan_name is not None:
                update_doc["name"] = request.training_plan_name
            if request.tags is not None:
                update_doc["tags"] = request.tags
            if request.added_object is not None:
                for obj in request.added_object:
                    logger.debug(
                        f"Validating added object with ID {obj.id} and type {obj.type}"
                    )
                    if obj.type == "module":
                        module = await self.db.modules.find_one({
                            "_id":
                            ObjectId(obj.id),
                            "workspace":
                            workspace
                        })
                        if not module:
                            logger.warning(
                                f"Module with ID {obj.id} not found during update in workspace {workspace}."
                            )
                            raise HTTPException(
                                status_code=404,
                                detail=
                                f"Module with id {obj.id} not found in workspace {workspace}"
                            )
                    elif obj.type == "simulation":
                        simulation = await self.db.simulations.find_one({
                            "_id":
                            ObjectId(obj.id),
                            "workspace":
                            workspace
                        })
                        if not simulation:
                            logger.warning(
                                f"Simulation with ID {obj.id} not found during update in workspace {workspace}."
                            )
                            raise HTTPException(
                                status_code=404,
                                detail=
                                f"Simulation with id {obj.id} not found in workspace {workspace}"
                            )
                    else:
                        logger.warning(
                            f"Invalid object type: {obj.type} during update.")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid object type: {obj.type}")

                update_doc["addedObject"] = [
                    obj.dict() for obj in request.added_object
                ]

            update_doc["lastModifiedBy"] = request.user_id
            update_doc["lastModifiedAt"] = datetime.utcnow()

            logger.debug(
                f"Update document for training plan {training_plan_id}: {update_doc}"
            )
            result = await self.db.training_plans.update_one(
                {"_id": training_plan_id_object}, {"$set": update_doc})

            if result.modified_count == 0:
                logger.error(
                    "Failed to update training plan; no documents modified.")
                raise HTTPException(status_code=500,
                                    detail="Failed to update training plan")

            updated_plan = await self.get_training_plan_by_id(
                training_plan_id, workspace)
            logger.info(
                f"Training plan {training_plan_id} updated successfully.")
            return updated_plan
        except HTTPException as he:
            logger.error(f"HTTPException in update_training_plan: {he.detail}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error updating training plan: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error updating training plan: {str(e)}")

    async def fetch_training_plans(
            self,
            user_id: str,
            workspace: str,
            pagination: Optional[PaginationParams] = None) -> Dict[str, any]:
        """Fetch all training plans with pagination and filtering

        Returns a dictionary with:
        - training_plans: List of TrainingPlanData objects
        - total_count: Total number of training plans matching the query
        """
        logger.info(
            f"Fetching training plans for user_id={user_id} in workspace={workspace} with pagination"
        )
        try:
            # Build query filter based on pagination parameters
            query = {"workspace": workspace}  # Add workspace filter

            if pagination:
                logger.debug(f"Applying pagination parameters: {pagination}")

                # Apply search filter if provided
                if pagination.search:
                    search_regex = {
                        "$regex": pagination.search,
                        "$options": "i"
                    }
                    query["$or"] = [{
                        "name": search_regex
                    }, {
                        "tags": search_regex
                    }]

                # Apply tag filter if provided
                if pagination.tags and len(pagination.tags) > 0:
                    query["tags"] = {"$in": pagination.tags}

                # Apply created by filter if provided
                if pagination.createdBy:
                    query["createdBy"] = pagination.createdBy

                # Apply modified by filter if provided
                if pagination.modifiedBy:
                    query["lastModifiedBy"] = pagination.modifiedBy

                # Apply created date range filters if provided
                date_filter = {}
                if pagination.createdFrom:
                    date_filter["$gte"] = pagination.createdFrom
                if pagination.createdTo:
                    date_filter["$lte"] = pagination.createdTo
                if date_filter:
                    query["createdAt"] = date_filter

                # Apply modified date range filters if provided
                modified_date_filter = {}
                if pagination.modifiedFrom:
                    modified_date_filter["$gte"] = pagination.modifiedFrom
                if pagination.modifiedTo:
                    modified_date_filter["$lte"] = pagination.modifiedTo
                if modified_date_filter:
                    query["lastModifiedAt"] = modified_date_filter

            # Determine sort options
            sort_options = []
            if pagination and pagination.sortBy:
                # Convert camelCase sort field to database field name if needed
                sort_field_mapping = {
                    "name": "name",
                    "lastModifiedAt": "lastModifiedAt",
                    "createdAt": "createdAt",
                    "modifiedBy": "lastModifiedBy",
                    "createdBy": "createdBy",
                    # Add other mappings as needed
                }
                db_field = sort_field_mapping.get(pagination.sortBy,
                                                  pagination.sortBy)
                sort_direction = 1 if pagination.sortDir == "asc" else -1
                sort_options.append((db_field, sort_direction))
            else:
                # Default sort by lastModifiedAt
                sort_options.append(("lastModifiedAt", -1))

            # Get total count for pagination metadata
            total_count = await self.db.training_plans.count_documents(query)

            # Calculate pagination
            skip = 0
            limit = 50  # Default limit

            if pagination:
                limit = pagination.pagesize
                skip = (pagination.page - 1) * limit

            logger.debug(f"Query filter: {query}")
            logger.debug(f"Sort options: {sort_options}")
            logger.debug(f"Skip: {skip}, Limit: {limit}")

            # Execute the query with pagination
            cursor = self.db.training_plans.find(query).sort(
                sort_options).skip(skip).limit(limit)
            training_plans = []

            async for doc in cursor:
                total_estimated_time = 0
                for obj in doc.get("addedObject", []):
                    try:
                        if obj["type"] == "module":
                            module = await self.db.modules.find_one({
                                "_id":
                                ObjectId(obj["id"]),
                                "workspace":
                                workspace  # Filter modules by workspace
                            })
                            if module:
                                for sim_id in module.get("simulationIds", []):
                                    sim = await self.db.simulations.find_one({
                                        "_id":
                                        ObjectId(sim_id),
                                        "workspace":
                                        workspace  # Filter simulations by workspace
                                    })
                                    if sim and "estimatedTimeToAttemptInMins" in sim:
                                        total_estimated_time += sim[
                                            "estimatedTimeToAttemptInMins"]
                        elif obj["type"] == "simulation":
                            sim = await self.db.simulations.find_one({
                                "_id":
                                ObjectId(obj["id"]),
                                "workspace":
                                workspace  # Filter simulations by workspace
                            })
                            if sim and "estimatedTimeToAttemptInMins" in sim:
                                total_estimated_time += sim[
                                    "estimatedTimeToAttemptInMins"]
                    except Exception as ex:
                        logger.warning(
                            f"Skipping invalid object {obj.get('id', 'unknown')} due to: {ex}"
                        )
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

            logger.info(
                f"Total training plans fetched: {len(training_plans)}, Total count: {total_count}"
            )
            return {
                "training_plans": training_plans,
                "total_count": total_count
            }
        except Exception as e:
            logger.error(f"Error fetching training plans: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching training plans: {str(e)}")

    async def get_training_plan_by_id(
            self, training_plan_id: str,
            workspace: str) -> Optional[TrainingPlanData]:
        """Fetch a single training plan by ID"""
        logger.info(
            f"Fetching training plan by ID: {training_plan_id} in workspace {workspace}"
        )
        try:
            training_plan_id_object = ObjectId(training_plan_id)
            doc = await self.db.training_plans.find_one({
                "_id": training_plan_id_object,
                "workspace": workspace
            })
            if not doc:
                logger.warning(
                    f"No training plan found for ID {training_plan_id} in workspace {workspace}"
                )
                return None

            total_estimated_time = 0
            enriched_added_objects = []

            for obj in doc.get("addedObject", []):
                try:
                    if obj["type"] == "module":
                        module = await self.db.modules.find_one({
                            "_id":
                            ObjectId(obj["id"]),
                            "workspace":
                            workspace  # Filter modules by workspace
                        })
                        if module:
                            module_simulations = []
                            for sim_id in module.get("simulationIds", []):
                                sim = await self.db.simulations.find_one({
                                    "_id":
                                    ObjectId(sim_id),
                                    "workspace":
                                    workspace  # Filter simulations by workspace
                                })
                                if sim and "estimatedTimeToAttemptInMins" in sim:
                                    total_estimated_time += sim[
                                        "estimatedTimeToAttemptInMins"]
                                    module_simulations.append({
                                        "id":
                                        str(sim["_id"]),
                                        "name":
                                        sim.get("name", ""),
                                        "estimatedTime":
                                        sim.get("estimatedTimeToAttemptInMins",
                                                0)
                                    })

                            enriched_added_objects.append({
                                "type":
                                "module",
                                "id":
                                str(module["_id"]),
                                "name":
                                module.get("name", ""),
                                "simulations":
                                module_simulations
                            })

                    elif obj["type"] == "simulation":
                        sim = await self.db.simulations.find_one({
                            "_id":
                            ObjectId(obj["id"]),
                            "workspace":
                            workspace  # Filter simulations by workspace
                        })
                        if sim and "estimatedTimeToAttemptInMins" in sim:
                            total_estimated_time += sim[
                                "estimatedTimeToAttemptInMins"]
                            enriched_added_objects.append({
                                "type":
                                "simulation",
                                "id":
                                str(sim["_id"]),
                                "name":
                                sim.get("name", ""),
                                "estimatedTime":
                                sim.get("estimatedTimeToAttemptInMins", 0)
                            })

                except Exception as ex:
                    logger.warning(
                        f"Skipping invalid object {obj.get('id', 'unknown')} due to: {ex}"
                    )
                    continue

            training_plan_data = TrainingPlanData(
                id=str(doc["_id"]),
                name=doc.get("name", ""),
                tags=doc.get("tags", []),
                added_object=enriched_added_objects,
                created_by=doc.get("createdBy", ""),
                created_at=doc.get("createdAt", datetime.utcnow()).isoformat(),
                last_modified_by=doc.get("lastModifiedBy", ""),
                last_modified_at=doc.get("lastModifiedAt",
                                         datetime.utcnow()).isoformat(),
                estimated_time=total_estimated_time)
            logger.info(
                f"Training plan {training_plan_id} fetched successfully.")
            return training_plan_data
        except Exception as e:
            logger.error(f"Error fetching training plan by ID: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching training plan: {str(e)}")
