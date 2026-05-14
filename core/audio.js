/**
 * Cocapn Core — Web Audio Sonification
 * Each constraint event produces a tone. Weyl sectors map to pentatonic notes.
 * Drift creates interference beating. Violations produce dissonance.
 */

import { SECTOR_FREQS } from './eisenstein.js';

let audioCtx = null;
let masterGain = null;
let initialized = false;

function ensureAudio() {
  if (initialized) return;
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  masterGain = audioCtx.createGain();
  masterGain.gain.value = 0.15;
  masterGain.connect(audioCtx.destination);
  initialized = true;
}

/** Resume audio context (must be called from user gesture) */
export function resumeAudio() {
  ensureAudio();
  if (audioCtx.state === 'suspended') audioCtx.resume();
}

/** Play a snap tone — short, clear, pentatonic */
export function playSnap(sector, volume = 0.3) {
  ensureAudio();
  if (audioCtx.state === 'suspended') return;
  
  const freq = SECTOR_FREQS[sector % SECTOR_FREQS.length];
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  const now = audioCtx.currentTime;
  
  osc.type = 'triangle';
  osc.frequency.setValueAtTime(freq, now);
  osc.frequency.exponentialRampToValueAtTime(freq * 1.01, now + 0.05);
  
  gain.gain.setValueAtTime(0, now);
  gain.gain.linearRampToValueAtTime(volume, now + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
  
  osc.connect(gain);
  gain.connect(masterGain);
  osc.start(now);
  osc.stop(now + 0.35);
}

/** Play a violation — sharp dissonant buzz */
export function playViolation() {
  ensureAudio();
  if (audioCtx.state === 'suspended') return;
  
  const now = audioCtx.currentTime;
  const osc1 = audioCtx.createOscillator();
  const osc2 = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  
  osc1.type = 'sawtooth';
  osc1.frequency.value = 220;
  osc2.type = 'sawtooth';
  osc2.frequency.value = 233; // tritone-ish dissonance
  
  gain.gain.setValueAtTime(0, now);
  gain.gain.linearRampToValueAtTime(0.2, now + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
  
  osc1.connect(gain);
  osc2.connect(gain);
  gain.connect(masterGain);
  osc1.start(now);
  osc2.start(now);
  osc1.stop(now + 0.45);
  osc2.stop(now + 0.45);
}

/** Play a consensus chord — multiple harmonics resolving */
export function playConsensus(numNodes) {
  ensureAudio();
  if (audioCtx.state === 'suspended') return;
  
  const now = audioCtx.currentTime;
  const baseFreq = 261.63; // C4
  const harmonics = [1, 1.25, 1.5, 2]; // major chord tones
  
  harmonics.forEach((h, i) => {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.value = baseFreq * h;
    
    gain.gain.setValueAtTime(0, now + i * 0.08);
    gain.gain.linearRampToValueAtTime(0.12, now + i * 0.08 + 0.05);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.8);
    
    osc.connect(gain);
    gain.connect(masterGain);
    osc.start(now + i * 0.08);
    osc.stop(now + 0.85);
  });
}

/** Ambient drone — low hum for the landing page */
export function startDrone() {
  ensureAudio();
  if (audioCtx.state === 'suspended') return;
  
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.type = 'sine';
  osc.frequency.value = 110;
  gain.gain.value = 0.06;
  
  // Subtle LFO modulation
  const lfo = audioCtx.createOscillator();
  const lfoGain = audioCtx.createGain();
  lfo.frequency.value = 0.2;
  lfoGain.gain.value = 0.015;
  lfo.connect(lfoGain);
  lfoGain.connect(gain.gain);
  lfo.start();
  
  osc.connect(gain);
  gain.connect(masterGain);
  osc.start();
  
  return { stop: () => { osc.stop(); lfo.stop(); }, gain };
}
