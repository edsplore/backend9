from fastapi import APIRouter, HTTPException
from domain.services.module_service import ModuleService
from api.schemas.requests import CreateModuleRequest, FetchModulesRequest
from api.schemas.responses import CreateModuleResponse, FetchModulesResponse

router = APIRouter()


class ModuleController:

    def __init__(self):
        self.service = ModuleService()

    async def create_module(
            self, request: CreateModuleRequest) -> CreateModuleResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.module_name:
            raise HTTPException(status_code=400, detail="Missing 'moduleName'")
        if not request.simulations:
            raise HTTPException(status_code=400,
                                detail="Missing 'simulations'")

        result = await self.service.create_module(request)
        return CreateModuleResponse(id=result["id"], status=result["status"])

    async def fetch_modules(
            self, request: FetchModulesRequest) -> FetchModulesResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")

        modules = await self.service.fetch_modules(request.user_id)
        return FetchModulesResponse(modules=modules)


controller = ModuleController()


@router.post("/modules/create", tags=["Modules", "Create"])
async def create_module(request: CreateModuleRequest) -> CreateModuleResponse:
    return await controller.create_module(request)


@router.post("/modules/fetch", tags=["Modules", "Read"])
async def fetch_modules(request: FetchModulesRequest) -> FetchModulesResponse:
    return await controller.fetch_modules(request)
