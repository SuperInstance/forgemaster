/**
 * FLUX-Tensor-MIDI — PLATO rooms as musicians
 * 
 * Zero dependencies. ESM module. Node.js >= 18.
 * 
 * Each room is a musician with a T-0 clock, Eisenstein rhythmic snap,
 * and side-channel signals (nods, smiles, frowns).
 */

// ── Constants ──────────────────────────────────────────────────────────

const SQRT3 = Math.sqrt(3);
const INV_SQRT3 = 1 / SQRT3;
const PPQN = 480;

// ── FluxVector ─────────────────────────────────────────────────────────

export class FluxChannel {
  constructor(salience = 0.5, tolerance = 0.5) {
    this.salience = salience;
    this.tolerance = tolerance;
  }
  
  toJSON() { return { salience: this.salience, tolerance: this.tolerance }; }
}

export class FluxVector {
  constructor(channels) {
    this.channels = channels || Array.from({ length: 9 }, () => new FluxChannel());
  }
  
  cosineSimilarity(other) {
    let dot = 0, magA = 0, magB = 0;
    for (let i = 0; i < 9; i++) {
      const a = this.channels[i].salience;
      const b = other.channels[i].salience;
      dot += a * b;
      magA += a * a;
      magB += b * b;
    }
    return dot / (Math.sqrt(magA * magB) + 1e-10);
  }
  
  checkAlignment(other) {
    const similarity = this.cosineSimilarity(other);
    let inTolerance = true;
    for (let i = 0; i < 9; i++) {
      const delta = Math.abs(this.channels[i].salience - other.channels[i].salience);
      if (delta > other.channels[i].tolerance) {
        inTolerance = false;
        break;
      }
    }
    return { similarity, inTolerance, delta: 1 - similarity };
  }
  
  adapt(observation, learningRate = 0.1) {
    for (let i = 0; i < 9; i++) {
      const target = observation.channels[i].salience;
      this.channels[i].salience += learningRate * (target - this.channels[i].salience);
      const tTarget = observation.channels[i].tolerance;
      this.channels[i].tolerance += learningRate * (tTarget - this.channels[i].tolerance);
    }
  }
  
  toJSON() { return this.channels.map(c => c.toJSON()); }
  
  static fromJSON(data) {
    return new FluxVector(data.map(c => new FluxChannel(c.salience, c.tolerance)));
  }
}

// ── TZeroClock ─────────────────────────────────────────────────────────

export class TZeroClock {
  constructor(interval = 300, adaptive = true) {
    this.interval = interval;
    this.adaptive = adaptive;
    this.alpha = 0.1;
    this.tLast = Date.now() / 1000;
    this.tZero = this.tLast + interval;
  }
  
  tick() {
    const now = Date.now() / 1000;
    if (now >= this.tZero) {
      const delta = now - this.tZero;
      if (this.adaptive) {
        const actual = now - this.tLast;
        this.interval = this.interval * (1 - this.alpha) + actual * this.alpha;
      }
      this.tLast = now;
      this.tZero = now + this.interval;
      return { late: true, delta, missed: Math.floor(delta / this.interval) };
    }
    return { late: false, delta: 0, missed: 0 };
  }
  
  reset() {
    this.tLast = Date.now() / 1000;
    this.tZero = this.tLast + this.interval;
  }
}

// ── Eisenstein Snap ────────────────────────────────────────────────────

export function eisensteinSnap(real, imag) {
  const bf = 2 * imag / SQRT3;
  const af = real + imag / SQRT3;
  const b = Math.round(bf);
  const a = Math.round(af);
  const norm = a * a - a * b + b * b;
  return { a, b, norm };
}

