import requests

class WhisperService:
    def __init__(self):
        self.api_link = 'https://9ad2-213-192-2-119.ngrok-free.app/api/v1/transcribe'
        
    def transcribe_audio(self, audio_file):
        files = {"audio": audio_file}
        response = requests.post(self.api_link, files=files)

        if response.status_code == 200:
            return response.json()["text"]
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None

whisper_service = WhisperService()