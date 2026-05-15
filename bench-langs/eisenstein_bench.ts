// Eisenstein Kernel Benchmark — TypeScript (Node.js)

function eisensteinNorm(a: number, b: number): number {
    return a * a - a * b + b * b;
}

function eisensteinSnap(x: number, y: number): [number, number] {
    const q = (2.0 / 3.0 * x - 1.0 / 3.0 * y);
    const r = (2.0 / 3.0 * y);
    let rq = Math.round(q);
    let rr = Math.round(r);
    const rs = Math.round(-q - r);
    const diff = Math.abs(rq + rr + rs);
    if (diff === 2) {
        if (Math.abs(rq - q) > Math.abs(rr - r)) {
            rq = -rr - rs;
        } else {
            rr = -rq - rs;
        }
    }
    return [rq, rr];
}

function constraintCheck(a: number, b: number, radius: number): boolean {
    return eisensteinNorm(a, b) <= radius * radius;
}

const N = 10_000_000;

// Seed random (deterministic via simple LCG)
let seed = 42;
function seededRandom(): number {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
}
function randInt(min: number, max: number): number {
    return Math.floor(seededRandom() * (max - min + 1)) + min;
}

// Generate data
const normA = new Int32Array(N);
const normB = new Int32Array(N);
const snapX = new Float64Array(N);
const snapY = new Float64Array(N);
const conA = new Int32Array(N);
const conB = new Int32Array(N);
const conR = new Float64Array(N);

for (let i = 0; i < N; i++) {
    normA[i] = randInt(-1000, 1000);
    normB[i] = randInt(-1000, 1000);
    snapX[i] = seededRandom() * 200.0 - 100.0;
    snapY[i] = seededRandom() * 200.0 - 100.0;
    conA[i] = randInt(-100, 100);
    conB[i] = randInt(-100, 100);
    conR[i] = seededRandom() * 49.0 + 1.0;
}

// Benchmark norm
let normSum = 0;
let start = performance.now();
for (let i = 0; i < N; i++) {
    normSum += eisensteinNorm(normA[i], normB[i]);
}
const normTime = (performance.now() - start) / 1000;

// Benchmark snap
let snapFirst: [number, number] = [0, 0];
start = performance.now();
for (let i = 0; i < N; i++) {
    const s = eisensteinSnap(snapX[i], snapY[i]);
    if (i === 0) snapFirst = s;
}
const snapTime = (performance.now() - start) / 1000;

// Benchmark constraint
let conPass = 0;
start = performance.now();
for (let i = 0; i < N; i++) {
    if (constraintCheck(conA[i], conB[i], conR[i])) conPass++;
}
const conTime = (performance.now() - start) / 1000;

console.log(`TypeScript Results (N=${N.toLocaleString()}):`);
console.log(`  eisenstein_norm:  ${normTime.toFixed(3)}s  (sum=${normSum})`);
console.log(`  eisenstein_snap:  ${snapTime.toFixed(3)}s  (first=(${snapFirst[0]},${snapFirst[1]}))`);
console.log(`  constraint_check: ${conTime.toFixed(3)}s  (pass=${conPass})`);
console.log(`  TOTAL: ${(normTime + snapTime + conTime).toFixed(3)}s`);
