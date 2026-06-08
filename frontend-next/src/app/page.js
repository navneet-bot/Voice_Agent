'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';
import '@/app/landing.css';
import {
  Phone,
  Shield,
  Activity,
  Sparkles,
  Clock,
  ArrowRight,
  Globe,
  Bot,
  Play,
  Pause,
  Layers,
  Volume2,
  Workflow,
  Zap,
  Lock,
  MessageSquare,
  Check,
  Menu,
  X,
  GitBranch,
  Terminal,
  ArrowRightLeft,
  ChevronRight,
  TrendingUp,
  Settings,
  Mic,
  Database,
  CheckCircle2,
  HelpCircle
} from 'lucide-react';

export default function LandingPage() {
  const { currentRole, user, loading: authLoading } = useAuth();
  const router = useRouter();

  // Navigation state
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  // Scroll effect for header
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 20) {
        setScrolled(true);
      } else {
        setScrolled(false);
      }
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // ── Visualizer Orb Canvas ────────────────────────────────────────────────
  const canvasRef = useRef(null);
  const [orbState, setOrbState] = useState('idle'); // 'idle' | 'listening' | 'speaking'
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    let time = 0;

    const resizeCanvas = () => {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Render loop
    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const baseRadius = Math.min(canvas.width, canvas.height) * 0.28;
      
      time += 0.02;

      // Draw background glow
      const glowGrad = ctx.createRadialGradient(
        centerX, centerY, 0,
        centerX, centerY, baseRadius * 2
      );
      
      let glowColor1 = 'rgba(124, 58, 237, 0.15)'; // purple
      let glowColor2 = 'rgba(59, 130, 246, 0.08)'; // blue
      let speedMultiplier = 1;
      let waveCount = 3;
      let amplitudeMultiplier = 1;

      if (orbState === 'listening') {
        glowColor1 = 'rgba(6, 182, 212, 0.2)'; // cyan
        glowColor2 = 'rgba(99, 102, 241, 0.1)'; // indigo
        speedMultiplier = 1.8;
        waveCount = 5;
        amplitudeMultiplier = 1.5;
      } else if (orbState === 'speaking') {
        glowColor1 = 'rgba(236, 72, 153, 0.25)'; // pink
        glowColor2 = 'rgba(124, 58, 237, 0.12)'; // purple
        speedMultiplier = 2.2;
        waveCount = 6;
        amplitudeMultiplier = 2.0;
      }

      glowGrad.addColorStop(0, glowColor1);
      glowGrad.addColorStop(0.5, glowColor2);
      glowGrad.addColorStop(1, 'transparent');
      
      ctx.fillStyle = glowGrad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius * 2, 0, Math.PI * 2);
      ctx.fill();

      // Draw rotating multi-layer wave structures
      for (let w = 0; w < waveCount; w++) {
        ctx.beginPath();
        const angleStep = (Math.PI * 2) / 180;
        
        // Color variables based on wave index and state
        let strokeColor = 'rgba(124, 58, 237, 0.35)'; // purple
        if (w % 2 === 1) strokeColor = 'rgba(59, 130, 246, 0.35)'; // blue
        if (w % 3 === 2) strokeColor = 'rgba(6, 182, 212, 0.35)'; // cyan

        if (orbState === 'speaking') {
          if (w % 2 === 0) strokeColor = 'rgba(236, 72, 153, 0.5)';
        }

        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = w === 0 ? 3 : 1.5;
        
        for (let i = 0; i <= 180; i++) {
          const angle = i * angleStep;
          // Complex noise using overlapping sine waves
          const wavePhase = time * speedMultiplier + w * 1.5;
          const noise = 
            Math.sin(angle * (3 + w) + wavePhase) * 12 * amplitudeMultiplier * Math.cos(angle * 2) +
            Math.cos(angle * (5 - w) - wavePhase * 0.8) * 8 * amplitudeMultiplier;
            
          const r = baseRadius + noise + (w * 5);
          
          const x = centerX + Math.cos(angle) * r;
          const y = centerY + Math.sin(angle) * r;
          
          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        
        // Close shape for full loop
        ctx.closePath();
        ctx.stroke();
      }

      // Render center glowing core
      const coreGrad = ctx.createRadialGradient(
        centerX, centerY, 0,
        centerX, centerY, baseRadius * 0.5
      );
      
      let coreColorStart = 'rgba(255, 255, 255, 0.85)';
      let coreColorEnd = 'rgba(124, 58, 237, 0.4)';
      
      if (orbState === 'listening') {
        coreColorEnd = 'rgba(6, 182, 212, 0.5)';
      } else if (orbState === 'speaking') {
        coreColorEnd = 'rgba(236, 72, 153, 0.6)';
      }

      coreGrad.addColorStop(0, coreColorStart);
      coreGrad.addColorStop(0.4, coreColorEnd);
      coreGrad.addColorStop(1, 'transparent');
      
      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius * 0.7, 0, Math.PI * 2);
      ctx.fill();

      // Render particles orbiting around
      ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
      for (let p = 0; p < 8; p++) {
        const pAngle = time * 0.5 + p * (Math.PI / 4);
        const pDist = baseRadius * 1.4 + Math.sin(time + p) * 15;
        const px = centerX + Math.cos(pAngle) * pDist;
        const py = centerY + Math.sin(pAngle) * pDist;
        
        ctx.beginPath();
        ctx.arc(px, py, 1.5 + Math.sin(time + p) * 1, 0, Math.PI * 2);
        ctx.fill();
      }

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resizeCanvas);
    };
  }, [orbState]);

  // Periodic visualizer state toggle for hero section demo
  useEffect(() => {
    const states = ['idle', 'speaking', 'listening'];
    let idx = 0;
    const interval = setInterval(() => {
      idx = (idx + 1) % states.length;
      setOrbState(states[idx]);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // ── Interactive Dashboard Mockup state ───────────────────────────────
  const [activeDashTab, setActiveDashTab] = useState('logs'); // 'logs' | 'campaigns' | 'analytics'
  const [isPlayingRecording, setIsPlayingRecording] = useState(false);
  const [recordingProgress, setRecordingProgress] = useState(35); // percentage
  
  // Dashboard audio simulation timer
  useEffect(() => {
    let playInterval;
    if (isPlayingRecording) {
      playInterval = setInterval(() => {
        setRecordingProgress(prev => {
          if (prev >= 100) {
            setIsPlayingRecording(false);
            return 0;
          }
          return prev + 1;
        });
      }, 150);
    }
    return () => clearInterval(playInterval);
  }, [isPlayingRecording]);

  // ── Multilingual Demo state ──────────────────────────────────────────
  const [activeLang, setActiveLang] = useState('hinglish'); // 'english' | 'hindi' | 'hinglish'
  
  const conversationData = {
    english: [
      { sender: 'lead', text: 'Hi, I saw a listing for 144 Pinecrest Drive. Is it still available?' },
      { sender: 'agent', text: 'Hello! Yes, that property is currently active. It is a stunning 4-bedroom house with a modernized kitchen. Would you like to schedule a private walkthrough this week?' },
      { sender: 'lead', text: 'Yes, but I can only do evenings after 6 PM.' },
      { sender: 'agent', text: 'No problem at all! I have slots open this Thursday at 6:30 PM. Would that work for you, or would Friday be better?' }
    ],
    hindi: [
      { sender: 'lead', text: 'नमस्ते, क्या मुझे इस जॉब के बारे में जानकारी मिल सकती है?' },
      { sender: 'agent', text: 'नमस्ते! बिल्कुल। यह कस्टमर सपोर्ट एग्जीक्यूटिव का रोल है, जिसमें रिमोट काम करने का विकल्प भी उपलब्ध है। क्या आपके पास पहले से कस्टमर सर्विस में कोई अनुभव है?' },
      { sender: 'lead', text: 'हाँ, मैंने दो साल एक बीपीओ में काम किया है।' },
      { sender: 'agent', text: 'बहुत बढ़िया! आपका अनुभव इस रोल के लिए काफी उपयुक्त है। क्या मैं आपकी इंटरव्यू कॉल कल दोपहर ३ बजे शेड्यूल कर दूँ?' }
    ],
    hinglish: [
      { sender: 'lead', text: 'Hi, call check karne ke liye. Mere feedback results kab tak aayenge?' },
      { sender: 'agent', text: 'Hey! Aapki audio call records analyze ho chuki hain. Main dekh paa raha hoon ki aapka QA score 94% hai, jo ki exceptional hai! Kal subah 10 baje tak complete report aapke dashboard pe reflect ho jayegi.' },
      { sender: 'lead', text: 'Oh nice, standard parameters pe evaluate kiya na?' },
      { sender: 'agent', text: 'Absolutely! Total latency, interruption capability aur customer sentiment guidelines ke criteria pe report generate hui hai. Anything else you need help with?' }
    ]
  };

  // ── How It Works step selection ──────────────────────────────────────
  const [activeStep, setActiveStep] = useState(0);
  const steps = [
    { title: "User Audio", icon: Mic, desc: "High fidelity audio streams from web clients via WebRTC or phone calls via Twilio connections directly to our ingest nodes." },
    { title: "Real-time STT", icon: RadioWave, desc: "Fast-streaming Speech-to-Text models convert speech into tokens with latency under 120ms." },
    { title: "Groq LLM Inference", icon: Bot, desc: "Groq LPU engines run advanced stateful LLMs, computing responses in a fraction of a second." },
    { title: "State Manager", icon: Layers, desc: "Dynamically tracks CRM variables, validation parameters, and routes variables using a smart state tree." },
    { title: "Ultra-Fast TTS", icon: Volume2, desc: "Converts text back into hyper-realistic, human-like voice synthesis with custom accents and custom breathing models." },
    { title: "Live AI Voice", icon: Phone, desc: "Delivers smooth audio frames back to the call WebSocket, managing barge-in interruptions seamlessly." }
  ];

  // Helper component for steps icon rendering
  function RadioWave(props) {
    return (
      <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 10a8 8 0 0 1 8-8" />
        <path d="M2 15a5 5 0 0 1 5-5" />
        <path d="M2 20a2 2 0 0 1 2-2" />
        <path d="M22 10a8 8 0 0 0-8-8" />
        <path d="M22 15a5 5 0 0 0-5-5" />
        <path d="M22 20a2 2 0 0 0-2-2" />
      </svg>
    );
  }

  // ── Use Cases interactive simulation state ───────────────────────────
  const [activeUseCase, setActiveUseCase] = useState(0);
  const useCases = [
    {
      title: "Real Estate",
      tag: "Lead Qualification",
      desc: "Instantly follow up with buyers who clicked on properties, qualify budget, schedule site visits, and sync notes to Salesforce.",
      script: "Hey! Saw you were checking out the luxury villa in Sector 62. Are you looking to move in next 3 months, or just exploring options?",
      metrics: "3.2x Booking Rate Increase"
    },
    {
      title: "Recruitment",
      tag: "High Volume Screening",
      desc: "Qualify thousands of applicants concurrently, conduct brief pre-screens, verify years of experience, and auto-book final interviews.",
      script: "Hi Rahul! I reviewed your application for the Node Developer role. Just wanted to double check, are you comfortable working on-site in Bangalore?",
      metrics: "85% HR Admin Time Saved"
    },
    {
      title: "Healthcare",
      tag: "Appointment Reminders",
      desc: "Call patients to confirm bookings, handle reschedules, answer pre-visit queries, and automatically update patient records.",
      script: "Hello Mrs. Sharma, this is Cosmic Clinic. Just calling to remind you of your appointment tomorrow at 11 AM. Do you need directions or prep instructions?",
      metrics: "90% No-Show Reduction"
    },
    {
      title: "Customer Support",
      tag: "Instant Resolutions",
      desc: "Resolve routine billing, booking, and shipping inquiries over real conversation. Escalate complex issues to human agents.",
      script: "Thanks for confirming your order number. I can see that your package is currently at the Delhi Hub and will be delivered by tomorrow 4 PM.",
      metrics: "72% First-Call Resolution"
    },
    {
      title: "Sales Automation",
      tag: "Cold Lead Activation",
      desc: "Nurture cold opt-in contacts at scale, pitch new promotions, handle basic objections, and route warm buyers directly to sales executives.",
      script: "Hey Amit! We noticed you signed up for our SaaS trial last month but didn't launch an agent. We just rolled out Groq-inference support. Care for a 2-min demo?",
      metrics: "45% Higher Conversion Rate"
    },
    {
      title: "Appointment Booking",
      tag: "24/7 Scheduling Assistant",
      desc: "Enable immediate phone-based booking for spas, clinics, consultancies, or service businesses. Synced with Google Calendar.",
      script: "Sure thing! I have a slot open for Hair Grooming this Saturday at 2 PM or 4 PM. Which one suits you best?",
      metrics: "35% Increase in Off-Hour Bookings"
    }
  ];

  return (
    <div className="tw-min-h-screen tw-bg-brand-bg tw-text-white tw-overflow-x-hidden tw-relative tw-bg-mesh-gradient">
      
      {/* ── TOP DECORATIVE ORBS ── */}
      <div className="tw-absolute tw-top-[-100px] tw-left-[-150px] tw-w-[500px] tw-height-[500px] tw-rounded-full tw-bg-brand-purple/10 tw-blur-[120px] tw-pointer-events-none orb-glow-purple tw-z-0" />
      <div className="tw-absolute tw-top-[150px] tw-right-[-100px] tw-w-[450px] tw-height-[450px] tw-rounded-full tw-bg-brand-blue/10 tw-blur-[100px] tw-pointer-events-none orb-glow-blue tw-z-0" />

      {/* ── HEADER NAVBAR ── */}
      <header className={`tw-fixed tw-top-0 tw-left-0 tw-w-full tw-z-50 tw-transition-all tw-duration-300 ${
        scrolled ? 'tw-bg-brand-bg/85 tw-backdrop-blur-md tw-border-b tw-border-white/5 tw-py-4' : 'tw-bg-transparent tw-py-6'
      }`}>
        <div className="tw-max-w-7xl tw-mx-auto tw-px-6 tw-flex tw-justify-between tw-items-center">
          
          {/* Logo */}
          <Link href="/" className="tw-flex tw-items-center tw-gap-2.5 tw-no-underline">
            <span className="tw-flex tw-items-center tw-justify-center tw-w-10 tw-height-10 tw-rounded-xl tw-bg-gradient-to-br tw-from-brand-indigo tw-to-brand-purple tw-shadow-lg tw-shadow-brand-indigo/35 tw-text-xl">
              🦎
            </span>
            <div className="tw-flex tw-flex-col">
              <span className="tw-font-bold tw-text-lg tw-text-white tw-tracking-tight tw-leading-none">
                Cosmic <span className="tw-text-brand-accent">Chameleon</span>
              </span>
              <span className="tw-text-[9px] tw-text-white/40 tw-tracking-widest tw-uppercase tw-mt-1">
                Voice AI Platform
              </span>
            </div>
          </Link>

          {/* Desktop Nav Items */}
          <nav className="tw-hidden md:tw-flex tw-items-center tw-gap-8">
            <a href="#features" className="tw-text-sm tw-font-medium tw-text-white/60 hover:tw-text-white tw-transition-colors tw-no-underline">Features</a>
            <a href="#pipeline" className="tw-text-sm tw-font-medium tw-text-white/60 hover:tw-text-white tw-transition-colors tw-no-underline">Architecture</a>
            <a href="#dashboard-preview" className="tw-text-sm tw-font-medium tw-text-white/60 hover:tw-text-white tw-transition-colors tw-no-underline">Dashboard</a>
            <a href="#use-cases" className="tw-text-sm tw-font-medium tw-text-white/60 hover:tw-text-white tw-transition-colors tw-no-underline">Solutions</a>
            <a href="#multilingual" className="tw-text-sm tw-font-medium tw-text-white/60 hover:tw-text-white tw-transition-colors tw-no-underline">Languages</a>
          </nav>

          {/* Desktop CTA actions */}
          <div className="tw-hidden md:tw-flex tw-items-center tw-gap-4">
            {authLoading ? (
              <div className="tw-w-6 tw-h-6 tw-border-2 tw-border-brand-purple/30 tw-border-t-brand-purple tw-rounded-full tw-animate-spin" />
            ) : user ? (
              <Link 
                href={currentRole === 'admin' ? '/monitor' : '/client-dashboard'} 
                className="tw-text-sm tw-font-semibold tw-px-5 tw-py-2.5 tw-rounded-xl tw-bg-white/5 hover:tw-bg-white/10 tw-border tw-border-white/10 hover:tw-border-white/20 tw-transition-all tw-no-underline tw-text-white"
              >
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link 
                  href="/login" 
                  className="tw-text-sm tw-font-medium tw-text-white/70 hover:tw-text-white tw-transition-colors tw-no-underline"
                >
                  Sign In
                </Link>
                <Link 
                  href="/login" 
                  className="tw-text-sm tw-font-semibold tw-px-5 tw-py-2.5 tw-rounded-xl tw-bg-gradient-to-r tw-from-brand-indigo tw-to-brand-purple hover:tw-opacity-95 tw-shadow-lg tw-shadow-brand-indigo/25 tw-transition-all tw-no-underline tw-text-white"
                >
                  Start Free Trial
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu trigger */}
          <button 
            onClick={() => setMobileMenuOpen(prev => !prev)}
            className="md:tw-hidden tw-text-white/70 hover:tw-text-white tw-bg-white/5 hover:tw-bg-white/10 tw-border tw-border-white/10 tw-p-2 tw-rounded-lg tw-transition-all"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Mobile Navigation Drawer */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div 
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
              className="tw-absolute tw-top-full tw-left-0 tw-w-full tw-bg-brand-bgSecondary/98 tw-backdrop-blur-lg tw-border-b tw-border-white/5 tw-py-6 tw-px-6 tw-flex tw-flex-col tw-gap-4 md:tw-hidden tw-shadow-xl"
            >
              <a href="#features" onClick={() => setMobileMenuOpen(false)} className="tw-text-base tw-font-medium tw-text-white/70 hover:tw-text-white tw-py-2 tw-no-underline">Features</a>
              <a href="#pipeline" onClick={() => setMobileMenuOpen(false)} className="tw-text-base tw-font-medium tw-text-white/70 hover:tw-text-white tw-py-2 tw-no-underline">Architecture</a>
              <a href="#dashboard-preview" onClick={() => setMobileMenuOpen(false)} className="tw-text-base tw-font-medium tw-text-white/70 hover:tw-text-white tw-py-2 tw-no-underline">Dashboard</a>
              <a href="#use-cases" onClick={() => setMobileMenuOpen(false)} className="tw-text-base tw-font-medium tw-text-white/70 hover:tw-text-white tw-py-2 tw-no-underline">Solutions</a>
              <a href="#multilingual" onClick={() => setMobileMenuOpen(false)} className="tw-text-base tw-font-medium tw-text-white/70 hover:tw-text-white tw-py-2 tw-no-underline">Languages</a>
              <div className="tw-h-[1px] tw-bg-white/5 tw-my-2" />
              <div className="tw-flex tw-flex-col tw-gap-3">
                {user ? (
                  <Link 
                    href={currentRole === 'admin' ? '/monitor' : '/client-dashboard'} 
                    onClick={() => setMobileMenuOpen(false)}
                    className="tw-text-center tw-text-sm tw-font-semibold tw-py-3 tw-rounded-xl tw-bg-white/5 tw-border tw-border-white/10 tw-text-white tw-no-underline"
                  >
                    Go to Dashboard
                  </Link>
                ) : (
                  <>
                    <Link 
                      href="/login" 
                      onClick={() => setMobileMenuOpen(false)}
                      className="tw-text-center tw-text-sm tw-font-semibold tw-py-3 tw-rounded-xl tw-bg-white/5 tw-border tw-border-white/10 tw-text-white tw-no-underline"
                    >
                      Sign In
                    </Link>
                    <Link 
                      href="/login" 
                      onClick={() => setMobileMenuOpen(false)}
                      className="tw-text-center tw-text-sm tw-font-semibold tw-py-3 tw-rounded-xl tw-bg-gradient-to-r tw-from-brand-indigo tw-to-brand-purple tw-text-white tw-no-underline"
                    >
                      Start Free Trial
                    </Link>
                  </>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* ── SECTION 1: HERO SECTION ── */}
      <section className="tw-relative tw-pt-32 md:tw-pt-48 tw-pb-20 md:tw-pb-28 tw-max-w-7xl tw-mx-auto tw-px-6 tw-z-10">
        <div className="tw-grid tw-grid-cols-1 lg:tw-grid-cols-12 tw-gap-12 lg:tw-gap-6 tw-items-center">
          
          {/* Hero Left Content */}
          <div className="lg:tw-col-span-7 tw-flex tw-flex-col tw-gap-6 tw-text-left">
            
            {/* Glowing top badge */}
            <div className="tw-inline-flex tw-items-center tw-gap-2 tw-self-start tw-px-3.5 tw-py-1.5 tw-rounded-full tw-bg-brand-indigo/10 tw-border tw-border-brand-indigo/35 tw-shadow-inner tw-shadow-brand-indigo/5">
              <span className="tw-flex tw-h-2 tw-w-2 tw-relative">
                <span className="tw-animate-ping tw-absolute tw-inline-flex tw-h-full tw-w-full tw-rounded-full tw-bg-cyan-400 tw-opacity-75"></span>
                <span className="tw-relative tw-inline-flex tw-rounded-full tw-h-2 tw-w-2 tw-bg-cyan-500"></span>
              </span>
              <span className="tw-text-[11px] tw-font-bold tw-tracking-wider tw-uppercase tw-text-brand-accent">
                Next-Gen Audio Streaming Engine
              </span>
            </div>

            {/* Giant Title */}
            <h1 className="tw-text-4xl sm:tw-text-5xl lg:tw-text-6xl tw-font-extrabold tw-tracking-tight tw-text-white tw-leading-[1.1]">
              Deploy Human-Like <br/>
              <span className="tw-bg-clip-text tw-text-transparent tw-bg-gradient-to-r tw-from-indigo-400 tw-via-purple-400 tw-to-pink-400">
                AI Voice Agents
              </span> <br className="tw-hidden sm:tw-inline" />
              in Minutes
            </h1>

            {/* Subtitle */}
            <p className="tw-text-base sm:tw-text-lg tw-text-white/60 tw-max-w-xl tw-leading-relaxed tw-m-0">
              Real-time multilingual voice AI with ultra-low latency, intelligent workflows, and production-grade infrastructure. Run scalable campaigns that feel entirely human.
            </p>

            {/* CTAs */}
            <div className="tw-flex tw-flex-wrap tw-gap-4 tw-mt-2">
              <Link 
                href="/login" 
                className="tw-flex tw-items-center tw-gap-2 tw-text-sm tw-font-semibold tw-px-8 tw-py-4 tw-rounded-xl tw-bg-gradient-to-r tw-from-brand-indigo tw-via-brand-purple tw-to-pink-600 hover:tw-opacity-95 tw-shadow-xl tw-shadow-brand-indigo/30 tw-transition-all tw-no-underline tw-text-white hover:tw-scale-[1.02]"
              >
                Start Free Trial <ArrowRight size={16} />
              </Link>
              <a 
                href="#dashboard-preview" 
                className="tw-flex tw-items-center tw-gap-2 tw-text-sm tw-font-semibold tw-px-8 tw-py-4 tw-rounded-xl tw-bg-white/5 hover:tw-bg-white/10 tw-border tw-border-white/10 hover:tw-border-white/20 tw-transition-all tw-no-underline tw-text-white hover:tw-scale-[1.02]"
              >
                <Play size={14} className="tw-fill-white" /> Watch Demo
              </a>
            </div>

            {/* Quick Metrics */}
            <div className="tw-grid tw-grid-cols-2 sm:tw-grid-cols-4 tw-gap-4 tw-border-t tw-border-white/5 tw-pt-8 tw-mt-4">
              <div>
                <span className="tw-block tw-text-xs tw-text-white/40 tw-uppercase tw-tracking-wider">VAD Pipeline</span>
                <span className="tw-block tw-text-lg tw-font-bold tw-text-white tw-mt-1">Adaptive</span>
              </div>
              <div>
                <span className="tw-block tw-text-xs tw-text-white/40 tw-uppercase tw-tracking-wider">Groq Inference</span>
                <span className="tw-block tw-text-lg tw-font-bold tw-text-white tw-mt-1">LPU Powered</span>
              </div>
              <div>
                <span className="tw-block tw-text-xs tw-text-white/40 tw-uppercase tw-tracking-wider">Telephony Ingest</span>
                <span className="tw-block tw-text-lg tw-font-bold tw-text-white tw-mt-1">SIP/Twilio</span>
              </div>
              <div>
                <span className="tw-block tw-text-xs tw-text-white/40 tw-uppercase tw-tracking-wider">Interruption</span>
                <span className="tw-block tw-text-lg tw-font-bold tw-text-white tw-mt-1">Full Barge-In</span>
              </div>
            </div>

          </div>

          {/* Hero Right Visualizer & Cards */}
          <div className="lg:tw-col-span-5 tw-relative tw-flex tw-justify-center tw-items-center tw-w-full tw-h-[420px] lg:tw-h-[480px]">
            
            {/* Visualizer Canvas Container */}
            <div className="tw-absolute tw-w-[320px] tw-h-[320px] sm:tw-w-[360px] sm:tw-h-[360px] tw-flex tw-justify-center tw-items-center tw-z-10">
              <canvas ref={canvasRef} className="tw-w-full tw-h-full" />
              
              {/* Center status overlay inside orb */}
              <div className="tw-absolute tw-flex tw-flex-col tw-items-center tw-pointer-events-none">
                <span className="tw-text-[10px] tw-uppercase tw-tracking-widest tw-text-white/50">SYSTEM</span>
                <span className="tw-text-xs tw-font-semibold tw-text-white tw-mt-0.5 tw-capitalize">
                  {orbState === 'idle' ? 'Ready' : orbState === 'listening' ? 'Listening...' : 'Speaking...'}
                </span>
              </div>
            </div>

            {/* FLOATING UI CARD 1: LIVE CALL STATUS */}
            <div className="tw-absolute tw-top-4 tw-left-2 sm:tw-left-6 tw-z-20 glass-panel tw-p-3.5 tw-rounded-xl tw-flex tw-items-center tw-gap-3 tw-shadow-2xl animate-float-slow tw-max-w-[160px]">
              <div className="tw-relative tw-w-8 tw-h-8 tw-rounded-lg tw-bg-emerald-500/10 tw-flex tw-items-center tw-justify-center tw-text-emerald-400">
                <Phone size={14} className="tw-animate-bounce" />
                <span className="tw-absolute tw-top-[-2px] tw-right-[-2px] tw-w-2 tw-h-2 tw-rounded-full tw-bg-emerald-500 tw-animate-pulse" />
              </div>
              <div className="tw-flex tw-flex-col">
                <span className="tw-text-[9px] tw-text-white/40 tw-uppercase tw-tracking-wider">Live Call</span>
                <span className="tw-text-xs tw-font-bold tw-text-white">Active (01:24)</span>
              </div>
            </div>

            {/* FLOATING UI CARD 2: LATENCY STAT */}
            <div className="tw-absolute tw-top-12 tw-right-2 sm:tw-right-6 tw-z-20 glass-panel tw-p-3.5 tw-rounded-xl tw-flex tw-items-center tw-gap-3 tw-shadow-2xl animate-float-reverse tw-max-w-[150px]">
              <div className="tw-w-8 tw-h-8 tw-rounded-lg tw-bg-cyan-500/10 tw-flex tw-items-center tw-justify-center tw-text-cyan-400">
                <Clock size={15} />
              </div>
              <div className="tw-flex tw-flex-col">
                <span className="tw-text-[9px] tw-text-white/40 tw-uppercase tw-tracking-wider">VAD Latency</span>
                <span className="tw-text-xs tw-font-bold tw-text-white">&lt;500ms Response</span>
              </div>
            </div>

            {/* FLOATING UI CARD 3: AGENT UTTERANCE */}
            <div className="tw-absolute tw-bottom-12 tw-left-0 sm:tw-left-4 tw-z-20 glass-panel tw-p-3.5 tw-rounded-xl tw-flex tw-flex-col tw-gap-1.5 tw-shadow-2xl animate-float-reverse tw-max-w-[200px]">
              <div className="tw-flex tw-items-center tw-gap-2">
                <div className="tw-w-2 tw-h-2 tw-rounded-full tw-bg-purple-500" />
                <span className="tw-text-[9px] tw-text-white/40 tw-uppercase tw-tracking-wider">AI Speaking</span>
              </div>
              <p className="tw-text-xs tw-text-white/80 tw-leading-relaxed tw-italic tw-m-0">
                &ldquo;Sure, scheduling the site visit for Saturday at 3 PM.&rdquo;
              </p>
            </div>

            {/* FLOATING UI CARD 4: ANALYTICS SCORE */}
            <div className="tw-absolute tw-bottom-4 tw-right-0 sm:tw-right-4 tw-z-20 glass-panel tw-p-3.5 tw-rounded-xl tw-flex tw-items-center tw-gap-3 tw-shadow-2xl animate-float-slow tw-max-w-[170px]">
              <div className="tw-w-8 tw-h-8 tw-rounded-lg tw-bg-purple-500/10 tw-flex tw-items-center tw-justify-center tw-text-purple-400">
                <Activity size={14} />
              </div>
              <div className="tw-flex tw-flex-col">
                <span className="tw-text-[9px] tw-text-white/40 tw-uppercase tw-tracking-wider">Call QA Score</span>
                <span className="tw-text-xs tw-font-bold tw-text-white">96.8% Exceptional</span>
              </div>
            </div>

          </div>

        </div>
      </section>

      {/* ── SECTION 2: TRUST / STATS BAR ── */}
      <section className="tw-relative tw-border-y tw-border-white/5 tw-bg-brand-bgSecondary/60 tw-backdrop-blur-sm tw-z-10">
        <div className="tw-max-w-7xl tw-mx-auto tw-px-6 tw-py-10">
          <div className="tw-grid tw-grid-cols-2 md:tw-grid-cols-5 tw-gap-8 tw-text-center">
            
            <div className="tw-flex tw-flex-col tw-gap-1">
              <span className="tw-text-3xl md:tw-text-4xl tw-font-extrabold tw-bg-clip-text tw-text-transparent tw-bg-gradient-to-r tw-from-white tw-to-white/60">
                99.9%
              </span>
              <span className="tw-text-[10px] tw-font-bold tw-text-brand-indigo tw-uppercase tw-tracking-widest">
                Uptime SLA
              </span>
            </div>

            <div className="tw-flex tw-flex-col tw-gap-1">
              <span className="tw-text-3xl md:tw-text-4xl tw-font-extrabold tw-bg-clip-text tw-text-transparent tw-bg-gradient-to-r tw-from-white tw-to-white/60">
                &lt;500ms
              </span>
              <span className="tw-text-[10px] tw-font-bold tw-text-brand-blue tw-uppercase tw-tracking-widest">
                Voice Latency
              </span>
            </div>

            <div className="tw-flex tw-flex-col tw-gap-1">
              <span className="tw-text-3xl md:tw-text-4xl tw-font-extrabold tw-bg-clip-text tw-text-transparent tw-bg-gradient-to-r tw-from-white tw-to-white/60">
                1M+
              </span>
              <span className="tw-text-[10px] tw-font-bold tw-text-brand-purple tw-uppercase tw-tracking-widest">
                Conversations
              </span>
            </div>

            <div className="tw-flex tw-flex-col tw-gap-1">
              <span className="tw-text-3xl md:tw-text-4xl tw-font-extrabold tw-bg-clip-text tw-text-transparent tw-bg-gradient-to-r tw-from-white tw-to-white/60">
                Multi-Lang
              </span>
              <span className="tw-text-[10px] tw-font-bold tw-text-pink-500 tw-uppercase tw-tracking-widest">
                Hinglish/Hindi Support
              </span>
            </div>

            <div className="tw-flex tw-flex-col tw-gap-1 tw-col-span-2 md:tw-col-span-1">
              <span className="tw-text-3xl md:tw-text-4xl tw-font-extrabold tw-bg-clip-text tw-text-transparent tw-bg-gradient-to-r tw-from-white tw-to-white/60">
                100%
              </span>
              <span className="tw-text-[10px] tw-font-bold tw-text-cyan-400 tw-uppercase tw-tracking-widest">
                Barge-In Handling
              </span>
            </div>

          </div>
        </div>
      </section>

      {/* ── SECTION 3: FEATURES GRID ── */}
      <section id="features" className="tw-relative tw-py-20 md:tw-py-28 tw-max-w-7xl tw-mx-auto tw-px-6 tw-z-10">
        
        {/* Section Header */}
        <div className="tw-text-center tw-max-w-3xl tw-mx-auto tw-mb-16">
          <span className="tw-text-xs tw-font-semibold tw-tracking-widest tw-uppercase tw-text-brand-accent tw-bg-brand-indigo/10 tw-px-3.5 tw-py-1.5 tw-rounded-full">
            Core capabilities
          </span>
          <h2 className="tw-text-3xl sm:tw-text-4xl tw-font-bold tw-mt-5 tw-tracking-tight tw-text-white">
            Designed for Real-Time Conversational scale
          </h2>
          <p className="tw-text-sm sm:tw-text-base tw-text-white/60 tw-mt-4 tw-leading-relaxed">
            From adaptive voice activity detection to seamless WebRTC and Twilio SIP trunks, Cosmic Chameleon hosts everything necessary to deploy production-grade voice agents.
          </p>
        </div>

        {/* 12 Features Grid */}
        <div className="tw-grid tw-grid-cols-1 sm:tw-grid-cols-2 lg:tw-grid-cols-3 tw-gap-6">
          {[
            { title: "Real-Time Voice AI", icon: Mic, desc: "Streaming pipeline optimized for lightning fast audio packet delivery without buffering pauses." },
            { title: "Human-Like Flow", icon: Sparkles, desc: "Custom inflection and natural pause insertion so conversations sound organic, not mechanical." },
            { title: "Multilingual Support", icon: Globe, desc: "Native switching between English, Hindi, and colloquial Hinglish for absolute localization." },
            { title: "Smart State Flows", icon: Workflow, desc: "Advanced state machine allows agents to guide callers through complex logical branches and collections." },
            { title: "AI Call Analytics", icon: Activity, desc: "Automatic extraction of lead sentiments, follow-up flags, and customer objections directly after every call." },
            { title: "Live Transcripts", icon: MessageSquare, desc: "View text stream of ongoing phone conversations inside the monitor dashboard in real-time." },
            { title: "CRM Integrations", icon: Database, desc: "Bi-directional syncs with Salesforce, HubSpot, and custom REST webhooks to log data instantaneously." },
            { title: "WebRTC & Twilio Ready", icon: Phone, desc: "Seamless inbound/outbound support via SIP trunks, local phone numbers, or browser integrations." },
            { title: "Ultra-Low Latency", icon: Clock, desc: "Response pipeline engineered for a Sub-500ms TTFB (Time To First Byte), mimicking human voice responses." },
            { title: "Barge-In Protection", icon: ArrowRightLeft, desc: "Intelligent interruption handling immediately halts speech synthesis the millisecond the client speaks." },
            { title: "Custom Agent Profiles", icon: Bot, desc: "Define unique personas, prompt sets, vocal pitches, speaking velocities, and knowledge base documents." },
            { title: "Call Recording & QA", icon: Shield, desc: "Encrypted stereo recording audio files synced with detailed transcription guidelines and grading logs." }
          ].map((feat, index) => (
            <div key={index} className="gradient-border-wrapper">
              <div className="gradient-border-content tw-p-8 tw-h-full tw-flex tw-flex-col tw-gap-4">
                <div className="tw-w-10 tw-h-10 tw-rounded-lg tw-bg-brand-indigo/10 tw-flex tw-items-center tw-justify-center tw-text-brand-accent">
                  <feat.icon size={20} />
                </div>
                <h3 className="tw-text-lg tw-font-bold tw-text-white tw-mt-2">{feat.title}</h3>
                <p className="tw-text-xs sm:tw-text-sm tw-text-white/60 tw-leading-relaxed tw-m-0">{feat.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION 4: HOW IT WORKS PIPELINE ── */}
      <section className="tw-relative tw-py-20 md:tw-py-28 tw-bg-brand-bgSecondary/30 tw-border-y tw-border-white/5 tw-z-10">
        <div className="tw-max-w-7xl tw-mx-auto tw-px-6">
          
          {/* Header */}
          <div className="tw-text-center tw-max-w-3xl tw-mx-auto tw-mb-16">
            <span className="tw-text-xs tw-font-semibold tw-tracking-widest tw-uppercase tw-text-brand-accent">
              Execution Architecture
            </span>
            <h2 className="tw-text-3xl sm:tw-text-4xl tw-font-bold tw-mt-4 tw-tracking-tight tw-text-white">
              Under the Hood: Streaming Pipeline
            </h2>
            <p className="tw-text-sm tw-text-white/60 tw-mt-4 tw-m-0">
              Interactive block guide representing how data travels in real time to guarantee ultra-low latency conversations.
            </p>
          </div>

          {/* Interactive Steps Visual Pipeline */}
          <div className="tw-flex tw-flex-col lg:tw-flex-row tw-gap-8 tw-items-stretch">
            
            {/* Left Steps Cards Navigation */}
            <div className="lg:tw-w-1/2 tw-flex tw-flex-col tw-gap-3">
              {steps.map((step, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveStep(idx)}
                  className={`tw-w-full tw-text-left tw-flex tw-items-center tw-gap-4 tw-p-4 tw-rounded-xl tw-border tw-transition-all ${
                    activeStep === idx 
                      ? 'tw-bg-brand-indigo/10 tw-border-brand-indigo tw-shadow-inner' 
                      : 'tw-bg-transparent tw-border-white/5 hover:tw-bg-white/5 hover:tw-border-white/10'
                  }`}
                >
                  <span className={`tw-flex tw-items-center tw-justify-center tw-w-10 tw-h-10 tw-rounded-lg tw-transition-colors ${
                    activeStep === idx ? 'tw-bg-brand-indigo tw-text-white' : 'tw-bg-white/5 tw-text-white/60'
                  }`}>
                    <step.icon size={18} />
                  </span>
                  <div className="tw-flex-grow">
                    <span className="tw-block tw-text-[10px] tw-text-white/40 tw-uppercase tw-tracking-wider">Step {idx + 1}</span>
                    <span className="tw-block tw-text-sm tw-font-bold tw-text-white tw-mt-0.5">{step.title}</span>
                  </div>
                  <ChevronRight size={16} className={`tw-text-white/30 tw-transition-transform ${activeStep === idx ? 'tw-transform tw-translate-x-1 tw-text-brand-accent' : ''}`} />
                </button>
              ))}
            </div>

            {/* Right Details Panel */}
            <div className="lg:tw-w-1/2 tw-flex">
              <div className="tw-w-full glass-panel tw-p-8 tw-rounded-2xl tw-flex tw-flex-col tw-justify-between tw-relative tw-overflow-hidden">
                
                {/* Background glow in details panel */}
                <div className="tw-absolute tw-bottom-[-50px] tw-right-[-50px] tw-w-64 tw-h-64 tw-rounded-full tw-bg-brand-indigo/10 tw-blur-[80px] tw-pointer-events-none" />

                <div className="tw-flex tw-flex-col tw-gap-6 tw-z-10">
                  <div className="tw-inline-flex tw-self-start tw-px-3 tw-py-1 tw-rounded-full tw-bg-brand-indigo/20 tw-text-brand-accent tw-text-[10px] tw-font-bold tw-uppercase tw-tracking-wider">
                    Pipeline Node 0{activeStep + 1}
                  </div>
                  
                  <div className="tw-flex tw-items-center tw-gap-4">
                    <div className="tw-w-14 tw-h-14 tw-rounded-xl tw-bg-brand-indigo tw-text-white tw-flex tw-items-center tw-justify-center">
                      {(() => {
                        const Icon = steps[activeStep].icon;
                        return <Icon size={28} />;
                      })()}
                    </div>
                    <h3 className="tw-text-2xl tw-font-bold tw-text-white tw-m-0">{steps[activeStep].title}</h3>
                  </div>

                  <p className="tw-text-sm sm:tw-text-base tw-text-white/70 tw-leading-relaxed tw-mt-2">
                    {steps[activeStep].desc}
                  </p>
                </div>

                {/* Sub features highlights */}
                <div className="tw-border-t tw-border-white/5 tw-pt-6 tw-mt-8 tw-z-10">
                  <span className="tw-block tw-text-[10px] tw-text-white/40 tw-uppercase tw-tracking-widest tw-mb-4">Key Stream Parameters</span>
                  <div className="tw-grid tw-grid-cols-2 tw-gap-4">
                    <div className="tw-flex tw-items-center tw-gap-2">
                      <CheckCircle2 size={14} className="tw-text-emerald-400" />
                      <span className="tw-text-xs tw-text-white/80">Groq LLM Powered</span>
                    </div>
                    <div className="tw-flex tw-items-center tw-gap-2">
                      <CheckCircle2 size={14} className="tw-text-emerald-400" />
                      <span className="tw-text-xs tw-text-white/80">Streaming Inference</span>
                    </div>
                    <div className="tw-flex tw-items-center tw-gap-2">
                      <CheckCircle2 size={14} className="tw-text-emerald-400" />
                      <span className="tw-text-xs tw-text-white/80">Adaptive VAD</span>
                    </div>
                    <div className="tw-flex tw-items-center tw-gap-2">
                      <CheckCircle2 size={14} className="tw-text-emerald-400" />
                      <span className="tw-text-xs tw-text-white/80">Edge-synthesized Voice</span>
                    </div>
                  </div>
                </div>

              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── SECTION 5: LIVE DASHBOARD PREVIEW ── */}
      <section id="dashboard-preview" className="tw-relative tw-py-20 md:tw-py-28 tw-max-w-7xl tw-mx-auto tw-px-6 tw-z-10">
        
        {/* Section Header */}
        <div className="tw-text-center tw-max-w-3xl tw-mx-auto tw-mb-12">
          <span className="tw-text-xs tw-font-semibold tw-tracking-widest tw-uppercase tw-text-brand-accent">
            Control Room
          </span>
          <h2 className="tw-text-3xl sm:tw-text-4xl tw-font-bold tw-mt-4 tw-tracking-tight tw-text-white">
            SLEEK Interactive Dashboard Preview
          </h2>
          <p className="tw-text-sm sm:tw-text-base tw-text-white/60 tw-mt-4 tw-leading-relaxed">
            Monitor, update, and manage campaigns in real-time. Gain key insights into speech metrics, call histories, latency performance, and agent state maps.
          </p>
        </div>

        {/* Dashboard Mockup Shell */}
        <div className="glass-panel tw-rounded-2xl tw-overflow-hidden tw-shadow-2xl tw-border tw-border-white/10 tw-bg-[#090d1a]/90">
          
          {/* Window Header */}
          <div className="tw-bg-[#0c1224] tw-border-b tw-border-white/5 tw-px-6 tw-py-4 tw-flex tw-justify-between tw-items-center">
            <div className="tw-flex tw-items-center tw-gap-3">
              {/* Fake Window Buttons */}
              <div className="tw-flex tw-gap-1.5">
                <span className="tw-w-3 tw-h-3 tw-rounded-full tw-bg-rose-500/80" />
                <span className="tw-w-3 tw-h-3 tw-rounded-full tw-bg-amber-500/80" />
                <span className="tw-w-3 tw-h-3 tw-rounded-full tw-bg-emerald-500/80" />
              </div>
              <div className="tw-h-4 tw-w-[1px] tw-bg-white/10" />
              <div className="tw-flex tw-items-center tw-gap-2">
                <span className="tw-text-[11px] tw-font-bold tw-text-white/80 tw-tracking-wider tw-uppercase">Chameleon Core</span>
                <span className="tw-bg-brand-indigo/10 tw-text-brand-accent tw-text-[9px] tw-font-bold tw-px-2 tw-py-0.5 tw-rounded-full">v2.0 Beta</span>
              </div>
            </div>

            {/* Fake Controls */}
            <div className="tw-flex tw-items-center tw-gap-3">
              <div className="tw-flex tw-bg-[#060a14] tw-p-1 tw-rounded-lg tw-border tw-border-white/5">
                <button 
                  onClick={() => setActiveDashTab('logs')}
                  className={`tw-text-[10px] tw-font-bold tw-px-3 tw-py-1.5 tw-rounded-md tw-transition-colors ${
                    activeDashTab === 'logs' ? 'tw-bg-brand-indigo tw-text-white' : 'tw-text-white/40 hover:tw-text-white'
                  }`}
                >
                  Live Logs
                </button>
                <button 
                  onClick={() => setActiveDashTab('campaigns')}
                  className={`tw-text-[10px] tw-font-bold tw-px-3 tw-py-1.5 tw-rounded-md tw-transition-colors ${
                    activeDashTab === 'campaigns' ? 'tw-bg-brand-indigo tw-text-white' : 'tw-text-white/40 hover:tw-text-white'
                  }`}
                >
                  Campaigns
                </button>
                <button 
                  onClick={() => setActiveDashTab('analytics')}
                  className={`tw-text-[10px] tw-font-bold tw-px-3 tw-py-1.5 tw-rounded-md tw-transition-colors ${
                    activeDashTab === 'analytics' ? 'tw-bg-brand-indigo tw-text-white' : 'tw-text-white/40 hover:tw-text-white'
                  }`}
                >
                  Analytics
                </button>
              </div>
            </div>
          </div>

          {/* Interactive Screen Area */}
          <div className="tw-p-6">
            <AnimatePresence mode="wait">
              
              {/* Tab 1: Live Logs view */}
              {activeDashTab === 'logs' && (
                <motion.div 
                  key="logs"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                  className="tw-grid tw-grid-cols-1 lg:tw-grid-cols-3 tw-gap-6"
                >
                  
                  {/* Dashboard Sidebar: Call log list */}
                  <div className="lg:tw-col-span-1 tw-bg-[#060a14]/60 tw-border tw-border-white/5 tw-rounded-xl tw-p-4">
                    <div className="tw-flex tw-justify-between tw-items-center tw-mb-4">
                      <span className="tw-text-xs tw-font-bold tw-text-white/70">Recent Calls</span>
                      <span className="tw-flex tw-items-center tw-gap-1.5 tw-text-[10px] tw-text-emerald-400 tw-font-bold">
                        <span className="tw-w-1.5 tw-h-1.5 tw-rounded-full tw-bg-emerald-500 tw-animate-pulse" /> Live Inbound
                      </span>
                    </div>

                    <div className="tw-flex tw-flex-col tw-gap-2.5">
                      {[
                        { lead: "Karan Johar", phone: "+91 98451 22910", time: "Just now", status: "Active", bg: "tw-bg-brand-indigo/10 tw-border-brand-indigo/30" },
                        { lead: "Priya Sharma", phone: "+91 90021 88471", time: "3 mins ago", status: "Transferred", bg: "tw-bg-transparent tw-border-white/5" },
                        { lead: "Anoop Kumar", phone: "+91 76201 11342", time: "14 mins ago", status: "Answered", bg: "tw-bg-transparent tw-border-white/5" },
                        { lead: "Nisha Patel", phone: "+91 88910 03418", time: "42 mins ago", status: "No Answer", bg: "tw-bg-transparent tw-border-white/5" }
                      ].map((item, idx) => (
                        <div key={idx} className={`tw-p-3 tw-rounded-lg tw-border tw-flex tw-justify-between tw-items-center ${item.bg}`}>
                          <div>
                            <span className="tw-block tw-text-xs tw-font-bold tw-text-white">{item.lead}</span>
                            <span className="tw-block tw-text-[10px] tw-text-white/40 tw-mt-0.5">{item.phone}</span>
                          </div>
                          <div className="tw-text-right">
                            <span className={`tw-inline-block tw-text-[9px] tw-font-bold tw-px-2 tw-py-0.5 tw-rounded-full ${
                              item.status === 'Active' ? 'tw-bg-emerald-500/20 tw-text-emerald-400' :
                              item.status === 'Transferred' ? 'tw-bg-purple-500/20 tw-text-purple-400' :
                              item.status === 'Answered' ? 'tw-bg-blue-500/20 tw-text-blue-400' :
                              'tw-bg-white/5 tw-text-white/45'
                            }`}>{item.status}</span>
                            <span className="tw-block tw-text-[9px] tw-text-white/30 tw-mt-1">{item.time}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Dashboard Center: Live transcript */}
                  <div className="lg:tw-col-span-2 tw-flex tw-flex-col tw-gap-4">
                    
                    {/* Active call headers */}
                    <div className="tw-bg-[#060a14]/60 tw-border tw-border-white/5 tw-rounded-xl tw-p-4 tw-flex tw-justify-between tw-items-center">
                      <div className="tw-flex tw-items-center tw-gap-3">
                        <div className="tw-w-9 tw-h-9 tw-rounded-lg tw-bg-brand-indigo/10 tw-flex tw-items-center tw-justify-center tw-text-brand-accent">
                          <Mic size={16} />
                        </div>
                        <div>
                          <span className="tw-block tw-text-xs tw-font-bold tw-text-white">Active Call: Karan Johar</span>
                          <span className="tw-block tw-text-[10px] tw-text-white/40 tw-mt-0.5">Campaign: Real Estate May Followups</span>
                        </div>
                      </div>
                      
                      <div className="tw-flex tw-items-center tw-gap-4">
                        <div className="tw-text-right">
                          <span className="tw-block tw-text-[9px] tw-text-white/40 tw-uppercase tw-tracking-wider">Latency Score</span>
                          <span className="tw-block tw-text-xs tw-font-bold tw-text-emerald-400">340ms average</span>
                        </div>
                        <div className="tw-text-right">
                          <span className="tw-block tw-text-[9px] tw-text-white/40 tw-uppercase tw-tracking-wider">CRM Synced</span>
                          <span className="tw-block tw-text-xs tw-font-bold tw-text-emerald-400">HubSpot ok</span>
                        </div>
                      </div>
                    </div>

                    {/* Chat log body */}
                    <div className="tw-bg-[#060a14]/40 tw-border tw-border-white/5 tw-rounded-xl tw-p-4 tw-h-[220px] tw-overflow-y-auto tw-flex tw-flex-col tw-gap-4">
                      <div className="tw-flex tw-items-start tw-gap-2.5">
                        <span className="tw-text-[10px] tw-font-bold tw-text-white/30 tw-mt-1">11:04:12</span>
                        <div className="tw-bg-white/5 tw-border tw-border-white/5 tw-p-3 tw-rounded-lg tw-max-w-[85%]">
                          <span className="tw-block tw-text-[9px] tw-font-bold tw-text-white/40 tw-uppercase tw-tracking-wider">Customer</span>
                          <span className="tw-block tw-text-xs tw-text-white/90 tw-mt-1">Hi, Sector 62 wale project ke regarding push notification mila tha. Kya uski bookings open hain abhi?</span>
                        </div>
                      </div>

                      <div className="tw-flex tw-items-start tw-gap-2.5 tw-flex-row-reverse">
                        <span className="tw-text-[10px] tw-font-bold tw-text-white/30 tw-mt-1">11:04:13</span>
                        <div className="tw-bg-brand-indigo/15 tw-border tw-border-brand-indigo/30 tw-p-3 tw-rounded-lg tw-max-w-[85%]">
                          <span className="tw-block tw-text-[9px] tw-font-bold tw-text-brand-accent tw-uppercase tw-tracking-wider">Chameleon AI</span>
                          <span className="tw-block tw-text-xs tw-text-white/90 tw-mt-1">Hello! Yes, bookings are active. We have 3BHK options facing the park, and a few developer units remaining. Kya main aapka visit Saturday ko schedule kar sakti hoon?</span>
                        </div>
                      </div>

                      <div className="tw-flex tw-items-start tw-gap-2.5">
                        <span className="tw-text-[10px] tw-font-bold tw-text-white/30 tw-mt-1">11:04:16</span>
                        <div className="tw-bg-white/5 tw-border tw-border-white/5 tw-p-3 tw-rounded-lg tw-max-w-[85%]">
                          <span className="tw-block tw-text-[9px] tw-font-bold tw-text-white/40 tw-uppercase tw-tracking-wider">Customer</span>
                          <span className="tw-block tw-text-xs tw-text-white/90 tw-mt-1">Acha, parking charges extra hain ya built-in? Aur site vis-</span>
                        </div>
                      </div>

                      <div className="tw-flex tw-items-start tw-gap-2.5 tw-flex-row-reverse">
                        <span className="tw-text-[10px] tw-font-bold tw-text-white/30 tw-mt-1">11:04:17</span>
                        <div className="tw-bg-brand-indigo/15 tw-border tw-border-brand-indigo/30 tw-p-3 tw-rounded-lg tw-max-w-[85%]">
                          <span className="tw-block tw-text-[9px] tw-font-bold tw-text-brand-indigo tw-uppercase tw-tracking-wider">Chameleon AI <span className="tw-text-[9px] tw-text-rose-500 tw-font-bold tw-ml-1.5 tw-normal-case tw-italic">Interrupted</span></span>
                          <span className="tw-block tw-text-xs tw-text-white/90 tw-mt-1">Built-in parking allocation hai! Built-in parking covers one spot, for additional spots developers nominal rates charge karte hain. But sorry aap site visit ke regarding kuch bol rahe the?</span>
                        </div>
                      </div>
                    </div>

                    {/* Audio Recorder Playback Control panel */}
                    <div className="tw-bg-[#060a14]/60 tw-border tw-border-white/5 tw-rounded-xl tw-p-4">
                      <div className="tw-flex tw-items-center tw-justify-between tw-gap-4">
                        
                        {/* Play control */}
                        <div className="tw-flex tw-items-center tw-gap-3">
                          <button 
                            onClick={() => setIsPlayingRecording(!isPlayingRecording)}
                            className="tw-w-10 tw-h-10 tw-rounded-full tw-bg-brand-indigo hover:tw-bg-brand-purple tw-text-white tw-flex tw-items-center tw-justify-center tw-transition-colors"
                          >
                            {isPlayingRecording ? <Pause size={16} /> : <Play size={16} className="tw-ml-0.5" />}
                          </button>
                          <div>
                            <span className="tw-block tw-text-xs tw-font-bold tw-text-white">Call Recording Preview</span>
                            <span className="tw-block tw-text-[10px] tw-text-white/40 tw-mt-0.5">Recording ID: rec_094711</span>
                          </div>
                        </div>

                        {/* Progress Bar & Waveform representation */}
                        <div className="tw-flex-grow tw-hidden sm:tw-flex tw-items-center tw-gap-2">
                          <span className="tw-text-[10px] tw-text-white/40">00:32</span>
                          <div className="tw-flex-grow tw-h-2 tw-bg-white/5 tw-rounded-full tw-relative tw-overflow-hidden">
                            <div 
                              className="tw-absolute tw-left-0 tw-top-0 tw-h-full tw-bg-gradient-to-r tw-from-brand-indigo tw-to-brand-purple"
                              style={{ width: `${recordingProgress}%` }}
                            />
                          </div>
                          <span className="tw-text-[10px] tw-text-white/40">01:30</span>
                        </div>

                        {/* Stats detail */}
                        <div className="tw-text-right">
                          <span className="tw-block tw-text-[9px] tw-text-white/40 tw-uppercase tw-tracking-wider">VAD State</span>
                          <span className="tw-inline-flex tw-items-center tw-gap-1 tw-text-[10px] tw-font-bold tw-text-brand-accent">
                            <Volume2 size={12} /> Active Voice
                          </span>
                        </div>

                      </div>
                    </div>

                  </div>

                </motion.div>
              )}

              {/* Tab 2: Campaigns */}
              {activeDashTab === 'campaigns' && (
                <motion.div 
                  key="campaigns"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                  className="tw-grid tw-grid-cols-1 md:tw-grid-cols-2 lg:tw-grid-cols-3 tw-gap-6"
                >
                  {[
                    { name: "Real Estate May Followups", leads: 450, processed: 412, success: 38, status: "Active", bg: "tw-bg-brand-indigo/10 tw-border-brand-indigo/30" },
                    { name: "Recruitment Outreach Q2", leads: 1200, processed: 1200, success: 184, status: "Completed", bg: "tw-bg-transparent tw-border-white/5" },
                    { name: "Healthcare Checkups Oct", leads: 820, processed: 0, success: 0, status: "Pending", bg: "tw-bg-transparent tw-border-white/5" }
                  ].map((camp, idx) => (
                    <div key={idx} className={`tw-p-5 tw-rounded-xl tw-border ${camp.bg} tw-flex tw-flex-col tw-gap-4`}>
                      <div className="tw-flex tw-justify-between tw-items-start">
                        <span className="tw-text-sm tw-font-bold tw-text-white">{camp.name}</span>
                        <span className={`tw-text-[9px] tw-font-bold tw-px-2.5 tw-py-0.5 tw-rounded-full ${
                          camp.status === 'Active' ? 'tw-bg-emerald-500/20 tw-text-emerald-400' :
                          camp.status === 'Completed' ? 'tw-bg-blue-500/20 tw-text-blue-400' :
                          'tw-bg-white/5 tw-text-white/45'
                        }`}>{camp.status}</span>
                      </div>

                      <div className="tw-grid tw-grid-cols-3 tw-gap-2 tw-text-center tw-bg-[#060a14]/40 tw-p-3 tw-rounded-lg">
                        <div>
                          <span className="tw-block tw-text-[9px] tw-text-white/40 tw-uppercase">Leads</span>
                          <span className="tw-block tw-text-xs tw-font-bold tw-text-white tw-mt-1">{camp.leads}</span>
                        </div>
                        <div>
                          <span className="tw-block tw-text-[9px] tw-text-white/40 tw-uppercase">Called</span>
                          <span className="tw-block tw-text-xs tw-font-bold tw-text-white tw-mt-1">{camp.processed}</span>
                        </div>
                        <div>
                          <span className="tw-block tw-text-[9px] tw-text-white/40 tw-uppercase">Booked</span>
                          <span className="tw-block tw-text-xs tw-font-bold tw-text-brand-accent tw-mt-1">{camp.success}</span>
                        </div>
                      </div>

                      {/* Progress representation */}
                      <div>
                        <div className="tw-flex tw-justify-between tw-text-[9px] tw-text-white/40 tw-mb-1">
                          <span>Outbound Dial Rate</span>
                          <span>{Math.round((camp.processed / camp.leads) * 100)}%</span>
                        </div>
                        <div className="tw-h-1.5 tw-bg-white/5 tw-rounded-full tw-relative tw-overflow-hidden">
                          <div 
                            className="tw-absolute tw-left-0 tw-top-0 tw-h-full tw-bg-gradient-to-r tw-from-brand-indigo tw-to-brand-purple"
                            style={{ width: `${(camp.processed / camp.leads) * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </motion.div>
              )}

              {/* Tab 3: Analytics */}
              {activeDashTab === 'analytics' && (
                <motion.div 
                  key="analytics"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                  className="tw-grid tw-grid-cols-1 md:tw-grid-cols-2 lg:tw-grid-cols-4 tw-gap-6"
                >
                  {[
                    { label: "Total Latency", val: "380ms", desc: "P95 Audio Response TTFB", change: "-42ms vs last week", positive: true },
                    { label: "Lead Conversion", val: "22.4%", desc: "Appointments booked directly", change: "+4.1% vs last week", positive: true },
                    { label: "Barge-in Error Rate", val: "1.2%", desc: "Interruption recovery failures", change: "-0.3% vs last week", positive: true },
                    { label: "Avg Call Duration", val: "3m 12s", desc: "Average human talk duration", change: "+14s vs last week", positive: true }
                  ].map((stat, idx) => (
                    <div key={idx} className="tw-bg-[#060a14]/60 tw-border tw-border-white/5 tw-p-5 tw-rounded-xl tw-flex tw-flex-col tw-gap-2">
                      <span className="tw-text-xs tw-font-bold tw-text-white/40 tw-uppercase tw-tracking-wider">{stat.label}</span>
                      <span className="tw-text-2xl tw-font-extrabold tw-text-white tw-mt-1">{stat.val}</span>
                      <span className="tw-text-[10px] tw-text-white/60">{stat.desc}</span>
                      
                      <div className="tw-border-t tw-border-white/5 tw-pt-3 tw-mt-4 tw-flex tw-items-center tw-justify-between">
                        <span className="tw-text-[10px] tw-text-emerald-400 tw-font-bold tw-flex tw-items-center tw-gap-1">
                          <TrendingUp size={12} /> {stat.change}
                        </span>
                      </div>
                    </div>
                  ))}
                </motion.div>
              )}

            </AnimatePresence>
          </div>

        </div>
      </section>

      {/* ── SECTION 6: MULTILINGUAL AI SECTION ── */}
      <section id="multilingual" className="tw-relative tw-py-20 md:tw-py-28 tw-bg-brand-bgSecondary/30 tw-border-y tw-border-white/5 tw-z-10">
        <div className="tw-max-w-7xl tw-mx-auto tw-px-6">
          <div className="tw-grid tw-grid-cols-1 lg:tw-grid-cols-12 tw-gap-12 tw-items-center">
            
            {/* Left Content */}
            <div className="lg:tw-col-span-5 tw-flex tw-flex-col tw-gap-6 tw-text-left">
              <span className="tw-text-xs tw-font-semibold tw-tracking-widest tw-uppercase tw-text-brand-accent">
                Language localization
              </span>
              <h2 className="tw-text-3xl sm:tw-text-4xl tw-font-bold tw-m-0 tw-tracking-tight tw-text-white">
                Understands real conversational language — not just keywords
              </h2>
              <p className="tw-text-sm sm:tw-text-base tw-text-white/60 tw-leading-relaxed tw-m-0">
                Cosmic Chameleon is pre-trained to parse colloquial Indian structures, switching dynamically between native English, clean Hindi, and fast-paced blended Hinglish.
              </p>

              {/* Language selector pills */}
              <div className="tw-flex tw-bg-[#060a14] tw-p-1 tw-rounded-xl tw-border tw-border-white/5 tw-self-start">
                {[
                  { id: 'english', label: 'English' },
                  { id: 'hindi', label: 'हिंदी (Hindi)' },
                  { id: 'hinglish', label: 'Hinglish' }
                ].map((lang) => (
                  <button
                    key={lang.id}
                    onClick={() => setActiveLang(lang.id)}
                    className={`tw-text-xs tw-font-bold tw-px-4 tw-py-2.5 tw-rounded-lg tw-transition-colors ${
                      activeLang === lang.id ? 'tw-bg-brand-indigo tw-text-white' : 'tw-text-white/45 hover:tw-text-white'
                    }`}
                  >
                    {lang.label}
                  </button>
                ))}
              </div>

              {/* Visual latency highlight badge */}
              <div className="tw-flex tw-items-center tw-gap-3.5 tw-bg-brand-indigo/10 tw-border tw-border-brand-indigo/20 tw-p-4 tw-rounded-xl">
                <Globe size={24} className="tw-text-brand-accent" />
                <div>
                  <span className="tw-block tw-text-xs tw-font-bold tw-text-white">Continuous Speech Translation</span>
                  <span className="tw-block tw-text-[11px] tw-text-white/50 tw-mt-0.5">Zero delays in semantic language decoding models.</span>
                </div>
              </div>

            </div>

            {/* Right Chat Bubble Display */}
            <div className="lg:tw-col-span-7">
              <div className="glass-panel tw-p-6 sm:tw-p-8 tw-rounded-2xl tw-relative tw-overflow-hidden">
                <div className="tw-absolute tw-top-[-40px] tw-left-[-40px] tw-w-48 tw-h-48 tw-rounded-full tw-bg-brand-indigo/5 tw-blur-[80px] tw-pointer-events-none" />

                <div className="tw-flex tw-justify-between tw-items-center tw-border-b tw-border-white/5 tw-pb-4 tw-mb-6">
                  <div className="tw-flex tw-items-center tw-gap-2">
                    <span className="tw-text-xs tw-font-bold tw-text-white/70">Conversation Simulator</span>
                    <span className="tw-text-[10px] tw-text-brand-accent tw-font-bold tw-uppercase tw-tracking-widest">({activeLang})</span>
                  </div>
                  <span className="tw-flex tw-items-center tw-gap-1.5 tw-text-[10px] tw-text-white/40">
                    <Clock size={12} /> Live stream simulation
                  </span>
                </div>

                {/* Dialog bubles list */}
                <div className="tw-flex tw-flex-col tw-gap-5">
                  <AnimatePresence mode="popLayout">
                    {conversationData[activeLang].map((msg, idx) => (
                      <motion.div
                        key={`${activeLang}-${idx}`}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.25, delay: idx * 0.1 }}
                        className={`tw-flex tw-items-start tw-gap-3.5 ${
                          msg.sender === 'agent' ? 'tw-flex-row-reverse' : ''
                        }`}
                      >
                        {/* Avatar */}
                        <div className={`tw-flex tw-items-center tw-justify-center tw-w-8 tw-h-8 tw-rounded-full tw-flex-shrink-0 ${
                          msg.sender === 'agent' 
                            ? 'tw-bg-brand-indigo tw-text-white' 
                            : 'tw-bg-white/10 tw-text-white/70 tw-text-xs tw-font-bold'
                        }`}>
                          {msg.sender === 'agent' ? '🤖' : '👤'}
                        </div>

                        {/* Bubble */}
                        <div className={`tw-p-4 tw-rounded-2xl tw-max-w-[80%] ${
                          msg.sender === 'agent'
                            ? 'tw-bg-brand-indigo/15 tw-border tw-border-brand-indigo/35 tw-rounded-tr-none'
                            : 'tw-bg-white/5 tw-border tw-border-white/5 tw-rounded-tl-none'
                        }`}>
                          <span className="tw-block tw-text-[9px] tw-font-bold tw-text-white/40 tw-uppercase tw-tracking-wider">
                            {msg.sender === 'agent' ? 'Cosmic Agent' : 'User'}
                          </span>
                          <p className="tw-text-xs sm:tw-text-sm tw-text-white/90 tw-leading-relaxed tw-mt-1.5 tw-m-0">
                            {msg.text}
                          </p>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>

              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── SECTION 7: USE CASES SECTION ── */}
      <section id="use-cases" className="tw-relative tw-py-20 md:tw-py-28 tw-max-w-7xl tw-mx-auto tw-px-6 tw-z-10">
        
        {/* Section Header */}
        <div className="tw-text-center tw-max-w-3xl tw-mx-auto tw-mb-16">
          <span className="tw-text-xs tw-font-semibold tw-tracking-widest tw-uppercase tw-text-brand-accent">
            Industry deployment
          </span>
          <h2 className="tw-text-3xl sm:tw-text-4xl tw-font-bold tw-mt-4 tw-tracking-tight tw-text-white">
            Engineered for specific business conversations
          </h2>
          <p className="tw-text-sm sm:tw-text-base tw-text-white/60 tw-mt-4 tw-leading-relaxed">
            Tailor-made state flows and validation scripts designed to meet compliance and capture high-converting metrics in seconds.
          </p>
        </div>

        {/* 6 Grid items */}
        <div className="tw-grid tw-grid-cols-1 md:tw-grid-cols-2 lg:tw-grid-cols-3 tw-gap-6">
          {useCases.map((useCase, idx) => (
            <div 
              key={idx}
              onClick={() => setActiveUseCase(idx)}
              className={`tw-cursor-pointer tw-text-left tw-p-8 tw-rounded-2xl tw-border tw-transition-all ${
                activeUseCase === idx 
                  ? 'tw-bg-brand-indigo/10 tw-border-brand-indigo tw-shadow-xl tw-shadow-brand-indigo/5' 
                  : 'glass-panel hover:tw-border-white/20'
              }`}
            >
              <div className="tw-flex tw-justify-between tw-items-center tw-mb-4">
                <span className="tw-text-xs tw-font-bold tw-text-brand-accent tw-uppercase tw-tracking-wider">{useCase.tag}</span>
                <span className="tw-text-[10px] tw-font-bold tw-text-emerald-400 tw-bg-emerald-500/10 tw-px-2 tw-py-0.5 tw-rounded-full">{useCase.metrics}</span>
              </div>
              
              <h3 className="tw-text-xl tw-font-bold tw-text-white">{useCase.title}</h3>
              
              <p className="tw-text-xs sm:tw-text-sm tw-text-white/60 tw-leading-relaxed tw-mt-3 tw-m-0">
                {useCase.desc}
              </p>

              {/* Sample script preview */}
              <div className="tw-mt-5 tw-pt-4 tw-border-t tw-border-white/5">
                <span className="tw-block tw-text-[9px] tw-text-white/30 tw-uppercase tw-tracking-wider">Agent Script Preview</span>
                <p className="tw-text-xs tw-text-white/80 tw-italic tw-leading-relaxed tw-mt-1.5 tw-m-0">
                  &ldquo;{useCase.script}&rdquo;
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION 8: AI PIPELINE SECTION ── */}
      <section id="pipeline" className="tw-relative tw-py-20 md:tw-py-28 tw-bg-brand-bgSecondary/30 tw-border-y tw-border-white/5 tw-z-10">
        <div className="tw-max-w-7xl tw-mx-auto tw-px-6">
          
          {/* Header */}
          <div className="tw-text-center tw-max-w-3xl tw-mx-auto tw-mb-16">
            <span className="tw-text-xs tw-font-semibold tw-tracking-widest tw-uppercase tw-text-brand-accent">
              Platform Architecture
            </span>
            <h2 className="tw-text-3xl sm:tw-text-4xl tw-font-bold tw-mt-4 tw-tracking-tight tw-text-white">
              Low-Latency Audio Pipeline Nodes
            </h2>
            <p className="tw-text-sm tw-text-white/60 tw-mt-4 tw-leading-relaxed">
              We leverage an advanced WebSockets infrastructure combining Pipecat, Groq LPU processing engines, and fast edge-TTS endpoints to deliver responses with human velocity.
            </p>
          </div>

          {/* Architecture Node Diagram */}
          <div className="glass-panel tw-rounded-2xl tw-p-8 tw-overflow-x-auto">
            <div className="tw-min-w-[800px] tw-flex tw-justify-between tw-items-center tw-relative tw-py-6">
              
              {/* Connecting back lines */}
              <div className="tw-absolute tw-left-8 tw-right-8 tw-top-1/2 tw-h-[2px] tw-bg-gradient-to-r tw-from-cyan-500 tw-via-brand-indigo tw-to-pink-500 tw-opacity-20 tw-z-0" />

              {/* Node 1 */}
              <div className="tw-flex tw-flex-col tw-items-center tw-gap-3.5 tw-relative tw-z-10 tw-w-[140px]">
                <div className="tw-w-14 tw-h-14 tw-rounded-xl tw-bg-[#0c1224] tw-border tw-border-cyan-500/50 tw-text-cyan-400 tw-flex tw-items-center tw-justify-center tw-shadow-lg tw-shadow-cyan-500/10">
                  <Phone size={22} className="glow-blue" />
                </div>
                <div className="tw-text-center">
                  <span className="tw-block tw-text-xs tw-font-bold tw-text-white">Browser / Twilio</span>
                  <span className="tw-block tw-text-[9px] tw-text-white/40 tw-mt-0.5">SIP / WebRTC Call</span>
                </div>
              </div>

              <div className="tw-text-white/20 tw-font-bold">➔</div>

              {/* Node 2 */}
              <div className="tw-flex tw-flex-col tw-items-center tw-gap-3.5 tw-relative tw-z-10 tw-w-[140px]">
                <div className="tw-w-14 tw-h-14 tw-rounded-xl tw-bg-[#0c1224] tw-border tw-border-brand-indigo/50 tw-text-brand-indigo tw-flex tw-items-center tw-justify-center tw-shadow-lg tw-shadow-brand-indigo/10">
                  <GitBranch size={22} className="glow-purple" />
                </div>
                <div className="tw-text-center">
                  <span className="tw-block tw-text-xs tw-font-bold tw-text-white">WebSockets</span>
                  <span className="tw-block tw-text-[9px] tw-text-white/40 tw-mt-0.5">Streaming Audio API</span>
                </div>
              </div>

              <div className="tw-text-white/20 tw-font-bold">➔</div>

              {/* Node 3 */}
              <div className="tw-flex tw-flex-col tw-items-center tw-gap-3.5 tw-relative tw-z-10 tw-w-[140px]">
                <div className="tw-w-14 tw-h-14 tw-rounded-xl tw-bg-[#0c1224] tw-border tw-border-brand-purple/50 tw-text-brand-purple tw-flex tw-items-center tw-justify-center tw-shadow-lg tw-shadow-brand-purple/10">
                  <Layers size={22} />
                </div>
                <div className="tw-text-center">
                  <span className="tw-block tw-text-xs tw-font-bold tw-text-white">Pipecat Stream</span>
                  <span className="tw-block tw-text-[9px] tw-text-white/40 tw-mt-0.5">VAD Orchestrator</span>
                </div>
              </div>

              <div className="tw-text-white/20 tw-font-bold">➔</div>

              {/* Node 4 */}
              <div className="tw-flex tw-flex-col tw-items-center tw-gap-3.5 tw-relative tw-z-10 tw-w-[140px]">
                <div className="tw-w-14 tw-h-14 tw-rounded-xl tw-bg-[#0c1224] tw-border tw-border-pink-500/50 tw-text-pink-400 tw-flex tw-items-center tw-justify-center tw-shadow-lg tw-shadow-pink-500/10">
                  <Terminal size={22} />
                </div>
                <div className="tw-text-center">
                  <span className="tw-block tw-text-xs tw-font-bold tw-text-white">Groq LLM Engine</span>
                  <span className="tw-block tw-text-[9px] tw-text-white/40 tw-mt-0.5">LPU Inference Node</span>
                </div>
              </div>

              <div className="tw-text-white/20 tw-font-bold">➔</div>

              {/* Node 5 */}
              <div className="tw-flex tw-flex-col tw-items-center tw-gap-3.5 tw-relative tw-z-10 tw-w-[140px]">
                <div className="tw-w-14 tw-h-14 tw-rounded-xl tw-bg-[#0c1224] tw-border tw-border-amber-500/50 tw-text-amber-400 tw-flex tw-items-center tw-justify-center tw-shadow-lg tw-shadow-amber-500/10">
                  <Volume2 size={22} />
                </div>
                <div className="tw-text-center">
                  <span className="tw-block tw-text-xs tw-font-bold tw-text-white">Edge TTS Synthesizer</span>
                  <span className="tw-block tw-text-[9px] tw-text-white/40 tw-mt-0.5">Accented Voice Outputs</span>
                </div>
              </div>

            </div>
          </div>

        </div>
      </section>

      {/* ── SECTION 9: TESTIMONIALS ── */}
      <section className="tw-relative tw-py-20 md:tw-py-28 tw-max-w-7xl tw-mx-auto tw-px-6 tw-z-10">
        
        {/* Header */}
        <div className="tw-text-center tw-max-w-3xl tw-mx-auto tw-mb-16">
          <span className="tw-text-xs tw-font-semibold tw-tracking-widest tw-uppercase tw-text-brand-accent">
            Customer voices
          </span>
          <h2 className="tw-text-3xl sm:tw-text-4xl tw-font-bold tw-mt-4 tw-tracking-tight tw-text-white">
            Trusted by modern sales & operational hubs
          </h2>
        </div>

        {/* 3 cards grid */}
        <div className="tw-grid tw-grid-cols-1 md:tw-grid-cols-3 tw-gap-8">
          {[
            {
              quote: "Cosmic Chameleon transformed our real estate inbound queries. The Hinglish support was crucial since our target buyers speak a mix of Hindi and English. Absolute game changer.",
              author: "Nikhil Kamath",
              role: "Head of Operations at Zenith Homes",
              avatar: "NK"
            },
            {
              quote: "We screen over 800 applicants weekly for delivery roles. Integrating Chameleon voice agents with our custom CRM API saved us 120+ HR screening hours every month.",
              author: "Aditi Rao",
              role: "VP of People at FleetRunner Logistics",
              avatar: "AR"
            },
            {
              quote: "The barge-in interruption capability is where this platform completely outperforms standard bots. It handles verbal pauses and interruption perfectly.",
              author: "Siddharth Mehta",
              role: "CTO at SecureCare Health",
              avatar: "SM"
            }
          ].map((testi, idx) => (
            <div key={idx} className="glass-panel tw-p-8 tw-rounded-2xl tw-flex tw-flex-col tw-justify-between tw-gap-6 tw-relative">
              
              {/* Quote bubble visual decorator */}
              <span className="tw-absolute tw-top-4 tw-right-6 tw-text-5xl tw-text-white/5 tw-font-serif tw-pointer-events-none">&ldquo;</span>
              
              <p className="tw-text-xs sm:tw-text-sm tw-text-white/70 tw-leading-relaxed tw-italic tw-m-0">
                &ldquo;{testi.quote}&rdquo;
              </p>

              <div className="tw-flex tw-items-center tw-gap-3.5">
                <div className="tw-w-9 tw-h-9 tw-rounded-full tw-bg-brand-indigo/20 tw-border tw-border-brand-indigo/35 tw-flex tw-items-center tw-justify-center tw-text-xs tw-font-bold tw-text-brand-accent">
                  {testi.avatar}
                </div>
                <div>
                  <span className="tw-block tw-text-xs tw-font-bold tw-text-white">{testi.author}</span>
                  <span className="tw-block tw-text-[10px] tw-text-white/40 tw-mt-0.5">{testi.role}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION 10: FINAL CTA ── */}
      <section className="tw-relative tw-py-20 md:tw-py-28 tw-max-w-7xl tw-mx-auto tw-px-6 tw-z-10">
        
        {/* Floating gradient box */}
        <div className="tw-relative tw-rounded-3xl tw-overflow-hidden tw-bg-[#090d1a] tw-border tw-border-white/10 tw-p-8 sm:tw-p-12 md:tw-p-16 tw-text-center tw-shadow-2xl">
          
          {/* Background glowing effects inside CTA */}
          <div className="tw-absolute tw-bottom-[-100px] tw-left-[-100px] tw-w-[350px] tw-h-[350px] tw-bg-brand-indigo/10 tw-rounded-full tw-blur-[100px] tw-pointer-events-none" />
          <div className="tw-absolute tw-top-[-100px] tw-right-[-100px] tw-w-[350px] tw-h-[350px] tw-bg-brand-purple/10 tw-rounded-full tw-blur-[100px] tw-pointer-events-none" />

          <div className="tw-relative tw-z-10 tw-max-w-3xl tw-mx-auto tw-flex tw-flex-col tw-gap-6 tw-items-center">
            
            <span className="tw-text-xs tw-font-semibold tw-tracking-widest tw-uppercase tw-text-brand-accent">
              Get Started In Minutes
            </span>

            <h2 className="tw-text-3xl sm:tw-text-4xl md:tw-text-5xl tw-font-extrabold tw-tracking-tight tw-text-white tw-leading-tight">
              Start Building Production-Grade <br/>
              Voice AI Today
            </h2>

            <p className="tw-text-sm sm:tw-text-base tw-text-white/60 tw-max-w-xl tw-leading-relaxed tw-m-0">
              Create an account now to get 100 free outbound/inbound call minutes evaluated on our Groq LPU voice pipeline.
            </p>

            <div className="tw-flex tw-flex-wrap tw-justify-center tw-gap-4 tw-mt-4">
              <Link 
                href="/login" 
                className="tw-flex tw-items-center tw-gap-2 tw-text-sm tw-font-semibold tw-px-8 tw-py-4 tw-rounded-xl tw-bg-gradient-to-r tw-from-brand-indigo tw-to-brand-purple hover:tw-opacity-95 tw-shadow-xl tw-shadow-brand-indigo/25 tw-transition-all tw-no-underline tw-text-white hover:tw-scale-[1.02]"
              >
                Get Started Free
              </Link>
              <a 
                href="mailto:contact@cosmicchameleon.ai" 
                className="tw-flex tw-items-center tw-gap-2 tw-text-sm tw-font-semibold tw-px-8 tw-py-4 tw-rounded-xl tw-bg-white/5 hover:tw-bg-white/10 tw-border tw-border-white/10 hover:tw-border-white/20 tw-transition-all tw-no-underline tw-text-white hover:tw-scale-[1.02]"
              >
                Book Enterprise Demo
              </a>
            </div>

          </div>
        </div>
      </section>

      {/* ── SECTION 11: FOOTER ── */}
      <footer className="tw-relative tw-border-t tw-border-white/5 tw-bg-brand-bgSecondary/60 tw-py-16 tw-z-10">
        <div className="tw-max-w-7xl tw-mx-auto tw-px-6">
          <div className="tw-grid tw-grid-cols-1 md:tw-grid-cols-12 tw-gap-10 tw-mb-12">
            
            {/* Brand column */}
            <div className="md:tw-col-span-4 tw-flex tw-flex-col tw-gap-4">
              <Link href="/" className="tw-flex tw-items-center tw-gap-2.5 tw-no-underline">
                <span className="tw-flex tw-items-center tw-justify-center tw-w-9 tw-height-9 tw-rounded-lg tw-bg-gradient-to-br tw-from-brand-indigo tw-to-brand-purple tw-text-lg">
                  🦎
                </span>
                <span className="tw-font-bold tw-text-md tw-text-white">
                  Cosmic <span className="tw-text-brand-accent">Chameleon</span>
                </span>
              </Link>
              <p className="tw-text-xs tw-text-white/40 tw-leading-relaxed tw-max-w-xs tw-m-0">
                “Human-Like AI Voice Agents for Real Conversations.” Build low-latency calling structures powered by streaming APIs and Groq inference servers.
              </p>
            </div>

            {/* Links Columns */}
            <div className="md:tw-col-span-2 tw-flex tw-flex-col tw-gap-3.5">
              <span className="tw-text-[10px] tw-font-bold tw-text-white/60 tw-uppercase tw-tracking-wider">Product</span>
              <a href="#features" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">Features</a>
              <a href="#pipeline" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">Pipeline Node</a>
              <a href="#use-cases" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">Solutions</a>
              <a href="/login" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">Sign In</a>
            </div>

            <div className="md:tw-col-span-2 tw-flex tw-flex-col tw-gap-3.5">
              <span className="tw-text-[10px] tw-font-bold tw-text-white/60 tw-uppercase tw-tracking-wider">Developers</span>
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">GitHub</a>
              <a href="#pipeline" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">API Docs</a>
              <a href="#pipeline" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">WebSockets SDK</a>
              <a href="#pipeline" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">Latency Metrics</a>
            </div>

            <div className="md:tw-col-span-2 tw-flex tw-flex-col tw-gap-3.5">
              <span className="tw-text-[10px] tw-font-bold tw-text-white/60 tw-uppercase tw-tracking-wider">Pricing & Trust</span>
              <a href="/login" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">Usage Pricing</a>
              <a href="#features" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">SLA Uptime</a>
              <a href="#features" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">Privacy Guard</a>
              <a href="#features" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">Compliance Logs</a>
            </div>

            <div className="md:tw-col-span-2 tw-flex tw-flex-col tw-gap-3.5">
              <span className="tw-text-[10px] tw-font-bold tw-text-white/60 tw-uppercase tw-tracking-wider">Contact</span>
              <a href="mailto:contact@cosmicchameleon.ai" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">contact@cosmicchameleon.ai</a>
              <a href="tel:+18005550190" className="tw-text-xs tw-text-white/40 hover:tw-text-white tw-transition-colors tw-no-underline">Toll Free Support</a>
            </div>

          </div>

          {/* Bottom Copyright */}
          <div className="tw-border-t tw-border-white/5 tw-pt-8 tw-flex tw-flex-col sm:tw-flex-row tw-justify-between tw-items-center tw-gap-4">
            <span className="tw-text-xs tw-text-white/30">
              &copy; {new Date().getFullYear()} Cosmic Chameleon Platform. All rights reserved.
            </span>
            <div className="tw-flex tw-gap-6">
              <Link href="/login" className="tw-text-xs tw-text-white/30 hover:tw-text-white tw-no-underline">Privacy Policy</Link>
              <Link href="/login" className="tw-text-xs tw-text-white/30 hover:tw-text-white tw-no-underline">Terms of Service</Link>
            </div>
          </div>

        </div>
      </footer>

    </div>
  );
}
