import { useState, useEffect, useRef } from "react";
import "./AudioPillPlayer.css";

export default function AudioPillPlayer({ text, label = "Oral Case Briefing" }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [supported, setSupported] = useState(true);
  const utteranceRef = useRef(null);

  useEffect(() => {
    if (!("speechSynthesis" in window)) {
      setSupported(false);
    }
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handleTogglePlay = () => {
    if (!supported || !text) return;

    if (isPlaying && !isPaused) {
      window.speechSynthesis.pause();
      setIsPaused(true);
      return;
    }

    if (isPaused) {
      window.speechSynthesis.resume();
      setIsPaused(false);
      return;
    }

    window.speechSynthesis.cancel();

    const cleanText = text
      .replace(/[#*_`]/g, "")
      .replace(/₹/g, "Rupees ")
      .replace(/§/g, "Section ");

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utteranceRef.current = utterance;

    // Pick best available English voice
    const voices = window.speechSynthesis.getVoices();
    const indVoice = voices.find((v) => v.lang.includes("en-IN") || v.name.includes("India"));
    const engVoice = indVoice || voices.find((v) => v.lang.startsWith("en"));
    if (engVoice) utterance.voice = engVoice;

    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    utterance.onstart = () => {
      setIsPlaying(true);
      setIsPaused(false);
    };

    utterance.onend = () => {
      setIsPlaying(false);
      setIsPaused(false);
    };

    utterance.onerror = () => {
      setIsPlaying(false);
      setIsPaused(false);
    };

    window.speechSynthesis.speak(utterance);
  };

  const handleStop = (e) => {
    e.stopPropagation();
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setIsPlaying(false);
    setIsPaused(false);
  };

  if (!supported || !text) return null;

  return (
    <div className={`audio-pill-container ${isPlaying ? "active" : ""}`}>
      <button className="audio-pill-btn" onClick={handleTogglePlay} title="Listen to 3-sentence oral brief">
        <span className="audio-pill-icon">
          {isPlaying && !isPaused ? "⏸" : "🔊"}
        </span>
        <span className="audio-pill-label">{label}</span>

        {/* Animated Soundwave Equalizer */}
        <div className={`audio-wave-bars ${isPlaying && !isPaused ? "animating" : ""}`}>
          <span className="bar bar-1"></span>
          <span className="bar bar-2"></span>
          <span className="bar bar-3"></span>
          <span className="bar bar-4"></span>
          <span className="bar bar-5"></span>
        </div>
      </button>

      {isPlaying && (
        <button className="audio-pill-stop" onClick={handleStop} title="Stop Audio">
          ⏹
        </button>
      )}
    </div>
  );
}
