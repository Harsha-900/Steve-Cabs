import sys
import json
import soundfile as sf
import numpy as np
from transformers import AutoModel

# Load model once (cached after first run)
repo_id = "ai4bharat/IndicF5"
model = AutoModel.from_pretrained(repo_id, trust_remote_code=True)

def generate_audio(text, ref_audio_path, ref_text, output_path, sample_rate=24000):
    audio = model(text, ref_audio_path=ref_audio_path, ref_text=ref_text)
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    sf.write(output_path, np.array(audio, dtype=np.float32), sample_rate)
    return output_path

if __name__ == "__main__":
    input_data = json.loads(sys.argv[1])
    generate_audio(
        input_data["text"],
        input_data["ref_audio"],
        input_data["ref_text"],
        input_data["output"]
    )
    print(input_data["output"])