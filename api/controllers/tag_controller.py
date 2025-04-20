from fastapi import APIRouter, HTTPException
from domain.services.tag_service import TagService
from api.schemas.requests import CreateTagRequest, FetchTagsRequest
from api.schemas.responses import CreateTagResponse, FetchTagsResponse
from utils.logger import Logger

logger = Logger.get_logger(__name__)

router = APIRouter()


class TagController:

    def __init__(self):
        self.service = TagService()
        logger.info("TagController initialized.")

    async def create_tag(self, request: CreateTagRequest) -> CreateTagResponse:
        logger.info("Received request to create a new tag.")
        logger.debug(f"Request data: {request.dict()}")
        try:
            result = await self.service.create_tag(request)
            logger.info(f"Tag created successfully: {result}")
            return CreateTagResponse(id=result["id"], status=result["status"])
        except Exception as e:
            logger.error(f"Error creating tag: {str(e)}", exc_info=True)
            raise

    async def fetch_tags(self, request: FetchTagsRequest) -> FetchTagsResponse:
        logger.info("Fetching all tags.")
        try:
            tags = await self.service.fetch_tags(request.user_id)
            logger.debug(f"Tags fetched: {tags}")
            return FetchTagsResponse(tags=tags)
        except Exception as e:
            logger.error(f"Error fetching tags: {str(e)}", exc_info=True)
            raise


controller = TagController()


@router.post("/tags/create", tags=["Tags", "Create"])
async def create_tag(request: CreateTagRequest) -> CreateTagResponse:
    """Create a new tag"""
    return await controller.create_tag(request)


@router.post("/tags/fetch", tags=["Tags", "Read"])
async def fetch_tags(request: FetchTagsRequest) -> FetchTagsResponse:
    """Fetch all tags"""
    return await controller.fetch_tags(request)
