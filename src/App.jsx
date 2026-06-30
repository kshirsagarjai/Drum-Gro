import { useRef, useState } from "react";
import {
  uploadAudio,
  analyzeAudio,
  getStatus,
  getTimeline,
  getAudioUrl,
} from "./api";
import { AudioMixer } from "./audioMixer";
import "./App.css";

const LAYERS = [
  { key: "kick", label: "Kick" },
  { key: "snare", label: "Snare" },
  { key: "hi_hat", label: "Hi-hat" },
  { key: "crash", label: "Crash" },
];

const PLAYER_PRESETS = [
  {
    label: "Kick only",
    layers: ["kick"],
  },
  {
    label: "Snare only",
    layers: ["snare"],
  },
  {
    label: "Hi-hat only",
    layers: ["hi_hat"],
  },
  {
    label: "Kick + snare",
    layers: ["kick", "snare"],
  },
  {
    label: "Kick + hi-hat",
    layers: ["kick", "hi_hat"],
  },
  {
    label: "Snare + hi-hat",
    layers: ["snare", "hi_hat"],
  },
  {
    label: "Full reconstruction",
    layers: ["kick", "snare", "hi_hat", "crash"],
  },
];

function getFirstBeatOffset(timeline) {
  const events = timeline?.events || [];

  const firstBeatEvent = events.find(
    (event) => Number(event.beat) === 1
  );

  if (firstBeatEvent && typeof firstBeatEvent.time === "number") {
    return firstBeatEvent.time;
  }

  if (events.length > 0 && typeof events[0].time === "number") {
    return events[0].time;
  }

  return 0;
}

