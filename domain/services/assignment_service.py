from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from infrastructure.database import Database
from api.schemas.requests import (CreateAssignmentRequest, PaginationParams)
from api.schemas.responses import (AssignmentData, FetchAssignmentsResponse,
                                   FetchAssignedPlansResponse,
                                   TrainingPlanDetails, ModuleDetails,
                                   SimulationDetails, Stats, StatsData,
                                   PaginationMetadata)
from fastapi import HTTPException

from utils.logger import Logger

logger = Logger.get_logger(__name__)


class AssignmentService:

    def __init__(self):
        self.db = Database()
        logger.info("AssignmentService initialized.")

    # New method in your service class
    async def assignment_name_exists(self, name: str, workspace: str) -> bool:
        """Check if a assignment with the given name already exists in the workspace"""
        logger.info(
            f"Checking if assignment name '{name}' exists in workspace {workspace}"
        )
        try:
            # Query the database for assignment with the same name in the workspace
            count = await self.db.assignments.count_documents({
                "name":
                name,
                "workspace":
                workspace
            })
            return count > 0
        except Exception as e:
            logger.error(f"Error checking assignment name existence: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error checking assignment name: {str(e)}")

    async def create_assignment(self, request: CreateAssignmentRequest,
                                workspace: str) -> Dict:
        """Create a new assignment"""
        logger.info("Received request to create a new assignment.")
        logger.debug(
            f"Assignment request data: {request.dict()}, workspace: {workspace}"
        )
        try:
            # Check if a assignment with this name already exists in the workspace
            name_exists = await self.assignment_name_exists(
                request.name, workspace)
            if name_exists:
                logger.warning(
                    f"Assignment with name '{request.name}' already exists in workspace {workspace}"
                )
                # Return a specific error for duplicate names
                return {
                    "status": "error",
                    "message": "Assignment with this name already exists",
                }

            assignment_doc = {
                "id": request.id,
                "name": request.name,
                "type": request.type,
                "startDate": request.start_date,
                "endDate": request.end_date,
                "teamId": [team.dict() for team in request.team_id],
                "traineeId": request.trainee_id,
                "createdBy": request.user_id,
                "createdAt": datetime.utcnow(),
                "lastModifiedBy": request.user_id,
                "lastModifiedAt": datetime.utcnow(),
                "status": "published",
                "workspace": workspace
            }

            result = await self.db.assignments.insert_one(assignment_doc)
            assignment_id = str(result.inserted_id)
            logger.info(f"Assignment inserted with ID: {assignment_id}")

            # Process trainee IDs
            for trainee_id in request.trainee_id:
                logger.debug(
                    f"Processing trainee_id={trainee_id} for assignment={assignment_id}"
                )
                await self._process_user_assignment(trainee_id, assignment_id,
                                                    workspace)

            # Process team members
            for team in request.team_id:
                if team.leader and team.leader.user_id:
                    logger.debug(
                        f"Processing team leader={team.leader.user_id} for assignment={assignment_id}"
                    )
                    await self._process_user_assignment(
                        team.leader.user_id, assignment_id, workspace,
                        team.leader.dict())

                if team.team_members:
                    for member in team.team_members:
                        if member.user_id:
                            logger.debug(
                                f"Processing team member={member.user_id} for assignment={assignment_id}"
                            )
                            await self._process_user_assignment(
                                member.user_id, assignment_id, workspace,
                                member.dict())

            logger.info("Assignment creation completed successfully.")
            return {"id": assignment_id, "status": "success"}
        except Exception as e:
            logger.error(f"Error creating assignment: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error creating assignment: {str(e)}")

    async def _process_user_assignment(self,
                                       user_id: str,
                                       assignment_id: str,
                                       workspace: str,
                                       user_data: Dict = None) -> None:
        """Process user document creation or update for assignments"""
        logger.debug(
            f"Processing user assignment for user_id={user_id}, assignment_id={assignment_id}, workspace={workspace}"
        )
        try:
            existing_user = await self.db.users.find_one({
                "_id": user_id,
                "workspace": workspace
            })
            if existing_user:
                logger.debug(
                    f"User {user_id} found in workspace {workspace}. Updating assignments array."
                )
                update_doc = {"$addToSet": {"assignments": assignment_id}}

                if user_data:
                    logger.debug(f"Updating user fields with: {user_data}")
                    update_doc["$set"] = {
                        "first_name": user_data.get("first_name"),
                        "last_name": user_data.get("last_name"),
                        "email": user_data.get("email"),
                        "phone_no": user_data.get("phone_no"),
                        "fullName": user_data.get("fullName"),
                        "lastModifiedAt": datetime.utcnow()
                    }

                await self.db.users.update_one(
                    {
                        "_id": user_id,
                        "workspace": workspace
                    }, update_doc)
                logger.debug(
                    f"User {user_id} assignments array updated successfully in workspace {workspace}."
                )
            else:
                logger.debug(
                    f"User {user_id} does not exist in workspace {workspace}. Creating new user document."
                )
                new_user = {
                    "_id": user_id,
                    "assignments": [assignment_id],
                    "createdAt": datetime.utcnow(),
                    "lastModifiedAt": datetime.utcnow(),
                    "workspace": workspace
                }

                if user_data:
                    logger.debug(f"Adding user data to new user: {user_data}")
                    new_user.update({
                        "first_name": user_data.get("first_name"),
                        "last_name": user_data.get("last_name"),
                        "email": user_data.get("email"),
                        "phone_no": user_data.get("phone_no"),
                        "fullName": user_data.get("fullName")
                    })

                await self.db.users.insert_one(new_user)
                logger.debug(
                    f"New user {user_id} created successfully in workspace {workspace}."
                )
        except Exception as e:
            logger.error(f"Error processing user assignment: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error processing user assignment: {str(e)}")

    async def fetch_assignments(
            self,
            workspace: str,
            pagination: Optional[PaginationParams] = None) -> Dict[str, any]:
        """Fetch all assignments with pagination and filtering"""
        logger.info("Fetching all assignments with pagination.")
        try:
            # Build query filter based on pagination parameters
            query = {"workspace": workspace}

            if pagination:
                logger.debug(f"Applying pagination parameters: {pagination}")

                # Apply search filter if provided
                if pagination.search:
                    search_regex = {
                        "$regex": pagination.search,
                        "$options": "i"
                    }
                    query["$or"] = [{
                        "name": search_regex
                    }, {
                        "type": search_regex
                    }]

                if pagination.type:
                    query["type"] = pagination.type

                # Apply created by filter if provided
                if pagination.createdBy:
                    query["createdBy"] = pagination.createdBy

                # Apply modified by filter if provided
                if pagination.modifiedBy:
                    query["lastModifiedBy"] = pagination.modifiedBy

                # Apply created date range filters if provided
                date_filter = {}
                if pagination.createdFrom:
                    date_filter["$gte"] = pagination.createdFrom
                if pagination.createdTo:
                    date_filter["$lte"] = pagination.createdTo
                if date_filter:
                    query["createdAt"] = date_filter

                # Apply modified date range filters if provided
                modified_date_filter = {}
                if pagination.modifiedFrom:
                    modified_date_filter["$gte"] = pagination.modifiedFrom
                if pagination.modifiedTo:
                    modified_date_filter["$lte"] = pagination.modifiedTo
                if modified_date_filter:
                    query["lastModifiedAt"] = modified_date_filter

            # Determine sort options
            sort_options = []
            if pagination and pagination.sortBy:
                # Convert camelCase sort field to database field name if needed
                sort_field_mapping = {
                    "name": "name",
                    "type": "type",
                    "startDate": "startDate",
                    "endDate": "endDate",
                    "lastModifiedAt": "lastModifiedAt",
                    "createdAt": "createdAt",
                    "status": "status"
                    # Add other mappings as needed
                }
                db_field = sort_field_mapping.get(pagination.sortBy,
                                                  pagination.sortBy)
                sort_direction = 1 if pagination.sortDir == "asc" else -1
                sort_options.append((db_field, sort_direction))
            else:
                # Default sort by lastModifiedAt
                sort_options.append(("lastModifiedAt", -1))

            # Get total count for pagination metadata
            total_count = await self.db.assignments.count_documents(query)

            # Calculate pagination
            skip = 0
            limit = 50  # Default limit

            if pagination:
                limit = pagination.pagesize
                skip = (pagination.page - 1) * limit

            logger.debug(f"Query filter: {query}")
            logger.debug(f"Sort options: {sort_options}")
            logger.debug(f"Skip: {skip}, Limit: {limit}")

            # Execute the query with pagination
            cursor = self.db.assignments.find(query).sort(sort_options).skip(
                skip).limit(limit)
            assignments = []

            async for doc in cursor:
                team_ids = []
                if doc.get("teamId"):
                    for team in doc["teamId"]:
                        if isinstance(team, dict) and team.get("team_id"):
                            team_ids.append(team["team_id"])

                assignment = AssignmentData(
                    id=doc.get("id", ""),
                    name=doc.get("name", ""),
                    type=doc.get("type", ""),
                    start_date=doc.get("startDate", ""),
                    end_date=doc.get("endDate", ""),
                    team_id=team_ids,
                    trainee_id=doc.get("traineeId", []),
                    created_by=doc.get("createdBy", ""),
                    created_at=doc.get("createdAt",
                                       datetime.utcnow()).isoformat(),
                    last_modified_by=doc.get("lastModifiedBy", ""),
                    last_modified_at=doc.get("lastModifiedAt",
                                             datetime.utcnow()).isoformat(),
                    status=doc.get("status", ""))
                assignments.append(assignment)

            logger.info(
                f"Fetched {len(assignments)} assignment(s) from the database. Total count: {total_count}"
            )
            return {"assignments": assignments, "total_count": total_count}
        except Exception as e:
            logger.error(f"Error fetching assignments: {str(e)}",
                         exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error fetching assignments: {str(e)}")

    from bson import ObjectId

    _STATUS_PRIORITY = {"not_started": 0, "in_progress": 1, "completed": 2}

    async def fetch_assigned_plans(
            self,
            user_id: str,
            workspace: str,
            pagination: Optional[PaginationParams] = None) -> Dict[str, any]:
        """Fetch assigned training plans with nested details and pagination"""
        logger.info(
            f"Fetching assigned training plans for user_id={user_id} in workspace={workspace}"
        )
        try:
            user = await self.db.users.find_one({
                "_id": user_id,
                "workspace": workspace
            })
            if not user:
                logger.warning(
                    f"User {user_id} not found in workspace {workspace}.")
                raise HTTPException(status_code=404,
                                    detail=f"User {user_id} not found")

            assignment_ids = user.get("assignments", [])
            logger.debug(
                f"Assignment IDs for user {user_id}: {assignment_ids}")

            object_ids = [ObjectId(aid) for aid in assignment_ids]

            # Build base query
            base_query = {
                "_id": {
                    "$in": object_ids
                },
                "status": "published",
                "workspace": workspace
            }

            # Applying additional filters if pagination parameters are provided
            query = base_query.copy()
            if pagination and pagination.search:
                search_regex = {"$regex": pagination.search, "$options": "i"}
                query["$and"] = [
                    base_query, {
                        "$or": [{
                            "name": search_regex
                        }, {
                            "type": search_regex
                        }]
                    }
                ]

            # Determine sort options
            sort_options = []
            if pagination and pagination.sortBy:
                # Convert camelCase sort field to database field name if needed
                sort_field_mapping = {
                    "name": "name",
                    "type": "type",
                    "startDate": "startDate",
                    "endDate": "endDate",
                    "createdAt": "createdAt",
                    "lastModifiedAt": "lastModifiedAt",
                    # Add other mappings as needed
                }
                db_field = sort_field_mapping.get(pagination.sortBy,
                                                  pagination.sortBy)
                sort_direction = 1 if pagination.sortDir == "asc" else -1
                sort_options.append((db_field, sort_direction))
            else:
                # Default sort by lastModifiedAt
                sort_options.append(("lastModifiedAt", -1))

            # Get total count for pagination metadata
            total_count = await self.db.assignments.count_documents(query)

            # Apply pagination to the query
            skip = 0
            limit = 50  # Default limit

            if pagination:
                limit = pagination.pagesize
                skip = (pagination.page - 1) * limit

            logger.debug(f"Query filter: {query}")
            logger.debug(f"Sort options: {sort_options}")
            logger.debug(f"Skip: {skip}, Limit: {limit}")

            # Execute the paginated query
            assignments = await self.db.assignments.find(query).sort(
                sort_options).skip(skip).limit(limit).to_list(None)

            training_plans = []
            modules = []
            simulations = []
            total_simulations = 0

            for assignment in assignments:
                logger.debug(f"Processing assignment: {assignment}")
                if assignment["type"] == "TrainingPlan":
                    training_plan = await self.db.training_plans.find_one({
                        "_id":
                        ObjectId(assignment["id"]),
                        "workspace":
                        workspace
                    })
                    if training_plan:
                        plan_modules = []
                        plan_total_simulations = 0
                        plan_est_time = 0

                        for added_obj in training_plan.get("addedObject", []):
                            if added_obj["type"] == "module":
                                module_details = await self._get_module_details(
                                    added_obj["id"], assignment["endDate"],
                                    str(assignment["_id"]), user_id, workspace)
                                if module_details:
                                    plan_modules.append(module_details)
                                    plan_total_simulations += module_details.total_simulations
                                    plan_est_time += sum(
                                        sim.estTime
                                        for sim in module_details.simulations)
                                    total_simulations += module_details.total_simulations

                            elif added_obj["type"] == "simulation":
                                sim_details = await self._get_simulation_details(
                                    added_obj["id"], assignment["endDate"],
                                    str(assignment["_id"]), user_id, workspace)
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

                        training_plans.append(
                            TrainingPlanDetails(
                                id=str(training_plan["_id"]),
                                name=training_plan.get("name", ""),
                                completion_percentage=0,
                                total_modules=len(plan_modules),
                                total_simulations=plan_total_simulations,
                                est_time=plan_est_time,
                                average_sim_score=0,
                                due_date=assignment["endDate"],
                                status=plan_status,
                                modules=plan_modules,
                            ))
                elif assignment["type"] == "Module":
                    module_details = await self._get_module_details(
                        assignment["id"], assignment["endDate"],
                        str(assignment["_id"]), user_id, workspace)
                    if module_details:
                        modules.append(module_details)
                        total_simulations += module_details.total_simulations
                elif assignment["type"] == "Simulation":
                    sim_details = await self._get_simulation_details(
                        assignment["id"], assignment["endDate"],
                        str(assignment["_id"]), user_id, workspace)
                    if sim_details:
                        # Consolidate duplicates by assignment with precedence
                        existing_index = next(
                            (idx for idx, s in enumerate(simulations)
                             if s.assignment_id == sim_details.assignment_id),
                            None,
                        )
                        if existing_index is not None:
                            existing_sim = simulations[existing_index]
                            if self._STATUS_PRIORITY[
                                    sim_details.
                                    status] > self._STATUS_PRIORITY[
                                        existing_sim.status]:
                                simulations[existing_index] = sim_details
                        else:
                            simulations.append(sim_details)
                            total_simulations += 1

            stats = Stats(
                simulation_completed=StatsData(
                    total_simulations=total_simulations,
                    completed_simulations=0,
                    percentage=0,
                ),
                timely_completion=StatsData(
                    total_simulations=total_simulations,
                    completed_simulations=0,
                    percentage=0,
                ),
                average_sim_score=0,
                highest_sim_score=0,
            )

            logger.info(
                f"Finished fetching assigned plans for user_id={user_id}. "
                f"Total simulations found: {total_simulations}, total count: {total_count}"
            )

            # Return both the data and the total count for pagination metadata
            return {
                "data":
                FetchAssignedPlansResponse(
                    training_plans=training_plans,
                    modules=modules,
                    simulations=simulations,
                    stats=stats,
                ),
                "total_count":
                total_count
            }
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error fetching assigned plans: {str(e)}",
                         exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching assigned plans: {str(e)}")

    async def _get_simulation_details(
            self, sim_id: str, due_date: str, assignment_id: str, user_id: str,
            workspace: str) -> SimulationDetails | None:
        """Helper method to get simulation details with status precedence"""
        logger.debug(f"Fetching simulation details for sim_id={sim_id}")
        try:
            sim = await self.db.simulations.find_one({
                "_id": ObjectId(sim_id),
                "workspace": workspace
            })
            if not sim:
                logger.warning(f"Simulation {sim_id} not found.")
                return None

            # Fetch **all** user simulation progress rows for this sim + assignment
            progress_list = await self.db.user_sim_progress.find({
                "userId":
                user_id,
                "assignmentId":
                assignment_id,
                "simulationId":
                sim_id,
                "workspace":
                workspace
            }).to_list(None)

            # Determine status with precedence: completed > in_progress > not_started
            status = "not_started"
            if progress_list:
                statuses = {
                    p.get("status", "not_started")
                    for p in progress_list
                }
                if "completed" in statuses:
                    status = "completed"
                elif "in_progress" in statuses:
                    status = "in_progress"

            if ((status == 'not_started' or status == 'in_progress')
                    and datetime.now() > datetime.strptime(
                        due_date, '%Y-%m-%d')):
                status = 'over_due'

            logger.debug(
                f"Simulation {sim_id} retrieved with consolidated status {status}"
            )

            # Getting scores
            scores = {}
            # TODO: Ask do we need the latest attept response?
            # if(status == 'completed'):
            # scores = progress_list.get('scores')

            return SimulationDetails(
                simulation_id=str(sim["_id"]),
                name=sim.get("name", ""),
                type=sim.get("type", ""),
                level="beginner",  # Default value
                estTime=sim.get("estimatedTimeToAttemptInMins", 0),
                dueDate=due_date,
                status=status,
                scores=scores,
                highest_attempt_score=0,
                assignment_id=assignment_id,
            )
        except Exception as e:
            logger.error(f"Error fetching simulation details: {str(e)}",
                         exc_info=True)
            return None

    async def _get_module_details(self, module_id: str, due_date: str,
                                  assignment_id: str, user_id: str,
                                  workspace: str) -> ModuleDetails:
        logger.debug(f"Fetching module details for module_id={module_id}")
        try:
            module = await self.db.modules.find_one({
                "_id": ObjectId(module_id),
                "workspace": workspace
            })
            if not module:
                logger.warning(f"Module {module_id} not found.")
                return None

            module_simulations = []
            sim_statuses = []

            for sim_id in module.get("simulationIds", []):
                sim_details = await self._get_simulation_details(
                    sim_id, due_date, assignment_id, user_id, workspace)
                if sim_details:
                    module_simulations.append(sim_details)
                    sim_statuses.append(sim_details.status)

            # Determine module status
            if all(status == "completed" for status in sim_statuses):
                module_status = "completed"
            elif any(status == "in_progress" for status in sim_statuses):
                module_status = "in_progress"
            elif any(status == "over_due" for status in sim_statuses):
                module_status = "over_due"
            else:
                module_status = "not_started"

            logger.debug(
                f"Module {module_id} has {len(module_simulations)} simulation(s) with status={module_status}"
            )
            return ModuleDetails(id=str(module["_id"]),
                                 name=module.get("name", ""),
                                 total_simulations=len(module_simulations),
                                 average_score=0,
                                 due_date=due_date,
                                 status=module_status,
                                 simulations=module_simulations)
        except Exception as e:
            logger.error(f"Error fetching module details: {str(e)}",
                         exc_info=True)
            return None
