from fastapi import APIRouter, HTTPException
from bson import ObjectId
from fastapi.responses import Response
from infrastructure.database import Database

from utils.logger import Logger

logger = Logger.get_logger(__name__)


router = APIRouter()


class ImageController:
    def __init__(self):
        self.db = Database()
        logger.info("ImageController initialized.")
    
    async def get_image(self, image_id: str):
        """Retrieve an image by ID"""
        logger.info(f"Received request to fetch image with ID: {image_id}")
        try:
            image_id_object = ObjectId(image_id)
            logger.debug(f"Converted image_id to ObjectId: {image_id_object}")
    
            image = await self.db.images.find_one({"_id": image_id_object})
            if not image:
                logger.warning(f"No image found for ID: {image_id}")
                raise HTTPException(status_code=404, detail="Image not found")
    
            logger.info(f"Image found for ID: {image_id}")
            return Response(content=image["data"],
                            media_type=image["contentType"])
    
        except Exception as e:
            logger.error(f"Error retrieving image with ID {image_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error retrieving image: {str(e)}")


controller = ImageController()

@router.get("/images/{image_id}", tags=["Images"])
async def get_image(image_id: str):
    """Get image by ID"""
    return await controller.get_image(image_id)
