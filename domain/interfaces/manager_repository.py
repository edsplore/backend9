from abc import ABC, abstractmethod
from typing import Dict, List
from api.schemas.responses import ( FetchManagerDashboardResponse)

class IManagerRepository(ABC):
    @abstractmethod
    async def get_manager_dashboard_data(self, user_id: str) -> Dict:
        pass
    @abstractmethod
    async def get_all_assigments_by_user_details(self, user_id: str, reporting_userIds: List[str], type: str) -> FetchManagerDashboardResponse:
        pass
    
    