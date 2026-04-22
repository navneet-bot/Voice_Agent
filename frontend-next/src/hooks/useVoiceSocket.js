import { useState, useRef, useCallback } from 'react';

export function useVoiceSocket(agentId, activeClient) {
  const [isConnected, setIsConnected] = useState(false);
  const [statusText, setStatusText] = useState('Idle');
  const [transcripts, setTranscripts] = useState([]);
  const [events, setEvents] = useState([]);
  
  const wsRef = useRef(null);
  const audioCtxRef = useRef(null);
  const micStreamRef = useRef(null);
  const nextStartTimeRef = useRef(0);
  const pingIntervalRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const shouldReconnectRef = useRef(false);
  const playbackReleaseTimeoutRef = useRef(null);
  const micBlockedUntilRef = useRef(0);
  
  // Statistical Jitter Tracking
  const lastPacketAtRef = useRef(0);
  const emaJitterRef = useRef(50); // Default 50ms jitter estimate
  const activeGenIdRef = useRef(0);
  const expectsGenHeaderRef = useRef(false);

  const clearPlaybackReleaseTimer = useCallback(() => {
    if (playbackReleaseTimeoutRef.current) {
      clearTimeout(playbackReleaseTimeoutRef.current);
      playbackReleaseTimeoutRef.current = null;
    }
  }, []);

  const holdMicInput = useCallback((holdMs = 0) => {
    const now = performance.now();
    micBlockedUntilRef.current = Math.max(micBlockedUntilRef.current, now + holdMs);
    clearPlaybackReleaseTimer();
  }, [clearPlaybackReleaseTimer]);

  const scheduleMicResume = useCallback((ctx, tailMs = 320) => {
    const queuedMs = Math.max(0, (nextStartTimeRef.current - ctx.currentTime) * 1000);
    const releaseAfterMs = queuedMs + tailMs;
    holdMicInput(releaseAfterMs);
    playbackReleaseTimeoutRef.current = setTimeout(() => {
      const now = performance.now();
      if (now >= micBlockedUntilRef.current) {
        micBlockedUntilRef.current = 0;
      }
    }, releaseAfterMs);
  }, [holdMicInput]);

  const isMicInputBlocked = useCallback(() => (
    performance.now() < micBlockedUntilRef.current
  ), []);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(t => t.stop());
      micStreamRef.current = null;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
    if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    clearPlaybackReleaseTimer();
    
    setIsConnected(false);
    setStatusText('Session ended');
    activeGenIdRef.current = 0;
    expectsGenHeaderRef.current = false;
    micBlockedUntilRef.current = 0;
    nextStartTimeRef.current = 0;
  }, [clearPlaybackReleaseTimer]);

  const connect = useCallback(async (isDemo = false, leadName = 'Demo User', isReconnect = false) => {
    if (!isReconnect) disconnect();
    
    try {
      if (!isReconnect) setStatusText('Initialising audio...');
      
      const ctx = new (window.AudioContext || window.webkitAudioContext)(); // Use hardware rate for stability
      audioCtxRef.current = ctx;
      if (ctx.state === 'suspended') await ctx.resume();
      let workletLoaded = false;

      // Implement AudioWorklet Load (REQUIRED for zero-stutter)
      try {
        await ctx.audioWorklet.addModule('/audio-worklet-processor.js');
        workletLoaded = true;
      } catch (e) {
        console.warn("AudioWorklet failed, falling back to ScriptProcessor (Degraded)", e);
      }

      const clientId = encodeURIComponent(activeClient);
      const encodedLead = encodeURIComponent(leadName);
      const endpoint = isDemo 
        ? `api/voice-demo?agentId=${encodeURIComponent(agentId)}&clientId=${clientId}&leadName=${encodedLead}`
        : `api/voice-live?agentId=${encodeURIComponent(agentId)}`;

      const wsUrl = `ws://${window.location.hostname}:8000/${endpoint}`;
      const socket = new WebSocket(wsUrl);
      socket.binaryType = 'arraybuffer';
      wsRef.current = socket;
      shouldReconnectRef.current = true;

      socket.onopen = async () => {
        setIsConnected(true);
        setStatusText('🔴 Listening — speak now');
        
        // Handshake: Tell server our hardware rate so STT works perfectly
        socket.send(JSON.stringify({ type: 'mic_ready', sampleRate: ctx.sampleRate }));
        if (!isReconnect) {
          setTranscripts([]);
          setEvents([]);
        }

        const mic = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
        });
        micStreamRef.current = mic;
        
        const source = ctx.createMediaStreamSource(mic);
        
        if (workletLoaded) {
          const workletNode = new AudioWorkletNode(ctx, 'mic-capture-processor');
          source.connect(workletNode);
          workletNode.port.onmessage = (e) => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              if (isMicInputBlocked()) return;
              // Worklet emits Float32 samples; backend expects raw PCM16 bytes.
              const f32 = e.data;
              const i16 = new Int16Array(f32.length);
              for (let i = 0; i < f32.length; i++) {
                const s = Math.max(-1, Math.min(1, f32[i]));
                i16[i] = s < 0 ? s * 32768 : s * 32767;
              }
              wsRef.current.send(i16.buffer);
            }
          };
        } else {
          // Fallback if worklet failed
          const processor = ctx.createScriptProcessor(2048, 1, 1);
          const silentGain = ctx.createGain();
          silentGain.gain.value = 0;
          source.connect(processor);
          processor.connect(silentGain);
          silentGain.connect(ctx.destination);
          processor.onaudioprocess = (e) => {
            if (isMicInputBlocked()) return;
            const inp = e.inputBuffer.getChannelData(0);
            const i16 = new Int16Array(inp.length);
            for (let j = 0; j < inp.length; j++) i16[j] = Math.max(-32768, Math.min(32767, inp[j] * 32767));
            if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(i16.buffer);
          };
        }

        pingIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(new TextEncoder().encode('ping'));
        }, 5000);
      };

      socket.onmessage = (e) => {
        if (!audioCtxRef.current) return;
        
        if (typeof e.data === 'string') {
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === 'transcript') {
              setTranscripts(prev => [...prev, msg]);
            } else if (msg.type === 'gen_id') {
              activeGenIdRef.current = msg.value;
              expectsGenHeaderRef.current = true;
              holdMicInput(250);
            } else if (msg.type?.startsWith('call_')) {
              setEvents(prev => [...prev, msg]);
            }
          } catch (_) {}
          return;
        }

        // Binary PCM from server (supports both with/without 4-byte GenID header).
        if (e.data.byteLength < 2) return;
        let payloadOffset = 0;
        if (expectsGenHeaderRef.current && e.data.byteLength > 4) {
          const view = new DataView(e.data);
          const incomingGenId = view.getInt32(0, true);
          if (incomingGenId < activeGenIdRef.current) return;
          payloadOffset = 4;
        }

        const payloadBytes = e.data.byteLength - payloadOffset;
        if (payloadBytes < 2) return;
        const pcmData = new Int16Array(e.data, payloadOffset, Math.floor(payloadBytes / 2));
        if (pcmData.length === 0) return; // Guard against empty audio chunks

        const floatData = new Float32Array(pcmData.length);
        for (let i = 0; i < pcmData.length; i++) floatData[i] = pcmData[i] / 32768;
        
        // 4. STATISTICAL ADAPTIVE JITTER BUFFER
        const nowReal = performance.now();
        if (lastPacketAtRef.current > 0) {
          const delta = nowReal - lastPacketAtRef.current;
          const jitter = Math.abs(delta - 20); // ideal interval 20ms
          emaJitterRef.current = emaJitterRef.current * 0.9 + jitter * 0.1;
        }
        lastPacketAtRef.current = nowReal;

        const buf = ctx.createBuffer(1, floatData.length, 24000);
        buf.getChannelData(0).set(floatData);
        const src = ctx.createBufferSource();
        src.buffer = buf;
        src.connect(ctx.destination);
        
        const ctxNow = ctx.currentTime;
        // Increase lead time to 80ms minimum to prevent breaking/pops
        const adaptiveLead = Math.min(0.5, Math.max(0.08, (emaJitterRef.current / 1000) * 3.0));
        
        if (nextStartTimeRef.current < ctxNow) {
          nextStartTimeRef.current = ctxNow + adaptiveLead;
        }
        
        src.start(nextStartTimeRef.current);
        nextStartTimeRef.current += buf.duration;
        scheduleMicResume(ctx);
      };

      socket.onclose = () => {
        setIsConnected(false);
        if (!shouldReconnectRef.current) {
          setStatusText('Session ended');
          return;
        }
        setStatusText('Reconnecting...');
        reconnectTimeoutRef.current = setTimeout(() => connect(isDemo, leadName, true), 2000);
      };
      
      socket.onerror = () => {
        setStatusText('Voice server error.');
        disconnect();
      };

    } catch (err) {
      console.error(err);
      setStatusText('Mic access denied or server unreachable.');
      disconnect();
    }
  }, [agentId, activeClient, clearPlaybackReleaseTimer, disconnect, holdMicInput, isMicInputBlocked, scheduleMicResume]);

  const clearTranscripts = () => setTranscripts([]);

  return { connect, disconnect, isConnected, statusText, transcripts, events, clearTranscripts };
}
