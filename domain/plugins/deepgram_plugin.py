import aiohttp
from typing import List, Dict
from semantic_kernel.functions import kernel_function
from utils.logger import Logger  # Make sure this path matches your project structure

logger = Logger.get_logger(__name__)


class DeepgramPlugin:

    def __init__(self, api_key: str):
        self.api_key = api_key
        logger.info("DeepgramPlugin initialized.")

    @kernel_function(
        description="Transcribes audio content to text using Deepgram",
        name="transcribe_audio")
    async def transcribe_audio(self, audio_content: bytes) -> str:
        """
        Transcribes audio content using Deepgram API
        """
        logger.info("Received request to transcribe audio using Deepgram.")
        url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&diarize=true"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav"
        }

        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(f"POST to Deepgram API: {url}")
                async with session.post(url,
                                        headers=headers,
                                        data=audio_content) as response:
                    if response.status != 200:
                        logger.error(
                            f"Deepgram API returned status {response.status}")
                        raise Exception(
                            "Failed to process audio with Deepgram")

                    result = await response.json()
                    logger.debug(f"Deepgram API response: {result}")
                    transcript = (result.get("results", {}).get(
                        "channels",
                        [{}])[0].get("alternatives",
                                     [{}])[0].get("paragraphs",
                                                  {}).get("transcript", ""))

                    logger.info("Audio transcribed successfully.")
                    return transcript
        except Exception as e:
            logger.error(f"Error transcribing audio with Deepgram: {str(e)}",
                         exc_info=True)
            raise

    async def transcribe_audio_visual(self, audio_content: bytes) -> str:
        """
        Transcribes audio content using Deepgram API
        """
        logger.info("Received request to transcribe audio using Deepgram.")
        url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav"
        }

        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(f"POST to Deepgram API: {url}")
                async with session.post(url,
                                        headers=headers,
                                        data=audio_content) as response:
                    if response.status != 200:
                        logger.error(
                            f"Deepgram API returned status {response.status}")
                        raise Exception(
                            "Failed to process audio with Deepgram")

                    result = await response.json()
                    logger.debug(f"Deepgram API response: {result}")
                    transcript = (result.get("results", {}).get(
                        "channels",
                        [{}])[0].get("alternatives",
                                     [{}])[0].get("paragraphs",
                                                  {}).get("transcript", ""))

                    logger.info("Audio transcribed successfully.")
                    return transcript
        except Exception as e:
            logger.error(f"Error transcribing audio with Deepgram: {str(e)}",
                         exc_info=True)
            raise
