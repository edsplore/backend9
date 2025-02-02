from typing import List, Dict, Any
import aiohttp
from fastapi import HTTPException
from config import RETELL_API_KEY

class VoiceService:
    async def list_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices from Retell AI"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {RETELL_API_KEY}'
                }

                async with session.get(
                    'https://api.retellai.com/list-voices',
                    headers=headers
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail="Failed to fetch voices from Retell AI"
                        )

                    return await response.json()

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching voices: {str(e)}"
            )