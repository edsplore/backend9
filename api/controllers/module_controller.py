from fastapi import APIRouter, HTTPException, Request
from domain.services.module_service import ModuleService
from api.schemas.requests import (CreateModuleRequest, FetchModulesRequest,
                                  CloneModuleRequest, UpdateModuleRequest,
                                  PaginationParams)
from api.schemas.responses import (CreateModuleResponse, FetchModulesResponse,
                                   ModuleData, PaginationMetadata)

from utils.logger import Logger

logger = Logger.get_logger(__name__)

router = APIRouter()


class ModuleController:

    def __init__(self):
        self.service = ModuleService()
        logger.info("ModuleController initialized.")

    async def create_module(
            self, request: CreateModuleRequest, workspace: str) -> CreateModuleResponse:
        logger.info(f"Request received to create a new module in workspace {workspace}.")
        logger.debug(f"Request data: {request.dict()}")

        try:

            result = await self.service.create_module(request, workspace)

            # Check for duplicate name error
            if result.get("status") == "error":
                # Return a 409 Conflict for duplicate names
                if "already exists" in result.get("message", ""):
                    raise HTTPException(status_code=409,
                                        detail=result["message"])
                # Handle other errors with a 400 Bad Request
                else:
                    raise HTTPException(status_code=400,
                                        detail=result["message"])

            logger.info(f"Module created with ID: {result['id']} in workspace {workspace}")
            return CreateModuleResponse(id=result["id"],
                                        status=result["status"])
        except Exception as e:
            logger.error(f"Error creating module: {str(e)}", exc_info=True)
            raise

    async def fetch_modules(
        self, request: FetchModulesRequest, workspace: str) -> FetchModulesResponse:
        logger.info(f"Fetching modules for user_id: {request.user_id} in workspace {workspace}")
        try:
            # Pass the pagination parameters and workspace to the service layer
            result = await self.service.fetch_modules(
                request.user_id, 
                workspace,
                pagination=request.pagination
            )

            modules = result["modules"]
            total_count = result["total_count"]

            # Create pagination metadata if pagination was requested
            pagination_metadata = None
            if request.pagination:
                page = request.pagination.page
                pagesize = request.pagination.pagesize
                total_pages = (total_count + pagesize - 1) // pagesize  # Ceiling division

                pagination_metadata = PaginationMetadata(
                    total_count=total_count,
                    page=page,
                    pagesize=pagesize,
                    total_pages=total_pages
                )

            logger.info(f"Fetched {len(modules)} module(s) out of {total_count} total.")
            return FetchModulesResponse(
                modules=modules,
                pagination=pagination_metadata
            )
        except Exception as e:
            logger.error(f"Error fetching modules: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching modules: {str(e)}")

    async def get_module_by_id(self, module_id: str, workspace: str) -> ModuleData:
        logger.info(f"Fetching module by ID: {module_id} in workspace {workspace}")
        try:

            module = await self.service.get_module_by_id(module_id, workspace)
            if not module:
                logger.warning(f"Module with ID {module_id} not found in workspace {workspace}.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Module with id {module_id} not found in workspace {workspace}")

            logger.info(f"Module with ID {module_id} fetched successfully.")
            return module
        except Exception as e:
            logger.error(f"Error fetching module by ID: {str(e)}",
                         exc_info=True)
            raise

    async def clone_module(
            self, request: CloneModuleRequest, workspace: str) -> CreateModuleResponse:
        logger.info(f"Cloning module in workspace {workspace}.")
        logger.debug(f"Clone request data: {request.dict()}")

        try:

            result = await self.service.clone_module(request, workspace)
            logger.info(f"Module cloned. New ID: {result['id']}")
            return CreateModuleResponse(id=result["id"],
                                        status=result["status"])
        except Exception as e:
            logger.error(f"Error cloning module: {str(e)}", exc_info=True)
            raise

    async def update_module(self, module_id: str,
                            request: UpdateModuleRequest, workspace: str) -> ModuleData:
        logger.info(f"Updating module with ID: {module_id} in workspace {workspace}")
        logger.debug(f"Update request: {request.dict()}")

        try:

            result = await self.service.update_module(module_id, request, workspace)
            logger.info(f"Module {module_id} updated successfully.")
            return result
        except Exception as e:
            logger.error(f"Error updating module: {str(e)}", exc_info=True)
            raise


controller = ModuleController()


@router.post("/modules/create", tags=["Modules", "Create"])
async def create_module(request: CreateModuleRequest, current_request: Request) -> CreateModuleResponse:
    workspace = current_request.headers.get('x-workspace-id')
    if not workspace:
        raise HTTPException(status_code=400, detail="Workspace ID is required")
    return await controller.create_module(request, workspace)


@router.post("/modules/clone", tags=["Modules", "Create"])
async def clone_module(request: CloneModuleRequest, current_request: Request) -> CreateModuleResponse:
    """Clone an existing module"""
    workspace = current_request.headers.get('x-workspace-id')
    if not workspace:
        raise HTTPException(status_code=400, detail="Workspace ID is required")
    return await controller.clone_module(request, workspace)


@router.put("/modules/{module_id}/update", tags=["Modules", "Update"])
async def update_module(module_id: str,
                        request: UpdateModuleRequest, current_request: Request) -> ModuleData:
    """Update an existing module"""
    workspace = current_request.headers.get('x-workspace-id')
    if not workspace:
        raise HTTPException(status_code=400, detail="Workspace ID is required")
    return await controller.update_module(module_id, request, workspace)


@router.post("/modules/fetch", tags=["Modules", "Read"])
async def fetch_modules(request: FetchModulesRequest, current_request: Request) -> FetchModulesResponse:
    workspace = current_request.headers.get('x-workspace-id')
    if not workspace:
        raise HTTPException(status_code=400, detail="Workspace ID is required")
    return await controller.fetch_modules(request, workspace)


@router.get("/modules/fetch/{module_id}", tags=["Modules", "Read"])
async def get_module_by_id(module_id: str, current_request: Request) -> ModuleData:
    """Get a single module by ID"""
    workspace = current_request.headers.get('x-workspace-id')
    if not workspace:
        raise HTTPException(status_code=400, detail="Workspace ID is required")
    return await controller.get_module_by_id(module_id, workspace)