/**
 * MicCaptureProcessor — AudioWorklet replacement for ScriptProcessor.
 *
 * Accumulates incoming Float32 audio samples in a ring buffer and posts
 * chunks of 2048 samples to the main thread for WebSocket transmission.
 *
 * Runs at whatever sample rate the AudioContext is created with.
 * We create the AudioContext at 16000 Hz so no resampling is needed.
 *
 * Served by FastAPI at /audio-worklet-processor.js
 */
class MicCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer  = [];
    this._chunkSz = 2048;   // samples per message — ~128ms at 16 kHz
  }

  process(inputs /*, outputs, parameters */) {
    const channelData = inputs[0]?.[0];  // mono input channel
    if (!channelData) return true;

    // Accumulate samples
    for (let i = 0; i < channelData.length; i++) {
      this._buffer.push(channelData[i]);
    }

    // Flush complete chunks to the main thread
    while (this._buffer.length >= this._chunkSz) {
      const chunk = new Float32Array(this._buffer.splice(0, this._chunkSz));
      this.port.postMessage(chunk, [chunk.buffer]);
    }

    return true;   // keep processor alive
  }
}

registerProcessor('mic-capture-processor', MicCaptureProcessor);
