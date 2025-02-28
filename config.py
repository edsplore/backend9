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

# Azure OpenAI Configuration
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME",
                                         "gpt-4o-simulator")
AZURE_OPENAI_KEY = os.getenv(
    "AZURE_OPENAI_KEY",
    "9cBKHrEKbc07HRGSQzLaqmB0YvSQLCrDKWRkQBHBPyvAhfrdfCrTJQQJ99BBACYeBjFXJ3w3AAABACOGWBtj"
)
AZURE_OPENAI_BASE_URL = os.getenv(
    "AZURE_OPENAI_BASE_URL", "https://everai-simulator.openai.azure.com")

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

if not RETELL_API_KEY:
    raise ValueError(
        "Retell API key not set. Please set RETELL_API_KEY environment variable."
    )

if not AZURE_OPENAI_DEPLOYMENT_NAME:
    raise ValueError(
        "Azure OpenAI deployment name not set. Please set AZURE_OPENAI_DEPLOYMENT_NAME environment variable."
    )

if not AZURE_OPENAI_KEY:
    raise ValueError(
        "Azure OpenAI key not set. Please set AZURE_OPENAI_KEY environment variable."
    )

if not AZURE_OPENAI_BASE_URL:
    raise ValueError(
        "Azure OpenAI base URL not set. Please set AZURE_OPENAI_BASE_URL environment variable."
    )
