import requests
import sounddevice as sd
import soundfile as sf
import io
import wave
import time
from datetime import datetime
import os



def get_orpheus_response(query: str):
        # Prepare the request data
    data = {
        "text": query,
        "voice": "zac"
    }
    
    try:
        # Make streaming request
        response = requests.post(url, json=data, stream=True)
        response.raise_for_status()
        
        # Create a binary buffer for the audio data
        audio_data = io.BytesIO()
        
        # Stream the response data
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                audio_data.write(chunk)
        
        # Reset buffer position
        audio_data.seek(0)
        
        # Create generated_audio directory if it doesn't exist
        os.makedirs('generated_audio', exist_ok=True)
        
        
        # Play audio if requested
        if play_audio:
            audio_data.seek(0)
            with wave.open(audio_data, 'rb') as wav_file:
                # Get audio parameters
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                framerate = wav_file.getframerate()
                frames = wav_file.readframes(wav_file.getnframes())
                
                # Convert to numpy array and play
                import numpy as np
                audio_array = np.frombuffer(frames, dtype=np.int16)
                sd.play(audio_array, framerate)
                sd.wait()  # Wait until audio finishes playing

    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
    except Exception as e:
        print(f"Error processing audio: {e}")
