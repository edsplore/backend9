import os
from dotenv import load_dotenv

load_dotenv()

# Provide default values if environment variables are not set
MONGO_URI = os.getenv("mongo-url", "mongodb://localhost:27017")
DB_NAME = os.getenv("db-name", "everai_simulator")  # Default database name if not set

# Validate configuration
if not MONGO_URI:
    raise ValueError("MongoDB URI not set. Please set 'mongo-url' environment variable.")

if not isinstance(DB_NAME, str):
    raise ValueError("Database name must be a string")