from fastapi import APIRouter, HTTPException
from api.schemas.requests import CreateModuleRequest, FetchModulesRequest, CloneModuleRequest, UpdateModuleRequest, FetchManagerDashboardTrainingPlansRequest
from api.schemas.responses import CreateModuleResponse, FetchModulesResponse, ModuleData, FetchManagerDashboardTrainingPlansResponse
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
    
    async def fetch_manager_dashboard_training_plans(self, request: FetchManagerDashboardTrainingPlansRequest) -> FetchManagerDashboardTrainingPlansResponse:
        reporting_userIds= [request.user_id, '67ceaa2136089d2932548b99', '67f6a6a2a7b7f121fc91f2b5']
        logger.info(f"Fetching manager dashboard training plans for user_id={request.user_id}, reporting_userIds={reporting_userIds}")
        try:
            response = await self.service.fetch_manager_dashboard_training_plans(request.user_id, reporting_userIds)
            logger.debug(f"Manager dashboard training plans: {response}")
            return response;
        except Exception as e:
            logger.error(f"Error fetching manager dashboard training plans: {str(e)}", exc_info=True)
            raise

controller = ManagerController()

@router.post("/manager-dashboard-data/fetch", tags=["Manager", "Read"])
async def fetch_manager_dashboard_data(request):
    logger.info("API endpoint called: /manager-dashboard-data/fetch")
    logger.debug(f"Request body: {request}")
    ## return await controller.get_manager_dashboard_data(user_id)

@router.post("/manager-dashboard-data/training-plans/fetch", tags=["Manager", "Read"])
async def fetch_manager_dashboard_training_plans(
        request: FetchManagerDashboardTrainingPlansRequest) -> FetchManagerDashboardTrainingPlansResponse:
    """Fetch assigned training plans with nested details"""
    return await controller.fetch_manager_dashboard_training_plans(request)