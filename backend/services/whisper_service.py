import requests
import base64
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self):
        self.api_link = 'https://legal-bluebird-bright.ngrok-free.app/api/v1/sst'
        
    def transcribe_audio(self, audio_data):
        """
        Transcribe audio using external Whisper API service
        
        Args:
            audio_data: Either base64 encoded string or raw audio bytes
        
        Returns:
            Transcribed text or None if error
        """
        try:
            # Check if input is already base64 string (from JSON request)
            if isinstance(audio_data, str):
                # Already base64 encoded, send as JSON
                response = requests.post(
                    self.api_link,
                    json={"audio": audio_data},
                    headers={"Content-Type": "application/json"}
                )
            else:
                # Binary audio data, send as file
                # Make sure we're sending a file-like object
                if not hasattr(audio_data, 'read'):
                    # Convert bytes to file-like object if needed
                    audio_data = BytesIO(audio_data)
                
                files = {"audio": audio_data}
                response = requests.post(self.api_link, files=files)

            if response.status_code == 200:
                result = response.json()
                print(result)
                return result.get("text", "")
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return None

whisper_service = WhisperService()