export function snapRhythmicRatio(ratio) {
  // Snap a tempo ratio to the nearest simple rhythmic relationship
  const targets = [
    { ratio: 0.25, name: 'sixteenth' },
    { ratio: 1/3, name: 'triplet-third' },
    { ratio: 0.5, name: 'half' },
    { ratio: 2/3, name: 'triplet-two' },
    { ratio: 1.0, name: 'unison' },
    { ratio: 1.5, name: 'dotted' },
    { ratio: 2.0, name: 'double' },
    { ratio: 3.0, name: 'triple' },
    { ratio: 4.0, name: 'quadruple' },
  ];
  
  let best = targets[0];
  let bestDist = Infinity;
  for (const t of targets) {
    const dist = Math.abs(ratio - t.ratio);
    if (dist < bestDist) {
      bestDist = dist;
      best = t;
    }
  }
  return { ...best, delta: ratio - best.ratio };
}

// ── Side Channels ──────────────────────────────────────────────────────

export class Nod {
  constructor(from, to, timestamp, context = '') {
    this.from = from;
    this.to = to;
    this.timestamp = timestamp;
    this.context = context;
  }
  toJSON() { return { type: 'nod', from: this.from, to: this.to, timestamp: this.timestamp, context: this.context }; }
}

export class Smile {
  constructor(from, to, timestamp) {
    this.from = from;
    this.to = to;
    this.timestamp = timestamp;
  }
  toJSON() { return { type: 'smile', from: this.from, to: this.to, timestamp: this.timestamp }; }
}

export class Frown {
  constructor(from, to, timestamp, delta = 0) {
    this.from = from;
    this.to = to;
    this.timestamp = timestamp;
    this.delta = delta;
  }
  toJSON() { return { type: 'frown', from: this.from, to: this.to, timestamp: this.timestamp, delta: this.delta }; }
}

// ── MidiEvent ──────────────────────────────────────────────────────────

export const EventType = {
  NOTE_ON: 0, NOTE_OFF: 1, CC: 2, NOD: 3, SMILE: 4, FROWN: 5,
};

export const Channel = {
  VISUAL: 1, TEXT: 2, AUDIO: 3, COLOR: 4, MOTION: 5,
  EFFECTS: 6, DATA: 7, SIDECHANNEL: 8, META: 9,
};

export class MidiEvent {
  constructor({ type = EventType.NOTE_ON, channel = 1, timestamp = 0, pitch = 60, velocity = 80, duration = 0 } = {}) {
    this.type = type;
    this.channel = channel;
    this.timestamp = timestamp;
    this.pitch = pitch;
    this.velocity = velocity;
    this.duration = duration;
  }
  
  toJSON() { return { type: this.type, channel: this.channel, timestamp: this.timestamp, pitch: this.pitch, velocity: this.velocity, duration: this.duration }; }
}

// ── Harmony ────────────────────────────────────────────────────────────

export function jaccardSimilarity(setA, setB) {
  const a = new Set(setA);
  const b = new Set(setB);
  let intersection = 0;
  for (const x of a) if (b.has(x)) intersection++;
  const union = new Set([...a, ...b]).size;
  return union === 0 ? 0 : intersection / union;
}

export class HarmonyState {
  constructor(targetRoom) {
    this.targetRoom = targetRoom;
    this.jaccard = 0;
    this.correlation = 0;
    this.lastSync = 0;
    this.snapDelta = 0;
    this.chordQuality = 'silence'; // unison, consonance, dissonance, counterpoint, silence
  }
}

// ── RoomMusician ───────────────────────────────────────────────────────

export class RoomMusician {
  constructor({ roomId, instrument = '', tempoBpm = 72, subdivision = 24, midiChannel = 1 } = {}) {
    this.roomId = roomId;
    this.instrument = instrument;
    this.clock = new TZeroClock(60 / tempoBpm);
    this.flux = new FluxVector();
    this.tempoBpm = tempoBpm;
    this.subdivision = subdivision;
    this.midiChannel = midiChannel;
    this.listeningTo = [];
    this.harmonyMap = new Map();
    this.pendingNods = [];
    this.pendingSmiles = [];
    this.pendingFrowns = [];
    this.playing = true;
    this.tileHistory = [];
    this.midiEvents = [];
  }
  
