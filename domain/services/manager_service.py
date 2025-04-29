from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from domain.interfaces.manager_repository import IManagerRepository
from domain.services.assignment_service import AssignmentService
from infrastructure.repositories.manager_repository import ManagerRepository
from infrastructure.database import Database
from api.schemas.responses import (FetchManagerDashboardTrainingPlansResponse, TrainingPlanDetails, ModuleDetails,
                                   SimulationDetails, FetchManagerDashnoardTrainingPlansDetails, TrainingPlanDetailsByUser, TrainingPlanDetailsMinimal)

from fastapi import HTTPException

from utils.logger import Logger  # Make sure the import path is correct for your project

logger = Logger.get_logger(__name__)

class ManagerService:

    def __init__(self, repository: IManagerRepository = None):
        self.db = Database()
        self.repository = repository or ManagerRepository()
        logger.info("ManagerService initialized.")

    
    
    async def get_all_assigments_by_user_details(self,
                                   user_id: str, reporting_userIds: List[str]) -> List[TrainingPlanDetailsMinimal]: 
        """Get All Assignment By User Details"""
        logger.info(f"Get All Assignment By User Details user_id={user_id}, reporting_userIds={reporting_userIds}")
        try:
            
            assignmentWithUsers = []
            # for userId in reporting_userIds:
            user = await self.db.users.find_one({"_id": reporting_userIds[0]})
            if not user:
                logger.warning(f"User {user_id} not found.")
                raise HTTPException(status_code=404,
                                    detail=f"User {user_id} not found")
            
            assignment_ids = user.get("assignments", [])
            logger.debug(
                f"Assignment IDs for user {user_id}: {assignment_ids}")
            
            object_ids = [ObjectId(aid) for aid in assignment_ids]
            assignments = await self.db.assignments.find({
                "_id": {
                    "$in": object_ids
                },
                "type": "TrainingPlan",
                "status": "published"
            }).to_list(None)


            # # Mapping assignments by trainingPlans
            for assignment in assignments:
                if assignment["id"] not in [assignmentWithUsers["id"] for tp in assignmentWithUsers]:
                    assignmentWithUsers.append(assignment)
                else:
                    for assignmentWithUser in assignmentWithUsers:
                        if assignmentWithUser["id"] == assignment["id"]:
                            assignmentWithUser["teamId"].append(assignment["teamId"])
                            assignmentWithUser["traineeId"].append(assignment["traineeId"])
                    

            assignment_service = AssignmentService()
            userMap = {}
            training_plans = [] 
            for assignment in assignmentWithUsers:
                logger.debug(f"Processing assignment: {assignment}")
                
                if assignment["type"] == "TrainingPlan":
                    training_plan = await self.db.training_plans.find_one(
                        {"_id": ObjectId(assignment["id"])})
                    if training_plan:
                        for userId in assignment['traineeId']:
                            training_plans_by_user = [] 
                            total_simulations = 0
                            plan_modules = []
                            plan_total_simulations = 0
                            plan_est_time = 0

                            for added_obj in training_plan.get("addedObject", []):
                                if added_obj["type"] == "module":
                                    module_details = await assignment_service._get_module_details(
                                        added_obj["id"],
                                        assignment["endDate"],
                                        str(assignment["_id"]),
                                        userId,
                                    )
                                    if module_details:
                                        plan_modules.append(module_details)
                                        plan_total_simulations += (
                                            module_details.total_simulations)
                                        plan_est_time += sum(
                                            sim.estTime
                                            for sim in module_details.simulations)
                                        total_simulations += module_details.total_simulations

                                elif added_obj["type"] == "simulation":
                                    sim_details = await assignment_service._get_simulation_details(
                                        added_obj["id"],
                                        assignment["endDate"],
                                        str(assignment["_id"]),
                                        userId,
                                    )
                                    if sim_details:
                                        plan_modules.append(
                                            ModuleDetails(
                                                id=sim_details.simulation_id,
                                                name=sim_details.name,
                                                total_simulations=1,
                                                average_score=0,
                                                due_date=assignment["endDate"],
                                                status="not_started",
                                                simulations=[sim_details],
                                            ))
                                        plan_total_simulations += 1
                                        plan_est_time += sim_details.estTime
                                        total_simulations += 1

                            module_statuses = [mod.status for mod in plan_modules]
                            if all(status == "completed"
                                for status in module_statuses):
                                plan_status = "completed"
                            elif any(status == "in_progress"
                                    for status in module_statuses):
                                plan_status = "in_progress"
                            else:
                                plan_status = "not_started"
                            training_plans_by_user.append(TrainingPlanDetailsByUser(
                                 completion_percentage=0,
                                total_modules=len(plan_modules),
                                total_simulations=plan_total_simulations,
                                est_time=plan_est_time,
                                average_sim_score=0,
                                due_date=assignment["endDate"],
                                status=plan_status,
                                user_id=userId,
                                modules=plan_modules,
                            ))

                        training_plans.append(
                            TrainingPlanDetailsMinimal(
                                id=str(training_plan["_id"]),
                                name=training_plan.get("name", ""),
                                user=training_plans_by_user
                            ))
                        userMap['userId'] = training_plans
            
            # training_plans = await self.repository.fetch_manager_dashboard_training_plans(user_id)
            return training_plans
            
        except Exception as e:
            logger.error(f"Error Getting All Assignment By User Details {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error Getting All Assignment By User Details {str(e)}")
    
    async def fetch_manager_dashboard_training_plans(self,
                                user_id: str, reporting_userIds: List[str]) -> FetchManagerDashboardTrainingPlansResponse: 
            logger.info(f"Fetching manager dashboard training plans for user_id={user_id} and reporting_userIds={reporting_userIds}")
            try:
                training_plans = await self.get_all_assigments_by_user_details(user_id, reporting_userIds)
                return FetchManagerDashboardTrainingPlansResponse(training_plans=training_plans)
            except Exception as e:
                logger.error(f"Error fetching manager dashboard training plans: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error fetching manager dashboard training plans: {str(e)}")