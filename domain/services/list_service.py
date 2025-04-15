from typing import Dict, List
from bson import ObjectId
from infrastructure.database import Database
from api.schemas.responses import ListItemData
from fastapi import HTTPException

from utils.logger import Logger  # Make sure the path to Logger is correct for your project

logger = Logger.get_logger(__name__)


class ListService:

    def __init__(self):
        self.db = Database()
        logger.info("ListService initialized.")

    async def list_training_plans(self, user_id: str) -> List[ListItemData]:
        """List all training plans with summary information"""
        logger.info("Request received to list training plans.")
        logger.debug(f"user_id: {user_id}")
        try:
            cursor = self.db.training_plans.find({})
            training_plans = []

            async for doc in cursor:
                total_sims = 0
                for obj in doc.get("addedObject", []):
                    if obj["type"] == "simulation":
                        total_sims += 1
                    elif obj["type"] == "module":
                        try:
                            module = await self.db.modules.find_one(
                                {"_id": ObjectId(obj["id"])})
                            if module:
                                total_sims += len(
                                    module.get("simulationIds", []))
                        except Exception as ex:
                            logger.warning(
                                f"Skipping invalid module for ID {obj['id']} due to: {ex}"
                            )
                            continue

                tp_id = str(doc["_id"])
                name = doc.get("name", "")
                logger.debug(
                    f"Found training plan: {name}, ID: {tp_id}, total_sims={total_sims}"
                )

                training_plan = ListItemData(name=name,
                                             id=tp_id,
                                             type="Training plan",
                                             sims=total_sims)
                training_plans.append(training_plan)

            logger.info(f"Total training plans found: {len(training_plans)}")
            return training_plans
        except Exception as e:
            logger.error(f"Error listing training plans: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error listing training plans: {str(e)}")

    async def list_modules(self, user_id: str) -> List[ListItemData]:
        """List all modules with summary information"""
        logger.info("Request received to list modules.")
        logger.debug(f"user_id: {user_id}")
        try:
            cursor = self.db.modules.find({})
            modules = []

            async for doc in cursor:
                total_sims = len(doc.get("simulationIds", []))
                m_id = str(doc["_id"])
                name = doc.get("name", "")
                logger.debug(
                    f"Found module: {name}, ID: {m_id}, total_sims={total_sims}"
                )

                module = ListItemData(name=name,
                                      id=m_id,
                                      type="Module",
                                      sims=total_sims)
                modules.append(module)

            logger.info(f"Total modules found: {len(modules)}")
            return modules
        except Exception as e:
            logger.error(f"Error listing modules: {e}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error listing modules: {str(e)}")

    async def list_simulations(self, user_id: str) -> List[ListItemData]:
        """List all published simulations with summary information"""
        logger.info("Request received to list simulations.")
        logger.debug(f"user_id: {user_id}")
        try:
            cursor = self.db.simulations.find({"status": "published"})
            simulations = []

            async for doc in cursor:
                s_id = str(doc["_id"])
                name = doc.get("name", "")
                logger.debug(f"Found published simulation: {name}, ID: {s_id}")

                simulation = ListItemData(name=name,
                                          id=s_id,
                                          type="Sim",
                                          sims=0)
                simulations.append(simulation)

            logger.info(
                f"Total published simulations found: {len(simulations)}")
            return simulations
        except Exception as e:
            logger.error(f"Error listing simulations: {e}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error listing simulations: {str(e)}")
