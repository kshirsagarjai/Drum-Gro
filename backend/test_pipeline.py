import requests
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000/api"

# Put a real pre-separated drum stem in your backend folder
# and make sure this name matches exactly.
TEST_AUDIO = "final_billie_jean.mp3"


def test_pipeline():
    print("1. Uploading drum stem...")

    audio_path = Path(TEST_AUDIO)

    if not audio_path.exists():
        print(f"Error: {audio_path} not found.")
        print("Put a drum stem file in the backend folder, or update TEST_AUDIO.")
        return

    print(f"   Found file: {audio_path.resolve()}")
    print(f"   File size: {audio_path.stat().st_size / 1024 / 1024:.2f} MB")

    try:
        with open(audio_path, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/upload",
                files={"file": (audio_path.name, f, "audio/wav")},
                timeout=60,
            )
    except requests.exceptions.RequestException as e:
        print(f"Upload request failed: {e}")
        print("Check that the FastAPI server is running at http://127.0.0.1:8000")
        return

    print(f"   Upload response code: {response.status_code}")

    if response.status_code != 200:
        print("Upload failed:")
        print(response.text)
        return

    try:
        data = response.json()
    except ValueError:
        print("Upload response was not valid JSON:")
        print(response.text)
        return

    file_id = data.get("file_id")

    if not file_id:
        print("Upload response did not include file_id:")
        print(data)
        return

    print(f"   Uploaded. File ID: {file_id}")

    print("2. Starting analysis...")

    try:
        response = requests.post(
            f"{BASE_URL}/analyze/{file_id}",
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        print(f"Analysis request failed: {e}")
        return

    print(f"   Analysis response code: {response.status_code}")

    if response.status_code != 200:
        print("Analysis trigger failed:")
        print(response.text)
        return

    print("3. Waiting for analysis...")

    max_attempts = 30
    final_status = None

    for attempt in range(1, max_attempts + 1):
        time.sleep(2)

        try:
            response = requests.get(
                f"{BASE_URL}/status/{file_id}",
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            print(f"Status request failed: {e}")
            return

        if response.status_code != 200:
            print(f"Status request returned {response.status_code}:")
            print(response.text)
            return

        try:
            status_data = response.json()
        except ValueError:
            print("Status response was not valid JSON:")
            print(response.text)
            return

        status = status_data.get("status")
        final_status = status

        print(f"   Attempt {attempt}/{max_attempts}, status: {status}")

        if status == "completed":
            break

        if status == "failed":
            print("Analysis failed. Check the Uvicorn terminal for the actual error.")
            return

        if status == "not_found":
            print("Status not found.")
            print("This usually means one of these is true:")
            print("1. main.py is still importing the old routes_process.py router.")
            print("2. test_pipeline.py is calling the wrong route.")
            print("3. The server was not restarted after changing main.py.")
            return

    if final_status != "completed":
        print("Analysis timed out.")
        print("Check the Uvicorn terminal to see whether analysis is stuck or failed silently.")
        return

    print("4. Fetching timeline...")

    try:
        response = requests.get(
            f"{BASE_URL}/timeline/{file_id}",
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        print(f"Timeline request failed: {e}")
        return

    print(f"   Timeline response code: {response.status_code}")

    if response.status_code != 200:
        print("Timeline fetch failed:")
        print(response.text)
        return

    try:
        timeline = response.json()
    except ValueError:
        print("Timeline response was not valid JSON:")
        print(response.text)
        return

    tempo = timeline.get("tempo")
    beats = timeline.get("beats", [])
    events = timeline.get("events", [])

    print(f"   Tempo: {tempo}")
    print(f"   Beats detected: {len(beats)}")
    print(f"   Drum events detected: {len(events)}")

    timeline_path = Path(f"storage/processed/{file_id}/timeline.json")
    prepared_path = Path(f"storage/processed/{file_id}/prepared.wav")

    print("5. Checking output files...")

    if prepared_path.exists():
        print(f"   Found prepared audio: {prepared_path}")
    else:
        print(f"   Missing prepared audio: {prepared_path}")

    if timeline_path.exists():
        print(f"   Found timeline: {timeline_path}")
    else:
        print(f"   Missing timeline: {timeline_path}")

    if prepared_path.exists() and timeline_path.exists():
        print("6. Success. Revised drum-stem analysis pipeline is working.")
    else:
        print("6. Partial success. API returned data, but one or more expected files are missing.")

    print("7. Checking audio layer URLs...")

    layers_to_check = [
      "kick",
      "snare",
      "hi_hat",
      "crash",
     "full_reconstruction",
     "prepared",
    ]

    for layer in layers_to_check:
        response = requests.get(f"{BASE_URL}/audio/{file_id}/{layer}")

        if response.status_code == 200:
            print(f"   {layer}: OK")
        else:
            print(f"   {layer}: FAILED ({response.status_code})")
    

if __name__ == "__main__":
    test_pipeline()
