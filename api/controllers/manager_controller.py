from fastapi import APIRouter
from api.schemas.requests import ManagerDashboardAggregateRequest, FetchManagerDashboardTrainingEntityRequest
from api.schemas.responses import ManagerDashboardTrainingEntityTableResponse, ManagerDashboardAggregateDetails
from domain.services.manager_service import ManagerService

from utils.logger import Logger

logger = Logger.get_logger(__name__)
router = APIRouter()

class ManagerController:
    def __init__(self):
        self.service = ManagerService()
        logger.info("ManagerController initialized.")

    async def get_manager_dashboard_data(self, request: ManagerDashboardAggregateRequest) -> ManagerDashboardAggregateDetails:
        logger.info("Received request to fetch manager dashboard data.")
        logger.debug(f"user_id: {request.user_id}")
        try:
            data = await self.service.get_manager_dashboard_data(
                request.user_id, 
                request.reportee_user_ids,
                request.reportee_team_ids,
                request.params)
            logger.info(f"Manager dashboard data fetched successfully for user_id: {request.user_id}")
            return data
        except Exception as e:
            logger.error(f"Error fetching manager dashboard data: {str(e)}", exc_info=True)
            raise

    async def fetch_manager_dashboard_table_data(self, request: FetchManagerDashboardTrainingEntityRequest) -> ManagerDashboardTrainingEntityTableResponse:
        logger.info(f"Fetching manager dashboard simulations for user_id={request.user_id}, reporting_userIds={request.reportee_user_ids}, reporting_teamIds={request.reportee_team_ids}")
        try:
            response = await self.service.fetch_manager_dashboard_training_entity_data(
                request.user_id, 
                request.reportee_user_ids, 
                request.reportee_team_ids, 
                request.type, 
                request.params,
                request.pagination)
            logger.debug(f"Manager dashboard simulations: {response}")
            return response
        except Exception as e:
            logger.error(f"Error fetching manager dashboard simulations: {str(e)}", exc_info=True)
            raise

controller = ManagerController()

@router.post("/manager-dashboard-data/fetch/training-entity", tags=["Manager", "Read"])
async def fetch_manager_dashboard_table_data(request: FetchManagerDashboardTrainingEntityRequest):
    logger.info("API endpoint called: /manager-dashboard-data/fetch/training-entity")
    logger.debug(f"Request body: {request}")
    return await controller.fetch_manager_dashboard_table_data(request)

@router.post("/manager-dashboard-data/fetch", tags=["Manager", "Read"])
async def fetch_manager_dashboard_data(request: ManagerDashboardAggregateRequest):
    logger.info("API endpoint called: /manager-dashboard-data/fetch")
    logger.debug(f"Request body: {request}")
    return await controller.get_manager_dashboard_data(request)







