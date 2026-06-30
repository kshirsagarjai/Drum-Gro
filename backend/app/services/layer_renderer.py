from pathlib import Path
import json

import numpy as np
import soundfile as sf


LABELS = [
    "kick",
    "snare",
    "hi_hat",
    "crash",
]


def _make_envelope(length: int, attack: int, decay: int) -> np.ndarray:
    """
    Create a simple attack-decay envelope.
    """
    if length <= 0:
        return np.array([], dtype=np.float32)

    attack = max(1, min(attack, length))
    decay = max(1, min(decay, length - attack))

    sustain = max(0, length - attack - decay)

    attack_curve = np.linspace(0.0, 1.0, attack, dtype=np.float32)
    decay_curve = np.linspace(1.0, 0.0, decay, dtype=np.float32)

    if sustain > 0:
        sustain_curve = np.zeros(sustain, dtype=np.float32)
        envelope = np.concatenate([attack_curve, decay_curve, sustain_curve])
    else:
        envelope = np.concatenate([attack_curve, decay_curve])
        envelope = envelope[:length]

    if len(envelope) < length:
        envelope = np.pad(envelope, (0, length - len(envelope)))

    return envelope.astype(np.float32)


def _sine_sweep(length: int, sr: int, start_freq: float, end_freq: float) -> np.ndarray:
    """
    Create a simple pitch sweep, useful for synthetic kick/tom-like sounds.
    """
    if length <= 0:
        return np.array([], dtype=np.float32)

    t = np.linspace(0, length / sr, length, endpoint=False)
    freqs = np.linspace(start_freq, end_freq, length)
    phase = 2 * np.pi * np.cumsum(freqs) / sr

    return np.sin(phase).astype(np.float32)


def _noise(length: int) -> np.ndarray:
    return np.random.uniform(-1.0, 1.0, length).astype(np.float32)


def _highpass_noise(length: int) -> np.ndarray:
    """
    Simple bright noise by subtracting a moving average.
    """
    noise = _noise(length)

    if length < 8:
        return noise

    kernel_size = 8
    kernel = np.ones(kernel_size) / kernel_size
    low = np.convolve(noise, kernel, mode="same")

    return (noise - low).astype(np.float32)


def synth_kick(sr: int) -> np.ndarray:
    duration = 0.22
    length = int(duration * sr)

    tone = _sine_sweep(
        length=length,
        sr=sr,
        start_freq=120,
        end_freq=45,
    )

    envelope = _make_envelope(
        length=length,
        attack=int(0.005 * sr),
        decay=int(0.18 * sr),
    )

    click_len = int(0.01 * sr)
    click = np.zeros(length, dtype=np.float32)

    if click_len > 0:
        click[:click_len] = _highpass_noise(click_len) * 0.25

    return ((tone * envelope) + click).astype(np.float32) * 0.9


def synth_snare(sr: int) -> np.ndarray:
    duration = 0.18
    length = int(duration * sr)

    noise = _highpass_noise(length)

    envelope = _make_envelope(
        length=length,
        attack=int(0.003 * sr),
        decay=int(0.14 * sr),
    )

    body = _sine_sweep(
        length=length,
        sr=sr,
        start_freq=220,
        end_freq=180,
    ) * 0.25

    return ((noise * envelope * 0.7) + (body * envelope)).astype(np.float32)


def synth_hi_hat(sr: int) -> np.ndarray:
    duration = 0.07
    length = int(duration * sr)

    noise = _highpass_noise(length)

    envelope = _make_envelope(
        length=length,
        attack=int(0.002 * sr),
        decay=int(0.045 * sr),
    )

    return (noise * envelope * 0.35).astype(np.float32)


def synth_crash(sr: int) -> np.ndarray:
    duration = 1.2
    length = int(duration * sr)

    noise = _highpass_noise(length)

    envelope = _make_envelope(
        length=length,
        attack=int(0.005 * sr),
        decay=int(1.0 * sr),
    )

    return (noise * envelope * 0.45).astype(np.float32)


def _normalize(audio: np.ndarray, peak: float = 0.95) -> np.ndarray:
    current_peak = float(np.max(np.abs(audio))) if len(audio) > 0 else 0.0

    if current_peak > peak:
        return (audio / current_peak * peak).astype(np.float32)

    return audio.astype(np.float32)


def _add_sample(layer: np.ndarray, sample: np.ndarray, start_sample: int):
    """
    Add one synthesized sample into a layer at a given start sample.
    """
    if start_sample >= len(layer):
        return

    end_sample = min(len(layer), start_sample + len(sample))
    sample_end = end_sample - start_sample

    if sample_end <= 0:
        return

    layer[start_sample:end_sample] += sample[:sample_end]


def render_component_layers(file_id: str, audio_path: Path):
    """
    Render clean synthetic educational layers from timeline.json.

    This does not attempt source separation.
    It reconstructs the rhythmic structure using simple synthesized drum sounds.
    """
    processed_dir = Path("storage/processed") / file_id
    timeline_path = processed_dir / "timeline.json"

    if not timeline_path.exists():
        raise FileNotFoundError(f"Timeline not found: {timeline_path}")

    with timeline_path.open("r", encoding="utf-8") as f:
        timeline = json.load(f)

    events = timeline.get("events", [])

    if not events:
        raise ValueError("No events found in timeline.json")

    sr = 44100

    final_event_time = max(float(event["time"]) for event in events)
    duration_seconds = final_event_time + 2.0
    total_samples = int(duration_seconds * sr)

    layers_dir = processed_dir / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)

    layers = {
        label: np.zeros(total_samples, dtype=np.float32)
        for label in LABELS
    }

    samples = {
        "kick": synth_kick(sr),
        "snare": synth_snare(sr),
        "hi_hat": synth_hi_hat(sr),
        "crash": synth_crash(sr),
    }

    for event in events:
        event_time = float(event["time"])
        components = event.get("components", [])

        start_sample = int(event_time * sr)

        for component in components:
            if component not in layers:
                continue

            _add_sample(
                layer=layers[component],
                sample=samples[component],
                start_sample=start_sample,
            )

    output_files = {}

    full_mix = np.zeros(total_samples, dtype=np.float32)

    for label, layer_audio in layers.items():
        layer_audio = _normalize(layer_audio)

        output_path = layers_dir / f"{label}.wav"
        sf.write(str(output_path), layer_audio, sr)

        output_files[label] = str(output_path)

        full_mix += layer_audio

    full_mix = _normalize(full_mix)

    full_path = layers_dir / "full_reconstruction.wav"
    sf.write(str(full_path), full_mix, sr)

    output_files["full_reconstruction"] = str(full_path)

    layers_metadata = {
        "file_id": file_id,
        "mode": "synthetic_educational_reconstruction",
        "sample_rate": sr,
        "layers": output_files,
    }

    metadata_path = layers_dir / "layers.json"

    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(layers_metadata, f, indent=2)

    return layers_metadata
