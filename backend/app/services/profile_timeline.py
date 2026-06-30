from pathlib import Path
import json


def beat_to_seconds(
    bar: int,
    beat: float,
    bpm: float,
    beats_per_bar: int,
    first_event_time_seconds: float,
    first_event_bar: int,
    first_event_beat: float,
) -> float:
    """
    Convert bar + beat position into seconds.

    beat examples:
    1.0 = beat 1
    1.5 = eighth-note after beat 1
    2.0 = beat 2
    """

    seconds_per_beat = 60.0 / bpm

    event_absolute_beats = ((bar - 1) * beats_per_bar) + (beat - 1.0)

    first_absolute_beats = (
        ((first_event_bar - 1) * beats_per_bar)
        + (first_event_beat - 1.0)
    )

    beat_difference = event_absolute_beats - first_absolute_beats

    return first_event_time_seconds + (beat_difference * seconds_per_beat)


def load_profile(profile_path: Path) -> dict:
    with profile_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def profile_to_timeline(profile_path: Path, file_id: str) -> dict:
    profile = load_profile(profile_path)

    bpm = float(profile["bpm"])
    time_signature = profile.get("time_signature", "4/4")
    beats_per_bar = int(time_signature.split("/")[0])

    alignment = profile["audio_alignment"]

    first_event_time_seconds = float(alignment["first_event_time_seconds"])
    first_event_bar = int(alignment["first_event_bar"])
    first_event_beat = float(alignment["first_event_beat"])

    events = []

    for event in profile["events"]:
        bar = int(event["bar"])
        beat = float(event["beat"])
        components = list(event["components"])

        time_seconds = beat_to_seconds(
            bar=bar,
            beat=beat,
            bpm=bpm,
            beats_per_bar=beats_per_bar,
            first_event_time_seconds=first_event_time_seconds,
            first_event_bar=first_event_bar,
            first_event_beat=first_event_beat,
        )

        events.append(
            {
                "time": round(time_seconds, 6),
                "bar": bar,
                "beat": beat,
                "components": components,
                "confidence": {
                    component: 1.0 for component in components
                },
                "label": components[0] if components else "unknown",
                "source": "manual_profile",
            }
        )

    timeline = {
        "file_id": file_id,
        "song": profile.get("song"),
        "artist": profile.get("artist"),
        "tempo": bpm,
        "time_signature": time_signature,
        "events": events,
        "summary": summarize_profile_events(events),
    }

    return timeline


def summarize_profile_events(events: list[dict]) -> dict:
    summary = {
        "total_events": len(events),
        "kick": 0,
        "snare": 0,
        "hi_hat": 0,
        "crash": 0,
        "unknown": 0,
        "multi_component_events": 0,
    }

    for event in events:
        components = event.get("components", [])

        if len(components) > 1:
            summary["multi_component_events"] += 1

        if not components:
            summary["unknown"] += 1

        for component in components:
            if component not in summary:
                summary[component] = 0

            summary[component] += 1

    return summary


def save_timeline(timeline: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2)

    return output_path
