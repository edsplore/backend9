# domain/services/simulation_service.py
from typing import Dict, List
import json
import aiohttp
from datetime import datetime
from config import OPENAI_API_KEY
from infrastructure.database import Database
from api.schemas.requests import CreateSimulationRequest
from fastapi import HTTPException 

class SimulationService:
    def __init__(self):
        self.db = Database()

    async def create_simulation(self, request: CreateSimulationRequest) -> str:
        """Create a new simulation"""
        try:
            # Generate prompt using OpenAI
            prompt = await self._generate_simulation_prompt(request.script)

            # Create simulation document
            simulation_doc = {
                "name": request.name,
                "divisionId": request.division_id,
                "departmentId": request.department_id,
                "type": request.type,
                "script": [s.dict() for s in request.script],
                "lastModifiedBy": request.user_id,
                "lastModified": datetime.utcnow(),
                "createdBy": request.user_id,
                "createdOn": datetime.utcnow(),
                "status": "draft",
                "version": 1,
                "prompt": prompt,
                "tags": request.tags
            }

            # Insert into database
            result = await self.db.simulations.insert_one(simulation_doc)
            return str(result.inserted_id)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating simulation: {str(e)}")

    async def _generate_simulation_prompt(self, script: List[Dict]) -> str:
        """Generate simulation prompt using OpenAI"""
        try:
            # Convert script to conversation format for prompt
            conversation = "\n".join([
                f"{s.role}: {s.script_sentence}" for s in script
            ])

            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {OPENAI_API_KEY}',
                    'Content-Type': 'application/json'
                }

                data = {
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Create a detailed prompt for a customer service simulation based on the following conversation. The prompt should help generate realistic customer responses that match the conversation flow and context. Consider the sequence of interactions and maintain consistency with the original conversation."
                        },
                        {
                            "role": "user",
                            "content": conversation
                        }
                    ]
                }

                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail=response
                        )

                    result = await response.json()
                    return result['choices'][0]['message']['content']

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating simulation prompt: {str(e)}"
            )
