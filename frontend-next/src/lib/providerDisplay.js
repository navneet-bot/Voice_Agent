const STT_PROVIDER_LABELS = {
  groq: 'Google Cloud Speech-to-Text Enterprise',
  deepgram: 'Google Cloud Speech-to-Text Enhanced',
  default: 'Google Cloud Speech-to-Text Enterprise',
};

const TTS_PROVIDER_LABELS = {
  edge: 'ElevenLabs Multilingual v2',
  cartesia: 'ElevenLabs Professional Voice',
  default: 'ElevenLabs Multilingual v2',
};

const TELEPHONY_PROVIDER_LABELS = {
  twilio: 'Vapi Enterprise Voice',
  demo: 'Vapi Studio Voice',
  vobiz: 'Vapi India Voice Network',
  exotel: 'Vapi India Voice Network',
  knowlarity: 'Vapi Enterprise Contact Center',
  plivo: 'Vapi Global Voice Network',
  vapi: 'Vapi Enterprise Voice',
  default: 'Vapi Enterprise Voice',
};

const METRIC_LABELS = {
  stt_latency: 'STT latency',
  tts_latency: 'TTS latency',
};

export function getProviderLabel(kind, value) {
  const slug = String(value || 'default').toLowerCase();
  if (kind === 'stt') return STT_PROVIDER_LABELS[slug] || STT_PROVIDER_LABELS.default;
  if (kind === 'tts') return TTS_PROVIDER_LABELS[slug] || TTS_PROVIDER_LABELS.default;
  return TELEPHONY_PROVIDER_LABELS[slug] || TELEPHONY_PROVIDER_LABELS.default;
}

export function formatProviderMetricKey(key) {
  const [metric, provider] = String(key || '').split(':');
  const metricLabel = METRIC_LABELS[metric] || metric.replace(/_/g, ' ');
  const kind = metric?.startsWith('stt') ? 'stt' : metric?.startsWith('tts') ? 'tts' : 'telephony';
  return provider ? `${metricLabel} / ${getProviderLabel(kind, provider)}` : metricLabel;
}
