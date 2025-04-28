from typing import Dict, List, Optional
from datetime import datetime
from domain.interfaces.manager_repository import IManagerRepository
from infrastructure.repositories.manager_repository import ManagerRepository
from fastapi import HTTPException

from utils.logger import Logger  # Make sure the import path is correct for your project

logger = Logger.get_logger(__name__)

class ManagerService:

    def __init__(self, repository: IManagerRepository = None):
        self.repository = repository or ManagerRepository()
        logger.info("ManagerService initialized.")