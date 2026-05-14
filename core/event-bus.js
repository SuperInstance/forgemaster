/**
 * Cocapn Core — Cross-Demo Event Bus
 * Uses BroadcastChannel for zero-latency same-origin communication.
 * Additive: demos can ignore messages they don't care about.
 */

const BUS = new BroadcastChannel('cocapn-universe');
const handlers = {};
let _id = Math.random().toString(36).slice(2, 8);

export function setSourceId(id) { _id = id; }

/**
 * Broadcast a typed event to all other Cocapn pages.
 * @param {string} type  — event type (e.g. 'drift:lap', 'snap:event')
 * @param {object} payload — event data
 */
export function emit(type, payload) {
  BUS.postMessage({ type, source: _id, ts: performance.now(), payload });
}

/**
 * Subscribe to events of a given type.
 * @param {string} type — event type, or '*' for all
 * @param {function} fn — callback(payload, meta)
 * @returns {function} unsubscribe function
 */
export function subscribe(type, fn) {
  if (!handlers[type]) handlers[type] = [];
  handlers[type].push(fn);
  return () => {
    handlers[type] = handlers[type].filter(f => f !== fn);
  };
}

// Internal dispatch
BUS.onmessage = (e) => {
  const { type, source, ts, payload } = e.data;
  // Don't process our own messages
  if (source === _id) return;
  const meta = { source, ts, age: performance.now() - ts };
  // Specific handlers
  if (handlers[type]) {
    for (const fn of handlers[type]) fn(payload, meta);
  }
  // Wildcard handlers
  if (handlers['*']) {
    for (const fn of handlers['*']) fn(type, payload, meta);
  }
};

/**
 * Subscribe to all events (debug/control room use).
 * @param {function} fn — callback(type, payload, meta)
 */
export function subscribeAll(fn) {
  return subscribe('*', fn);
}

// Event type constants for discoverability
export const EVENTS = {
  // Drift Race
  DRIFT_LAP: 'drift:lap',
  DRIFT_STATE: 'drift:state',
  // Hex Snap
  SNAP_EVENT: 'snap:event',
  SNAP_CLEAR: 'snap:clear',
  // Constraint Funnel
  FUNNEL_TEMP: 'funnel:temp',
  FUNNEL_PHASE: 'funnel:phase',
  FUNNEL_ANOMALY: 'funnel:anomaly',
  // Safe Arm
  ARM_POSE: 'arm:pose',
  ARM_VIOLATION: 'arm:violation',
  ARM_SNAP: 'arm:snap',
  // FLUX VM
  VM_STEP: 'vm:step',
  VM_OUTPUT: 'vm:output',
  VM_HALT: 'vm:halt',
  // Fleet Topology
  FLEET_STATE: 'fleet:state',
  FLEET_SPOOF: 'fleet:spoof',
  FLEET_CONSENSUS: 'fleet:consensus',
  // Memory Palace
  MEMORY_VISIT: 'memory:visit',
  // System
  UNIVERSE_HEARTBEAT: 'universe:heartbeat',
  TOUR_COMMAND: 'tour:command',
};
