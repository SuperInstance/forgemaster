/**
 * Cocapn Core — Guided Tour Engine
 * ES Module. Works as a standalone overlay on any page.
 *
 * Usage:
 *   import { Tour } from '../core/tour.js';
 *   const tour = new Tour(steps, { storageKey: 'my-tour' });
 *   tour.start();
 */

// ─── Event bus (graceful degradation if not available) ──────────────────────
let _emit = () => {};
try {
  const busUrl = new URL('../core/event-bus.js', import.meta.url).href;
  import(busUrl).then(mod => {
    _emit = (type, payload) => mod.emit(type, payload);
  }).catch(() => {});
} catch {}

// ─── Utility ─────────────────────────────────────────────────────────────────

function $(sel, root = document) { return root.querySelector(sel); }

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

/**
 * Returns the bounding rect of an element in viewport coordinates,
 * with a small padding applied.
 */
function getRect(el, pad = 12) {
  const r = el.getBoundingClientRect();
  return {
    top:    r.top    - pad,
    left:   r.left   - pad,
    right:  r.right  + pad,
    bottom: r.bottom + pad,
    width:  r.width  + pad * 2,
    height: r.height + pad * 2,
    cx:     (r.left + r.right)  / 2,
    cy:     (r.top  + r.bottom) / 2,
  };
}

// ─── Stylesheet ──────────────────────────────────────────────────────────────

