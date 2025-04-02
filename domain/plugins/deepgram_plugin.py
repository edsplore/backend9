from semantic_kernel.functions import kernel_function
from typing import List, Dict
import aiohttp


class DeepgramPlugin:

    def __init__(self, api_key: str):
        self.api_key = api_key

    @kernel_function(
        description="Transcribes audio content to text using Deepgram",
        name="transcribe_audio")
    async def transcribe_audio(self, audio_content: bytes) -> str:
        """
        Transcribes audio content using Deepgram API
        """
        url = 'https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&diarize=true'
        headers = {
            'Authorization': f'Token {self.api_key}',
            'Content-Type': 'audio/wav'
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers,
                                    data=audio_content) as response:
                if response.status != 200:
                    raise Exception("Failed to process audio with Deepgram")

                result = await response.json()
                print(result)
                return result.get('results', {}).get('channels', [{}])[0].get(
                    'alternatives',
                    [{}])[0].get('paragraphs').get('transcript', '')
