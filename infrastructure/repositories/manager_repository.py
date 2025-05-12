from typing import Dict, List, Optional ,Type, Union
from datetime import datetime
from bson import ObjectId
from domain.interfaces.manager_repository import IManagerRepository
from domain.services.assignment_service import AssignmentService
from infrastructure.database import Database
from api.schemas.requests import PaginationParams
from api.schemas.responses import ( ModuleDetails, SimulationDetails,
    ModuleDetailsByUser, TrainingPlanDetailsByUser, TrainingPlanDetailsMinimal, 
    ModuleDetailsMinimal, FetchManagerDashboardResponse, SimulationDetailsMinimal, 
    SimulationDetailsByUser, PaginationMetadata)

from fastapi import HTTPException
import math

from utils.logger import Logger 
logger = Logger.get_logger(__name__)

class ManagerRepository(IManagerRepository):
    def __init__(self):
        self.db = Database()
        self.assignment_service = AssignmentService()
        logger.info("ManagerRepository initialized.")

    async def get_manager_dashboard_data(self, user_id: str) -> Dict:
        logger.info(f"Fetching manager dashboard data for user_id: {user_id}")
        return {}

    def calculate_simulation_attempts_status(self, user_sim_progress_list, due_date):
        try:
            status = "not_started"
            if user_sim_progress_list:
                statuses = {attempt.get("status", "not_started") for attempt in user_sim_progress_list}
                if "completed" in statuses:
                    completed_only = [attempt for attempt in user_sim_progress_list if attempt.get("status") == "completed"]
                    # Sort the completed attempts by completedAt in ascending order
                    completed_sorted = sorted(
                        completed_only,
                        key=lambda attempt: attempt["completedAt"])
                    # Get the first completed attempt
                    first_item = completed_sorted[0]
                    # Parse both dates
                    completed_at = first_item["completedAt"]
                    assignment_due_date = datetime.strptime(due_date, "%Y-%m-%d")
                    if completed_at > assignment_due_date:
                        status = "completed"
                    else:
                        status = "completed_on_time"
                elif "in_progress" in statuses:
                    status = "in_progress"
            if((status == 'not_started' or status == 'in_progress' ) and datetime.now() > datetime.strptime(due_date, '%Y-%m-%d')):
                status = 'over_due'
            return status
        except Exception as e:
            logger.error(f"Error fetching simulation attempt status: {str(e)}", exc_info=True)
            return "not_started"

    def calculate_simulation_attempts_score(self, user_sim_progress_list):
        try:
            total_attempts_score = 0
            no_of_completed_attempts = 0
            if user_sim_progress_list:
                completed_only = [attempt for attempt in user_sim_progress_list if attempt.get("status") == "completed"]
                total_score = 0
                if completed_only:
                    for attempt in completed_only:
                        if attempt.get("scores"):
                            scores = attempt.get("scores")
                            if scores.get("Sim Accuracy"):
                                sim_accuracy_score = scores.get("Sim Accuracy")
                                total_score += sim_accuracy_score
                            elif scores.get("Keyword Score"):
                                keyword_score = scores.get("Keyword Score")
                                total_score += keyword_score
                            elif scores.get("Click Score"):
                                click_score = scores.get("Click Score")
                                total_score += click_score
                            elif scores.get("Confidence"):
                                confidence_score = scores.get("Confidence")
                                total_score += confidence_score
                            elif scores.get("Energy"):
                                energy_score = scores.get("Energy")
                                total_score += energy_score
                            elif scores.get("Concentration"):
                                concentration_score = scores.get("Concentration")
                                total_score += concentration_score                    
                        total_attempts_score += total_score / len(completed_only)
                        no_of_completed_attempts += 1
            if no_of_completed_attempts > 0:
                return math.ceil(total_attempts_score / no_of_completed_attempts)
            return 0
        except Exception as e:
            logger.error(f"Error calculating simulation attempt score: {str(e)}", exc_info=True)
            return 0

    def calculate_status_modules_and_training_plans(self, status_list: List[str]):
        try:
            if not status_list:
                return "not_started"
            status_set = set(status_list)

            # If "not_started" is present along with any of the progressing/completed statuses, set to "in_progress"
            if "not_started" in status_set and any(
                status in status_set for status in {"completed_on_time", "in_progress"}):
                return "in_progress"
            if status_set == {"completed_on_time"}:
                return "completed_on_time"
            elif status_set.issubset({"completed_on_time", "completed"}):
                return "completed"
            elif "over_due" in status_set:
                return "over_due"
            elif "in_progress" in status_set:
                return "in_progress"
            else:
                return "not_started"
        except Exception as e:
            logger.error(f"Error fetching simulation attempt status: {str(e)}", exc_info=True)
            return "not_started"

    def calculate_single_training_entity_completion_rate(self, status_list: List[str])->Dict[str, int]:
        try:
            if not status_list:
                return {"completion_rate": 0, "adherence_rate": 0}

            total_count = len(status_list)
            completion_count = sum(1 for status in status_list if status in {"completed", "completed_on_time"})
            adherence_count = sum(1 for status in status_list if status == "completed_on_time")

            completion_rate = completion_count / total_count if total_count > 0 else 0
            adherence_rate = adherence_count / completion_count if completion_count > 0 else 0

            return {
                "completion_rate": math.ceil(completion_rate * 100),
                "adherence_rate": math.ceil(adherence_rate * 100)
            }
        except Exception as e:
            logger.error(f"Error calculating single training entity completion percentage: {str(e)}", exc_info=True)
            return {"completion_rate": 0, "adherence_rate": 0}

    def get_team_ids_from_teams(self, teams, unique_teams):
        # Add team members from teamId list
        team_ids = []
        for team in teams:
            team_id = team.get("team_id")
            team_ids.append(team_id)
            if not unique_teams.get(team_id):
                curr_team_members = []
                for member in team.get("team_members", []):
                    team_member_id = member.get("user_id")
                    curr_team_members.append(team_member_id)
                unique_teams[team_id] = curr_team_members
        return team_ids, unique_teams

    def assign_team_member_ids_to_team_id(self, teams, unique_teams):
        for team in teams:
            team_id = team.get("team_id")
            if not unique_teams.get(team_id):
                curr_team_members = []
                for member in team.get("team_members", []):
                    team_member_id = member.get("user_id")
                    curr_team_members.append(team_member_id)
                unique_teams[team_id] = curr_team_members
        return unique_teams

    async def fetch_assignments_by_training_entity(self, user_id: str, reporting_userIds: List[str], reporting_teamIds: List[str],  type: Optional[str], filters: Dict, training_entity_filters: Dict, pagination: Optional[PaginationParams] = None):
        logger.info(f"Fetching assignments by training entity for user_id: {user_id}")
        try:
            # Fetch assignments
            assignmentWithUsersAndTeamsObj = {}
            assignmentWithUsersAndTeamsList = []
            unique_teams = {}
            query = {}
            # --- Training Entity Filtering ---
            training_entity_query = {}
            # Set pagination parameters
            pagination_params = PaginationMetadata(total_count=0, page=0, pagesize=0, total_pages=0)
            if pagination:
                page = pagination.page
                pagesize = pagination.pagesize
                skip = ((page + 1) - 1) * pagesize
                total_count = 0
                pagination_params = PaginationMetadata(total_count=0, page=page, pagesize=pagesize, total_pages=0)

            if type:
                query["type"] = type

            or_conditions = []
            # Add traineeIds condition if reporting_userIds is provided
            if reporting_userIds:
                or_conditions.append({"traineeId": {"$in": reporting_userIds}})

            # Add teamIds condition if reporting_teamIds is provided
            all_team_ids = []
            # Handle createdBy filter for Training Plans or Modules or Simualtions Collections
            if training_entity_filters.get("team_ids"):
                all_team_ids.extend(training_entity_filters["team_ids"])
            else:
                if reporting_teamIds:
                    all_team_ids.extend(reporting_teamIds)

            if all_team_ids:
                or_conditions.append({
                    "teamId": {
                        "$elemMatch": {
                            "team_id": {"$in": all_team_ids}
                        }
                    }
                })

            if or_conditions:
                query["$or"] = or_conditions

            # Handle date filters on createdAt for Assignments Collection
            if filters.get("start_date") or filters.get("end_date"):
                date_filter = {}
                if filters.get("start_date"):
                    start_date = datetime.strptime(filters.get("start_date"), "%Y-%m-%d")
                    date_filter["$gte"] = start_date
                if filters.get("end_date"):
                    end_date = datetime.strptime(filters.get("end_date"), "%Y-%m-%d")
                    date_filter["$lte"] = end_date
                query["createdAt"] = date_filter

            # Handle date filters on createdAt for Training Plans or Modules or Simualtions Collections
            if training_entity_filters.get("start_date") or training_entity_filters.get("end_date"):
                entity_date_filter = {}
                if training_entity_filters.get("start_date"):
                    entity_date_filter["$gte"] = datetime.strptime(training_entity_filters["start_date"], "%Y-%m-%d")
                if training_entity_filters.get("end_date"):
                    entity_date_filter["$lte"] = datetime.strptime(training_entity_filters["end_date"], "%Y-%m-%d")
                training_entity_query["createdAt"] = entity_date_filter

            # Handle createdBy filter for Training Plans or Modules or Simualtions Collections
            if training_entity_filters.get("created_by"):
                training_entity_query["createdBy"] =  {"$in": training_entity_filters["created_by"]}
            # Handle search query filter
            search_query = training_entity_filters.get("training_entity_search_query")
            if search_query:
                # Use regex for partial matching (case-insensitive)
                search_regex = {"$regex": search_query, "$options": "i"}

                # Attempt to convert search query to ObjectId if valid
                object_id_query = None
                try:
                    object_id_query = ObjectId(search_query)
                except Exception:
                    # If conversion fails, skip adding the `_id` condition
                    pass

                # Apply search query to both `name` and `_id` fields
                search_conditions = [{"name": search_regex}]
                if object_id_query:
                    search_conditions.append({"_id": object_id_query})

                training_entity_query["$or"] = search_conditions

            # Fetch training entity IDs based on filters
            if type and type == "TrainingPlan":
                matching_training_plan_ids = await self.db.training_plans.distinct("_id", training_entity_query)
                matching_training_plan_ids_str = [str(id) for id in matching_training_plan_ids]

                # Filter assignments using matching training plan IDs
                query["id"] = {"$in": matching_training_plan_ids_str}
            elif type and type == "Module":
                matching_module_ids = await self.db.modules.distinct("_id", training_entity_query)
                matching_module_ids_str = [str(id) for id in matching_module_ids]

                # Filter assignments using matching module IDs
                query["id"] = {"$in": matching_module_ids_str}
            elif type and type == "Simulation":
                matching_simulation_ids = await self.db.simulations.distinct("_id", training_entity_query)
                matching_simulation_ids_str = [str(id) for id in matching_simulation_ids]

                # Filter assignments using matching simulation IDs
                query["id"] = {"$in": matching_simulation_ids_str}

            final_query = query.copy()
            if pagination:
                # Get all unique training plan IDs matching filter
                unique_training_entity_ids = await self.db.assignments.distinct("id", query)
                total_count = len(unique_training_entity_ids)

                # Apply pagination to the IDs
                paginated_ids = unique_training_entity_ids[skip:skip + pagesize]
                final_query["id"] = {"$in": paginated_ids}

            assignments = await self.db.assignments.find(final_query).to_list()
            for assignment in assignments:
                self.assign_team_member_ids_to_team_id(assignment["teamId"], unique_teams)
                if assignmentWithUsersAndTeamsObj.get(assignment["id"]):
                    assignmentWithUsersAndTeamsObj.get(assignment["id"]).append(assignment)
                else:
                    assignmentWithUsersAndTeamsObj[assignment["id"]] = [assignment]

            unique_user_id_by_assignment = {}
            unique_team_id_by_assignment = {}
            assignmentWithUserAttemptsByAssignmentId = {}

            for assignment_id, assigned_assignments in assignmentWithUsersAndTeamsObj.items():
                if not assignmentWithUserAttemptsByAssignmentId.get(assignment_id):
                    assignmentWithUserAttemptsByAssignmentId[assignment_id] = []
                for assignment in assigned_assignments:
                    if not unique_user_id_by_assignment.get(assignment_id):
                        unique_user_id_by_assignment[assignment_id] = []
                    if not unique_team_id_by_assignment.get(assignment_id):
                        unique_team_id_by_assignment[assignment_id] = []

                    # Removing duplicates- if same user has been assigned same training entity before then its not considered 
                    user_ids_not_previously_assigned = []
                    for each_trainee_id in assignment["traineeId"]:
                        if each_trainee_id not in unique_user_id_by_assignment[assignment_id]:
                            user_ids_not_previously_assigned.append(each_trainee_id)
                            unique_user_id_by_assignment[assignment_id].append(each_trainee_id)

                    # Removing duplicates- if same team has been assigned same training entity before then its not considered 
                    team_ids_not_previously_assigned = []

                    for each_team in assignment["teamId"]:
                        if each_team.get("team_id") not in unique_team_id_by_assignment[assignment_id]:
                            team_ids_not_previously_assigned.append(each_team.get("team_id"))
                            unique_team_id_by_assignment[assignment_id].append(each_team.get("team_id"))

                    # Filtering out the trainees that are not reporting to the manager
                    common_trainee_ids = set(user_ids_not_previously_assigned).intersection(reporting_userIds)
                    filtered_trainee_ids = list(common_trainee_ids) if common_trainee_ids else []

                    # Filtering out the teams that are not reporting to the manager
                    common_team_ids = set(team_ids_not_previously_assigned).intersection(all_team_ids)
                    filtered_team_ids = list(common_team_ids) if common_team_ids else []

                    # Add all filtered teams members to the filtered trainee list and also check dupliacates if a certain team member has been assigned same training entity before
                    for team_id in filtered_team_ids:
                        if unique_teams.get(team_id):
                            team_members_ids = unique_teams[team_id]
                            for each_member_id in team_members_ids:
                                if each_member_id not in filtered_trainee_ids:
                                    filtered_trainee_ids.append(each_member_id)

                    assignment.update({
                        "traineeId": filtered_trainee_ids,
                        "team_ids": filtered_team_ids
                    })
                    #assignmentWithUsersAndTeamsObj[assignment_id] = assignment
                    #assignmentWithUsersAndTeamsList.append(assignment)
                    assignmentWithUserAttemptsByAssignmentId[assignment_id].append(assignment)

            if pagination:
                pagination_params.total_count = total_count
                pagination_params.total_pages = math.ceil(total_count / pagination_params.pagesize)

            return assignmentWithUserAttemptsByAssignmentId, unique_teams, pagination_params
        except Exception as e:
            logger.error(f"Error fetching assignments by training entity: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching assignments by training entity: {str(e)}")

    async def get_simulation_stats(self, sim_id: str, assignment_id: str, user_id: str, due_date: str):
        try:
            sim = await self.db.simulations.find_one({"_id": ObjectId(sim_id)})
            if not sim:
                logger.warning(f"Simulation {sim_id} not found.")
                return None
            # Fetch **all** user simulation progress rows for this sim + assignment
            progress_list = await self.db.user_sim_progress.find({
                "userId": user_id,
                "assignmentId": assignment_id,
                "simulationId":sim_id
            }).to_list(None)

            # Determine status with precedence: completed > in_progress > not_started
            status = self.calculate_simulation_attempts_status(progress_list, due_date)
            logger.debug(
                f"Simulation {sim_id} retrieved with consolidated status {status}"
            )
            # Getting scores
            # TODO: Ask do we need the latest attempt response score?
            scores = {}
            avg_score_attempts = self.calculate_simulation_attempts_score(progress_list)

            return SimulationDetailsByUser(
                simulation_id=str(sim["_id"]),
                name=sim.get("name", ""),
                type=sim.get("type", ""),
                level= "beginner",
                est_time=sim.get("estimatedTimeToAttemptInMins", 0),
                dueDate=due_date,
                status=status,
                scores=scores,
                highest_attempt_score=0,
                average_score=avg_score_attempts,
                assignment_id=assignment_id,
                user_id=user_id
            )

        except Exception as e:
            logger.error(f"Error fetching simulation stats: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching simulation stats: {str(e)}")

    async def get_module_stats(self, module_id, assignment_id, user_id, due_date):
        try:
            module = await self.db.modules.find_one({"_id": ObjectId(module_id)})
            if not module:
                logger.warning(f"Module {module_id} not found.")
                return None

            module_simulations = []
            module_sim_statuses = []
            module_sim_scores = []
            total_module_est_time = 0
            for sim_id in module.get("simulationIds", []):
                sim_details = await self.get_simulation_stats(sim_id, assignment_id, user_id, due_date)
                if sim_details:
                    module_simulations.append(sim_details)
                    module_sim_statuses.append(sim_details.status)
                    module_sim_scores.append(sim_details.average_score)
                    total_module_est_time += sim_details.est_time

            # Determine module status
            module_status = self.calculate_status_modules_and_training_plans(module_sim_statuses)

            # Determine module completion and adherence percentage
            module_completion_rate = self.calculate_single_training_entity_completion_rate(module_sim_statuses)

            # Determine module average score
            module_average_score = sum(module_sim_scores) / len(module_sim_scores) if module_sim_scores else 0

            logger.debug(
                f"Module {module_id} has {len(module_simulations)} simulation(s) with status={module_status}"
            )

            return ModuleDetailsByUser(
                name=module.get("name", ""),
                total_simulations=len(module_simulations),
                average_score=module_average_score,
                due_date=due_date,
                status=module_status,
                user_id=user_id,
                simulations=module_simulations,
                completion_percentage=module_completion_rate["completion_rate"],
                adherence_percentage=module_completion_rate["adherence_rate"],
                est_time=total_module_est_time
            )
        except Exception as e:
            logger.error(f"Error fetching module stats: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching module stats: {str(e)}")

    async def get_training_plan_stats(self, assignment, userId):
        try:
            training_plan = await self.db.training_plans.find_one({"_id": ObjectId(assignment["id"])})
            if training_plan:
                plan_modules = []
                plan_total_simulations = 0
                plan_est_time = 0
                plan_simulations = []
                for added_obj in training_plan.get("addedObject", []):
                    if added_obj["type"] == "module":
                        module_details = await self.get_module_stats(added_obj["id"], str(assignment["_id"]), userId, assignment["endDate"])
                        if module_details:
                            plan_modules.append(module_details)
                            plan_total_simulations += module_details.total_simulations
                            plan_est_time += module_details.est_time

                    elif added_obj["type"] == "simulation":
                        sim_details = await self.get_simulation_stats(added_obj["id"], str(assignment["_id"]), userId, assignment["endDate"])
                        if sim_details:
                            plan_simulations.append(sim_details)
                            plan_total_simulations += 1
                            plan_est_time += sim_details.est_time

                modules_statuses = [mod.status for mod in plan_modules]
                simulations_statuses = [sim.status for sim in plan_simulations]
                tp_children_statuses = modules_statuses + simulations_statuses

                # Determine Training Plan status
                plan_status = self.calculate_status_modules_and_training_plans(tp_children_statuses)

                # Determine Training Plan completion and adherence percentage
                plan_completion_rate = self.calculate_single_training_entity_completion_rate(tp_children_statuses)

                # Determine Training Plan average score
                plan_average_score = (sum(sim.average_score for sim in plan_simulations) + sum(mod.average_score for mod in plan_modules)) / (len(plan_simulations) + len(plan_modules)) if plan_simulations or plan_modules else 0

                return TrainingPlanDetailsByUser(
                    name=training_plan.get("name", ""),
                    completion_percentage=plan_completion_rate["completion_rate"],
                    adherence_percentage=plan_completion_rate["adherence_rate"],
                    total_modules=len(plan_modules),
                    total_simulations=plan_total_simulations,
                    est_time=plan_est_time,
                    average_score=plan_average_score,
                    due_date=assignment["endDate"],
                    status=plan_status,
                    user_id=userId,
                    modules=plan_modules,
                    simulations=plan_simulations
                )
            return None
        except Exception as e:
            logger.error(f"Error fetching training plan stats: {str(e)}", exc_info=True)
            return None

    async def get_all_assigments_by_user_details(self,
        user_id: str, reporting_userIds: List[str], type: str, 
        pagination: Optional[PaginationParams] = None) -> FetchManagerDashboardResponse:
        """Get All Assignments By User Details

        Returns:
            FetchManagerDashboardResponse containing training plans, modules, and simulations
        """
        logger.info(f"Get All Assignments By User Details user_id={user_id}, reporting_userIds={reporting_userIds}")
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
                            #assignment['teamId'] = assignment['teamId']
                            assignment["_id"] = str(assignment["_id"])
                            assignmentWithUsers.append(assignment)
                        else:
                            for assignmentWithUser in assignmentWithUsers:
                                if assignmentWithUser["id"] == assignment["id"]:
                                    assignmentWithUser["teamId"] = assignment['teamId'] + assignmentWithUser["teamId"]
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
                                simulations=[]
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

