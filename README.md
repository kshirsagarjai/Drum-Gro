# Drum Groove Decomposition Interface

An interactive web tool that separates a drum groove into its individual components – kick, snare, and hi-hat – and allows users to listen to each layer in isolation or in any combination. Designed to assist self-taught musicians in identifying and reproducing drum grooves without formal percussion training.

Built as part of an undergraduate thesis investigating whether interactive groove decomposition improves drum learning outcomes compared to standard audio playback. This repository contains the full-stack application and the performance metric computation scripts used in the associated pilot study.

---

## Table of Contents

- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Tool](#running-the-tool)
- [Processing a New Audio File](#processing-a-new-audio-file)
- [Running the Metric Computation Script](#running-the-metric-computation-script)
- [Backend API Reference](#backend-api-reference)
- [Backend Dependencies](#backend-dependencies)
- [Frontend Dependencies](#frontend-dependencies)
- [Storage Directory](#storage-directory)
- [Pilot Study Data](#pilot-study-data)
- [.gitignore](#gitignore)
- [Acknowledgements](#acknowledgements)
- [Licence](#licence)

---

## Repository Structure

```
drum-groove-decomposition/
│
├── README.md
├── .gitignore
│
├── backend/
│   ├── main.py               # FastAPI entry point and all API route definitions
│   ├── audio_processor.py    # Core audio pipeline (beat tracking, drum detection,
│   │                         # stem separation, timeline generation)
│   ├── requirements.txt      # Python dependencies
│   └── storage/              # Auto-generated at runtime – do not commit contents
│       └── processed/
│           └── <file_id>/
│               └── timeline.json
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       └── components/
│           ├── AudioPlayer.jsx
│           ├── LayerControls.jsx
│           ├── GrooveVisualiser.jsx
│           └── SongSelector.jsx
│
└── metrics/
    ├── compute_metrics.py
    └── data/
        ├── P1_highway_tool.json
        ├── P2_highway_tool.json
        ├── P3_highway_control.json
        └── P3_highway_tool.json
```

> **Note:** Component filenames inside `frontend/src/components/` should be verified against your local project before pushing.

---

## Prerequisites

### Backend
- Python 3.9 or higher
- **ffmpeg** – required by librosa for audio decoding
  - macOS: `brew install ffmpeg`
  - Ubuntu / Debian: `sudo apt install ffmpeg`
  - Windows: download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

### Frontend
- Node.js 18 or higher
- npm 9 or higher

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/drum-groove-decomposition.git
cd drum-groove-decomposition
```

### 2. Set up the backend

```bash
cd backend
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Set up the frontend

```bash
cd frontend
npm install
```

---

## Running the Tool

### Start the backend server

From inside the `backend/` directory with the virtual environment active:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive API docs (Swagger UI) are at `http://localhost:8000/docs`.

### Start the frontend development server

From inside the `frontend/` directory:

```bash
npm run dev
```

The app will be available at `http://localhost:5173` (Vite default).

> The frontend expects the backend to be running on port 8000. If you change the backend port, update the API base URL in `frontend/src/App.jsx` accordingly.

---

## Processing a New Audio File

To generate a ground truth timeline for a new song:

1. Start the backend server (see above).
2. POST the audio file to the `/upload` endpoint via the Swagger UI at `http://localhost:8000/docs`, or use curl:

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@/path/to/your/audio.wav"
```

3. The response will include a `file_id`. The processed timeline will be saved to:

```
backend/storage/processed/<file_id>/timeline.json
```

4. Note this `file_id` – you will need the timeline path if running the metric computation script against this file.

---

## Running the Metric Computation Script

`metrics/compute_metrics.py` computes three performance metrics for each participant recording against a ground truth timeline.

| Metric | Description |
|--------|-------------|
| **Hit rate** | Proportion of ground truth events matched within a ±200 ms tolerance window |
| **MAE** | Mean absolute timing error (ms) of matched hits |
| **CIA** | Component Identification Accuracy – proportion of all ground truth events for which the correct pad (kick or snare) was hit within the tolerance window |

### Setup

The script requires Python with `numpy` installed:

```bash
pip install numpy
```

### Configure file paths

Open `metrics/compute_metrics.py` and update the ground truth path near the top of the file:

```python
GT = load_ground_truth(
    r"../backend/storage/processed/<your_file_id>/timeline.json"
)
```

If your participant JSON files are not in `metrics/data/`, update the four `load_performance()` call paths accordingly.

### Run

```bash
cd metrics
python compute_metrics.py
```

The script will print per-recording metrics and a summary table.

### Offset correction notes

A global offset correction is applied to each recording before metric computation to account for the gap between the MIDI recording clock start and the audio playback start.

- **P1 and P2** use fixed CIA-optimised offsets derived from the pilot study (`-3810 ms` and `-3330 ms` respectively). If you are running new recordings, re-run the CIA offset search by calling `find_best_offset_by_cia()` for each participant before calling `compute_metrics_fixed_offset()`.
- **P3** uses an automated match-count offset search within a ±5 second window.

### Participant JSON format

Each participant JSON file must be a list of hit objects:

```json
[
  { "time_sec": 1.423, "component": "kick" },
  { "time_sec": 1.941, "component": "snare" },
  { "time_sec": 2.103, "component": "hihat" }
]
```

`component` must be one of: `"kick"`, `"snare"`, `"hihat"`.  
`time_sec` is the absolute timestamp in seconds from the start of the MIDI recording clock (before offset correction is applied).

---

## Backend API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload an audio file for processing. Returns a `file_id`. |
| `GET` | `/timeline/{file_id}` | Retrieve the generated timeline JSON for a processed file. |
| `GET` | `/stems/{file_id}/{component}` | Stream a separated audio stem (`kick`, `snare`, `hihat`). |
| `GET` | `/status/{file_id}` | Check the processing status of an uploaded file. |

Full interactive documentation is available at `http://localhost:8000/docs` when the server is running.

---

## Backend Dependencies

Listed in `backend/requirements.txt`. Key packages:

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework and API routing |
| `uvicorn` | ASGI server for running FastAPI |
| `python-multipart` | File upload handling |
| `librosa` | Beat tracking, onset detection, audio analysis |
| `numpy` | Numerical operations |
| `soundfile` | Audio file reading and writing |

Install all with:

```bash
pip install -r backend/requirements.txt
```

---

## Frontend Dependencies

Key packages (see `frontend/package.json` for the full list):

| Package | Purpose |
|---------|---------|
| `react` | UI framework |
| `vite` | Development server and build tooling |
| `axios` | HTTP requests to the backend API |

Install all with:

```bash
cd frontend && npm install
```

Build for production:

```bash
npm run build
```

---

## Storage Directory

The `backend/storage/` directory is created automatically at runtime when the first audio file is processed. It is excluded from version control via `.gitignore`.

Each processed file is stored under its UUID:

```
storage/processed/<file_id>/
└── timeline.json      # Tempo, beat timestamps, and drum event list
```

The `timeline.json` schema:

```json
{
  "tempo": 116.0,
  "beats": [0.517, 1.034, ...],
  "events": [
    { "time": 0.517, "component": "kick" },
    { "time": 1.034, "component": "snare" }
  ]
}
```

> Do not manually edit `timeline.json` files. Re-upload the audio file via `/upload` to regenerate a fresh timeline.

---

## Pilot Study Data

The `metrics/data/` directory contains the four MIDI performance recordings from the pilot study, exported as JSON. All recordings are for the *Highway to Hell* (AC/DC) drum groove excerpt. Participant coding:

| File | Participant | Condition |
|------|-------------|-----------|
| `P1_highway_tool.json` | P1 | Experimental (Interactive Tool) |
| `P2_highway_tool.json` | P2 | Experimental (Interactive Tool) |
| `P3_highway_control.json` | P3 | Control (Audio Playback) |
| `P3_highway_tool.json` | P3 | Experimental (Interactive Tool) |

P1 and P2 completed the Experimental condition only. P3 completed both conditions and is the only participant for whom a within-subjects comparison is available.

---

## .gitignore

Recommended `.gitignore` contents:

```
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Storage – exclude audio files and stems, keep timeline files
backend/storage/
!backend/storage/processed/**/timeline.json

# Node
frontend/node_modules/
frontend/dist/

# Environment variables
.env
.env.local
```

---

## Acknowledgements

Audio analysis pipeline built using [librosa](https://librosa.org).  
Beat tracking based on the dynamic programming beat tracker as implemented in librosa (Ellis, 2007).  
This tool was developed as part of an undergraduate thesis project. The accompanying study is a pilot investigation; all findings are descriptive and intended to inform future confirmatory research.

---

## Licence

MIT
