import requests
import base64
import io


class WhisperService:
    def __init__(self):
        self.url = "https://ef37-213-192-2-119.ngrok-free.app/api/v1/transcribe"

    def transcribe_audio(self, audio_file: str):
        """
        Transcribe audio using external whisper API service
        
        Args:
            audio_file (str): Base64 encoded audio data
            
        Returns:
            str: Transcribed text from the audio
        """
        
        try:
            # Decode base64 string to binary data
            audio_bytes = base64.b64decode(audio_file)
            
            # Create a file-like object from the bytes
            audio_file_obj = io.BytesIO(audio_bytes)
            
            # Send as multipart form upload - matching the new API expectation
            files = {
                'audio': ('audio.mp3', audio_file_obj, 'audio/mpeg')
            }
            
            # Make the request
            response = requests.post(self.url, files=files)
            response.raise_for_status()
            
            # Process the response
            try:
                result = response.json()
                return result.get('text', result)
            except:
                return response.text
            
        except requests.exceptions.RequestException as e:
            # Handle any request-related errors
            raise Exception(f"Error transcribing audio: {str(e)}")
        

whisper_service = WhisperService()

