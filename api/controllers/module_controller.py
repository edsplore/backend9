from fastapi import APIRouter, HTTPException
from domain.services.module_service import ModuleService
from api.schemas.requests import CreateModuleRequest, FetchModulesRequest, CloneModuleRequest, UpdateModuleRequest
from api.schemas.responses import CreateModuleResponse, FetchModulesResponse, ModuleData

from utils.logger import Logger

logger = Logger.get_logger(__name__)

router = APIRouter()


class ModuleController:

    def __init__(self):
        self.service = ModuleService()
        logger.info("ModuleController initialized.")

    async def create_module(
            self, request: CreateModuleRequest) -> CreateModuleResponse:
        logger.info("Request received to create a new module.")
        logger.debug(f"Request data: {request.dict()}")

        try:

            result = await self.service.create_module(request)
            logger.info(f"Module created with ID: {result['id']}")
            return CreateModuleResponse(id=result["id"],
                                        status=result["status"])
        except Exception as e:
            logger.error(f"Error creating module: {str(e)}", exc_info=True)
            raise

    async def fetch_modules(
            self, request: FetchModulesRequest) -> FetchModulesResponse:
        logger.info(f"Fetching modules for user_id: {request.user_id}")
        try:

            modules = await self.service.fetch_modules(request.user_id)
            logger.info(f"Fetched {len(modules)} modules.")
            return FetchModulesResponse(modules=modules)
        except Exception as e:
            logger.error(f"Error fetching modules: {str(e)}", exc_info=True)
            raise

    async def get_module_by_id(self, module_id: str) -> ModuleData:
        logger.info(f"Fetching module by ID: {module_id}")
        try:

            module = await self.service.get_module_by_id(module_id)
            if not module:
                logger.warning(f"Module with ID {module_id} not found.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Module with id {module_id} not found")

            logger.info(f"Module with ID {module_id} fetched successfully.")
            return module
        except Exception as e:
            logger.error(f"Error fetching module by ID: {str(e)}",
                         exc_info=True)
            raise

    async def clone_module(
            self, request: CloneModuleRequest) -> CreateModuleResponse:
        logger.info("Cloning module.")
        logger.debug(f"Clone request data: {request.dict()}")

        try:

            result = await self.service.clone_module(request)
            logger.info(f"Module cloned. New ID: {result['id']}")
            return CreateModuleResponse(id=result["id"],
                                        status=result["status"])
        except Exception as e:
            logger.error(f"Error cloning module: {str(e)}", exc_info=True)
            raise

    async def update_module(self, module_id: str,
                            request: UpdateModuleRequest) -> ModuleData:
        logger.info(f"Updating module with ID: {module_id}")
        logger.debug(f"Update request: {request.dict()}")

        try:

            result = await self.service.update_module(module_id, request)
            logger.info(f"Module {module_id} updated successfully.")
            return result
        except Exception as e:
            logger.error(f"Error updating module: {str(e)}", exc_info=True)
            raise


controller = ModuleController()


@router.post("/modules/create", tags=["Modules", "Create"])
async def create_module(request: CreateModuleRequest) -> CreateModuleResponse:
    return await controller.create_module(request)


@router.post("/modules/clone", tags=["Modules", "Create"])
async def clone_module(request: CloneModuleRequest) -> CreateModuleResponse:
    """Clone an existing module"""
    return await controller.clone_module(request)


@router.put("/modules/{module_id}/update", tags=["Modules", "Update"])
async def update_module(module_id: str,
                        request: UpdateModuleRequest) -> ModuleData:
    """Update an existing module"""
    return await controller.update_module(module_id, request)


@router.post("/modules/fetch", tags=["Modules", "Read"])
async def fetch_modules(request: FetchModulesRequest) -> FetchModulesResponse:
    return await controller.fetch_modules(request)


@router.get("/modules/fetch/{module_id}", tags=["Modules", "Read"])
async def get_module_by_id(module_id: str) -> ModuleData:
    """Get a single module by ID"""
    return await controller.get_module_by_id(module_id)