const TOUR_CSS = `
.tour-overlay {
  position: fixed; inset: 0; z-index: 99990;
  pointer-events: none;
  transition: opacity .4s ease;
}
.tour-overlay.hidden { opacity: 0; }

/* SVG cutout mask rendered via clip-path on the dark layer */
.tour-dim {
  position: absolute; inset: 0;
  background: rgba(0, 0, 0, 0.72);
  pointer-events: auto;
  transition: clip-path .5s cubic-bezier(0.22, 1, 0.36, 1);
}

/* Highlight ring around target */
.tour-ring {
  position: absolute;
  border-radius: 10px;
  border: 2px solid rgba(0, 212, 255, 0.7);
  box-shadow: 0 0 0 4px rgba(0, 212, 255, 0.12),
              0 0 24px rgba(0, 212, 255, 0.25);
  pointer-events: none;
  transition: all .5s cubic-bezier(0.22, 1, 0.36, 1);
  animation: tour-ring-pulse 2s ease-in-out infinite;
}
@keyframes tour-ring-pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(0,212,255,0.12), 0 0 24px rgba(0,212,255,0.25); }
  50%       { box-shadow: 0 0 0 8px rgba(0,212,255,0.18), 0 0 40px rgba(0,212,255,0.4); }
}

/* Tooltip card */
.tour-card {
  position: absolute;
  width: clamp(280px, 34vw, 440px);
  background: rgba(13, 17, 23, 0.92);
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  border: 1px solid rgba(0, 212, 255, 0.22);
  border-radius: 16px;
  padding: 20px 22px 16px;
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.04) inset,
    0 8px 40px rgba(0,0,0,0.6),
    0 0 60px rgba(0, 212, 255, 0.07);
  pointer-events: auto;
  transition: all .45s cubic-bezier(0.22, 1, 0.36, 1);
  font-family: 'SF Pro Display', 'Segoe UI', system-ui, sans-serif;
}

/* Arrow pointer */
.tour-card::before {
  content: '';
  position: absolute;
  width: 12px; height: 12px;
  background: rgba(13, 17, 23, 0.92);
  border: 1px solid rgba(0, 212, 255, 0.22);
  transform: rotate(45deg);
  transition: all .45s cubic-bezier(0.22, 1, 0.36, 1);
}
.tour-card[data-arrow="top"]::before    { top: -7px; left: 50%; margin-left:-6px; border-bottom:none; border-right:none; }
.tour-card[data-arrow="bottom"]::before { bottom:-7px; left:50%; margin-left:-6px; border-top:none; border-left:none; }
.tour-card[data-arrow="left"]::before   { left:-7px; top:28px; border-bottom:none; border-right:none; transform:rotate(-45deg); }
.tour-card[data-arrow="right"]::before  { right:-7px; top:28px; border-top:none; border-left:none; transform:rotate(45deg); }

/* Act badge */
.tour-act-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 10px;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.2);
  color: rgba(0, 212, 255, 0.85);
}
.tour-act-badge .act-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: currentColor;
  animation: tour-dot-pulse 1.5s ease-in-out infinite;
}
@keyframes tour-dot-pulse {
  0%,100% { opacity:1; } 50% { opacity:0.3; }
}

.tour-card-title {
  font-size: 15px;
  font-weight: 600;
  color: #e6edf3;
  margin-bottom: 8px;
  line-height: 1.3;
}

.tour-card-body {
  font-size: 13px;
  color: #8b949e;
  line-height: 1.6;
  margin-bottom: 14px;
}

/* Wait prompt */
.tour-wait-prompt {
  display: none;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(0, 212, 255, 0.06);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 11px;
  color: rgba(0, 212, 255, 0.8);
  animation: wait-pulse .8s ease-in-out infinite alternate;
}
.tour-wait-prompt.active { display: flex; }
@keyframes wait-pulse {
  from { border-color: rgba(0,212,255,0.15); }
  to   { border-color: rgba(0,212,255,0.45); }
}
.tour-wait-icon { font-size: 14px; }

/* Progress bar */
.tour-progress-track {
  width: 100%;
  height: 2px;
  background: rgba(255,255,255,0.06);
  border-radius: 2px;
  margin-bottom: 14px;
  overflow: hidden;
}
.tour-progress-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, #00d4ff, #7c5cfc);
  transition: width .5s cubic-bezier(0.22, 1, 0.36, 1);
}

/* Controls row */
.tour-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tour-step-count {
  font-size: 10px;
  color: #484f58;
  font-variant-numeric: tabular-nums;
  font-family: 'SF Mono', monospace;
  margin-right: auto;
}
.tour-btn {
  padding: 7px 16px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid;
  transition: all .2s cubic-bezier(0.22, 1, 0.36, 1);
  letter-spacing: .3px;
  font-family: 'SF Pro Display', system-ui, sans-serif;
}
.tour-btn:active { transform: scale(0.95); }
.tour-btn-skip {
  background: transparent;
  border-color: rgba(255,255,255,0.08);
  color: #484f58;
}
.tour-btn-skip:hover { color: #8b949e; border-color: rgba(255,255,255,0.15); }
.tour-btn-prev {
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.08);
  color: #8b949e;
}
.tour-btn-prev:hover { background: rgba(255,255,255,0.08); color: #e6edf3; }
.tour-btn-next {
  background: rgba(0,212,255,0.12);
  border-color: rgba(0,212,255,0.3);
  color: #00d4ff;
}
.tour-btn-next:hover {
  background: rgba(0,212,255,0.22);
  border-color: rgba(0,212,255,0.6);
  box-shadow: 0 0 16px rgba(0,212,255,0.2);
}
.tour-btn-next:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  pointer-events: none;
}

/* Transition slide */
.tour-transition-card {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  opacity: 0;
  transition: opacity .5s ease;
}
.tour-transition-card.active {
  opacity: 1;
  pointer-events: auto;
}
.tour-transition-inner {
  background: rgba(13, 17, 23, 0.95);
  backdrop-filter: blur(32px);
  border: 1px solid rgba(124, 92, 252, 0.3);
  border-radius: 20px;
  padding: 36px 48px;
  text-align: center;
  max-width: 480px;
  box-shadow: 0 0 80px rgba(124, 92, 252, 0.15);
}
.tour-transition-inner h3 {
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: rgba(124, 92, 252, 0.8);
  margin-bottom: 16px;
}
.tour-transition-inner p {
  font-size: 18px;
  font-weight: 300;
  color: #e6edf3;
  line-height: 1.5;
}
.tour-transition-continue {
  margin-top: 24px;
  padding: 10px 28px;
  background: rgba(124,92,252,0.15);
  border: 1px solid rgba(124,92,252,0.4);
  border-radius: 10px;
  color: #a78bfa;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: 'SF Pro Display', system-ui, sans-serif;
  transition: all .2s;
}
.tour-transition-continue:hover {
  background: rgba(124,92,252,0.28);
  box-shadow: 0 0 24px rgba(124,92,252,0.2);
}
`;