  perform(observation) {
    const event = new MidiEvent({
      type: EventType.NOTE_ON,
      channel: this.midiChannel,
      timestamp: Date.now() / 1000,
      pitch: 60,
      velocity: 80,
      duration: 60 / this.tempoBpm,
    });
    this.midiEvents.push(event);
    this.tileHistory.push({ timestamp: event.timestamp, observation });
    return event;
  }
  
  listen(otherRoom) {
    if (!this.harmonyMap.has(otherRoom.roomId)) {
      this.harmonyMap.set(otherRoom.roomId, new HarmonyState(otherRoom.roomId));
    }
    const harmony = this.harmonyMap.get(otherRoom.roomId);
    
    // Compute temporal overlap
    const myBeats = this.tileHistory.map(t => Math.round(t.timestamp * this.tempoBpm / 60));
    const theirBeats = otherRoom.tileHistory.map(t => Math.round(t.timestamp * otherRoom.tempoBpm / 60));
    harmony.jaccard = jaccardSimilarity(myBeats, theirBeats);
    harmony.lastSync = Date.now() / 1000;
    
    return harmony;
  }
  
  receiveNod(nod) { this.pendingNods.push(nod); }
  sendSmile(target) { return new Smile(this.roomId, target, Date.now() / 1000); }
  sendFrown(target, delta) { return new Frown(this.roomId, target, Date.now() / 1000, delta); }
  
  tick() {
    const result = this.clock.tick();
    if (this.playing && result.late) {
      return this.perform({ tick: result });
    }
    return null;
  }
}

// ── Band (Ensemble) ────────────────────────────────────────────────────

export class Band {
  constructor(name) {
    this.name = name;
    this.musicians = new Map();
  }
  
  addMusician(musician) {
    this.musicians.set(musician.roomId, musician);
  }
  
  removeMusician(roomId) {
    this.musicians.delete(roomId);
  }
  
  tick() {
    const events = [];
    for (const [id, musician] of this.musicians) {
      const event = musician.tick();
      if (event) events.push(event);
    }
    
    // Update pairwise harmony
    const ids = [...this.musicians.keys()];
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = this.musicians.get(ids[i]);
        const b = this.musicians.get(ids[j]);
        if (a.listeningTo.includes(ids[j])) a.listen(b);
        if (b.listeningTo.includes(ids[i])) b.listen(a);
      }
    }
    
    return events;
  }
  
  harmonyReport() {
    const report = {};
    for (const [id, m] of this.musicians) {
      report[id] = Object.fromEntries(
        [...m.harmonyMap.entries()].map(([k, v]) => [k, { jaccard: v.jaccard, quality: v.chordQuality }])
      );
    }
    return report;
  }
}

// ── Score (VMS encoder/decoder) ────────────────────────────────────────

export class Score {
  constructor({ name = '', tempoBpm = 72, latticeDivisions = 12 } = {}) {
    this.name = name;
    this.tempoBpm = tempoBpm;
    this.latticeDivisions = latticeDivisions;
    this.events = [];
  }
  
  addEvent(event) {
    const grid = 1 / this.latticeDivisions;
    event.timestamp = Math.round(event.timestamp / grid) * grid;
    this.events.push(event);
    return event;
  }
  
  toJSON() {
    return {
      format: 'vms',
      version: '0.1.0',
      name: this.name,
      tempo_bpm: this.tempoBpm,
      lattice_divisions: this.latticeDivisions,
      events: this.events.map(e => e.toJSON()),
    };
  }
  
  static fromJSON(data) {
    const score = new Score({
      name: data.name,
      tempoBpm: data.tempo_bpm,
      latticeDivisions: data.lattice_divisions,
    });
    score.events = (data.events || []).map(e => new MidiEvent(e));
    return score;
  }
}

// ── Default export ─────────────────────────────────────────────────────

export default {
  FluxChannel, FluxVector, TZeroClock,
  eisensteinSnap, snapRhythmicRatio,
  Nod, Smile, Frown,
  MidiEvent, EventType, Channel,
  jaccardSimilarity, HarmonyState,
  RoomMusician, Band, Score,
};
