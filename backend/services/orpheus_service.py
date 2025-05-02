import requests
from flask import Response, stream_with_context




class OrpheusService:
    def __init__(self):
        self.url = "https://a487-213-192-2-119.ngrok-free.app/tts"
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
            return Response(
                stream_with_context(generate()),
                content_type='audio/wav',
                headers={
                    'Cache-Control': 'no-cache',
                    'Transfer-Encoding': 'chunked'
                }
            )

        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return Response(str(e), status=500)
        except Exception as e:
            print(f"Error processing audio: {e}")
            return Response(str(e), status=500)

orpheus_service = OrpheusService()