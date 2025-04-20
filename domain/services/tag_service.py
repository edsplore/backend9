from typing import Dict, List
from datetime import datetime
from infrastructure.database import Database
from api.schemas.requests import CreateTagRequest
from api.schemas.responses import TagData
from fastapi import HTTPException
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class TagService:

    def __init__(self):
        self.db = Database()
        logger.info("TagService initialized.")

    async def create_tag(self, request: CreateTagRequest) -> Dict:
        """Create a new tag"""
        logger.info("Creating new tag.")
        logger.debug(f"Tag request data: {request.dict()}")
        try:
            tag_doc = {
                "name": request.name,
                "createdBy": request.user_id,
                "createdAt": datetime.utcnow(),
                "lastModifiedBy": request.user_id,
                "lastModifiedAt": datetime.utcnow()
            }

            result = await self.db.tags.insert_one(tag_doc)
            logger.info(f"Tag created with ID: {result.inserted_id}")
            return {"id": str(result.inserted_id), "status": "success"}
        except Exception as e:
            logger.error(f"Error creating tag: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error creating tag: {str(e)}")

    async def fetch_tags(self, user_id: str) -> List[TagData]:
        """Fetch all tags"""
        logger.info(f"Fetching tags for user_id={user_id}")
        try:
            cursor = self.db.tags.find({})
            tags = []

            async for doc in cursor:
                tag = TagData(
                    id=str(doc["_id"]),
                    name=doc.get("name", ""),
                    created_by=doc.get("createdBy", ""),
                    created_at=doc.get("createdAt",
                                       datetime.utcnow()).isoformat(),
                    last_modified_by=doc.get("lastModifiedBy", ""),
                    last_modified_at=doc.get("lastModifiedAt",
                                             datetime.utcnow()).isoformat())
                tags.append(tag)

            logger.info(f"Fetched {len(tags)} tags")
            return tags
        except Exception as e:
            logger.error(f"Error fetching tags: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error fetching tags: {str(e)}")
