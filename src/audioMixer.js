export class AudioMixer {
  constructor() {
    this.audioContext = null;
    this.buffers = {};
    this.sources = [];
    this.isPlaying = false;
    this.startedAt = 0;
  }

  getContext() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();
    }

    return this.audioContext;
  }

  async loadLayer(layerName, url) {
    const context = this.getContext();

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to load ${layerName}: ${response.status}`);
    }

    const arrayBuffer = await response.arrayBuffer();
    const audioBuffer = await context.decodeAudioData(arrayBuffer);

    this.buffers[layerName] = audioBuffer;

    return audioBuffer;
  }

  async loadLayers(layerMap) {
    const entries = Object.entries(layerMap);

    await Promise.all(
      entries.map(([layerName, url]) => this.loadLayer(layerName, url))
    );

    return this.buffers;
  }

  play(selectedLayers, options = {}) {
    const context = this.getContext();

    if (this.isPlaying) {
      this.stop();
    }

    const offset = options.offset || 0;
    const gainValue = options.gain ?? 0.9;

    const bpm = Number(options.bpm || 100);
    const beatSeconds = 60 / bpm;

    const countInEnabled = options.countInEnabled ?? true;
    const countInBeats = countInEnabled ? options.countInBeats ?? 4 : 0;

    const metronomeEnabled = options.metronomeEnabled ?? true;
    const beatsPerBar = options.beatsPerBar ?? 4;

    const selectedBuffers = selectedLayers
      .filter((layerName) => this.buffers[layerName])
      .map((layerName) => ({
        layerName,
        buffer: this.buffers[layerName],
      }));

    if (selectedBuffers.length === 0) {
      throw new Error("No selected layers are loaded.");
    }

    const maxDuration = Math.max(
      ...selectedBuffers.map(({ buffer }) =>
        Math.max(0, buffer.duration - offset)
      )
    );

    const playbackDuration = options.duration || maxDuration;

    const masterGain = context.createGain();
    masterGain.gain.value = gainValue;
    masterGain.connect(context.destination);

    const startTime = context.currentTime + 0.1;
    const countInDuration = countInBeats * beatSeconds;
    const layerStartTime = startTime + countInDuration;

    this.sources = [];

    if (countInEnabled) {
      this.scheduleMetronome({
        context,
        startTime,
        beatSeconds,
        countInBeats,
        playbackDuration: metronomeEnabled ? playbackDuration : 0,
        countInDuration,
        beatsPerBar,
      });
    }

    if (!countInEnabled && metronomeEnabled) {
      this.scheduleMetronome({
        context,
        startTime,
        beatSeconds,
        countInBeats: 0,
        playbackDuration,
        countInDuration: 0,
        beatsPerBar,
      });
    }

    selectedBuffers.forEach(({ buffer }) => {
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(masterGain);

      if (playbackDuration) {
        source.start(layerStartTime, offset, playbackDuration);
      } else {
        source.start(layerStartTime, offset);
      }

      source.onended = () => {
        this.isPlaying = false;
      };

      this.sources.push(source);
    });

    this.isPlaying = true;
    this.startedAt = Date.now();
  }

  scheduleMetronome({
    context,
    startTime,
    beatSeconds,
    countInBeats,
    playbackDuration,
    countInDuration,
    beatsPerBar,
  }) {
    const totalClickDuration = countInDuration + playbackDuration;
    const totalClicks = Math.ceil(totalClickDuration / beatSeconds) + 1;

    for (let i = 0; i < totalClicks; i++) {
      const clickTime = startTime + i * beatSeconds;

      const isCountInClick = i < countInBeats;
      const beatInBar = i % beatsPerBar;
      const isDownbeat = beatInBar === 0;

      const frequency = isDownbeat ? 1200 : 900;
      const volume = isCountInClick ? 0.35 : 0.18;

      this.scheduleClick(context, clickTime, frequency, volume);
    }
  }

  scheduleClick(context, time, frequency, volume) {
    const oscillator = context.createOscillator();
    const gain = context.createGain();

    oscillator.type = "square";
    oscillator.frequency.value = frequency;

    gain.gain.setValueAtTime(0.0001, time);
    gain.gain.linearRampToValueAtTime(volume, time + 0.002);
    gain.gain.exponentialRampToValueAtTime(0.001, time + 0.06);

    oscillator.connect(gain);
    gain.connect(context.destination);

    oscillator.start(time);
    oscillator.stop(time + 0.07);

    this.sources.push(oscillator);
  }

  stop() {
    this.sources.forEach((source) => {
      try {
        source.stop();
      } catch {
        // Ignore already-stopped sources.
      }
    });

    this.sources = [];
    this.isPlaying = false;
  }

  hasLoaded(layerName) {
    return Boolean(this.buffers[layerName]);
  }

  clear() {
    this.stop();
    this.buffers = {};
  }
}