function injectStyles() {
  if (document.getElementById('cocapn-tour-css')) return;
  const style = document.createElement('style');
  style.id = 'cocapn-tour-css';
  style.textContent = TOUR_CSS;
  document.head.appendChild(style);
}

// ─── Tour class ──────────────────────────────────────────────────────────────

export class Tour {
  /**
   * @param {TourStep[]} steps
   * @param {TourOptions} options
   *
   * TourStep {
   *   selector?: string        — CSS selector for target element (null = center screen)
   *   title: string            — bold heading
   *   body: string             — paragraph text
   *   position?: 'top'|'bottom'|'left'|'right'|'auto'  default 'auto'
   *   act?: string             — Act label e.g. 'ACT 1 · THE PROBLEM'
   *   actColor?: string        — CSS color for act badge
   *   action?: {
   *     type: 'click'|'wait-event'|'wait-count'|'timer'|'manual'
   *     target?: string        — selector (click, wait-count)
   *     event?: string         — BroadcastChannel event type (wait-event)
   *     count?: number         — how many events/clicks (wait-count)
   *     duration?: number      — ms (timer)
   *     prompt?: string        — what to show user
   *   }
   *   transition?: string      — if set, show a fullscreen transition card with this text before step
   *   transitionTitle?: string — small label above transition text
   * }
   *
   * TourOptions {
   *   storageKey?: string       — sessionStorage key (default 'cocapn-tour')
   *   onComplete?: () => void
   *   onSkip?: () => void
   *   onStep?: (index, step) => void
   * }
   */
  constructor(steps, options = {}) {
    this.steps = steps;
    this.opts = {
      storageKey: 'cocapn-tour',
      onComplete: () => {},
      onSkip: () => {},
      onStep: () => {},
      ...options,
    };

    this.currentIndex = 0;
    this._waiting = false;
    this._actionCount = 0;
    this._unsubscribeBus = null;
    this._clickListeners = [];
    this._timerHandle = null;
    this._destroyed = false;

    // DOM references (created lazily)
    this._overlay = null;
    this._dim = null;
    this._ring = null;
    this._card = null;
    this._transitionCard = null;
  }

  // ── Lifecycle ──────────────────────────────────────────────────────────────

  start(fromIndex = null) {
    injectStyles();
    this._buildDOM();

    // Restore from sessionStorage
    if (fromIndex === null) {
      const saved = sessionStorage.getItem(this.opts.storageKey);
      fromIndex = saved !== null ? parseInt(saved, 10) : 0;
    }

    this.currentIndex = clamp(fromIndex, 0, this.steps.length - 1);
    this._overlay.classList.remove('hidden');
    this._goToStep(this.currentIndex);
  }

  resume() {
    const saved = sessionStorage.getItem(this.opts.storageKey);
    this.start(saved !== null ? parseInt(saved, 10) : 0);
  }

  destroy() {
    this._destroyed = true;
    this._cleanupAction();
    if (this._overlay) this._overlay.remove();
    this._overlay = null;
  }

  // ── DOM Construction ───────────────────────────────────────────────────────

