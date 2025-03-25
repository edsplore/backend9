from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                client = AsyncIOMotorClient(MONGO_URI)
                db = client[DB_NAME]

                # Initialize collections
                cls._instance.users = db["users"]
                cls._instance.assignments = db["assignments"]
                cls._instance.training_plans = db["trainingPlans"]
                cls._instance.modules = db["modules"]
                cls._instance.simulations = db["simulations"]
                cls._instance.user_sim_progress = db["userSimulationProgress"]
                cls._instance.sim_attempts = db["simulationAttempts"]
                cls._instance.images = db[
                    "images"]  # New collection for storing images
            except Exception as e:
                raise ConnectionError(
                    f"Failed to connect to MongoDB: {str(e)}")

        return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
