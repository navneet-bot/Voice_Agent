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
  
  // Statistical Jitter Tracking
  const lastPacketAtRef = useRef(0);
  const emaJitterRef = useRef(50); // Default 50ms jitter estimate
  const activeGenIdRef = useRef(0);

  const disconnect = useCallback(() => {
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
    
    setIsConnected(false);
    setStatusText('Session ended');
  }, []);

  const connect = useCallback(async (isDemo = false, leadName = 'Demo User', isReconnect = false) => {
    if (!isReconnect) disconnect();
    
    try {
      if (!isReconnect) setStatusText('Initialising audio...');
      
      const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioCtxRef.current = ctx;
      if (ctx.state === 'suspended') await ctx.resume();

      // Implement AudioWorklet Load (REQUIRED for zero-stutter)
      try {
        await ctx.audioWorklet.addModule('/audio-worklet-processor.js');
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

      socket.onopen = async () => {
        setIsConnected(true);
        setStatusText('🔴 Listening — speak now');
        if (!isReconnect) {
          setTranscripts([]);
          setEvents([]);
        }

        const mic = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
        });
        micStreamRef.current = mic;
        
        const source = ctx.createMediaStreamSource(mic);
        
        if (ctx.audioWorklet && ctx.audioWorklet.addModule) {
          const workletNode = new AudioWorkletNode(ctx, 'mic-capture-processor');
          source.connect(workletNode);
          workletNode.port.onmessage = (e) => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.send(e.data.buffer);
            }
          };
        } else {
          // Fallback if worklet failed
          const processor = ctx.createScriptProcessor(2048, 1, 1);
          source.connect(processor);
          processor.connect(ctx.destination);
          processor.onaudioprocess = (e) => {
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
            } else if (msg.type?.startsWith('call_')) {
              setEvents(prev => [...prev, msg]);
            }
          } catch (_) {}
          return;
        }

        // Binary PCM from server (with 4-byte GenID header)
        if (e.data.byteLength < 4) return;
        const view = new DataView(e.data);
        const incomingGenId = view.getInt32(0, true);
        
        // 5. ENFORCE GENERATION ID (Senior requirement)
        if (incomingGenId < activeGenIdRef.current) {
          return; // Drop stale audio
        }

        const pcmData = new Int16Array(e.data, 4); // Start after 4-byte header
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
        // base delay + (variance * safety)
        const adaptiveLead = Math.min(0.4, Math.max(0.04, (emaJitterRef.current / 1000) * 2.5));
        
        if (nextStartTimeRef.current < ctxNow) nextStartTimeRef.current = ctxNow + adaptiveLead;
        src.start(nextStartTimeRef.current);
        nextStartTimeRef.current += buf.duration;
      };

      socket.onclose = () => {
        setIsConnected(false);
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
  }, [agentId, activeClient, disconnect]);

  const clearTranscripts = () => setTranscripts([]);

  return { connect, disconnect, isConnected, statusText, transcripts, events, clearTranscripts };
}
