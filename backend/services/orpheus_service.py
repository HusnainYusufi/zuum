import requests
from fastapi.responses import StreamingResponse
from fastapi import HTTPException




class OrpheusService:
    def __init__(self):
        self.url = "https://legal-bluebird-bright.ngrok-free.app/api/v1/tts"
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
            
            # Return a streaming response directly with the content from the external API
            return StreamingResponse(
                response.iter_content(chunk_size=1024),
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