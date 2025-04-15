from typing import List, Dict, Any
import aiohttp
from fastapi import HTTPException
from config import RETELL_API_KEY
from utils.logger import Logger  # Make sure your import path is correct

logger = Logger.get_logger(__name__)


class VoiceService:

    async def list_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices from Retell AI"""
        logger.info("Fetching list of available voices from Retell AI.")
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {RETELL_API_KEY}'}
                logger.debug(
                    f"GET request to Retell AI: /list-voices with headers: {headers}"
                )

                async with session.get('https://api.retellai.com/list-voices',
                                       headers=headers) as response:
                    logger.debug(
                        f"Retell AI response status: {response.status}")
                    if response.status != 200:
                        logger.error(
                            f"Failed to fetch voices. Status code: {response.status}"
                        )
                        raise HTTPException(
                            status_code=response.status,
                            detail="Failed to fetch voices from Retell AI")

                    voices = await response.json()
                    logger.info(
                        "Successfully retrieved voices from Retell AI.")
                    logger.debug(f"Voices data: {voices}")
                    return voices
        except Exception as e:
            logger.error(f"Error fetching voices: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail=f"Error fetching voices: {str(e)}")
