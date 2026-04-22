class MicCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._bufferSize = 2048; // ~128ms at 16kHz
    this._buffer = new Float32Array(this._bufferSize);
    this._bufferIndex = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0];
    
    for (let i = 0; i < channelData.length; i++) {
      // Keep worklet output as Float32; the main thread owns PCM16 packing.
      this._buffer[this._bufferIndex++] = channelData[i];

      if (this._bufferIndex >= this._bufferSize) {
        // Send a copy of the buffer
        this.port.postMessage(this._buffer.slice(0));
        this._bufferIndex = 0;
      }
    }

    return true;
  }
}

registerProcessor('mic-capture-processor', MicCaptureProcessor);
