from typing import Dict, List, Optional , Union
from domain.interfaces.manager_repository import IManagerRepository
from domain.services.assignment_service import AssignmentService
from infrastructure.repositories.manager_repository import ManagerRepository
from infrastructure.database import Database
from api.schemas.requests import PaginationParams
from api.schemas.responses import (FetchManagerDashboardTrainingPlansResponse, 
                                   FetchManagerDashboardModulesResponse, FetchManagerDashboardSimultaionResponse,  ManagerDashboardAggregateAssignmentCounts,
                                   ManagerDashboardAssignmentCounts, ManagerDashboardAggregateDetails, ManagerDashboardAggregateMetrics, TraineeAssignmentAttemptStatus, TrainingEntity,ManagerDashboardTrainingEntityTableResponse)


from fastapi import HTTPException
import math


from utils.logger import Logger  # Make sure the import path is correct for your project


logger = Logger.get_logger(__name__)


class ManagerService:


    def __init__(self, repository: IManagerRepository = None):
        self.db = Database()
        self.repository = ManagerRepository()
        logger.info("ManagerService initialized.")


   
    async def fetch_manager_dashboard_training_plans(self,
                                user_id: str, reporting_userIds: List[str]) -> FetchManagerDashboardTrainingPlansResponse:
            logger.info(f"Fetching manager dashboard training plans for user_id={user_id} and reporting_userIds={reporting_userIds}")
            try:
                dashboard_response = await self.get_all_assigments_by_user_details(user_id, reporting_userIds, 'TrainingPlan')
                training_plans = []


                for trainingPlan in dashboard_response.training_plans:
                    trainees = []
                    for user in trainingPlan.user:
                        trainees.append(FetchManagerDashboardTrainingPlansResponse.TraineeStatus(
                            name=user.user_id,
                            class_id=12344,
                            status=user.status,
                            due_date=user.due_date,
                            avg_score='NA'
                        ))
                    training_plans.append(FetchManagerDashboardTrainingPlansResponse.TrainingPlan(
                        id= trainingPlan.id,
                        name=trainingPlan.name,
                        completion_rate = '0',
                        adherence_rate= '0',
                        avg_score= trainingPlan.average_score,
                        est_time = "15s",
                        trainees= trainees
                    ))


                return FetchManagerDashboardTrainingPlansResponse(training_plans=training_plans)
            except Exception as e:
                logger.error(f"Error fetching manager dashboard training plans: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error fetching manager dashboard training plans: {str(e)}")


    async def fetch_manager_dashboard_modules(self,
                                user_id: str, reporting_userIds: List[str]) -> FetchManagerDashboardTrainingPlansResponse:
            logger.info(f"Fetching manager dashboard modules for user_id={user_id} and reporting_userIds={reporting_userIds}")
            try:
                dashboard_response = await self.get_all_assigments_by_user_details(user_id, reporting_userIds, 'Module')
                modules = []
                for module in dashboard_response.modules:
                    trainees = []
                    for user in module.user:
                        trainees.append(FetchManagerDashboardModulesResponse.TraineeStatus(
                            name=user.user_id,
                            class_id=12344,
                            status=user.status,
                            due_date=user.due_date,
                            avg_score='NA'
                        ))
                    modules.append(FetchManagerDashboardModulesResponse.Module(
                        id= module.id,
                        name=module.name,
                        completion_rate = '0',
                        adherence_rate= '0',
                        avg_score= module.average_score,
                        est_time = "15s",
                        trainees= trainees
                    ))
                return FetchManagerDashboardModulesResponse(modules=modules)
            except Exception as e:
                logger.error(f"Error fetching manager dashboard modules: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error fetching manager dashboard modules: {str(e)}")


    async def fetch_manager_dashboard_simulations(self,
                            user_id: str, reporting_userIds: List[str]) -> FetchManagerDashboardSimultaionResponse:
        logger.info(f"Fetching manager dashboard simulations for user_id={user_id} and reporting_userIds={reporting_userIds}")
        try:
            dashboard_response = await self.get_all_assigments_by_user_details(user_id, reporting_userIds, 'Simulation')
            simulations = []
            for module in dashboard_response.simulations:
                    trainees = []
                    for user in module.user:
                        trainees.append(FetchManagerDashboardSimultaionResponse.TraineeStatus(
                            name=user.user_id,
                            class_id=12344,
                            status=user.status,
                            due_date=user.dueDate,
                            avg_score='NA'
                        ))
                    simulations.append(FetchManagerDashboardSimultaionResponse.Simulation(
                        id= module.id,
                        name=module.name,
                        completion_rate = '0',
                        adherence_rate= '0',
                        avg_score= module.average_score,
                        est_time = "15s",
                        trainees= trainees
                    ))
            return FetchManagerDashboardSimultaionResponse(simulations=simulations)
        except Exception as e:
            logger.error(f"Error fetching manager dashboard simulations: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching manager dashboard simulations: {str(e)}")
   
    async def get_manager_dashboard_data(self, user_id: str, reporting_userIds: List[str]) -> ManagerDashboardAggregateDetails:
        logger.info("Fetching Manager Dashboard data.")
        logger.debug(f"user_id={user_id}")
        try:
            training_plan_data = await self.repository.get_all_assigments_by_user_details(user_id, reporting_userIds, 'TrainingPlan')
            module_data = await self.repository.get_all_assigments_by_user_details(user_id, reporting_userIds, 'Module')
            simulation_data = await self.repository.get_all_assigments_by_user_details(user_id, reporting_userIds, 'Simulation')
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
           
    async def fetch_manager_dashboard_training_entity_data(
        self,
        user_id: str,
        reporting_userIds: List[str],
        assignment_type: str,
        pagination: Optional[PaginationParams] = None
    ) -> ManagerDashboardTrainingEntityTableResponse:
        logger.info(f"Fetching manager dashboard data for user_id={user_id}, type={assignment_type}, and reporting_userIds={reporting_userIds}")

        try:
            dashboard_response = await self.repository.get_all_assigments_by_user_details(user_id, reporting_userIds, assignment_type, pagination)
            # Transform the data into the appropriate response format
            assignment_types = {
                'TrainingPlan': 'training_plans',
                'Module': 'modules',
                'Simulation': 'simulations'
            }

            result_list = []
                
            for item in getattr(dashboard_response, assignment_types[assignment_type], []):
                # Process trainee data for each item
                trainees = []
                for user in item.user:
                    trainee = TraineeAssignmentAttemptStatus(
                        name=user.user_id,
                        class_id=12344,
                        status=user.status,
                        due_date=getattr(user, 'due_date', getattr(user, 'dueDate', None)),
                        avg_score='NA'
                    )
                    trainees.append(trainee)


                # Create the item with its trainees
                result_item = TrainingEntity(
                    id=item.id,
                    name=item.name,
                    completion_rate='0',  
                    adherence_rate='0',  
                    avg_score=item.average_score,
                    est_time='15s',    
                    trainees=trainees
                )
                result_list.append(result_item)


            # Return the response with the transformed data
            return ManagerDashboardTrainingEntityTableResponse(training_entity=result_list, pagination=dashboard_response.pagination)


        except Exception as e:
            logger.error(f"Error fetching manager dashboard {assignment_type.lower()}s: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching manager dashboard {assignment_type.lower()}s: {str(e)}"
            )



