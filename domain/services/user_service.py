from typing import List
from domain.services.assignment_service import AssignmentService
from api.schemas.responses import (FetchAssignedPlansResponse, Stats, StatsData, AdminDashboardUserActivityStatsResponse)
from fastapi import HTTPException
from domain.utils.date_utils import DateUtils
import math


from utils.logger import Logger  # Ensure correct import path for your project
logger = Logger.get_logger(__name__)


class UserService:
    def __init__(self):
        logger.info("UserService initialized.")
        
    async def get_user_assignments_with_stats(self, user_id: str):
        logger.info("Fetching user assignments with stats.")
        logger.debug(f"user_id={user_id}")
        assignment_service = AssignmentService()
        try:
            assignments_with_stats: FetchAssignedPlansResponse = await assignment_service.fetch_assigned_plans(user_id)
            logger.info(f"Fetched assignments for user_id={user_id}.")
            return assignments_with_stats
        except Exception as e:
            logger.error(f"Error fetching assignments for user_id={user_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error fetching assignments for user_id={user_id}: {str(e)}")

    async def get_admin_dashboard_user_stats(self, user_id: str) -> List[AdminDashboardUserActivityStatsResponse]:
        logger.info("Fetching all users total simulations.")
        mock_user_list = [
            {
            "user_id": "67f6286b75b9226a9afabfaa",
            "first_name": "Anmol",
            "last_name": "Rishi",
            "email": "anmol_test@yopmail.com",
            "phone_no": "+919654115965",
            "division": "EverAI Labs",
            "department": "Product Design dev",
            "reporting_to": {
                "id": "67ebe72cb38db47a3d742543",
                "name": "Simulator Manager"
            },
            "class_id": "",
            "internal_user_id": "Anmol_internal",
            "external_user_id": "Anmol_external",
            "status": "ACTIVE",
            "created": {
                "user": {
                "id": "67a1188276d6606ab2c082b7",
                "name": "Maneesh Singh"
                },
                "time": "2025-04-09T07:57:31.444Z"
            },
            "updated": {
                "user": {
                "id": "67a1188276d6606ab2c082b7",
                "name": "Maneesh Singh"
                },
                "time": "2025-04-15T10:28:04.537Z"
            },
            "roles": [
                {
                "role_id": "67f6283975b9226a9afabfa9",
                "name": "anmol_test",
                "product": "Simulator"
                }
            ]
            }
        ]
        try:
            date_util = DateUtils()
            admin_dashboard_user_stats_list: List[AdminDashboardUserActivityStatsResponse] = []
            for user in mock_user_list:
                if user.get("user_id"):
                    user_object = {}
                    user_id = user.get("user_id")
                    user_object["id"] = user_id
                    user_object["name"] = user.get("first_name") + " " + user.get("last_name")
                    user_object["email"] = user.get("email")
                    user_object["role"] = "TEST_ROLE" ## need to devise a method how to identify teh exact role name from list of roles mentioned for user
                    user_object["division"] = user.get("division")
                    user_object["department"] = user.get("department")
                    user_object["addedOn"] = date_util.convert_to_human_readable(user.get("created").get("time"))
                    user_object["status"] = user.get("status")
                    user_object["activatedOn"] = "test-activated-on"
                    user_object["deActivatedOn"] = "test-deactivated-on"
                    user_object["loginCount"] = 0
                    user_object["lastLoginOn"] = "test-last-login-on"
                    user_object["lastSessionDuration"] = 0
                    user_object["assignedSimulations"] = 0
                    user_object["completionRate"] = 0
                    user_object["adherenceRate"] = 0
                    user_object["averageScore"] = 0
                    
                    assignments_with_stats: FetchAssignedPlansResponse = await self.get_user_assignments_with_stats(user_id)

                    if assignments_with_stats:
                        users_assignments_stats: Stats = assignments_with_stats.stats
                        if users_assignments_stats and users_assignments_stats.simulation_completed:
                            total_simulations = (users_assignments_stats.simulation_completed.total_simulations if users_assignments_stats.simulation_completed.total_simulations else 0)
                            user_object["assignedSimulations"] = total_simulations
                            user_object["completionRate"] = math.ceil(users_assignments_stats.simulation_completed.percentage)
                        if users_assignments_stats and users_assignments_stats.timely_completion:
                            user_object["adherenceRate"] = math.ceil(users_assignments_stats.timely_completion.percentage)
                        user_object["averageScore"] = math.ceil(users_assignments_stats.average_sim_score)
                
                    admin_dashboard_user_stats_list.append(AdminDashboardUserActivityStatsResponse(**user_object))
            
            return admin_dashboard_user_stats_list
        except Exception as e:
            logger.error(f"Error fetching assignments for user_id={user_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error fetching assignments for user_id={user_id}: {str(e)}")
        