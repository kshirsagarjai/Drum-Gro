from pathlib import Path
import librosa
import soundfile as sf

UPLOAD_DIR = Path("storage/uploads")
PROCESSED_DIR = Path("storage/processed")

def prepare_audio(file_id: str) -> Path:
    input_files = list(UPLOAD_DIR.glob(f"{file_id}.*"))

    if not input_files:
        raise FileNotFoundError(f"No uploaded file found for {file_id}")

    input_path = input_files[0]

    output_dir = PROCESSED_DIR / file_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "prepared.wav"

    audio, sr = librosa.load(
        str(input_path),
        sr=44100,
        mono=True
    )

    sf.write(str(output_path), audio, 44100)

    return output_path
