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
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    setIsConnected(false);
    setStatusText('Session ended');
  }, []);

  const connect = useCallback(async (isDemo = false, leadName = 'Demo User') => {
    disconnect();
    try {
      setStatusText('Initialising audio...');
      const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioCtxRef.current = ctx;
      if (ctx.state === 'suspended') await ctx.resume();

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
        setTranscripts([]);

        const mic = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
        });
        micStreamRef.current = mic;
        
        const source = ctx.createMediaStreamSource(mic);
        
        // Use ScriptProcessor for max compatibility here, matching index.html fallback
        const processor = ctx.createScriptProcessor(2048, 1, 1);
        source.connect(processor);
        processor.connect(ctx.destination);
        processor.onaudioprocess = (e) => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            const inp = e.inputBuffer.getChannelData(0);
            const i16 = new Int16Array(inp.length);
            for (let j = 0; j < inp.length; j++) {
              i16[j] = Math.max(-32768, Math.min(32767, inp[j] * 32767));
            }
            wsRef.current.send(i16.buffer);
          }
        };

        pingIntervalRef.current = setInterval(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(new TextEncoder().encode('ping'));
          }
        }, 5000);
      };

      nextStartTimeRef.current = 0;

      socket.onmessage = (e) => {
        if (!audioCtxRef.current) return;
        
        if (typeof e.data === 'string') {
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === 'transcript') {
              setTranscripts(prev => [...prev, msg]);
            } else if (msg.type?.startsWith('call_')) {
              setEvents(prev => [...prev, msg]);
            }
          } catch (_) {}
          return;
        }

        // Binary PCM from server
        const pcmData = new Int16Array(e.data);
        const floatData = new Float32Array(pcmData.length);
        for (let i = 0; i < pcmData.length; i++) floatData[i] = pcmData[i] / 32768;
        
        const buf = ctx.createBuffer(1, floatData.length, 24000);
        buf.getChannelData(0).set(floatData);
        const src = ctx.createBufferSource();
        src.buffer = buf;
        src.connect(ctx.destination);
        
        const now = ctx.currentTime;
        if (nextStartTimeRef.current < now) nextStartTimeRef.current = now + 0.15;
        src.start(nextStartTimeRef.current);
        nextStartTimeRef.current += buf.duration;
      };

      socket.onerror = () => {
        setStatusText('Voice server error.');
        disconnect();
      };
      
      socket.onclose = () => {
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
