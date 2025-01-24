from typing import List, Dict, Set
from domain.interfaces.training_repository import ITrainingRepository
from domain.models.training import (
    TrainingDataModel, ModuleModel, SimulationModel,
    SimulationCompletionStats, TimelyCompletionStats, TrainingStats
)
from infrastructure.database import Database

class TrainingRepository(ITrainingRepository):
    def __init__(self):
        self.db = Database()

    async def get_training_plans(self, user_id: str) -> List[TrainingDataModel]:
        training_plan_ids = await self._get_user_assignments(user_id)
        return await self._build_training_plans(user_id, training_plan_ids)

    async def get_training_stats(self, user_id: str) -> Dict:
        training_plan_ids = await self._get_user_assignments(user_id)

        total_simulations = 0
        completed_simulations = 0
        total_score = 0
        highest_score = 0

        for tp_id in training_plan_ids:
            plan = await self.db.training_plans.find_one({"_id": tp_id})
            if not plan:
                continue

            for module_id in plan.get("moduleIds", []):
                module = await self.db.modules.find_one({"_id": module_id})
                if not module:
                    continue

                for sim_id in module.get("simulationIds", []):
                    simulation = await self.db.simulations.find_one({"_id": sim_id})
                    if not simulation:
                        continue

                    total_simulations += 1
                    sim_progress = await self.db.user_sim_progress.find_one({
                        "userId": user_id,
                        "simulationId": sim_id
                    })

                    if sim_progress and sim_progress.get("status") == "completed":
                        completed_simulations += 1

                        if sim_progress.get("attemptIds"):
                            attempts_cursor = self.db.sim_attempts.find({
                                "_id": {"$in": sim_progress["attemptIds"]},
                                "userId": user_id,
                                "simulationId": sim_id
                            }).sort("lastAttemptedDate", -1)

                            async for attempt in attempts_cursor:
                                score = attempt.get("scorePercent", 0)
                                total_score += score
                                highest_score = max(highest_score, score)
                                break

        return {
            "simulation_completed": {
                "total_simulations": total_simulations,
                "completed_simulations": completed_simulations,
                "percentage": round((completed_simulations / total_simulations * 100 
                    if total_simulations > 0 else 0), 2)
            },
            "timely_completion": {
                "total_simulations": total_simulations,
                "completed_simulations": completed_simulations,
                "percentage": round((completed_simulations / total_simulations * 100 
                    if total_simulations > 0 else 0), 2)
            },
            "average_sim_score": round(total_score / completed_simulations 
                if completed_simulations > 0 else 0, 2),
            "highest_sim_score": highest_score
        }

    async def _get_user_assignments(self, user_id: str) -> Set[str]:
        user = await self.db.users.find_one({"_id": user_id})
        if not user:
            return set()

        division_id = user.get("divisionId")
        department_id = user.get("departmentId")

        assignments_cursor = self.db.assignments.find({
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

    async def _build_training_plans(self, user_id: str, training_plan_ids: Set[str]) -> List[TrainingDataModel]:
        training_plans = []

        for tp_id in training_plan_ids:
            plan = await self.db.training_plans.find_one({"_id": tp_id})
            if not plan:
                continue

            modules = []
            plan_total_score = 0
            plan_completed_sims = 0
            plan_total_sims = 0
            plan_total_time = 0

            for module_id in plan.get("moduleIds", []):
                module = await self.db.modules.find_one({"_id": module_id})
                if not module:
                    continue

                module_data = await self._build_module_data(module, user_id)
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

            training_plans.append(TrainingDataModel(
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

        return training_plans

    async def _build_module_data(self, module: dict, user_id: str) -> ModuleModel:
        sim_ids = module.get("simulationIds", [])
        simulations = []
        total_score = 0
        completed_count = 0
        progress_flag = False

        for sim_id in sim_ids:
            simulation = await self.db.simulations.find_one({"_id": sim_id})
            if simulation:
                sim_data = await self._build_simulation_data(simulation, user_id)
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

    async def _build_simulation_data(self, simulation: dict, user_id: str) -> SimulationModel:
        sim_progress = await self.db.user_sim_progress.find_one({
            "userId": user_id,
            "simulationId": simulation["_id"]
        })

        sim_data = SimulationModel(
            simulation_id=simulation["_id"],
            name=simulation.get("name", ""),
            type=simulation.get("type", ""),
            level=simulation.get("level", ""),
            est_time=simulation.get("estTime", 0),
            due_date=simulation.get("dueDate"),
            status=sim_progress.get("status", "not_started") if sim_progress else "not_started"
        )

        if sim_progress and sim_progress.get("attemptIds"):
            attempts_cursor = self.db.sim_attempts.find({
                "_id": {"$in": sim_progress["attemptIds"]},
                "userId": user_id,
                "simulationId": simulation["_id"]
            }).sort("lastAttemptedDate", -1)

            highest_score = 0
            async for attempt in attempts_cursor:
                score = attempt.get("scorePercent", 0)
                highest_score = max(highest_score, score)

            sim_data.highest_attempt_score = highest_score

        return sim_data

    @staticmethod
    def _determine_plan_status(modules: List[ModuleModel]) -> str:
        completed_count = sum(1 for m in modules if m.status == "completed")
        in_progress_count = sum(1 for m in modules if m.status == "in_progress")

        if completed_count == len(modules):
            return "completed"
        elif completed_count > 0 or in_progress_count > 0:
            return "in_progress"
        return "not_started"