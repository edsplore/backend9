from typing import Dict, List
from bson import ObjectId
from infrastructure.database import Database
from api.schemas.responses import ListItemData
from fastapi import HTTPException


class ListService:

    def __init__(self):
        self.db = Database()

    async def list_training_plans(self, user_id: str) -> List[ListItemData]:
        """List all training plans with summary information"""
        try:
            cursor = self.db.training_plans.find({})
            training_plans = []

            async for doc in cursor:
                # Count total simulations in this training plan
                total_sims = 0
                for obj in doc.get("addedObject", []):
                    if obj["type"] == "simulation":
                        total_sims += 1
                    elif obj["type"] == "module":
                        # Get module's simulations
                        try:
                            module = await self.db.modules.find_one(
                                {"_id": ObjectId(obj["id"])})
                            if module:
                                total_sims += len(
                                    module.get("simulationIds", []))
                        except Exception:
                            # Skip if module not found or invalid ID
                            continue

                training_plan = ListItemData(name=doc.get("name", ""),
                                             id=str(doc["_id"]),
                                             type="Training plan",
                                             sims=total_sims)
                training_plans.append(training_plan)

            return training_plans

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error listing training plans: {str(e)}")

    async def list_modules(self, user_id: str) -> List[ListItemData]:
        """List all modules with summary information"""
        try:
            cursor = self.db.modules.find({})
            modules = []

            async for doc in cursor:
                # Count total simulations in this module
                total_sims = len(doc.get("simulationIds", []))

                module = ListItemData(name=doc.get("name", ""),
                                      id=str(doc["_id"]),
                                      type="Module",
                                      sims=total_sims)
                modules.append(module)

            return modules

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error listing modules: {str(e)}")

    async def list_simulations(self, user_id: str) -> List[ListItemData]:
        """List all published simulations with summary information"""
        try:
            # Only find simulations with status "published"
            cursor = self.db.simulations.find({"status": "published"})
            simulations = []

            async for doc in cursor:
                simulation = ListItemData(
                    name=doc.get("name", ""),
                    id=str(doc["_id"]),
                    type="Sim",
                    sims=0  # Simulations don't have sub-simulations
                )
                simulations.append(simulation)

            return simulations

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error listing simulations: {str(e)}")
