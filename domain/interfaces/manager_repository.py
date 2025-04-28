from abc import ABC, abstractmethod
from typing import Dict

class IManagerRepository(ABC):
    @abstractmethod
    async def get_manager_dashboard_data(self, user_id: str) -> Dict:
        pass
    
    