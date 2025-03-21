from fastapi import APIRouter, HTTPException
from bson import ObjectId
from fastapi.responses import Response
from infrastructure.database import Database

router = APIRouter()


class ImageController:

    def __init__(self):
        self.db = Database()

    async def get_image(self, image_id: str):
        """Retrieve an image by ID"""
        try:
            # Convert string ID to ObjectId
            image_id_object = ObjectId(image_id)

            # Get image document
            image = await self.db.images.find_one({"_id": image_id_object})
            if not image:
                raise HTTPException(status_code=404, detail="Image not found")

            # Return image with proper content type
            return Response(content=image["data"],
                            media_type=image["contentType"])

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Error retrieving image: {str(e)}")


controller = ImageController()


@router.get("/images/{image_id}", tags=["Images"])
async def get_image(image_id: str):
    """Get image by ID"""
    return await controller.get_image(image_id)
