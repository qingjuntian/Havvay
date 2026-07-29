import os
from io import BytesIO

# Project root = parent of this src/ folder.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ensure ffplay (from ffmpeg) is on PATH so elevenlabs playback can find it
_ffmpeg_bin = r"C:\Program Files\ffmpeg-master-latest-win64-gpl\bin"
if os.path.isdir(_ffmpeg_bin):
    os.environ["PATH"] = _ffmpeg_bin + os.pathsep + os.environ["PATH"]

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

load_dotenv(os.path.join(ROOT, ".env"))

elevenlabs = ElevenLabs(
  api_key=os.getenv("ELEVENLABS_API_KEY"),
)


### Voice cloning example
# voice = elevenlabs.voices.ivc.create(
#     name="My Voice Clone",
#     # Replace with the paths to your audio files.
#     # The more files you add, the better the clone will be.
#     files=[BytesIO(open(os.path.join(ROOT, "data", "samples", "sample.mp3"), "rb").read())]
# )
# print(voice.voice_id)

### Text to speech example
audio = elevenlabs.text_to_speech.convert(
    text="多少人爱过你青春的片影，爱过你的美貌，以虚伪或是真情",
    voice_id="hZTuv9Zqrq4yHYrEmF1r", #"JBFqnCBsd6RMkjVDRZzb",  # "George" - browse voices at elevenlabs.io/app/voice-library
    model_id="eleven_v3",
    output_format="mp3_44100_128",
)

play(audio)