  _buildDOM() {
    if (this._overlay) return;

    const overlay = document.createElement('div');
    overlay.className = 'tour-overlay hidden';
    overlay.innerHTML = `
      <div class="tour-dim"></div>
      <div class="tour-ring"></div>
      <div class="tour-card" data-arrow="bottom">
        <div class="tour-act-badge" style="display:none">
          <span class="act-dot"></span>
          <span class="act-text"></span>
        </div>
        <div class="tour-progress-track">
          <div class="tour-progress-fill" style="width:0%"></div>
        </div>
        <div class="tour-card-title"></div>
        <div class="tour-card-body"></div>
        <div class="tour-wait-prompt">
          <span class="tour-wait-icon">⟳</span>
          <span class="tour-wait-text"></span>
        </div>
        <div class="tour-controls">
          <span class="tour-step-count"></span>
          <button class="tour-btn tour-btn-skip">Skip tour</button>
          <button class="tour-btn tour-btn-prev">← Prev</button>
          <button class="tour-btn tour-btn-next">Next →</button>
        </div>
      </div>
      <div class="tour-transition-card">
        <div class="tour-transition-inner">
          <h3 class="transition-title">Next</h3>
          <p class="transition-body"></p>
          <button class="tour-transition-continue">Continue →</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    this._overlay        = overlay;
    this._dim            = overlay.querySelector('.tour-dim');
    this._ring           = overlay.querySelector('.tour-ring');
    this._card           = overlay.querySelector('.tour-card');
    this._transitionCard = overlay.querySelector('.tour-transition-card');

    // Wire buttons
    overlay.querySelector('.tour-btn-skip').onclick  = () => this._skip();
    overlay.querySelector('.tour-btn-prev').onclick  = () => this._prev();
    overlay.querySelector('.tour-btn-next').onclick  = () => this._next();
    overlay.querySelector('.tour-transition-continue').onclick = () => this._hideTransition();

    // Prevent dim clicks from leaking through when waiting
    this._dim.onclick = () => {
      if (this._waiting) return;
      // clicking dim = next (UX affordance)
    };
  }

  // ── Navigation ─────────────────────────────────────────────────────────────

  _goToStep(index) {
    if (this._destroyed) return;
    this._cleanupAction();

    this.currentIndex = clamp(index, 0, this.steps.length - 1);
    const step = this.steps[this.currentIndex];

    // Persist
    sessionStorage.setItem(this.opts.storageKey, this.currentIndex);

    // Emit bus event
    _emit('tour:step', { index: this.currentIndex, step: step.title });
    this.opts.onStep(this.currentIndex, step);

    // If this step has a transition, show it first
    if (step.transition) {
      this._showTransition(step.transition, step.transitionTitle || 'Next');
      return; // _hideTransition will call _renderStep
    }

    this._renderStep(step);
  }

  _renderStep(step) {
    const card  = this._card;
    const total = this.steps.length;
    const idx   = this.currentIndex;

    // Progress
    const pct = ((idx + 1) / total * 100).toFixed(1);
    card.querySelector('.tour-progress-fill').style.width = pct + '%';
    card.querySelector('.tour-step-count').textContent = `${idx + 1} / ${total}`;

    // Act badge
    const badge = card.querySelector('.tour-act-badge');
    if (step.act) {
      badge.style.display = 'inline-flex';
      badge.querySelector('.act-text').textContent = step.act;
      if (step.actColor) {
        badge.style.background = step.actColor + '18';
        badge.style.borderColor = step.actColor + '44';
        badge.style.color = step.actColor;
      } else {
        badge.style.background = '';
        badge.style.borderColor = '';
        badge.style.color = '';
      }
    } else {
      badge.style.display = 'none';
    }

    // Content
    card.querySelector('.tour-card-title').textContent = step.title;
    card.querySelector('.tour-card-body').textContent  = step.body;

    // Prev/next buttons
    card.querySelector('.tour-btn-prev').style.display = idx === 0 ? 'none' : '';
    const nextBtn = card.querySelector('.tour-btn-next');

    // Wait prompt
    const waitEl = card.querySelector('.tour-wait-prompt');
    if (step.action && step.action.type !== 'manual') {
      waitEl.classList.add('active');
      const prompt = step.action.prompt || 'Waiting for your action…';
      waitEl.querySelector('.tour-wait-text').textContent = prompt;
      nextBtn.disabled = true;
      this._waiting = true;
      this._setupAction(step.action, () => this._next());
    } else {
      waitEl.classList.remove('active');
      nextBtn.disabled = false;
      this._waiting = false;
    }

    // Last step
    if (idx === total - 1) {
      nextBtn.textContent = 'Finish';
    } else {
      nextBtn.textContent = 'Next →';
    }

    // Position overlay
    this._positionOverlay(step);
  }

  _next() {
    if (this.currentIndex >= this.steps.length - 1) {
      this._complete();
    } else {
      this._goToStep(this.currentIndex + 1);
    }
  }

  _prev() {
    if (this.currentIndex > 0) {
      this._goToStep(this.currentIndex - 1);
    }
  }

  _skip() {
    this._cleanupAction();
    sessionStorage.removeItem(this.opts.storageKey);
    this._overlay.classList.add('hidden');
    setTimeout(() => this.destroy(), 500);
    this.opts.onSkip();
    _emit('tour:skip', { at: this.currentIndex });
  }

  _complete() {
    this._cleanupAction();
    sessionStorage.removeItem(this.opts.storageKey);
    _emit('tour:complete', {});
    this.opts.onComplete();
    this._overlay.classList.add('hidden');
    setTimeout(() => this.destroy(), 500);
  }

  // ── Overlay Positioning ────────────────────────────────────────────────────

  _positionOverlay(step) {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const el = step.selector ? $(step.selector) : null;

    if (!el) {
      // No target — center screen, no ring
      this._ring.style.opacity = '0';
      this._dimToRect(null);
      this._positionCard(vw / 2, vh * 0.62, 'center', vw, vh);
      return;
    }

    const rect = getRect(el);
    this._ring.style.opacity = '1';
    this._ring.style.left   = rect.left   + 'px';
    this._ring.style.top    = rect.top    + 'px';
    this._ring.style.width  = rect.width  + 'px';
    this._ring.style.height = rect.height + 'px';
    this._dimToRect(rect);

    const pos = step.position || 'auto';
    this._positionCard(rect.cx, rect.cy, pos, vw, vh, rect);
  }

  /**
   * Punch a transparent "hole" in the dim layer using clip-path.
   * Uses a polygon that covers the whole screen minus the highlighted rect.
   */
  _dimToRect(rect) {
    if (!rect) {
      this._dim.style.clipPath = '';
      return;
    }
    const { top, left, right, bottom } = rect;
    // Polygon with a rectangular cutout — uses the "even-odd" trick via SVG
    // Fallback: just darken without hole on older browsers (clip-path polyfill needed)
    this._dim.style.clipPath = `polygon(
      0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%,
      ${left}px ${top}px, ${left}px ${bottom}px,
      ${right}px ${bottom}px, ${right}px ${top}px, ${left}px ${top}px
    )`;
  }

  /**
   * Position the tooltip card relative to the target.
   */
  _positionCard(cx, cy, pos, vw, vh, rect = null) {
    const card = this._card;
    const cardW = Math.min(440, vw * 0.34, 440);
    const cardH = 200; // approximate
    const gap = 20;
    let top, left, arrow;

    if (pos === 'auto' && rect) {
      // Pick position with most space
      const spaceTop    = rect.top;
      const spaceBottom = vh - rect.bottom;
      const spaceLeft   = rect.left;
      const spaceRight  = vw - rect.right;
      const best = Math.max(spaceTop, spaceBottom, spaceLeft, spaceRight);
      if (best === spaceBottom) pos = 'bottom';
      else if (best === spaceTop) pos = 'top';
      else if (best === spaceRight) pos = 'right';
      else pos = 'left';
    }

    if (!rect) pos = 'center';

    switch (pos) {
      case 'bottom':
        top  = (rect ? rect.bottom : cy) + gap;
        left = cx - cardW / 2;
        arrow = 'top';
        break;
      case 'top':
        top  = (rect ? rect.top : cy) - cardH - gap;
        left = cx - cardW / 2;
        arrow = 'bottom';
        break;
      case 'right':
        top  = cy - cardH / 2;
        left = (rect ? rect.right : cx) + gap;
        arrow = 'left';
        break;
      case 'left':
        top  = cy - cardH / 2;
        left = (rect ? rect.left : cx) - cardW - gap;
        arrow = 'right';
        break;
      case 'center':
      default:
        top  = cy - cardH / 2;
        left = cx - cardW / 2;
        arrow = null;
        break;
    }

    // Clamp to viewport
    left = clamp(left, 12, vw - cardW - 12);
    top  = clamp(top,  12, vh - cardH - 12);

    card.style.left    = left + 'px';
    card.style.top     = top  + 'px';
    card.style.width   = cardW + 'px';
    card.setAttribute('data-arrow', arrow || '');
  }

  // ── Action System ──────────────────────────────────────────────────────────

  _setupAction(action, onComplete) {
    switch (action.type) {
      case 'click':
        this._setupClickAction(action, onComplete);
        break;
      case 'wait-event':
        this._setupEventAction(action, onComplete);
        break;
      case 'wait-count':
        this._setupCountAction(action, onComplete);
        break;
      case 'timer':
        this._setupTimerAction(action, onComplete);
        break;
      // 'manual' — user must click Next
    }
  }

  _setupClickAction(action, onComplete) {
    const target = action.target ? $(action.target) : null;
    if (!target) return;

    const handler = (e) => {
      e.stopPropagation();
      this._actionDone(onComplete);
    };
    target.addEventListener('click', handler, { once: true, capture: true });
    this._clickListeners.push({ el: target, handler, capture: true });
  }

  _setupCountAction(action, onComplete) {
    this._actionCount = 0;
    const target = action.target ? $(action.target) : document;
    const needed  = action.count || 1;
    const waitEl  = this._card.querySelector('.tour-wait-prompt');

    const handler = () => {
      this._actionCount++;
      const remaining = needed - this._actionCount;
      if (remaining > 0 && action.prompt) {
        waitEl.querySelector('.tour-wait-text').textContent =
          action.prompt.replace('{n}', remaining);
      }
      if (this._actionCount >= needed) {
        target.removeEventListener('click', handler, true);
        this._actionDone(onComplete);
      }
    };
    target.addEventListener('click', handler, { capture: true });
    this._clickListeners.push({ el: target, handler, capture: true });
  }

  _setupEventAction(action, onComplete) {
    const bus = new BroadcastChannel('cocapn-universe');
    const handler = (e) => {
      if (e.data && e.data.type === action.event) {
        bus.removeEventListener('message', handler);
        bus.close();
        this._actionDone(onComplete);
      }
    };
    bus.addEventListener('message', handler);
    this._unsubscribeBus = () => {
      bus.removeEventListener('message', handler);
      bus.close();
    };
  }

  _setupTimerAction(action, onComplete) {
    this._timerHandle = setTimeout(() => {
      this._actionDone(onComplete);
    }, action.duration || 5000);
  }

  _actionDone(onComplete) {
    if (this._destroyed) return;
    this._waiting = false;
    const waitEl = this._card.querySelector('.tour-wait-prompt');
    waitEl.classList.remove('active');
    waitEl.style.animation = 'none';
    waitEl.style.background = 'rgba(63,185,80,0.08)';
    waitEl.style.borderColor = 'rgba(63,185,80,0.3)';
    waitEl.style.color = '#3fb950';
    waitEl.querySelector('.tour-wait-icon').textContent = '✓';
    waitEl.querySelector('.tour-wait-text').textContent = 'Done! Click Next to continue.';
    waitEl.classList.add('active');
    this._card.querySelector('.tour-btn-next').disabled = false;
    // Auto-advance after 1.2s
    setTimeout(() => onComplete(), 1200);
  }

  _cleanupAction() {
    if (this._unsubscribeBus) {
      this._unsubscribeBus();
      this._unsubscribeBus = null;
    }
    for (const { el, handler, capture } of this._clickListeners) {
      el.removeEventListener('click', handler, capture);
    }
    this._clickListeners = [];
    if (this._timerHandle) {
      clearTimeout(this._timerHandle);
      this._timerHandle = null;
    }
    this._actionCount = 0;
    this._waiting = false;
  }

  // ── Transition Cards ───────────────────────────────────────────────────────

  _showTransition(text, title = 'Next') {
    const tc = this._transitionCard;
    tc.querySelector('.transition-title').textContent = title;
    tc.querySelector('.transition-body').textContent  = text;
    tc.classList.add('active');
    // Hide dim ring during transition
    this._ring.style.opacity = '0';
    this._dim.style.clipPath = '';
    this._card.style.opacity = '0';
    this._card.style.pointerEvents = 'none';
  }

  _hideTransition() {
    const tc = this._transitionCard;
    tc.classList.remove('active');
    this._card.style.opacity = '1';
    this._card.style.pointerEvents = '';
    // Now render the actual step (stripping the transition so it doesn't loop)
    const step = this.steps[this.currentIndex];
    this._renderStep(step);
  }
}

// ─── Convenience factory ─────────────────────────────────────────────────────

/**
 * Quick-start a tour from a definition object.
 * @param {object} def — { steps, ...options }
 * @returns {Tour}
 */
export function createTour(def) {
  const { steps, ...opts } = def;
  return new Tour(steps, opts);
}
