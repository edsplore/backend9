from typing import List, Dict, Any
from models.playback_data import SimulationAttempt, AttemptAnalytics
from database import db

class PlaybackDataService:
    def __init__(self):
        self.sim_attempts_coll = db["simulationAttempts"]
        self.simulations_coll = db["simulations"]
        self.modules_coll = db["modules"]
        self.training_plans_coll = db["trainingPlans"]

    async def get_attempts(self, user_id: str) -> List[SimulationAttempt]:
        attempts_cursor = self.sim_attempts_coll.find({"userId": user_id})
        
        response_data = []
        async for attempt_doc in attempts_cursor:
            attempt_data = await self._process_attempt(attempt_doc)
            if attempt_data:
                response_data.append(attempt_data)
        
        return response_data

    async def get_attempt_by_id(self, user_id: str, attempt_id: str) -> AttemptAnalytics:
        attempt_doc = await self.sim_attempts_coll.find_one({
            "_id": attempt_id,
            "userId": user_id
        })
        
        if not attempt_doc:
            return None

        simulation_id = attempt_doc.get("simulationId")
        simulation = await self.simulations_coll.find_one({"_id": simulation_id})
        
        if not simulation:
            return None

        analytics = attempt_doc.get("analytics", {})
        playback = attempt_doc.get("playback", {})

        return AttemptAnalytics(
            sentencewiseAnalytics=playback.get("sentencewiseAnalytics", []),
            audioUrl=playback.get("audioUrl", ""),
            transcript=playback.get("transcript", ""),
            transcriptObject=playback.get("transcriptObject", []),
            timeTakenSeconds=attempt_doc.get("timeTakenSeconds", 0),
            clickScore=analytics.get("clickScore", 0),
            textFieldKeywordScore=analytics.get("textFieldKeywordScore", 0),
            keywordScore=analytics.get("keywordScore", 0),
            simAccuracyScore=analytics.get("simAccuracyScore", 0),
            confidence=analytics.get("confidence", 0),
            energy=analytics.get("energy", 0),
            concentration=analytics.get("concentration", 0),
            minPassingScore=simulation.get("minPassingScore", 0)
        )

    async def _process_attempt(self, attempt_doc: Dict[str, Any]) -> SimulationAttempt:
        simulation_id = attempt_doc.get("simulationId")
        module_id = attempt_doc.get("moduleId")
        training_plan_id = attempt_doc.get("trainingPlanId")

        simulation = await self.simulations_coll.find_one({"_id": simulation_id})
        if not simulation:
            return None

        module = await self.modules_coll.find_one({"_id": module_id}) if module_id else None
        module_name = module.get("name", "") if module else ""

        training_plan = await self.training_plans_coll.find_one({"_id": training_plan_id})
        training_plan_name = training_plan.get("name", "") if training_plan else ""

        return SimulationAttempt(
            attemptId=str(attempt_doc.get("_id")),
            trainingPlan=training_plan_name,
            moduleName=module_name,
            simId=simulation_id,
            simName=simulation.get("name", ""),
            simType=simulation.get("type", ""),
            simLevel=simulation.get("level", ""),
            score=attempt_doc.get("scorePercent", 0),
            timeTaken=attempt_doc.get("timeTaken", 0),
            dueDate=simulation.get("dueDate"),
            attemptType=attempt_doc.get("attemptType", "N/A"),
            estTime=simulation.get("estTime", 0),
            attemptCount=1  # Constant as per requirement
        )