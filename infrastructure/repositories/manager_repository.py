from typing import Dict, List, Optional ,Type, Union
from datetime import datetime
from bson import ObjectId
from domain.interfaces.manager_repository import IManagerRepository
from domain.services.assignment_service import AssignmentService
from infrastructure.database import Database
from api.schemas.requests import PaginationParams
from api.schemas.responses import ( ModuleDetails,
                                   ModuleDetailsByUser, TrainingPlanDetailsByUser, TrainingPlanDetailsMinimal, ModuleDetailsMinimal, FetchManagerDashboardResponse, SimulationDetailsMinimal, SimulationDetailsByUser, PaginationMetadata)

from fastapi import HTTPException
import math
from utils.logger import Logger 



logger = Logger.get_logger(__name__)




class ManagerRepository(IManagerRepository):
    def __init__(self):
        self.db = Database()
        logger.info("ManagerRepository initialized.")
   
    async def get_manager_dashboard_data(self, user_id: str) -> Dict:
        logger.info(f"Fetching manager dashboard data for user_id: {user_id}")
        return {}
   
    
    async def   get_all_assigments_by_user_details(self,
                                   user_id: str, reporting_userIds: List[str], type: str, 
                                   pagination: Optional[PaginationParams] = None) -> FetchManagerDashboardResponse:
        """Get All Assignment By User Details
        
        Returns:
            FetchManagerDashboardResponse containing training plans, modules, and simulations
        """
        logger.info(f"Get All Assignment By User Details user_id={user_id}, reporting_userIds={reporting_userIds}")
        if pagination:
            logger.info(f"Pagination={pagination}")
        
        try:
            assignmentWithUsers = []
            total_count = 0
            
            # Calculate pagination parameters if pagination is provided
            # skip = 0
            # limit = None
            # page = 1
            # pagesize = 20  
            
            if pagination:
                page = pagination.page
                pagesize = pagination.pagesize
                skip = (page - 1) * pagesize

            for reporting_userId in reporting_userIds:
                user = await self.db.users.find_one({"_id": reporting_userId})
                if user:                
                    assignment_ids = user.get("assignments", [])
                    logger.debug(f"Assignment IDs for user {user_id}: {assignment_ids}")
                    
                    object_ids = [ObjectId(aid) for aid in assignment_ids]
                    
                    # Get total count for pagination if pagination is enabled
                    if pagination:
                        total_count += await self.db.assignments.count_documents({
                            "_id": {"$in": object_ids},
                            "type": type,
                        })
                    
                    # Create the query
                    assignment_query = self.db.assignments.find({
                        "_id": {"$in": object_ids},
                        "type": type,
                    })
                    
                    # Apply pagination if provided
                    if pagination:
                        assignment_query = assignment_query.skip(skip).limit(pagesize)
                    
                    # Execute the query
                    assignments = await assignment_query.to_list(None)

                    # Mapping assignments by type
                    for assignment in assignments:
                        if assignment["id"] not in [tp["id"] for tp in assignmentWithUsers]:
                            assignment['traineeId'] = set()
                            assignment['traineeId'].add(reporting_userId)
                            assignment['teamId'] = [reporting_userId]
                            assignmentWithUsers.append(assignment)
                        else:
                            for assignmentWithUser in assignmentWithUsers:
                                if assignmentWithUser["id"] == assignment["id"]:
                                    assignmentWithUser["teamId"].append(reporting_userId)
                                    assignmentWithUser["traineeId"].add(reporting_userId)
                                    break

            assignment_service = AssignmentService()
            userMap = {}
            training_plans = []
            modules = []
            simulations = []
            total_simulations = 0
            _STATUS_PRIORITY = {"not_started": 0, "in_progress": 1, "completed": 2}

            for assignment in assignmentWithUsers:
                logger.debug(f"Processing assignment: {assignment}")
                
                if assignment["type"] == "TrainingPlan":
                    training_plan = await self.db.training_plans.find_one(
                        {"_id": ObjectId(assignment["id"])})
                    if training_plan:
                        training_plans_by_user = []
                        for userId in assignment['traineeId']:
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
                                                status=sim_details.status,
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
                            elif any(status == "over_due"
                                    for status in module_statuses):
                                plan_status = "over_due"
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
                                completion_percentage=0,
                                average_score=0,
                                user=training_plans_by_user
                            ))
                        userMap['userId'] = training_plans

                elif assignment["type"] == "Module":
                    for userId in assignment['traineeId']:
                        module_by_user = []
                        module_total_simulations = 0
                        module_details = await assignment_service._get_module_details(
                            assignment["id"],
                            assignment["endDate"],
                            str(assignment["_id"]),
                            userId,
                        )
                        if module_details:
                            module_total_simulations += module_details.total_simulations    
                            if all(sim.status == "completed" for sim in module_details.simulations):
                                plan_status = "completed"
                            elif all(sim.status == "not_started" for sim in module_details.simulations):
                                plan_status = "not_started"
                            elif any(sim.status == "in_progress" for sim in module_details.simulations) and all(sim.status != "over_due" for sim in module_details.simulations):
                                plan_status = "in_progress"
                            else:
                                plan_status = "over_due"
                            module_by_user.append(
                                ModuleDetailsByUser(
                                    total_simulations=module_total_simulations,
                                    average_score=0,
                                    due_date=assignment["endDate"],
                                    status=plan_status,
                                    user_id=userId,
                                    simulations=module_details.simulations,
                                )
                            )
                            
                            modules.append(
                                ModuleDetailsMinimal(
                                    id=assignment["id"],
                                    name=module_details.name,
                                    completion_percentage=0,
                                    average_score=0,
                                    user=module_by_user
                                )
                            )
                        
                elif assignment["type"] == "Simulation":
                    for userId in assignment['traineeId']:
                        simulation_by_user = []
                        sim_details = await assignment_service._get_simulation_details(
                            assignment["id"],
                            assignment["endDate"],
                            str(assignment["_id"]),
                            userId,
                        )
                        if sim_details:
                            simulation_by_user.append(
                                SimulationDetailsByUser(
                                    simulation_id=sim_details.simulation_id,
                                    name=sim_details.name,
                                    type=sim_details.type,
                                    level=sim_details.level,
                                    estTime=sim_details.estTime,
                                    dueDate=sim_details.dueDate,
                                    status=sim_details.status,
                                    scores=sim_details.scores,
                                    highest_attempt_score=sim_details.highest_attempt_score,
                                    assignment_id=sim_details.assignment_id,
                                    user_id=userId
                                )
                            )
                            total_simulations += 1

                            simulations.append(
                                SimulationDetailsMinimal(
                                    id=sim_details.simulation_id,
                                    name=sim_details.name,
                                    completion_percentage=0,
                                    average_score=0,
                                    user=simulation_by_user
                                )
                            )

            # Add pagination metadata if pagination is provided
            if pagination:
                total_pages = math.ceil(total_count / pagesize)
                pagination_metadata = PaginationMetadata(
                    total_count=total_count,
                    page=page,
                    pagesize=pagesize,
                    total_pages=total_pages
                )
                logger.info(f"Pagination metadata: {pagination_metadata}")
                return FetchManagerDashboardResponse(
                    training_plans=training_plans, 
                    modules=modules, 
                    simulations=simulations, 
                    pagination=pagination_metadata
                )
            else:
                # Return response without pagination metadata
                return FetchManagerDashboardResponse(
                    training_plans=training_plans, 
                    modules=modules, 
                    simulations=simulations
                )
            
        except Exception as e:
            logger.error(f"Error Getting All Assignment By User Details {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error Getting All Assignment By User Details {str(e)}")





