from typing import List, Set
from models.training_data import (
    TrainingPlanModel, ModuleModel, SimulationModel,
    SimulationCompletionStats, TimelyCompletionStats,
    TrainingStats, TrainingDataResponse
)
from database import db

class TrainingDataService:
    def __init__(self):
        self.users_coll = db["users"]
        self.assignments_coll = db["assignments"]
        self.training_plans_coll = db["trainingPlans"]
        self.modules_coll = db["modules"]
        self.simulations_coll = db["simulations"]
        self.user_sim_progress_coll = db["userSimulationProgress"]
        self.sim_attempts_coll = db["simulationAttempts"]

    async def get_user_assignments(self, user_id: str) -> Set[str]:
        user = await self.users_coll.find_one({"_id": user_id})
        if not user:
            return set()

        division_id = user.get("divisionId")
        department_id = user.get("departmentId")

        assignments_cursor = self.assignments_coll.find({
            "assignedItemType": "trainingPlan",
            "status": "assigned",
            "$or": [
                {"assignedToType": "user", "assignedToId": user_id},
                {"assignedToType": "division", "assignedToId": division_id},
                {"assignedToType": "department", "assignedToId": department_id}
            ]
        })

        training_plan_ids = set()
        async for assignment in assignments_cursor:
            training_plan_ids.add(assignment["assignedItemId"])
        
        return training_plan_ids

    async def get_simulation_progress(self, user_id: str, sim_id: str):
        return await self.user_sim_progress_coll.find_one({
            "userId": user_id,
            "simulationId": sim_id
        })

    async def get_simulation_attempts(self, user_id: str, sim_id: str, attempt_ids: List[str]):
        attempts_cursor = self.sim_attempts_coll.find({
            "_id": {"$in": attempt_ids},
            "userId": user_id,
            "simulationId": sim_id
        }).sort("lastAttemptedDate", -1)
        
        highest_score = 0
        async for attempt in attempts_cursor:
            score = attempt.get("scorePercent", 0)
            highest_score = max(highest_score, score)
        
        return highest_score

    async def build_simulation_data(self, simulation: dict, user_id: str) -> SimulationModel:
        sim_progress = await self.get_simulation_progress(user_id, simulation["_id"])
        
        sim_data = SimulationModel(
            simulation_id=simulation["_id"],
            name=simulation.get("name", ""),
            type=simulation.get("type", ""),
            level=simulation.get("level", ""),
            est_time=simulation.get("estTime", 0),
            due_date=simulation.get("dueDate"),
            status=sim_progress.get("status", "not_started")
        )

        if sim_progress and sim_progress.get("attemptIds"):
            highest_score = await self.get_simulation_attempts(
                user_id, simulation["_id"], sim_progress["attemptIds"]
            )
            sim_data.highest_attempt_score = highest_score

        return sim_data

    async def build_module_data(self, module: dict, user_id: str) -> ModuleModel:
        sim_ids = module.get("simulationIds", [])
        simulations = []
        total_score = 0
        completed_count = 0
        progress_flag = False

        for sim_id in sim_ids:
            simulation = await self.simulations_coll.find_one({"_id": sim_id})
            if simulation:
                sim_data = await self.build_simulation_data(simulation, user_id)
                simulations.append(sim_data)
                
                if sim_data.highest_attempt_score is not None:
                    total_score += sim_data.highest_attempt_score
                if sim_data.status == "completed":
                    completed_count += 1
                elif sim_data.status == "in_progress":
                    progress_flag = True

        total_sims = len(simulations)
        avg_score = total_score / total_sims if total_sims > 0 else 0
        
        status = "not_started"
        if completed_count == total_sims:
            status = "completed"
        elif completed_count > 0 or progress_flag:
            status = "in_progress"

        return ModuleModel(
            id=module["_id"],
            name=module.get("name", ""),
            total_simulations=total_sims,
            average_score=avg_score,
            due_date=min((s.due_date for s in simulations if s.due_date), default=None),
            status=status,
            simulations=simulations
        )

    async def get_training_data(self, user_id: str) -> TrainingDataResponse:
        training_plan_ids = await self.get_user_assignments(user_id)
        
        training_plans = []
        total_simulations = 0
        completed_simulations = 0
        timely_simulations = 0
        total_score = 0
        highest_score = 0

        for tp_id in training_plan_ids:
            plan = await self.training_plans_coll.find_one({"_id": tp_id})
            if not plan:
                continue

            modules = []
            plan_total_score = 0
            plan_completed_sims = 0
            plan_total_sims = 0
            plan_total_time = 0

            for module_id in plan.get("moduleIds", []):
                module = await self.modules_coll.find_one({"_id": module_id})
                if not module:
                    continue

                module_data = await self.build_module_data(module, user_id)
                modules.append(module_data)

                for sim in module_data.simulations:
                    plan_total_sims += 1
                    plan_total_time += sim.est_time
                    if sim.highest_attempt_score:
                        plan_total_score += sim.highest_attempt_score
                    if sim.status == "completed":
                        plan_completed_sims += 1

            if plan_total_sims > 0:
                completion_percentage = (plan_completed_sims / plan_total_sims) * 100
                avg_score = plan_total_score / plan_total_sims
            else:
                completion_percentage = 0
                avg_score = 0

            training_plans.append(TrainingPlanModel(
                id=plan["_id"],
                name=plan.get("name", ""),
                completion_percentage=completion_percentage,
                total_modules=len(modules),
                total_simulations=plan_total_sims,
                est_time=plan_total_time,
                average_sim_score=avg_score,
                due_date=min((m.due_date for m in modules if m.due_date), default=None),
                status=self._determine_plan_status(modules),
                modules=modules
            ))

            # Update overall statistics
            total_simulations += plan_total_sims
            completed_simulations += plan_completed_sims
            total_score += plan_total_score
            highest_score = max(highest_score, max((s.highest_attempt_score or 0 
                for m in modules for s in m.simulations), default=0))

        return TrainingDataResponse(
            training_plans=training_plans,
            stats=TrainingStats(
                simulation_completed=SimulationCompletionStats(
                    total_simulations=total_simulations,
                    completed_simulations=completed_simulations,
                    percentage=round((completed_simulations / total_simulations * 100 
                        if total_simulations > 0 else 0), 2)
                ),
                timely_completion=TimelyCompletionStats(
                    total_simulations=total_simulations,
                    completed_simulations=completed_simulations,
                    percentage=round((completed_simulations / total_simulations * 100 
                        if total_simulations > 0 else 0), 2)
                ),
                average_sim_score=round(total_score / total_simulations 
                    if total_simulations > 0 else 0, 2),
                highest_sim_score=highest_score
            )
        )

    @staticmethod
    def _determine_plan_status(modules: List[ModuleModel]) -> str:
        completed_count = sum(1 for m in modules if m.status == "completed")
        in_progress_count = sum(1 for m in modules if m.status == "in_progress")
        
        if completed_count == len(modules):
            return "completed"
        elif completed_count > 0 or in_progress_count > 0:
            return "in_progress"
        return "not_started"