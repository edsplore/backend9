import os
from dotenv import load_dotenv

load_dotenv()

# Load environment variables (no defaults)
MONGO_URI = os.getenv("mongo-url")
DB_NAME = os.getenv("db-name")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RETELL_API_KEY = os.getenv("RETELL_API_KEY")
PUBLIC_KEY_PATH = os.getenv("PUBLIC_KEY_PATH")

#Allowed origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")

# Azure OpenAI Configuration
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_BASE_URL = os.getenv("AZURE_OPENAI_BASE_URL")

# Validate configuration
if not MONGO_URI:
    raise ValueError(
        "MongoDB URI not set. Please set 'mongo-url' environment variable.")

if not DB_NAME:
    raise ValueError(
        "Database name not set. Please set 'db-name' environment variable.")

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

if not PUBLIC_KEY_PATH:
    raise ValueError(
        "Public key path not set. Please set PUBLIC_KEY_PATH environment variable."
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
