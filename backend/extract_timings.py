import mido
import json
import os

DRUM_MAP = {
    36: "kick",
    38: "snare",
    42: "hi_hat",
}

def extract_timings(midi_path: str, output_path: str):
    mid = mido.MidiFile(midi_path)
    ticks_per_beat = mid.ticks_per_beat

    events = []
    tempo = 500000  # default 120 BPM

    for track in mid.tracks:
        elapsed_time = 0.0

        for msg in track:
            elapsed_time += mido.tick2second(msg.time, ticks_per_beat, tempo)

            if msg.type == "set_tempo":
                tempo = msg.tempo

            elif msg.type == "note_on" and msg.velocity > 0:
                component = DRUM_MAP.get(msg.note, "unknown")
                events.append({
                    "time_sec":  round(elapsed_time, 4),
                    "note":      msg.note,
                    "component": component,
                    "velocity":  msg.velocity
                })

    events.sort(key=lambda x: x["time_sec"])

    with open(output_path, "w") as f:
        json.dump(events, f, indent=2)

    kicks  = sum(1 for e in events if e["component"] == "kick")
    snares = sum(1 for e in events if e["component"] == "snare")
    hihats = sum(1 for e in events if e["component"] == "hi_hat")

    print(f"Saved: {output_path}")
    print(f"  Total events : {len(events)}")
    print(f"  Kick         : {kicks}")
    print(f"  Snare        : {snares}")
    print(f"  Hi-hat       : {hihats}")
    print(f"  First 5 hits :")
    for e in events[:5]:
        print(f"    t={e['time_sec']}s  {e['component']}")
    print()

# ── Run on all your recording files ──────────────────────────
# Name each file: P{participant number}_{song}_{condition}.mid

#extract_timings("P1_highway_control.mid",      "P1_highway_control.json")
extract_timings("P1_highway_tool.mid",         "P1_highway_tool.json")
#extract_timings("P3_billie_jean_control.mid",  "P3_billie_jean_control.json")
#extract_timings("P1_billie_jean_tool.mid",     "P1_billie_jean_tool.json")

# Repeat for P2, P3, P4, P5 by changing the filenames above
