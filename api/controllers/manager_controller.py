from fastapi import APIRouter
from api.schemas.requests import FetchManagerDashboardTrainingPlansRequest, FetchManagerDashboardTrainingEntityRequest
from api.schemas.responses import FetchManagerDashboardTrainingPlansResponse, FetchManagerDashboardModulesResponse, FetchManagerDashboardSimultaionResponse , ManagerDashboardTrainingEntityTableResponse
from domain.services.manager_service import ManagerService

from utils.logger import Logger

logger = Logger.get_logger(__name__)
router = APIRouter()

class ManagerController:
    def __init__(self):
        self.service = ManagerService()
        logger.info("ManagerController initialized.")

    async def get_manager_dashboard_data(self, request: FetchManagerDashboardTrainingPlansRequest) -> FetchManagerDashboardTrainingPlansResponse:
        logger.info("Received request to fetch manager dashboard data.")
        logger.debug(f"user_id: {request.user_id}")
        reporting_userIds= [request.user_id, '67ebe72cb38db47a3d742543', '67a31a99aa22bc6b9f0cf551', '67a1188276d6606ab2c082b7', '67ec0ae59ad3cd6528f866ab', 'trainee1']
        try:
            data = await self.service.get_manager_dashboard_data(request.user_id, reporting_userIds)
            logger.info(f"Manager dashboard data fetched successfully for user_id: {request.user_id}")
            return data
        except Exception as e:
            logger.error(f"Error fetching manager dashboard data: {str(e)}", exc_info=True)
            raise
   
    async def fetch_manager_dashboard_training_plans(self, request: FetchManagerDashboardTrainingPlansRequest) -> FetchManagerDashboardTrainingPlansResponse:
        reporting_userIds= [request.user_id, '67ebe72cb38db47a3d742543', '67a31a99aa22bc6b9f0cf551', '67a1188276d6606ab2c082b7', '67ec0ae59ad3cd6528f866ab']
        # reporting_userIds= ['trainee1', 'trainee2']
        logger.info(f"Fetching manager dashboard training plans for user_id={request.user_id}, reporting_userIds={reporting_userIds}")
        try:
            response = await self.service.fetch_manager_dashboard_training_entity_data(request.user_id, reporting_userIds,'TrainingPlan', FetchManagerDashboardTrainingPlansResponse)
            logger.debug(f"Manager dashboard training plans: {response}")
            return response
        except Exception as e:
            logger.error(f"Error fetching manager dashboard training plans: {str(e)}", exc_info=True)
            raise
   
    async def fetch_manager_dashboard_modules(self, request: FetchManagerDashboardTrainingPlansRequest) -> FetchManagerDashboardModulesResponse:
        # reporting_userIds= [request.user_id, '67ceaa2136089d2932548b99', '67a31a99aa22bc6b9f0cf551', '67a1188276d6606ab2c082b7', '67ec0ae59ad3cd6528f866ab']
        reporting_userIds= ['trainee1', 'trainee2']
        logger.info(f"Fetching manager dashboard training plans for user_id={request.user_id}, reporting_userIds={reporting_userIds}")
        try:
            response = await self.service.fetch_manager_dashboard_training_entity_data(request.user_id, reporting_userIds,'Module', FetchManagerDashboardModulesResponse)
            logger.debug(f"Manager dashboard training plans: {response}")
            return response
        except Exception as e:
            logger.error(f"Error fetching manager dashboard training plans: {str(e)}", exc_info=True)
            raise
   
    async def fetch_manager_dashboard_simulations(self, request: FetchManagerDashboardTrainingPlansRequest) -> FetchManagerDashboardSimultaionResponse:
        reporting_userIds= [request.user_id, '67ceaa2136089d2932548b99', '67a31a99aa22bc6b9f0cf551', '67a1188276d6606ab2c082b7', '67ec0ae59ad3cd6528f866ab', 'member2', 'trainee1', 'trainee2', '67fe55ab87ab384ebb086d63']
        #reporting_userIds= ['trainee1', 'trainee2']
        logger.info(f"Fetching manager dashboard simulations for user_id={request.user_id}, reporting_userIds={reporting_userIds}")
        try:
            response = await self.service.fetch_manager_dashboard_training_entity_data(request.user_id, reporting_userIds , 'Simulation', FetchManagerDashboardSimultaionResponse)
            logger.debug(f"Manager dashboard simulations: {response}")
            return response
        except Exception as e:
            logger.error(f"Error fetching manager dashboard simulations: {str(e)}", exc_info=True)
            raise

    async def fetch_manager_dashboard_table_data(self, request: FetchManagerDashboardTrainingEntityRequest) -> ManagerDashboardTrainingEntityTableResponse:
        reporting_userIds= [request.user_id, '67ceaa2136089d2932548b99', '67a31a99aa22bc6b9f0cf551', '67a1188276d6606ab2c082b7', '67ec0ae59ad3cd6528f866ab', 'member2']
        # reporting_userIds= ['trainee1', 'trainee2']
        logger.info(f"Fetching manager dashboard simulations for user_id={request.user_id}, reporting_userIds={reporting_userIds}")
        try:
            response = await self.service.fetch_manager_dashboard_training_entity_data(request.user_id, reporting_userIds , request.type, request.pagination)
            logger.debug(f"Manager dashboard simulations: {response}")
            return response
        except Exception as e:
            logger.error(f"Error fetching manager dashboard simulations: {str(e)}", exc_info=True)
            raise

controller = ManagerController()

@router.post("/manager-dashboard-data/fetch/training-entity", tags=["Manager", "Read"])
async def fetch_manager_dashboard_data(request: FetchManagerDashboardTrainingEntityRequest):
    logger.info("API endpoint called: /manager-dashboard-data/fetch/training-entity")
    logger.debug(f"Request body: {request}")
    return await controller.fetch_manager_dashboard_table_data(request)

@router.post("/manager-dashboard-data/fetch", tags=["Manager", "Read"])
async def fetch_manager_dashboard_data(request: FetchManagerDashboardTrainingPlansRequest):
    logger.info("API endpoint called: /manager-dashboard-data/fetch")
    logger.debug(f"Request body: {request}")
    return await controller.get_manager_dashboard_data(request)

@router.post("/manager-dashboard-data/training-plans/fetch", tags=["Manager", "Read"])
async def fetch_manager_dashboard_training_plans(
        request: FetchManagerDashboardTrainingPlansRequest) -> FetchManagerDashboardTrainingPlansResponse:
    """Fetch assigned training plans with nested details"""
    return await controller.fetch_manager_dashboard_training_plans(request)

@router.post("/manager-dashboard-data/modules/fetch", tags=["Manager", "Read"])
async def fetch_manager_dashboard_training_plans(
        request: FetchManagerDashboardTrainingPlansRequest) -> FetchManagerDashboardModulesResponse:
    """Fetch assigned training plans with nested details"""
    return await controller.fetch_manager_dashboard_modules(request)

@router.post("/manager-dashboard-data/simulations/fetch", tags=["Manager", "Read"])
async def fetch_manager_dashboard_simulations(
        request: FetchManagerDashboardTrainingPlansRequest) -> FetchManagerDashboardSimultaionResponse:
    """Fetch assigned simulations with nested details"""
    return await controller.fetch_manager_dashboard_simulations(request)







