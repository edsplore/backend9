from fastapi import FastAPI
import uvicorn
from api.controllers.training_controller import router as training_router
from api.controllers.playback_controller import router as playback_router
from api.controllers.script_converter_controller import router as script_converter_router
from api.controllers.simulation_controller import router as simulation_router
from api.controllers.voice_controller import router as voice_router
from api.controllers.module_controller import router as module_router
from api.controllers.training_plan_controller import router as training_plan_router
from api.controllers.list_controller import router as list_router
from api.controllers.assignment_controller import router as assignment_router
from api.controllers.image_controller import router as image_router
from api.controllers.tag_controller import router as tag_router
from api.controllers.manager_controller import router as manager_router
from api.controllers.admin_controller import router as admin_router
from api.controllers.user_controller import router as user_router
from middleware.auth_middleware import JWTAuthMiddleware
from utils.logger import Logger
from fastapi.middleware.cors import CORSMiddleware
from config import ALLOWED_ORIGINS

# Initialize logger
logger = Logger.get_logger(__name__)

app = FastAPI()

# Add JWT authentication middleware
# app.add_middleware(JWTAuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(training_router)
app.include_router(playback_router)
app.include_router(script_converter_router)
app.include_router(simulation_router)
app.include_router(voice_router)
app.include_router(module_router)
app.include_router(training_plan_router)
app.include_router(list_router)
app.include_router(assignment_router)
app.include_router(image_router)
app.include_router(tag_router)
app.include_router(manager_router)
app.include_router(admin_router)
app.include_router(user_router)


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello from EverAI Simulator Backend"}


if __name__ == "__main__":
    logger.info("Starting EverAI Simulator Backend")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
