from typing import Dict, List
from datetime import datetime
from bson import ObjectId
from infrastructure.database import Database
from api.schemas.requests import CreateModuleRequest
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
