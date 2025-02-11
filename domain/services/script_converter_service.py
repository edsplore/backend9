from fastapi import UploadFile, HTTPException
from typing import List, Dict
import json
import aiohttp
import asyncio
from config import DEEPGRAM_API_KEY, OPENAI_API_KEY
import PyPDF2
import io
import docx

class ScriptConverterService:
    async def convert_audio_to_script(self, user_id: str, audio_file: UploadFile) -> List[Dict[str, str]]:
        """
        Convert audio to script using Deepgram.
        """
        try:
            # Read the audio file content
            audio_content = await audio_file.read()

            # Prepare the Deepgram API request
            url = 'https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&diarize=true'
            headers = {
                'Authorization': f'Token {DEEPGRAM_API_KEY}',
                'Content-Type': 'audio/wav'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=audio_content) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail="Failed to process audio with Deepgram"
                        )

                    result = await response.json()

                    # Extract the transcript from Deepgram response
                    print(result.get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0].get('paragraphs').get('transcript', ''))
                    transcript = result.get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0].get('paragraphs').get('transcript', '')

                    # Convert transcript to conversation format using GPT-4
                    print(transcript)
                    return await self._convert_transcript_to_conversation_format(transcript)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

    async def convert_text_to_script(self, user_id: str, prompt: str) -> List[Dict[str, str]]:
        """
        Convert text to conversation script using GPT-4.
        """
        try:
            return await self._convert_prompt_to_conversation_format(prompt)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error converting text to script: {str(e)}")

    async def convert_file_to_script(self, user_id: str, file: UploadFile) -> List[Dict[str, str]]:
        """
        Convert file content to conversation script using GPT-4.
        """
        try:
            # Read file content based on type
            content = await self._extract_text_from_file(file)

            # Convert to conversation format
            return await self._convert_prompt_to_conversation_format(content)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

    async def _extract_text_from_file(self, file: UploadFile) -> str:
        """
        Extract text content from different file types
        """
        content = await file.read()

        if file.content_type == 'text/plain':
            return content.decode('utf-8')

        elif file.content_type == 'application/pdf':
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            return ' '.join(page.extract_text() for page in pdf_reader.pages)

        elif file.content_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            doc = docx.Document(io.BytesIO(content))
            return ' '.join(paragraph.text for paragraph in doc.paragraphs)

        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

    async def _convert_prompt_to_conversation_format(self, content: str) -> List[Dict[str, str]]:
        """
        Convert content to conversation format using GPT-4
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {OPENAI_API_KEY}',
                    'Content-Type': 'application/json'
                }

                data = {
                    "model": "gpt-4o",
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": "Convert the following text into a natural conversation between a user and an assistant. Return the result as a JSON object with a 'script' array containing objects with 'role' and 'message' fields. The conversation should flow naturally and make sense. There are only two roles 'Customer' and 'Trainee' in the conversation. The user is always the Customer and the Trainee is always the assistant."
                        },
                        {
                            "role": "user",
                            "content": content
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
                            detail="Failed to process with GPT-4"
                        )

                    result = await response.json()

                    # Extract the conversation from GPT-4 response
                    try:
                        conversation = json.loads(result['choices'][0]['message']['content'])
                        return conversation.get('script', [])
                    except (KeyError, json.JSONDecodeError) as e:
                        raise HTTPException(
                            status_code=500,
                            detail="Failed to parse GPT-4 response"
                        )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error converting to conversation format: {str(e)}"
            )

    async def _convert_transcript_to_conversation_format(self, content: str) -> List[Dict[str, str]]:
        print(content)
        """
        Convert content to conversation format using GPT-4
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {OPENAI_API_KEY}',
                    'Content-Type': 'application/json'
                }
    
                data = {
                    "model": "gpt-4o",
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": "Convert the following phoneCall transcript of two callers marked as Speaker 0 and Speaker 1 into a conversation between a Customer and Trainee. Return the result as a JSON object with a 'script' array containing objects with 'role' and 'message' fields. Also, do not add conversation from your end. As per transcript you can start conversation with either Customer or Trainee. Do not miss any important line from transcript."
                        },
                        {
                            "role": "user",
                            "content": content
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
                            detail="Failed to process with GPT-4"
                        )
    
                    result = await response.json()
    
                    # Extract the conversation from GPT-4 response
                    try:
                        conversation = json.loads(result['choices'][0]['message']['content'])
                        return conversation.get('script', [])
                    except (KeyError, json.JSONDecodeError) as e:
                        raise HTTPException(
                            status_code=500,
                            detail="Failed to parse GPT-4 response"
                        )
    
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error converting to conversation format: {str(e)}"
            )