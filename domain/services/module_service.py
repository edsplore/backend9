from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from infrastructure.database import Database
from api.schemas.requests import CreateModuleRequest, UpdateModuleRequest, CloneModuleRequest
from api.schemas.responses import ModuleData
from fastapi import HTTPException


class ModuleService:

    def __init__(self):
        self.db = Database()

    async def create_module(self, request: CreateModuleRequest) -> Dict:
        """Create a new module"""
        try:
            # Validate simulation IDs
            for sim_id in request.simulations:
                sim = await self.db.simulations.find_one(
                    {"_id": ObjectId(sim_id)})
                if not sim:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Simulation with id {sim_id} not found")

            # Create module document
            module_doc = {
                "name": request.module_name,
                "tags": request.tags,
                "simulationIds": request.simulations,
                "createdBy": request.user_id,
                "createdAt": datetime.utcnow(),
                "lastModifiedBy": request.user_id,
                "lastModifiedAt": datetime.utcnow()
            }

            # Insert into database
            result = await self.db.modules.insert_one(module_doc)

            return {"id": str(result.inserted_id), "status": "success"}

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error creating module: {str(e)}")

    async def clone_module(self, request: CloneModuleRequest) -> Dict:
        """Clone an existing module"""
        try:
            # Get existing module
            module_id_object = ObjectId(request.module_id)
            existing_module = await self.db.modules.find_one({"_id": module_id_object})

            if not existing_module:
                raise HTTPException(
                    status_code=404,
                    detail=f"Module with id {request.module_id} not found"
                )

            # Create new module document with data from existing one
            new_module = existing_module.copy()

            # Remove _id so a new one will be generated
            new_module.pop("_id")

            # Update metadata
            new_module["name"] = f"{existing_module['name']} (Copy)"
            new_module["createdBy"] = request.user_id
            new_module["createdAt"] = datetime.utcnow()
            new_module["lastModifiedBy"] = request.user_id
            new_module["lastModifiedAt"] = datetime.utcnow()

            # Insert new module
            result = await self.db.modules.insert_one(new_module)

            return {"id": str(result.inserted_id), "status": "success"}

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error cloning module: {str(e)}"
            )

    async def update_module(self, module_id: str, request: UpdateModuleRequest) -> ModuleData:
        """Update an existing module"""
        try:
            # Convert string ID to ObjectId
            module_id_object = ObjectId(module_id)

            # Get existing module
            existing_module = await self.db.modules.find_one({"_id": module_id_object})
            if not existing_module:
                raise HTTPException(
                    status_code=404,
                    detail=f"Module with id {module_id} not found")

            # Build update document
            update_doc = {}

            if request.module_name is not None:
                update_doc["name"] = request.module_name

            if request.tags is not None:
                update_doc["tags"] = request.tags

            if request.simulations is not None:
                # Validate simulation IDs
                for sim_id in request.simulations:
                    sim = await self.db.simulations.find_one(
                        {"_id": ObjectId(sim_id)})
                    if not sim:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Simulation with id {sim_id} not found")
                update_doc["simulationIds"] = request.simulations

            # Add metadata
            update_doc["lastModifiedBy"] = request.user_id
            update_doc["lastModifiedAt"] = datetime.utcnow()

            # Update database
            result = await self.db.modules.update_one(
                {"_id": module_id_object}, {"$set": update_doc})

            if result.modified_count == 0:
                raise HTTPException(status_code=500,
                                    detail="Failed to update module")

            # Get updated module
            updated_module = await self.get_module_by_id(module_id)
            return updated_module

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error updating module: {str(e)}")

    async def fetch_modules(self, user_id: str) -> List[ModuleData]:
        """Fetch all modules"""
        try:
            cursor = self.db.modules.find({})
            modules = []

            async for doc in cursor:
                # Calculate total estimated time from simulations
                total_estimated_time = 0
                for sim_id in doc.get("simulationIds", []):
                    try:
                        sim = await self.db.simulations.find_one(
                            {"_id": ObjectId(sim_id)})
                        if sim and "estimatedTimeToAttemptInMins" in sim:
                            total_estimated_time += sim[
                                "estimatedTimeToAttemptInMins"]
                    except Exception:
                        # Skip if simulation not found or invalid ID
                        continue

                module = ModuleData(
                    id=str(doc["_id"]),
                    name=doc.get("name", ""),
                    tags=doc.get("tags", []),
                    simulations_id=doc.get("simulationIds", []),
                    created_by=doc.get("createdBy", ""),
                    created_at=doc.get("createdAt",
                                       datetime.utcnow()).isoformat(),
                    last_modified_by=doc.get("lastModifiedBy", ""),
                    last_modified_at=doc.get("lastModifiedAt",
                                             datetime.utcnow()).isoformat(),
                    estimated_time=total_estimated_time)
                modules.append(module)

            return modules

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error fetching modules: {str(e)}")

    async def get_module_by_id(self, module_id: str) -> Optional[ModuleData]:
        """Fetch a single module by ID"""
        try:
            # Convert string ID to ObjectId
            module_id_object = ObjectId(module_id)

            # Find the module
            doc = await self.db.modules.find_one({"_id": module_id_object})

            if not doc:
                return None

            # Calculate total estimated time from simulations
            total_estimated_time = 0
            for sim_id in doc.get("simulationIds", []):
                try:
                    sim = await self.db.simulations.find_one(
                        {"_id": ObjectId(sim_id)})
                    if sim and "estimatedTimeToAttemptInMins" in sim:
                        total_estimated_time += sim["estimatedTimeToAttemptInMins"]
                except Exception:
                    # Skip if simulation not found or invalid ID
                    continue

            return ModuleData(
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

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching module: {str(e)}")