function App() {
  const mixerRef = useRef(new AudioMixer());

  const [selectedFile, setSelectedFile] = useState(null);
  const [fileId, setFileId] = useState(null);
  const [status, setStatus] = useState("idle");
  const [timeline, setTimeline] = useState(null);
  const [error, setError] = useState("");

  const [selectedLayers, setSelectedLayers] = useState([
    "kick",
    "snare",
    "hi_hat",
    "crash",
  ]);

  const [layersLoaded, setLayersLoaded] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);

  const [metronomeEnabled, setMetronomeEnabled] = useState(true);
  const [countInEnabled, setCountInEnabled] = useState(true);

  async function handleUploadAndAnalyze() {
    if (!selectedFile) {
      setError("Please select a WAV or MP3 drum stem first.");
      return;
    }

    setError("");
    setTimeline(null);
    setLayersLoaded(false);
    setIsPlaying(false);
    mixerRef.current.clear();
    setStatus("uploading");

    try {
      const uploadResult = await uploadAudio(selectedFile);
      setFileId(uploadResult.file_id);

      setStatus("starting analysis");

      await analyzeAudio(uploadResult.file_id);

      setStatus("processing");

      const completed = await pollUntilCompleted(uploadResult.file_id);

      if (!completed) {
        setError("Analysis timed out.");
        setStatus("failed");
        return;
      }

      const timelineResult = await getTimeline(uploadResult.file_id);
      setTimeline(timelineResult);

      setStatus("loading layers");

      await loadMixerLayers(uploadResult.file_id);

      setStatus("completed");
    } catch (err) {
      console.error(err);
      setError(
        err?.response?.data?.detail ||
          err.message ||
          "Something went wrong."
      );
      setStatus("failed");
    }
  }

  async function pollUntilCompleted(id) {
    const maxAttempts = 30;

    for (let i = 0; i < maxAttempts; i++) {
      const result = await getStatus(id);

      if (result.status === "completed") {
        return true;
      }

      if (result.status === "failed") {
        throw new Error("Analysis failed. Check backend terminal.");
      }

      await new Promise((resolve) => setTimeout(resolve, 1500));
    }

    return false;
  }

  async function loadMixerLayers(id) {
    const layerMap = {};

    LAYERS.forEach((layer) => {
      layerMap[layer.key] = getAudioUrl(id, layer.key);
    });

    await mixerRef.current.loadLayers(layerMap);
    setLayersLoaded(true);
  }

  function toggleLayer(layerKey) {
    setSelectedLayers((current) => {
      if (current.includes(layerKey)) {
        return current.filter((layer) => layer !== layerKey);
      }

      return [...current, layerKey];
    });
  }

  function applyPreset(layers) {
    setSelectedLayers(layers);
  }

  function playSelectedLayers() {
    if (!layersLoaded) {
      setError("Layers are not loaded yet.");
      return;
    }

    if (selectedLayers.length === 0) {
      setError("Select at least one layer to play.");
      return;
    }

    setError("");

    const playbackOffset = getFirstBeatOffset(timeline);

    try {
      mixerRef.current.play(selectedLayers, {
        bpm: timeline?.tempo || 100,
        offset: playbackOffset,
        metronomeEnabled,
        countInEnabled,
        countInBeats: 4,
        beatsPerBar: 4,
      });

      setIsPlaying(true);
    } catch (err) {
      console.error(err);
      setError(err.message || "Playback failed.");
      setIsPlaying(false);
    }
  }

  function stopPlayback() {
    mixerRef.current.stop();
    setIsPlaying(false);
  }

  const playbackOffset = getFirstBeatOffset(timeline);

  return (
    <main className="page">
      <section className="card">
        <h1>Drum Groove Decomposition Tool</h1>
        <p>
          Upload a pre-separated drum stem, generate a manual-profile timeline,
          and play clean educational layers.
        </p>

        <div className="upload-row">
          <input
            type="file"
            accept=".wav,.mp3,audio/wav,audio/mpeg"
            onChange={(event) => {
              setSelectedFile(event.target.files[0]);
              setError("");
            }}
          />

          <button onClick={handleUploadAndAnalyze}>
            Upload and analyze
          </button>
        </div>

        <p className="status">
          Status: <strong>{status}</strong>
        </p>

        {fileId && (
          <p className="small">
            File ID: <code>{fileId}</code>
          </p>
        )}

        {error && <p className="error">{error}</p>}
      </section>

      {timeline && (
        <>
          <section className="card">
            <h2>Timeline summary</h2>

            <div className="summary-grid">
              <SummaryItem label="Song" value={timeline.song} />
              <SummaryItem label="Artist" value={timeline.artist} />
              <SummaryItem label="Tempo" value={timeline.tempo} />
              <SummaryItem
                label="Playback starts at"
                value={`${playbackOffset.toFixed(3)}s`}
              />
              <SummaryItem
                label="Total events"
                value={timeline.summary?.total_events}
              />
              <SummaryItem label="Kick" value={timeline.summary?.kick} />
              <SummaryItem label="Snare" value={timeline.summary?.snare} />
              <SummaryItem label="Hi-hat" value={timeline.summary?.hi_hat} />
              <SummaryItem label="Crash" value={timeline.summary?.crash} />
            </div>
          </section>

          <section className="card">
            <h2>Interactive layer mixer</h2>

            <p className="small">
              Select layers, then play them together in sync.
            </p>

            <p className="small">
              Playback tempo: <strong>{timeline?.tempo ?? "-"}</strong> BPM
            </p>

            <p className="small">
              Count-in leads into the first beat at{" "}
              <strong>{playbackOffset.toFixed(3)}s</strong>.
            </p>

            <div className="checkbox-row">
              {LAYERS.map((layer) => (
                <label className="checkbox-label" key={layer.key}>
                  <input
                    type="checkbox"
                    checked={selectedLayers.includes(layer.key)}
                    onChange={() => toggleLayer(layer.key)}
                  />
                  {layer.label}
                </label>
              ))}
            </div>

            <div className="checkbox-row">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={countInEnabled}
                  onChange={() => setCountInEnabled((current) => !current)}
                />
                4-beat count-in
              </label>

              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={metronomeEnabled}
                  onChange={() =>
                    setMetronomeEnabled((current) => !current)
                  }
                />
                Metronome during playback
              </label>
            </div>

            <div className="preset-row">
              {PLAYER_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  className="secondary-button"
                  onClick={() => applyPreset(preset.layers)}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            <div className="transport-row">
              <button
                onClick={playSelectedLayers}
                disabled={!layersLoaded || isPlaying}
              >
                Play selected layers
              </button>

              <button
                className="secondary-button"
                onClick={stopPlayback}
                disabled={!isPlaying}
              >
                Stop
              </button>
            </div>

            <p className="small">
              Layers loaded: <strong>{layersLoaded ? "yes" : "no"}</strong>
            </p>
          </section>

          <section className="card">
            <h2>Reference audio files</h2>

            <div className="layers">
              <div className="layer">
                <h3>Original drum stem</h3>
                <audio controls src={getAudioUrl(fileId, "prepared")} />
              </div>

              <div className="layer">
                <h3>Full reconstruction</h3>
                <audio
                  controls
                  src={getAudioUrl(fileId, "full_reconstruction")}
                />
              </div>
            </div>
          </section>

          <section className="card">
            <h2>First timeline events</h2>

            <div className="events">
              {timeline.events.slice(0, 20).map((event, index) => (
                <div className="event" key={`${event.time}-${index}`}>
                  <span>{event.time.toFixed(3)}s</span>
                  <span>
                    Bar {event.bar}, beat {event.beat}
                  </span>
                  <span>{event.components.join(" + ")}</span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}

function SummaryItem({ label, value }) {
  return (
    <div className="summary-item">
      <span>{label}</span>
      <strong>{value ?? "-"}</strong>
    </div>
  );
}

export default App;
