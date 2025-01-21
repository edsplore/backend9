from fastapi import FastAPI
import uvicorn
from api.controllers.training_controller import router as training_router
from api.controllers.playback_controller import router as playback_router

app = FastAPI()

app.include_router(training_router)
app.include_router(playback_router)

@app.get("/")
async def root():
    return {"message": "Hello from EverAI Simulator Backend"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)