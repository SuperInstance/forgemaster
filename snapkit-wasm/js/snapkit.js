/**
 * @superinstance/snapkit-wasm — Eisenstein lattice snap for the browser and Node.js
 *
 * Loads the WASM module and provides a clean async API for:
 *   - Eisenstein integer snap (optimal O(1) Voronoi correction)
 *   - Eisenstein snap with guaranteed Voronoi nearest neighbor (3×3 search)
 *   - Batch snap operations
 *   - Beat grid temporal snap
 *
 * Coordinate convention:
 *   Eisenstein integer (a, b) ⟼ Cartesian (a − b/2, b·√3/2)
 *   ω = e^(2πi/3) = −1/2 + i√3/2
 */

/**
 * @typedef {Object} SnapResult
 * @property {number} a - Eisenstein integer a-coordinate
 * @property {number} b - Eisenstein integer b-coordinate
 * @property {number} snappedX - Snapped Cartesian x
 * @property {number} snappedY - Snapped Cartesian y
 * @property {number} distance - Euclidean distance from input to snapped point
 */

/**
 * @typedef {Object} BeatResult
 * @property {number} snappedTime - Snapped beat time
 * @property {number} offset - Offset from original time
 * @property {number} beatIndex - Beat index in the grid
 * @property {number} phase - Phase within the beat period [0, 1)
 */

class SnapKit {
  /** @type {WebAssembly.Instance|null} */
  #instance = null;
  /** @type {WebAssembly.Memory} */
  #memory;
  /** @type {DataView} */
  #view;
  /** @type {number} */
  #scratchPtr = 0; // 256-byte scratch buffer offset

  /**
   * Load and instantiate the WASM module.
   * @param {string|URL|ArrayBuffer|WebAssembly.Module} source - URL or precompiled module
   * @returns {Promise<SnapKit>}
   */
  static async init(source) {
    const kit = new SnapKit();
    await kit.#load(source);
    return kit;
  }

  async #load(source) {
    let module;
    if (source instanceof WebAssembly.Module) {
      module = source;
    } else if (source instanceof ArrayBuffer || source instanceof Uint8Array) {
      module = await WebAssembly.compile(source);
    } else {
      const url = source instanceof URL ? source : new URL(source);
      const response = await fetch(url);
      const bytes = await response.arrayBuffer();
      module = await WebAssembly.compile(bytes);
    }

    this.#memory = new WebAssembly.Memory({ initial: 16 }); // 1MB
    this.#view = new DataView(this.#memory.buffer);

    const imports = {
      env: {
        memory: this.#memory,
        // Provide f64 math functions that the WASM might need
        sqrt: Math.sqrt,
        round: Math.round,
        floor: Math.floor,
        ceil: Math.ceil,
        fmod: (x, y) => x % y,
      },
    };

    const instance = await WebAssembly.instantiate(module, imports);
    this.#instance = instance.instance || instance;

    // Allocate scratch buffer
    this.#scratchPtr = 256;
  }

  #refreshView() {
    if (this.#view.buffer !== this.#memory.buffer) {
      this.#view = new DataView(this.#memory.buffer);
    }
  }

  #exports() {
    return this.#instance.exports;
  }

  /**
   * Snap a point to the nearest Eisenstein integer (optimal O(1)).
   * @param {number} x - Cartesian x
   * @param {number} y - Cartesian y
   * @returns {SnapResult}
   */
  eisensteinSnap(x, y) {
    const ptr = this.#scratchPtr;
    this.#exports().eisenstein_snap(x, y, ptr);
    this.#refreshView();
    return this.#readSnapResult(ptr);
  }

  /**
   * Snap with guaranteed Voronoï nearest neighbor (3×3 search).
   * @param {number} x - Cartesian x
   * @param {number} y - Cartesian y
   * @returns {SnapResult}
   */
  eisensteinSnapVoronoi(x, y) {
    const ptr = this.#scratchPtr;
    this.#exports().eisenstein_snap_voronoi(x, y, ptr);
    this.#refreshView();
    return this.#readSnapResult(ptr);
  }

  /**
   * Batch snap multiple points at once.
   * @param {Array<{x: number, y: number}>} points
   * @returns {SnapResult[]}
   */
  eisensteinSnapBatch(points) {
    const len = points.length;
    if (len === 0) return [];

    // Allocate input buffer: len × 2 × f64 = len × 16 bytes
    const inPtr = this.#exports().wasm_alloc(len * 16);
    // Allocate output buffer: len × 32 bytes (padded for alignment)
    const outPtr = this.#exports().wasm_alloc(len * 32);

    this.#refreshView();

    // Write input (interleaved x, y pairs)
    for (let i = 0; i < len; i++) {
      this.#view.setFloat64(inPtr + i * 16, points[i].x, true);
      this.#view.setFloat64(inPtr + i * 16 + 8, points[i].y, true);
    }

    this.#exports().eisenstein_snap_batch(inPtr, len, outPtr);
    this.#refreshView();

    // Read results
    const results = new Array(len);
    for (let i = 0; i < len; i++) {
      results[i] = this.#readSnapResult(outPtr + i * 32);
    }
    return results;
  }

  /**
   * Get the covering radius of the Eisenstein (A₂) lattice: 1/√3 ≈ 0.57735.
   * @returns {number}
   */
  coveringRadius() {
    return this.#exports().covering_radius();
  }

  /**
   * Snap a timestamp to the nearest beat in a periodic grid.
   * @param {number} t - Timestamp
   * @param {number} period - Beat period
   * @returns {BeatResult}
   */
  beatGridSnap(t, period) {
    const ptr = this.#scratchPtr + 128; // Use offset within scratch
    this.#exports().beat_grid_snap(t, period, ptr);
    this.#refreshView();
    return this.#readBeatResult(ptr);
  }

  /**
   * Batch snap multiple timestamps.
   * @param {number[]} timestamps
   * @param {number} period
   * @returns {BeatResult[]}
   */
  beatGridSnapBatch(timestamps, period) {
    const len = timestamps.length;
    if (len === 0) return [];

    const inPtr = this.#exports().wasm_alloc(len * 8);
    const outPtr = this.#exports().wasm_alloc(len * 24);

    this.#refreshView();

    for (let i = 0; i < len; i++) {
      this.#view.setFloat64(inPtr + i * 8, timestamps[i], true);
    }

    this.#exports().beat_grid_snap_batch(inPtr, len, period, outPtr);
    this.#refreshView();

    const results = new Array(len);
    for (let i = 0; i < len; i++) {
      results[i] = this.#readBeatResult(outPtr + i * 24);
    }
    return results;
  }

  // ── Internal helpers ──

  /** @private */
  #readSnapResult(ptr) {
    return {
      a: this.#view.getInt32(ptr, true),
      b: this.#view.getInt32(ptr + 4, true),
      snappedX: this.#view.getFloat64(ptr + 8, true),
      snappedY: this.#view.getFloat64(ptr + 16, true),
      distance: this.#view.getFloat64(ptr + 24, true),
    };
  }

  /** @private */
  #readBeatResult(ptr) {
    return {
      snappedTime: this.#view.getFloat64(ptr, true),
      offset: this.#view.getFloat64(ptr + 8, true),
      beatIndex: this.#view.getInt32(ptr + 16, true),
      phase: this.#view.getFloat64(ptr + 20, true),
    };
  }
}

// ── Module exports ──

// Browser global
if (typeof window !== 'undefined') {
  window.SnapKit = SnapKit;
}

// CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SnapKit };
}

// ES module
if (typeof exports !== 'undefined') {
  exports.SnapKit = SnapKit;
}
