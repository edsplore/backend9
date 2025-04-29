from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from domain.interfaces.manager_repository import IManagerRepository
from domain.services.assignment_service import AssignmentService
from infrastructure.repositories.manager_repository import ManagerRepository
from infrastructure.database import Database
from api.schemas.responses import (FetchManagerDashboardTrainingPlansResponse, TrainingPlanDetails, ModuleDetails,
                                   SimulationDetails, ModuleDetailsByUser, TrainingPlanDetailsByUser, TrainingPlanDetailsMinimal, ModuleDetailsMinimal, FetchManagerDashboardResponse,
                                   FetchManagerDashboardModulesResponse, FetchManagerDashboardSimultaionResponse, SimulationDetailsMinimal, SimulationDetailsByUser, ManagerDashboardAggregateAssignmentCounts, 
                                   ManagerDashboardAssignmentCounts, ManagerDashboardAggregateDetails, ManagerDashboardAggregateMetrics)

from fastapi import HTTPException
import math

from utils.logger import Logger  # Make sure the import path is correct for your project

logger = Logger.get_logger(__name__)

class ManagerService:

    def __init__(self, repository: IManagerRepository = None):
        self.db = Database()
        self.repository = repository or ManagerRepository()
        logger.info("ManagerService initialized.")

    
    
    async def get_all_assigments_by_user_details(self,
                                   user_id: str, reporting_userIds: List[str], type: str) -> FetchManagerDashboardResponse: 
        """Get All Assignment By User Details"""
        logger.info(f"Get All Assignment By User Details user_id={user_id}, reporting_userIds={reporting_userIds}")
        try:
            
            assignmentWithUsers = []
            for reporting_userId in reporting_userIds:
                # for userId in reporting_userIds:
                user = await self.db.users.find_one({"_id": reporting_userId})
                if user:                
                    assignment_ids = user.get("assignments", [])
                    logger.debug(
                        f"Assignment IDs for user {user_id}: {assignment_ids}")
                    
                    object_ids = [ObjectId(aid) for aid in assignment_ids]
                    assignments = await self.db.assignments.find({
                        "_id": {
                            "$in": object_ids
                        },
                        "type": type,
                        # "status": "published"
                    }).to_list(None)

