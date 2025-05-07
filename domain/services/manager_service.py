from typing import Dict, List, Optional , Union
from domain.interfaces.manager_repository import IManagerRepository
from infrastructure.repositories.manager_repository import ManagerRepository
from infrastructure.database import Database
from api.schemas.requests import ManagerDashboardParams, PaginationParams
from api.schemas.responses import (ManagerDashboardAggregateAssignmentCounts,
    ManagerDashboardAssignmentCounts, ManagerDashboardAggregateDetails, ManagerDashboardAggregateMetrics,
    ManagerDashboardLeaderBoardsAggMetricWise, ManagerDashboardTeamWiseAggregateMetrics,
    TraineeAssignmentAttemptStatus, TrainingEntity, ManagerDashboardTrainingEntityTableResponse, TrainingPlanDetailsByUser,
    TrainingPlanDetailsMinimal, ModuleDetailsMinimal, FetchManagerDashboardResponse,
    ModuleDetailsByUser, SimulationDetailsByUser,
    SimulationDetailsMinimal)
from fastapi import HTTPException
import math
from utils.logger import Logger  # Make sure the import path is correct for your project

logger = Logger.get_logger(__name__)
class ManagerService:
    def __init__(self, repository: IManagerRepository = None):
        self.db = Database()
        self.repository = ManagerRepository()
        logger.info("ManagerService initialized.")
    
    def assign_training_entity_stats_agg_metrics(self, assignment_agg_stats_by_training_entity, training_entity: str, training_entity_list):
        for each_assigned_training_entity in training_entity_list:
            for each_assigned_user in each_assigned_training_entity.user:
                assignment_agg_stats_by_training_entity[training_entity]["total"] +=1
                assignment_agg_stats_by_training_entity[training_entity]["average_score"] += each_assigned_user.average_score
                if each_assigned_user.status == "completed_on_time":
                    assignment_agg_stats_by_training_entity[training_entity]["completed_on_time"] +=1
                if each_assigned_user.status == "completed" or each_assigned_user.status == "completed_on_time":
                    assignment_agg_stats_by_training_entity[training_entity]["completed"] +=1
                elif each_assigned_user.status == "in_progress":
                    assignment_agg_stats_by_training_entity[training_entity]["inProgress"] +=1
                elif each_assigned_user.status == "not_started":
                    assignment_agg_stats_by_training_entity[training_entity]["notStarted"] +=1
                elif each_assigned_user.status == "over_due":
                    assignment_agg_stats_by_training_entity[training_entity]["overdue"] +=1
    
    def get_training_entity_assessment_counts(self, assignment_agg_stats_by_training_entity, training_entity: str):
        return ManagerDashboardAssignmentCounts(
            total=assignment_agg_stats_by_training_entity[training_entity]["total"],
            completed=assignment_agg_stats_by_training_entity[training_entity]["completed"],
            inProgress=assignment_agg_stats_by_training_entity[training_entity]["inProgress"],
            notStarted=assignment_agg_stats_by_training_entity[training_entity]["notStarted"],
            overdue=assignment_agg_stats_by_training_entity[training_entity]["overdue"]
        )
    
    def get_completion_rate_or_adherence_rate(self, assignment_type: str, agg_metrics: Dict, metric: str):
        if metric == "completion_rate":
            if agg_metrics.get(assignment_type).get("total") > 0:
                return math.ceil((agg_metrics.get(assignment_type).get("completed") / agg_metrics.get(assignment_type).get("total"))*100)
            else:
                return 0
        elif metric == "adherence_rate":
            if agg_metrics.get(assignment_type).get("completed") > 0:
                return math.ceil((agg_metrics.get(assignment_type).get("completed_on_time") / agg_metrics.get(assignment_type).get("completed"))*100)
            else:
                return 0
        return 0
    
    async def get_assigments_attempt_stats_by_training_entity(self,
        user_id: str, reporting_userIds: List[str], reporting_teamIds: List[str], type: str,
        filters: Dict, training_entity_filters: Dict, pagination: Optional[PaginationParams] = None) -> FetchManagerDashboardResponse:
        """Get All Assignments By User Details
        
        Returns:
            FetchManagerDashboardResponse containing training plans, modules, and simulations
        """
        logger.info(f"Get All Assignments By User Details user_id={user_id}, reporting_userIds={reporting_userIds}")
        if pagination:
            logger.info(f"Pagination={pagination}")
        
        try:
            assignmentWithUsers = []
            assignmentWithUsers, unique_teams, pagination_params = await self.repository.fetch_assignments_by_training_entity(user_id, reporting_userIds, reporting_teamIds, type, filters, training_entity_filters, pagination)
            training_plans = []
            modules = []
            simulations = []
            total_simulations = 0
            # key - user_id, value - list of training plan, module, simulation details progress by user
            user_map: Dict[str, List[Union[TrainingPlanDetailsByUser, ModuleDetailsByUser, SimulationDetailsByUser]]] = {}

            for assignment in assignmentWithUsers:
                logger.debug(f"Processing assignment: {assignment}")
                if assignment["type"] == "TrainingPlan":
                    training_plans_by_user = []
                    training_plan_name = ""
                    for userId in assignment['traineeId']:
                        training_plan_user_stats = await self.repository.get_training_plan_stats(assignment, userId)
                        if training_plan_user_stats:
                            if user_map.get(userId):
                                user_map[userId].append(training_plan_user_stats)
                            else:
                                user_map[userId] = [training_plan_user_stats]
                            if training_plan_name == "":
                                training_plan_name = getattr(training_plan_user_stats, "name", "")
                            training_plans_by_user.append(training_plan_user_stats)
                    training_plans.append(
                        TrainingPlanDetailsMinimal(
                            id=assignment["id"],
                            name=training_plan_name,
                            completion_percentage=0,
                            average_score=0,
                            user=training_plans_by_user
                        ))
                elif assignment["type"] == "Module":
                    module_by_user_stats = []
                    for userId in assignment['traineeId']:
                        module_details = await self.repository.get_module_stats(assignment["id"], str(assignment["_id"]), userId, assignment["endDate"])
                        if module_details:
                            module_by_user_stats.append(module_details)
                            if user_map.get(userId):
                                user_map[userId].append(module_by_user_stats)
                            else:
                                user_map[userId] = [module_by_user_stats]
                    modules.append(
                        ModuleDetailsMinimal(
                            id=assignment["id"],
                            name=module_details.name,
                            completion_percentage=0,
                            average_score=module_details.average_score,
                            user=module_by_user_stats
                        )
                    )       
                elif assignment["type"] == "Simulation":
                    simulation_by_user_stats = []
                    for userId in assignment['traineeId']:
                        sim_details = await self.repository.get_simulation_stats(assignment["id"], str(assignment["_id"]), userId, assignment["endDate"])
                        if sim_details:
                            simulation_by_user_stats.append(sim_details)
                            total_simulations += 1
                            if user_map.get(userId):
                                user_map[userId].append(simulation_by_user_stats)
                            else:
                                user_map[userId] = [simulation_by_user_stats]
                    simulations.append(
                        SimulationDetailsMinimal(
                            id=sim_details.simulation_id,
                            name=sim_details.name,
                            completion_percentage=0,
                            average_score=sim_details.highest_attempt_score,
                            user=simulation_by_user_stats
                        )
                    )
            if not pagination:
                # key - team_id, value - list of training plan, module, simulation details progress by each of the team members
                team_wise_stats: Dict[str, List[Union[TrainingPlanDetailsByUser, ModuleDetailsByUser, SimulationDetailsByUser]]] = {}
                for assignment in assignmentWithUsers:
                    if assignment.get("team_ids"):
                        for team_id in assignment.get("team_ids"):
                            if unique_teams.get(team_id):
                                for team_member_id in unique_teams[team_id]:
                                    if user_map.get(team_member_id):
                                        if team_wise_stats.get(team_id):
                                            team_wise_stats[team_id].extend(user_map[team_member_id])
                                        else:
                                            team_wise_stats[team_id] = user_map[team_member_id]
            # Add pagination metadata if pagination is provided
            if pagination:
                logger.info(f"Pagination metadata: {pagination_params}")
                return FetchManagerDashboardResponse(
                    training_plans=training_plans, 
                    modules=modules, 
                    simulations=simulations, 
                    pagination=pagination_params
                )
            else:
                # Return response without pagination metadata
                return FetchManagerDashboardResponse(
                    training_plans=training_plans, 
                    modules=modules, 
                    simulations=simulations,
                    teams_stats=team_wise_stats
                )
            
        except Exception as e:
            logger.error(f"Error Getting All Assignment By User Details {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error Getting All Assignment By User Details {str(e)}")

    
    async def get_manager_dashboard_data(self, user_id: str, reporting_userIds: List[str], reporting_teamIds: List[str], params: ManagerDashboardParams) -> ManagerDashboardAggregateDetails:
        logger.info("Fetching Manager Dashboard data.")
        logger.debug(f"user_id={user_id}")
        try:
            global_filters = {}
            if params:
                if params.assignedDateRange:
                    global_filters["start_date"] = params.assignedDateRange.startDate
                    global_filters["end_date"] = params.assignedDateRange.endDate
            training_entity_data = await self.get_assigments_attempt_stats_by_training_entity(user_id, reporting_userIds, reporting_teamIds, None, global_filters, {}, None)
            assignment_agg_stats_by_training_entity = {
                "trainingPlans": {
                    "total": 0,
                    "completed": 0,
                    "inProgress": 0,
                    "notStarted": 0,
                    "overdue": 0,
                    "completed_on_time": 0,
                    "average_score": 0
                },
                "modules": {
                    "total": 0,
                    "completed": 0,
                    "inProgress": 0,
                    "notStarted": 0,
                    "overdue": 0,
                    "completed_on_time": 0,
                    "average_score": 0
                },
                "simulations": {
                    "total": 0,
                    "completed": 0,
                    "inProgress": 0,
                    "notStarted": 0,
                    "overdue": 0,
                    "completed_on_time": 0,
                    "average_score": 0
                }
            }
            self.assign_training_entity_stats_agg_metrics(assignment_agg_stats_by_training_entity, "trainingPlans", training_entity_data.training_plans)
            self.assign_training_entity_stats_agg_metrics(assignment_agg_stats_by_training_entity, "modules", training_entity_data.modules)
            self.assign_training_entity_stats_agg_metrics(assignment_agg_stats_by_training_entity, "simulations", training_entity_data.simulations)
            
            trainingPlanAssessmentCounts = self.get_training_entity_assessment_counts(assignment_agg_stats_by_training_entity, "trainingPlans")
            moduleAssessmentCounts = self.get_training_entity_assessment_counts(assignment_agg_stats_by_training_entity, "modules")
            simulationAssessmentCounts = self.get_training_entity_assessment_counts(assignment_agg_stats_by_training_entity, "simulations")

            assignmentCounts = ManagerDashboardAggregateAssignmentCounts(
                trainingPlans = trainingPlanAssessmentCounts,
                modules = moduleAssessmentCounts,
                simulations = simulationAssessmentCounts
            )

            training_plan_completion_rate = self.get_completion_rate_or_adherence_rate("trainingPlans", assignment_agg_stats_by_training_entity, "completion_rate")
            module_completion_rate = self.get_completion_rate_or_adherence_rate("modules", assignment_agg_stats_by_training_entity, "completion_rate")
            simulation_completion_rate = self.get_completion_rate_or_adherence_rate("simulations", assignment_agg_stats_by_training_entity, "completion_rate")

            training_plan_adherence_rate = self.get_completion_rate_or_adherence_rate("trainingPlans", assignment_agg_stats_by_training_entity, "adherence_rate")
            module_adherence_rate = self.get_completion_rate_or_adherence_rate("modules", assignment_agg_stats_by_training_entity, "adherence_rate")
            simulation_adherence_rate = self.get_completion_rate_or_adherence_rate("simulations", assignment_agg_stats_by_training_entity, "adherence_rate")
            

            completionRates = ManagerDashboardAggregateMetrics(
                trainingPlans=training_plan_completion_rate,
                modules=module_completion_rate,
                simulations=simulation_completion_rate
            )

            training_plans_average_score = 0
            modules_average_score = 0
            simulations_average_score = 0

            if assignment_agg_stats_by_training_entity["trainingPlans"]["total"] > 0:
                training_plans_average_score = math.ceil(assignment_agg_stats_by_training_entity["trainingPlans"]["average_score"]/assignment_agg_stats_by_training_entity["trainingPlans"]["total"])
            if assignment_agg_stats_by_training_entity["modules"]["total"] > 0:
                modules_average_score = math.ceil(assignment_agg_stats_by_training_entity["modules"]["average_score"]/assignment_agg_stats_by_training_entity["modules"]["total"])
            if assignment_agg_stats_by_training_entity["simulations"]["total"] > 0:
                simulations_average_score = math.ceil(assignment_agg_stats_by_training_entity["simulations"]["average_score"]/assignment_agg_stats_by_training_entity["simulations"]["total"])
            

            averageScores = ManagerDashboardAggregateMetrics(
                trainingPlans=training_plans_average_score,
                modules=modules_average_score,
                simulations=simulations_average_score 
            )

            adherenceRates = ManagerDashboardAggregateMetrics(
                trainingPlans=training_plan_adherence_rate,
                modules=module_adherence_rate,
                simulations=simulation_adherence_rate
            )

            team_wise_metric_stats = {}
            for teamId, team_user_assignments in training_entity_data.teams_stats.items():
                team_agg_status = {
                    "total": 0,
                    "completed": 0,
                    "inProgress": 0,
                    "notStarted": 0,
                    "overdue": 0,
                    "completed_on_time": 0
                }
                team_assignments_average_scores_list = []
                for each_user_assignment in team_user_assignments:
                    team_assignments_average_scores_list.append(each_user_assignment.average_score)
                    team_agg_status["total"] +=1
                    if each_user_assignment.status == "completed_on_time":
                        team_agg_status["completed_on_time"] +=1
                    if each_user_assignment.status == "completed" or each_user_assignment.status == "completed_on_time":
                        team_agg_status["completed"] +=1
                    elif each_user_assignment.status == "in_progress":
                        team_agg_status["inProgress"] +=1
                    elif each_user_assignment.status == "not_started":
                        team_agg_status["notStarted"] +=1
                    elif each_user_assignment.status == "over_due":
                        team_agg_status["overdue"] +=1
                completion_rate = 0
                adherence_rate = 0
                average_score = 0
                if team_agg_status["total"] > 0:
                    completion_rate = math.ceil((team_agg_status.get("completed") / team_agg_status.get("total"))*100)
                if team_agg_status["completed"] > 0:
                    adherence_rate = math.ceil((team_agg_status.get("completed_on_time") / team_agg_status.get("completed"))*100)
                if len(team_assignments_average_scores_list) > 0:
                    average_score = math.ceil(sum(team_assignments_average_scores_list) / len(team_assignments_average_scores_list))
                
                if team_wise_metric_stats.get("completion_rate"):
                    team_wise_metric_stats["completion_rate"].append(ManagerDashboardTeamWiseAggregateMetrics(team=teamId,score=completion_rate))
                else:
                    team_wise_metric_stats["completion_rate"] = [ManagerDashboardTeamWiseAggregateMetrics(team=teamId,score=completion_rate)]
                
                if team_wise_metric_stats.get("adherence_rate"):
                    team_wise_metric_stats["adherence_rate"].append(ManagerDashboardTeamWiseAggregateMetrics(team=teamId,score=adherence_rate))
                else:
                    team_wise_metric_stats["adherence_rate"] = [ManagerDashboardTeamWiseAggregateMetrics(team=teamId,score=adherence_rate)]
                
                if team_wise_metric_stats.get("average_score"):
                    team_wise_metric_stats["average_score"].append(ManagerDashboardTeamWiseAggregateMetrics(team=teamId,score=average_score))
                else:
                    team_wise_metric_stats["average_score"] = [ManagerDashboardTeamWiseAggregateMetrics(team=teamId,score=average_score)]
            
            if team_wise_metric_stats.get("completion_rate"):
                sorted_team_wise_completion_rate_metric = sorted(team_wise_metric_stats["completion_rate"], key=lambda team: team.score, reverse=True)
            else:
                sorted_team_wise_completion_rate_metric = []
            
            if team_wise_metric_stats.get("adherence_rate"):
                sorted_team_wise_adherence_rate_metric = sorted(team_wise_metric_stats["adherence_rate"], key=lambda team: team.score, reverse=True)
            else:
                sorted_team_wise_adherence_rate_metric = []
            
            if team_wise_metric_stats.get("average_score"):
                sorted_team_wise_average_score_metric = sorted(team_wise_metric_stats["average_score"], key=lambda team: team.score, reverse=True)
            else:
                sorted_team_wise_average_score_metric = []
            
            leaderBoards = ManagerDashboardLeaderBoardsAggMetricWise(
                completion=sorted_team_wise_completion_rate_metric,
                averageScore=sorted_team_wise_average_score_metric,
                adherence=sorted_team_wise_adherence_rate_metric
            )
           
            logger.info(
                f"Fetched Manager Dashboard data for user_id={user_id}.")
            return ManagerDashboardAggregateDetails(
                assignmentCounts=assignmentCounts,
                completionRates=completionRates,
                adherenceRates=adherenceRates,
                averageScores=averageScores,
                leaderBoards=leaderBoards
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
        reporting_teamIds: List[str],
        assignment_type: str,
        params: Optional[ManagerDashboardParams] = None,
        pagination: Optional[PaginationParams] = None
    ) -> ManagerDashboardTrainingEntityTableResponse:
        logger.info(f"Fetching manager dashboard data for user_id={user_id}, type={assignment_type}, and reporting_userIds={reporting_userIds}")
        try:
            global_filters = {}
            training_entity_filters = {}
            if params:
                if params.assignedDateRange:
                    global_filters["start_date"] = params.assignedDateRange.startDate
                    global_filters["end_date"] = params.assignedDateRange.endDate
                if params.trainingEntityDateRange:
                    training_entity_filters["start_date"] = params.trainingEntityDateRange.startDate
                    training_entity_filters["end_date"] = params.trainingEntityDateRange.endDate
                if params.trainingEntityCreatedBy:
                    training_entity_filters["created_by"] = params.trainingEntityCreatedBy
                if params.trainingEntityTeams:
                    training_entity_filters["team_ids"] = params.trainingEntityTeams
            
            if not pagination and assignment_type:
                pagination = PaginationParams(page=1, pagesize=5)

            dashboard_response = await self.get_assigments_attempt_stats_by_training_entity(user_id, reporting_userIds, reporting_teamIds, assignment_type, global_filters, training_entity_filters, pagination)
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
                statuses = []
                user_attempt_scores = []
                total_est_time = 0
                for user in item.user:
                    trainee = TraineeAssignmentAttemptStatus(
                        name=user.user_id,
                        classId=12344,
                        status="completed" if user.status == "completed_on_time" else user.status,
                        dueDate=getattr(user, 'due_date', getattr(user, 'dueDate', None)),
                        avgScore=user.average_score
                    )
                    trainees.append(trainee)
                    statuses.append(user.status)
                    user_attempt_scores.append(user.average_score)
                    total_est_time += user.est_time
                assigned_trainees = len(trainees)
                # Create the item with its trainees
                total_completed_count = sum(1 for status in statuses if status in {"completed", "completed_on_time"})
                total_completed_on_time_count = sum(1 for status in statuses if status == "completed_on_time")
                completion_rate = total_completed_count / assigned_trainees if assigned_trainees > 0 else 0
                adherence_rate = total_completed_on_time_count / total_completed_count if total_completed_count > 0 else 0
                completion_rate_percent = math.ceil(completion_rate * 100)
                adherence_rate_percent = math.ceil(adherence_rate * 100)
                avg_score = math.ceil(sum(user_attempt_scores) / len(user_attempt_scores)) if user_attempt_scores else 0

                result_item = TrainingEntity(
                    id=item.id,
                    name=item.name,
                    completionRate=completion_rate_percent,  
                    adherenceRate=adherence_rate_percent,  
                    avgScore=avg_score,
                    estTime=total_est_time,    
                    trainees=trainees,
                    assignedTrainees=assigned_trainees
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



