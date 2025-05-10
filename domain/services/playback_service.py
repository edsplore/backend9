from typing import List, Optional
from domain.models.playback import SimulationAttemptModel, AttemptAnalyticsModel, SimulationAttemptDetailModel
from infrastructure.database import Database
from infrastructure.repositories.playback_repository import PlaybackRepository
from domain.interfaces.playback_repository import IPlaybackRepository
from bson import ObjectId

from api.schemas.requests import PaginationParams
from api.schemas.responses import AttemptsStatsResponse, AttemptsResponse

from utils.logger import Logger  # Adjust import path if needed
from fastapi import HTTPException

logger = Logger.get_logger(__name__)


class PlaybackService:

    def __init__(self, repository: IPlaybackRepository = None):
        self.db = Database()
        self.repository = repository or PlaybackRepository()
        logger.info("PlaybackService initialized.")

    async def get_attempts(self, user_id: str, pagination: Optional[PaginationParams] ) -> AttemptsResponse:
        logger.info("Fetching attempts.")
        logger.debug(f"user_id={user_id}")
        try:
            query = {}
            
            if user_id:
                query['userId'] = user_id

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
                    }]
            
            # Get total count for pagination metadata
            total_count = await self.db.user_sim_progress.count_documents(query)

            # Calculate pagination
            skip = 0
            limit = 50  # Default limit
            

            if pagination:
                limit = pagination.pagesize
                skip = (pagination.page - 1) * limit
            
            logger.debug(f"Query filter: {query}")
            logger.debug(f"Skip: {skip}, Limit: {limit}")

            cursor = self.db.user_sim_progress.find(query).skip(
                skip).limit(limit)
            # attempts = await self.db.sim_attempts.find({"userId": user_id})
            attempts = []
            async for doc in cursor:
                attempts.append(
                    {
                        "id": doc.get("_id", ""),
                        "assignmentId": doc.get("assignmentId", ""),
                        "simulationId": doc.get("simulationId", ""),
                        "status": doc.get("status", ""),
                        "type": doc.get("type", ""),
                        "createdAt": doc.get("createdAt", ""),
                        "score": "0.0",
                        "lastModifiedAt": doc.get("lastModifiedAt", ""),
                        "estTime": doc.get("estTime", ""),
                    }
                )
            
            for attemptIndex in range(0,len(attempts)):
                simulation = await self.db.simulations.find_one({"_id": ObjectId(attempts[attemptIndex]["simulationId"])})
                attempts[attemptIndex]["simulation"] = simulation

                assignment = await self.db.assignments.find_one({"_id": ObjectId(attempts[attemptIndex]["assignmentId"])})
                attempts[attemptIndex]["assignment"] = assignment

            simulationsAttemps = []
            for attempt in attempts:
                if  attempt.get("assignment") == None:
                    continue;
                
                simLevel = "lvl1";
                if(attempt["simulation"]["lvl2"]["isEnabled"]):
                    simLevel = "lvl2";
                

                if(attempt["simulation"]["lvl2"]["isEnabled"]):
                    simLevel = "lvl3";

                if(attempt["simulation"]["lvl3"]["isEnabled"]):
                    simLevel = "lvl4";
                
                simulationsAttemps.append(
                    SimulationAttemptModel(
                        id=str(attempt["id"]) if isinstance(attempt["id"], ObjectId) else attempt["id"],
                        trainingPlan="" if attempt.get("assignment") is None else attempt["assignment"].get("name", ""),
                        moduleName=attempt.get("moduleName", ""),
                        simId=attempt["simulationId"],
                        simName="" if attempt.get("simulation") is None else attempt["simulation"].get("name", ""),
                        simType="" if attempt.get("simulation") is None else attempt["simulation"].get("type", ""),
                        simLevel=simLevel or "",
                        score=0.0,
                        status=attempt["status"] or "",
                        timeTaken=attempt.get("duration", 2),
                        dueDate=None if attempt.get("simulation") is None else attempt["simulation"].get("endDate"),
                        attemptType=attempt.get("attemptType", ""),
                        estTime=2,
                        attemptCount=4
                    )
                )
            return AttemptsResponse(attempts=simulationsAttemps, total_attempts=total_count)
        except Exception as e:
            logger.error(f"Error fetching attempts for dashboard: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching attempts for dashboard: {str(e)}")

    async def get_attempt_by_id(
            self, user_id: str,
            attempt_id: str) -> Optional[AttemptAnalyticsModel]:
        logger.info("Fetching attempt by ID.")
        logger.debug(f"user_id={user_id}, attempt_id={attempt_id}")

        try:
            attemptObj = await self.db.user_sim_progress.find_one({"_id": ObjectId(attempt_id), "userId": user_id})
            attempt= None
            if attemptObj:
                simulation = await self.db.simulations.find_one({"_id": ObjectId(attemptObj["simulationId"])})
                attemptObj["simulation"] = simulation

            simLevel = "lvl1";
            if(attemptObj["simulation"]["lvl2"]["isEnabled"]):
                simLevel = "lvl2";
            

            if(attemptObj["simulation"]["lvl2"]["isEnabled"]):
                simLevel = "lvl3";

            if(attemptObj["simulation"]["lvl3"]["isEnabled"]):
                simLevel = "lvl4";
            
            attempt = AttemptAnalyticsModel(
                        id=str(attemptObj["_id"]) if isinstance(attemptObj["_id"], ObjectId) else attemptObj["_id"],
                        sentencewiseAnalytics=[],
                        audioUrl=attemptObj.get("audioUrl", ""),
                        transcript=attemptObj.get("transcript", ""),
                        transcriptObject=attemptObj.get("transcriptObject", []),
                        timeTakenSeconds=attemptObj.get("duration", 0),
                        clickScore=attemptObj.get("scores", {}).get('ClickScore', 0),
                        textFieldKeywordScore=attemptObj.get("scores", {}).get('DataAccuracy', 0),
                        keywordScore=attemptObj.get("scores", {}).get('KeywordScore', 0),
                        simAccuracyScore=attemptObj.get("scores", {}).get('SimAccuracy', 0),
                        confidence=attemptObj.get("scores", {}).get('Confidence', 0),
                        energy=attemptObj.get("scores", {}).get('Energy', 0),
                        concentration=attemptObj.get("scores", {}).get('Concentration', 0),
                        minPassingScore=0,
                        name="" if attemptObj.get("simulation") is None else attemptObj["simulation"].get("name", ""),
                        completedAt= '', # attemptObj.get("completedAt", ""),
                        type="" if attemptObj.get("simulation") is None else attemptObj["simulation"].get("type", ""),
                        simLevel=simLevel or ""
                    )
            await self.repository.get_attempt_by_id(user_id, attempt_id)
            return attempt 
        except Exception as e:
            logger.error(f"Error fetching attempt: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching attempt: {str(e)}")

    async def get_attempt_stats(self, user_id: str) -> AttemptsStatsResponse:
        try:
            attempts = await self.get_attempts(user_id);
            
            simulations = {}
            for attempt in attempts:
                if attempt.simId not in simulations:
                    simulations[attempt.simId] = attempt
                else:
                    if attempt.status == "completed":
                        simulations[attempt.simId].status = "completed"
            
            total_simulations = len(simulations.keys())
            completed_simulations = len([sim for sim in simulations.values() if sim.status == "completed"])

            
            final_response = AttemptsStatsResponse(
                            simultion_completion = AttemptsStatsResponse.SimulationCompletion(
                                completed = completed_simulations,
                                total = total_simulations,
                                total_modules = 0
                            ),
                            ontime_completion  = AttemptsStatsResponse.OnTimeCompletion(
                                completed = completed_simulations,
                                total = total_simulations
                            ),
                            average_sim_score =  AttemptsStatsResponse.Scores(
                                percentage = 0,
                                difference_from_last_week = 0
                            ),
                            highest_sim_score = AttemptsStatsResponse.Scores(
                                percentage = 0,
                                difference_from_last_week = 0
                            )
                        )
            return final_response
        except Exception as e:
            logger.error(f"Error fetching attempt stats: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching attempt stats: {str(e)}");