# 68047e980b2daeb11a65c6bf
                    # # Mapping assignments by trainingPlans
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
                            if all(status == "completed" for status in module_details.simulations):
                                plan_status = "completed"
                            elif all(status == "not_started" for status in module_details.simulations):
                                plan_status = "not_started"
                            elif any(status == "in_progress" for status in module_details.simulations) and all(status != "over_due" for status in module_details.simulations):
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
                                    id = assignment["id"],
                                    name = module_details.name,
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
                            # Consolidate duplicates by assignment with precedence
                            # existing_index = next(
                            #     (idx for idx, s in enumerate(simulations)
                            #     if s.assignment_id == sim_details.assignment_id),
                            #     None,
                            # )
                            # if existing_index is not None:
                            #     existing_sim = simulations[existing_index]
                            #     if (_STATUS_PRIORITY[sim_details.status]
                            #             > _STATUS_PRIORITY[existing_sim.status]):
                            #         simulations[existing_index] = sim_details
                            # else:
                            simulation_by_user.append(
                                SimulationDetailsByUser(
                                    simulation_id=sim_details.simulation_id,
                                    name=sim_details.name,
                                    type=sim_details.type,
                                    level=sim_details.level,  # Default value
                                    estTime=sim_details.estTime,
                                    dueDate=sim_details.dueDate,
                                    status=sim_details.status,
                                    scores= sim_details.scores,
                                    highest_attempt_score=sim_details.highest_attempt_score,
                                    assignment_id=sim_details.assignment_id,
                                    user_id=userId
                                )
                            )
                            total_simulations += 1

        
                            simulations.append(
                                SimulationDetailsMinimal(
                                    id=sim_details.simulation_id,
                                    name= sim_details.name,
                                    completion_percentage = 0,
                                    average_score = 0,
                                    user=simulation_by_user
                                )
                            )

            # training_plans = await self.repository.fetch_manager_dashboard_training_plans(user_id)
            return FetchManagerDashboardResponse(training_plans=training_plans, modules=modules, simulations=simulations)
            
        except Exception as e:
            logger.error(f"Error Getting All Assignment By User Details {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error Getting All Assignment By User Details {str(e)}")
    
    async def fetch_manager_dashboard_training_plans(self,
                                user_id: str, reporting_userIds: List[str]) -> FetchManagerDashboardTrainingPlansResponse: 
            logger.info(f"Fetching manager dashboard training plans for user_id={user_id} and reporting_userIds={reporting_userIds}")
            try:
                dashboard_response = await self.get_all_assigments_by_user_details(user_id, reporting_userIds, 'TrainingPlan')
                return FetchManagerDashboardTrainingPlansResponse(training_plans=dashboard_response.training_plans)
            except Exception as e:
                logger.error(f"Error fetching manager dashboard training plans: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error fetching manager dashboard training plans: {str(e)}")

    async def fetch_manager_dashboard_modules(self,
                                user_id: str, reporting_userIds: List[str]) -> FetchManagerDashboardTrainingPlansResponse: 
            logger.info(f"Fetching manager dashboard modules for user_id={user_id} and reporting_userIds={reporting_userIds}")
            try:
                dashboard_response = await self.get_all_assigments_by_user_details(user_id, reporting_userIds, 'Module')
                return FetchManagerDashboardModulesResponse(modules=dashboard_response.modules)
            except Exception as e:
                logger.error(f"Error fetching manager dashboard modules: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error fetching manager dashboard modules: {str(e)}")

    async def fetch_manager_dashboard_simulations(self,
                            user_id: str, reporting_userIds: List[str]) -> FetchManagerDashboardSimultaionResponse: 
        logger.info(f"Fetching manager dashboard simulations for user_id={user_id} and reporting_userIds={reporting_userIds}")
        try:
            dashboard_response = await self.get_all_assigments_by_user_details(user_id, reporting_userIds, 'Simulation')
            return FetchManagerDashboardSimultaionResponse(simulations=dashboard_response.simulations)
        except Exception as e:
            logger.error(f"Error fetching manager dashboard simulations: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching manager dashboard simulations: {str(e)}")
    
    async def get_manager_dashboard_data(self, user_id: str, reporting_userIds: List[str]) -> ManagerDashboardAggregateDetails:
        logger.info("Fetching Manager Dashboard data.")
        logger.debug(f"user_id={user_id}")
        try:
            training_plan_data = await self.get_all_assigments_by_user_details(user_id, reporting_userIds, 'TrainingPlan')
            module_data = await self.get_all_assigments_by_user_details(user_id, reporting_userIds, 'Module')
            simulation_data = await self.get_all_assigments_by_user_details(user_id, reporting_userIds, 'Simulation')
            #return training_plan_data
            assignment_agg_stats_by_training_entity = {
                "trainingPlans": {
                    "total": 0,
                    "completed": 0,
                    "inProgress": 0,
                    "notStarted": 0,
                    "overdue": 0
                },
                "modules": {
                    "total": 0,
                    "completed": 0,
                    "inProgress": 0,
                    "notStarted": 0,
                    "overdue": 0
                },
                "simulations": {
                    "total": 0,
                    "completed": 0,
                    "inProgress": 0,
                    "notStarted": 0,
                    "overdue": 0
                }
            }
            
            for each_assigned_training_plan in training_plan_data.training_plans:
                for each_assigned_user in each_assigned_training_plan.user:
                    assignment_agg_stats_by_training_entity["trainingPlans"]["total"] +=1
                    if each_assigned_user.status == "completed":
                        assignment_agg_stats_by_training_entity["trainingPlans"]["completed"] +=1
                    elif each_assigned_user.status == "in_progress":
                        assignment_agg_stats_by_training_entity["trainingPlans"]["inProgress"] +=1
                    elif each_assigned_user.status == "not_started":
                        assignment_agg_stats_by_training_entity["trainingPlans"]["notStarted"] +=1
                    elif each_assigned_user.status == "over_due":
                        assignment_agg_stats_by_training_entity["trainingPlans"]["overdue"] +=1
            
            for each_assigned_module in module_data.modules:
                for each_assigned_user in each_assigned_module.user:
                    assignment_agg_stats_by_training_entity["modules"]["total"] +=1
                    if each_assigned_user.status == "completed":
                        assignment_agg_stats_by_training_entity["modules"]["completed"] +=1
                    elif each_assigned_user.status == "in_progress":
                        assignment_agg_stats_by_training_entity["modules"]["inProgress"] +=1
                    elif each_assigned_user.status == "not_started":
                        assignment_agg_stats_by_training_entity["modules"]["notStarted"] +=1
                    elif each_assigned_user.status == "over_due":
                        assignment_agg_stats_by_training_entity["modules"]["overdue"] +=1
            
            for each_assigned_simulation in simulation_data.simulations:
                for each_assigned_user in each_assigned_simulation.user:
                    assignment_agg_stats_by_training_entity["simulations"]["total"] +=1
                    if each_assigned_user.status == "completed":
                        assignment_agg_stats_by_training_entity["simulations"]["completed"] +=1
                    elif each_assigned_user.status == "in_progress":
                        assignment_agg_stats_by_training_entity["simulations"]["inProgress"] +=1
                    elif each_assigned_user.status == "not_started":
                        assignment_agg_stats_by_training_entity["simulations"]["notStarted"] +=1
                    elif each_assigned_user.status == "over_due":
                        assignment_agg_stats_by_training_entity["simulations"]["overdue"] +=1

            trainingPlanAssessmentCounts = ManagerDashboardAssignmentCounts(
                total=assignment_agg_stats_by_training_entity["trainingPlans"]["total"],
                completed=assignment_agg_stats_by_training_entity["trainingPlans"]["completed"],
                inProgress=assignment_agg_stats_by_training_entity["trainingPlans"]["inProgress"],
                notStarted=assignment_agg_stats_by_training_entity["trainingPlans"]["notStarted"],
                overdue=assignment_agg_stats_by_training_entity["trainingPlans"]["overdue"]
            )
            moduleAssessmentCounts = ManagerDashboardAssignmentCounts(
                total=assignment_agg_stats_by_training_entity["modules"]["total"],
                completed=assignment_agg_stats_by_training_entity["modules"]["completed"],
                inProgress=assignment_agg_stats_by_training_entity["modules"]["inProgress"],
                notStarted=assignment_agg_stats_by_training_entity["modules"]["notStarted"],
                overdue=assignment_agg_stats_by_training_entity["modules"]["overdue"]
            )
            simulationAssessmentCounts = ManagerDashboardAssignmentCounts(
                total=assignment_agg_stats_by_training_entity["simulations"]["total"],
                completed=assignment_agg_stats_by_training_entity["simulations"]["completed"],
                inProgress=assignment_agg_stats_by_training_entity["simulations"]["inProgress"],
                notStarted=assignment_agg_stats_by_training_entity["simulations"]["notStarted"],
                overdue=assignment_agg_stats_by_training_entity["simulations"]["overdue"]
            )
            assignmentCounts = ManagerDashboardAggregateAssignmentCounts(
                trainingPlans = trainingPlanAssessmentCounts,
                modules = moduleAssessmentCounts,
                simulations = simulationAssessmentCounts
            )
            
            training_plan_completion_rate = math.ceil((assignment_agg_stats_by_training_entity["trainingPlans"]["completed"] / assignment_agg_stats_by_training_entity["trainingPlans"]["total"])*100)
            module_completion_rate = math.ceil((assignment_agg_stats_by_training_entity["modules"]["completed"] / assignment_agg_stats_by_training_entity["modules"]["total"])*100)
            simulation_completion_rate = math.ceil((assignment_agg_stats_by_training_entity["simulations"]["completed"] / assignment_agg_stats_by_training_entity["simulations"]["total"])*100)

            completionRates = ManagerDashboardAggregateMetrics(
                trainingPlans=training_plan_completion_rate,
                modules=module_completion_rate,
                simulations=simulation_completion_rate
            )  

            averageScores = ManagerDashboardAggregateMetrics(
                trainingPlans=0,
                modules=0,
                simulations=0
            )

            adherenceRates = ManagerDashboardAggregateMetrics(
                trainingPlans=0,
                modules=0,
                simulations=0
            )
            
            logger.info(
                f"Fetched Manager Dashboard data for user_id={user_id}.")
            return ManagerDashboardAggregateDetails(
                assignmentCounts=assignmentCounts,
                completionRates=completionRates,
                adherenceRates=adherenceRates,
                averageScores=averageScores
            )
        except Exception as e:
            logger.error(
                f"Error fetching manager dashboard data for user_id={user_id}: {str(e)}",
                exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching manager dashboard data for user_id={user_id}: {str(e)}")
            

