import os
from dotenv import load_dotenv

load_dotenv()

# Provide default values if environment variables are not set
MONGO_URI = os.getenv("mongo-url", "mongodb://localhost:27017")
DB_NAME = os.getenv("db-name",
                    "everai_simulator")  # Default database name if not set
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY",
                             "90b109a0bc690efde72b6e9da892d9371885cb8f")
OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "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"
)
RETELL_API_KEY = os.getenv("RETELL_API_KEY",
                           "key_c98334da2d625bae2d5c9a24d33f")

# Validate configuration
if not MONGO_URI:
    raise ValueError(
        "MongoDB URI not set. Please set 'mongo-url' environment variable.")

if not isinstance(DB_NAME, str):
    raise ValueError("Database name must be a string")

if not DEEPGRAM_API_KEY:
    raise ValueError(
        "Deepgram API key not set. Please set DEEPGRAM_API_KEY environment variable."
    )

if not OPENAI_API_KEY:
    raise ValueError(
        "OpenAI API key not set. Please set OPENAI_API_KEY environment variable."
    )

if not RETELL_API_KEY:
    raise ValueError(
        "Retell API key not set. Please set RETELL_API_KEY environment variable."
    )
