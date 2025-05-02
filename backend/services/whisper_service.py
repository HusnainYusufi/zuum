import requests


class WhisperService:
    def __init__(self):
        self.url = "https://a487-213-192-2-119.ngrok-free.app/tts"

    def transcribe_audio(self, audio_file: str):
        """
        Transcribe audio using external whisper API service
        
        Args:
            audio_file (str): Base64 encoded audio data
            
        Returns:
            str: Transcribed text from the audio
        """
        
        try:
            # Prepare the request payload
            payload = {
                "audio": audio_file
            }
            
            # Make POST request to the whisper API
            response = requests.post(self.url, json=payload)
            response.raise_for_status()  # Raise exception for non-200 status codes
            
            # Return the transcribed text
            return response.json()
            
        except requests.exceptions.RequestException as e:
            # Handle any request-related errors
            raise Exception(f"Error transcribing audio: {str(e)}")
        

whisper_service = WhisperService()