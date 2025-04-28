from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from infrastructure.database import Database
from api.schemas.requests import (CreateModuleRequest, UpdateModuleRequest,
                                  CloneModuleRequest, PaginationParams)
from api.schemas.responses import ModuleData, PaginationMetadata
from fastapi import HTTPException

from utils.logger import Logger  # Make sure the import path is correct for your project

logger = Logger.get_logger(__name__)


class ModuleService:

    def __init__(self):
        self.db = Database()
        logger.info("ModuleService initialized.")

    async def create_module(self, request: CreateModuleRequest) -> Dict:
        """Create a new module"""
        logger.info("Received request to create a new module.")
        logger.debug(f"CreateModuleRequest data: {request.dict()}")
        try:
            # Validate simulation IDs
            for sim_id in request.simulations:
                logger.debug(f"Validating simulation ID: {sim_id}")
                sim = await self.db.simulations.find_one(
                    {"_id": ObjectId(sim_id)})
                if not sim:
                    logger.warning(f"Simulation with id {sim_id} not found.")
                    raise HTTPException(
                        status_code=404,
                        detail=f"Simulation with id {sim_id} not found")

            module_doc = {
                "name": request.module_name,
                "tags": request.tags,
                "simulationIds": request.simulations,
                "createdBy": request.user_id,
                "createdAt": datetime.utcnow(),
                "lastModifiedBy": request.user_id,
                "lastModifiedAt": datetime.utcnow()
            }

            logger.debug(f"Module document to be inserted: {module_doc}")
            result = await self.db.modules.insert_one(module_doc)
            module_id = str(result.inserted_id)
            logger.info(f"Module created successfully. ID: {module_id}")

            return {"id": module_id, "status": "success"}
        except HTTPException as he:
            logger.error(f"HTTPException in create_module: {he.detail}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error creating module: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error creating module: {str(e)}")

    async def clone_module(self, request: CloneModuleRequest) -> Dict:
        """Clone an existing module"""
        logger.info("Received request to clone a module.")
        logger.debug(f"CloneModuleRequest data: {request.dict()}")
        try:
            module_id_object = ObjectId(request.module_id)
            existing_module = await self.db.modules.find_one(
                {"_id": module_id_object})
            if not existing_module:
                logger.warning(
                    f"Module with id {request.module_id} not found.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Module with id {request.module_id} not found")

            new_module = existing_module.copy()
            new_module.pop("_id")

            new_module["name"] = f"{existing_module['name']} (Copy)"
            new_module["createdBy"] = request.user_id
            new_module["createdAt"] = datetime.utcnow()
            new_module["lastModifiedBy"] = request.user_id
            new_module["lastModifiedAt"] = datetime.utcnow()

            logger.debug(f"Cloned module document: {new_module}")
            result = await self.db.modules.insert_one(new_module)
            cloned_module_id = str(result.inserted_id)
            logger.info(
                f"Module cloned successfully. New ID: {cloned_module_id}")

            return {"id": cloned_module_id, "status": "success"}
        except HTTPException as he:
            logger.error(f"HTTPException in clone_module: {he.detail}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error cloning module: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error cloning module: {str(e)}")

    async def update_module(self, module_id: str,
                            request: UpdateModuleRequest) -> ModuleData:
        """Update an existing module"""
        logger.info(f"Received request to update module with ID: {module_id}")
        logger.debug(f"UpdateModuleRequest data: {request.dict()}")
        try:
            module_id_object = ObjectId(module_id)
            existing_module = await self.db.modules.find_one(
                {"_id": module_id_object})
            if not existing_module:
                logger.warning(f"Module with id {module_id} not found.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Module with id {module_id} not found")

            update_doc = {}
            if request.module_name is not None:
                update_doc["name"] = request.module_name
            if request.tags is not None:
                update_doc["tags"] = request.tags
            if request.simulations is not None:
                for sim_id in request.simulations:
                    logger.debug(
                        f"Validating simulation ID in update: {sim_id}")
                    sim = await self.db.simulations.find_one(
                        {"_id": ObjectId(sim_id)})
                    if not sim:
                        logger.warning(
                            f"Simulation with id {sim_id} not found during update."
                        )
                        raise HTTPException(
                            status_code=404,
                            detail=f"Simulation with id {sim_id} not found")
                update_doc["simulationIds"] = request.simulations

            update_doc["lastModifiedBy"] = request.user_id
            update_doc["lastModifiedAt"] = datetime.utcnow()

            result = await self.db.modules.update_one(
                {"_id": module_id_object}, {"$set": update_doc})

            if result.modified_count == 0:
                logger.error("Failed to update module. No documents modified.")
                raise HTTPException(status_code=500,
                                    detail="Failed to update module")

            updated_module = await self.get_module_by_id(module_id)
            logger.info(f"Module {module_id} updated successfully.")
            return updated_module
        except HTTPException as he:
            logger.error(f"HTTPException in update_module: {he.detail}",
                         exc_info=True)
            raise he
        except Exception as e:
            logger.error(f"Error updating module: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error updating module: {str(e)}")

    async def fetch_modules(self, user_id: str, pagination: Optional[PaginationParams] = None) -> Dict[str, any]:
        """Fetch all modules with pagination and filtering

        Returns a dictionary with:
        - modules: List of ModuleData objects
        - total_count: Total number of modules matching the query
        """
        logger.info(f"Fetching modules for user_id={user_id} with pagination")
        try:
            # Build query filter based on pagination parameters
            query = {}

            if pagination:
                logger.debug(f"Applying pagination parameters: {pagination}")

                # Apply search filter if provided
                if pagination.search:
                    search_regex = {"$regex": pagination.search, "$options": "i"}
                    query["$or"] = [
                        {"name": search_regex},
                        {"tags": search_regex}
                    ]

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
                db_field = sort_field_mapping.get(pagination.sortBy, pagination.sortBy)
                sort_direction = 1 if pagination.sortDir == "asc" else -1
                sort_options.append((db_field, sort_direction))
            else:
                # Default sort by lastModifiedAt
                sort_options.append(("lastModifiedAt", -1))

            # Get total count for pagination metadata
            total_count = await self.db.modules.count_documents(query)

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
            cursor = self.db.modules.find(query).sort(sort_options).skip(skip).limit(limit)
            modules = []

            async for doc in cursor:
                total_estimated_time = 0
                for sim_id in doc.get("simulationIds", []):
                    try:
                        sim = await self.db.simulations.find_one({"_id": ObjectId(sim_id)})
                        if sim and "estimatedTimeToAttemptInMins" in sim:
                            total_estimated_time += sim["estimatedTimeToAttemptInMins"]
                    except Exception as ex:
                        logger.warning(f"Skipping invalid simulation {sim_id}: {ex}")
                        continue

                module_data = ModuleData(
                    id=str(doc["_id"]),
                    name=doc.get("name", ""),
                    tags=doc.get("tags", []),
                    simulations_id=doc.get("simulationIds", []),
                    created_by=doc.get("createdBy", ""),
                    created_at=doc.get("createdAt", datetime.utcnow()).isoformat(),
                    last_modified_by=doc.get("lastModifiedBy", ""),
                    last_modified_at=doc.get("lastModifiedAt", datetime.utcnow()).isoformat(),
                    estimated_time=total_estimated_time
                )
                modules.append(module_data)

            logger.info(f"Total modules fetched: {len(modules)}, Total count: {total_count}")
            return {
                "modules": modules,
                "total_count": total_count
            }
        except Exception as e:
            logger.error(f"Error fetching modules: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching modules: {str(e)}"
            )

    async def get_module_by_id(self, module_id: str) -> Optional[ModuleData]:
        """Fetch a single module by ID"""
        logger.info(f"Fetching module by ID: {module_id}")
        try:
            module_id_object = ObjectId(module_id)
            doc = await self.db.modules.find_one({"_id": module_id_object})
            if not doc:
                logger.warning(f"No module found for ID: {module_id}")
                return None

            total_estimated_time = 0
            for sim_id in doc.get("simulationIds", []):
                try:
                    sim = await self.db.simulations.find_one(
                        {"_id": ObjectId(sim_id)})
                    if sim and "estimatedTimeToAttemptInMins" in sim:
                        total_estimated_time += sim[
                            "estimatedTimeToAttemptInMins"]
                except Exception as ex:
                    logger.warning(
                        f"Skipping invalid simulation {sim_id}: {ex}")
                    continue

            module_data = ModuleData(
                id=str(doc["_id"]),
                name=doc.get("name", ""),
                tags=doc.get("tags", []),
                simulations_id=doc.get("simulationIds", []),
                created_by=doc.get("createdBy", ""),
                created_at=doc.get("createdAt", datetime.utcnow()).isoformat(),
                last_modified_by=doc.get("lastModifiedBy", ""),
                last_modified_at=doc.get("lastModifiedAt",
                                         datetime.utcnow()).isoformat(),
                estimated_time=total_estimated_time)
            logger.info(f"Module {module_id} fetched successfully.")
            return module_data
        except Exception as e:
            logger.error(f"Error fetching module: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error fetching module: {str(e)}")
