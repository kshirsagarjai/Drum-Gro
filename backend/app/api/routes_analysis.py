from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import json

from app.services.audio_prepare import prepare_audio
from app.services.profile_timeline import profile_to_timeline, save_timeline
from app.services.layer_renderer import render_component_layers

router = APIRouter()

jobs = {}


@router.post("/analyze/{file_id}")
async def analyze_drum_stem(file_id: str, background_tasks: BackgroundTasks):
    input_files = list(Path("storage/uploads").glob(f"{file_id}.*"))

    if not input_files:
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    jobs[file_id] = "processing"
    background_tasks.add_task(run_analysis_task, file_id)

    return {
        "file_id": file_id,
        "status": "processing",
        "mode": "manual_profile",
    }


@router.post("/render-layers/{file_id}")
async def render_layers_only(file_id: str):
    processed_dir = Path("storage/processed") / file_id
    prepared_path = processed_dir / "prepared.wav"
    timeline_path = processed_dir / "timeline.json"

    if not prepared_path.exists():
        raise HTTPException(status_code=404, detail="prepared.wav not found")

    if not timeline_path.exists():
        raise HTTPException(status_code=404, detail="timeline.json not found")

    try:
        result = render_component_layers(file_id=file_id, audio_path=prepared_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Layer rendering failed: {e}")

    return {
        "file_id": file_id,
        "status": "completed",
        "layers": result,
    }


@router.get("/status/{file_id}")
async def get_status(file_id: str):
    return {
        "file_id": file_id,
        "status": jobs.get(file_id, "not_found"),
    }


@router.get("/timeline/{file_id}")
async def get_timeline(file_id: str):
    timeline_path = Path("storage/processed") / file_id / "timeline.json"

    if not timeline_path.exists():
        raise HTTPException(status_code=404, detail="Timeline not found")

    with timeline_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/layers/{file_id}")
async def get_layers(file_id: str):
    layers_metadata_path = (
        Path("storage/processed") / file_id / "layers" / "layers.json"
    )

    if not layers_metadata_path.exists():
        raise HTTPException(status_code=404, detail="Layers not found")

    with layers_metadata_path.open("r", encoding="utf-8") as f:
        return json.load(f)
    
@router.get("/audio/{file_id}/{layer_name}")
async def get_audio_layer(file_id: str, layer_name: str):
    """
    Serve rendered audio layers to the frontend.

    Valid layer names:
    - kick
    - snare
    - hi_hat
    - crash
    - full_reconstruction
    - prepared
    """

    allowed_layers = {
        "kick",
        "snare",
        "hi_hat",
        "crash",
        "full_reconstruction",
        "prepared",
    }

    if layer_name not in allowed_layers:
        raise HTTPException(status_code=400, detail="Invalid layer name")

    if layer_name == "prepared":
        audio_path = Path("storage/processed") / file_id / "prepared.wav"
    else:
        audio_path = Path("storage/processed") / file_id / "layers" / f"{layer_name}.wav"

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail=f"{layer_name}.wav not found")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        filename=f"{layer_name}.wav",
    )


def run_analysis_task(file_id: str):
    try:
        prepared_path = prepare_audio(file_id)

        profile_path = Path("app/profiles/billie_jean.json")

        timeline = profile_to_timeline(
            profile_path=profile_path,
            file_id=file_id,
        )

        save_timeline(
            timeline=timeline,
            output_path=Path("storage/processed") / file_id / "timeline.json",
        )

        render_component_layers(
            file_id=file_id,
            audio_path=prepared_path,
        )

        jobs[file_id] = "completed"

    except Exception as e:
        print(f"Analysis failed for {file_id}: {e}")
        jobs[file_id] = "failed"
