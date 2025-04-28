from fastapi import APIRouter, HTTPException
from api.schemas.requests import CreateModuleRequest, FetchModulesRequest, CloneModuleRequest, UpdateModuleRequest
from api.schemas.responses import CreateModuleResponse, FetchModulesResponse, ModuleData
from domain.services.manager_service import ManagerService

from utils.logger import Logger

logger = Logger.get_logger(__name__)

router = APIRouter()


class ManagerController:
    def __init__(self):
        self.service = ManagerService()
        logger.info("ManagerController initialized.")

    async def get_manager_dashboard_data(self, user_id: str):
        logger.info("Received request to fetch manager dashboard data.")
        logger.debug(f"user_id: {user_id}")

        try:
            # data = await self.service.get_manager_dashboard_data(user_id)
            logger.info(f"Manager dashboard data fetched successfully for user_id: {user_id}")
            # return data
        except Exception as e:
            logger.error(f"Error fetching manager dashboard data: {str(e)}", exc_info=True)
            raise

controller = ManagerController()

@router.post("/manager-dashboard-data/fetch", tags=["Manager", "Read"])
async def fetch_manager_dashboard_data(request):
    logger.info("API endpoint called: /manager-dashboard-data/fetch")
    logger.debug(f"Request body: {request}")
    ## return await controller.get_manager_dashboard_data(user_id)