from fastapi import APIRouter, HTTPException
from api.schemas.requests import AdminDashboardUserActivityStatsRequest
from api.schemas.responses import AdminDashboardUserActivityStatsResponse
from domain.services.user_service import UserService
from typing import List

from utils.logger import Logger

logger = Logger.get_logger(__name__)

router = APIRouter()


class AdminController:
    def __init__(self):
        self.user_service = UserService()
        logger.info("AdminController initialized.")

    async def fetch_admin_dashboard_data(self, request: AdminDashboardUserActivityStatsRequest) -> List[AdminDashboardUserActivityStatsResponse]:
        logger.info("Received request to fetch admin dashboard data.")
        logger.debug(f"user_id: {request.user_id}")
        
        try:
            data = await self.user_service.get_admin_dashboard_user_stats(request.user_id)
            logger.info(f"Manager dashboard data fetched successfully for user_id: {request.user_id}")
            return data
        except Exception as e:
            logger.error(f"Error fetching manager dashboard data: {str(e)}", exc_info=True)
            raise

controller = AdminController()

@router.post("/admin-dashboard/users/stats", tags=["Admin", "Read"])
async def fetch_admin_dashboard_data(request: AdminDashboardUserActivityStatsRequest) -> List[AdminDashboardUserActivityStatsResponse]:
    logger.info("API endpoint called: /admin-dashboard/users/stats")
    logger.debug(f"Request body: {request}")
    return await controller.fetch_admin_dashboard_data(request)
