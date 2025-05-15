import requests
from fastapi.responses import StreamingResponse
from fastapi import HTTPException




class OrpheusService:
    def __init__(self):
        self.url = "https://929f-216-81-245-137.ngrok-free.app/api/v1/tts"
        self.voice = "zac"

    def stream_audio_response(self, text: str):
        # Prepare the request data
        data = {
            "text": text,
            "voice": self.voice
        }
        
        try:
            # Make streaming request
            response = requests.post(self.url, json=data, stream=True)
            response.raise_for_status()
            
            # Create a generator function to stream the chunks
            def generate():
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk
            
            # Return a streaming response with appropriate headers
            return StreamingResponse(
                generate(),
                media_type='audio/wav',
                headers={
                    'Cache-Control': 'no-cache'
                }
            )

        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            print(f"Error processing audio: {e}")
            raise HTTPException(status_code=500, detail=str(e))

orpheus_service = OrpheusService()