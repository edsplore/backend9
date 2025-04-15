from fastapi import APIRouter, HTTPException
from domain.services.list_service import ListService
from api.schemas.requests import ListItemsRequest
from api.schemas.responses import ListTrainingPlansResponse, ListModulesResponse, ListSimulationsResponse
from utils.logger import Logger

router = APIRouter()

logger = Logger.get_logger(__name__)


class ListController:

    def __init__(self):
        self.service = ListService()
        logger.info("ListController initialized.")

    async def list_training_plans(
            self, request: ListItemsRequest) -> ListTrainingPlansResponse:
        logger.info("Request received to list training plans.")
        logger.debug(f"Request data: {request.dict()}")
    
        try:
            if not request.user_id:
                logger.warning("Missing 'userId' in training plans request.")
                raise HTTPException(status_code=400, detail="Missing 'userId'")
    
            training_plans = await self.service.list_training_plans(request.user_id)
            logger.info(f"Fetched {len(training_plans)} training plans for user {request.user_id}")
            return ListTrainingPlansResponse(training_plans=training_plans)
        except Exception as e:
            logger.error(f"Error listing training plans: {str(e)}", exc_info=True)
            raise
    
    async def list_modules(self,
                           request: ListItemsRequest) -> ListModulesResponse:
        logger.info("Request received to list modules.")
        logger.debug(f"Request data: {request.dict()}")
    
        try:
            if not request.user_id:
                logger.warning("Missing 'userId' in modules request.")
                raise HTTPException(status_code=400, detail="Missing 'userId'")
    
            modules = await self.service.list_modules(request.user_id)
            logger.info(f"Fetched {len(modules)} modules for user {request.user_id}")
            return ListModulesResponse(modules=modules)
        except Exception as e:
            logger.error(f"Error listing modules: {str(e)}", exc_info=True)
            raise
    
    async def list_simulations(
            self, request: ListItemsRequest) -> ListSimulationsResponse:
        logger.info("Request received to list simulations.")
        logger.debug(f"Request data: {request.dict()}")
    
        try:
            if not request.user_id:
                logger.warning("Missing 'userId' in simulations request.")
                raise HTTPException(status_code=400, detail="Missing 'userId'")
    
            simulations = await self.service.list_simulations(request.user_id)
            logger.info(f"Fetched {len(simulations)} simulations for user {request.user_id}")
            return ListSimulationsResponse(simulations=simulations)
        except Exception as e:
            logger.error(f"Error listing simulations: {str(e)}", exc_info=True)
            raise
    

controller = ListController()


@router.post("/list-training-plans", tags=["Read", "Training Plans"])
async def list_training_plans(
        request: ListItemsRequest) -> ListTrainingPlansResponse:
    """List all training plans with summary information"""
    return await controller.list_training_plans(request)


@router.post("/list-modules", tags=["Read", "Modules"])
async def list_modules(request: ListItemsRequest) -> ListModulesResponse:
    """List all modules with summary information"""
    return await controller.list_modules(request)


@router.post("/list-simulations", tags=["Read", "Simulations"])
async def list_simulations(
        request: ListItemsRequest) -> ListSimulationsResponse:
    """List all simulations with summary information"""
    return await controller.list_simulations(request)
