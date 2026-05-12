#!/usr/bin/env node
/**
 * Validate snapkit-js implementation against the test corpus.
 * Usage: node validate_js.js
 */

const fs = require('fs');

const SQRT3 = Math.sqrt(3);

function snapError(x, y, a, b) {
    const lx = a - b / 2.0;
    const ly = b * SQRT3 / 2.0;
    return Math.sqrt((x - lx) ** 2 + (y - ly) ** 2);
}

function eisensteinSnap(x, y) {
    const bFloat = 2.0 * y / SQRT3;
    const aFloat = x + y / SQRT3;

    const aLo = Math.floor(aFloat);
    const bLo = Math.floor(bFloat);

    let bestA = 0, bestB = 0, bestErr = Infinity;

    // Check 4 floor/ceil candidates
    for (let da = 0; da <= 1; da++) {
        for (let db = 0; db <= 1; db++) {
            const ca = aLo + da;
            const cb = bLo + db;
            const err = snapError(x, y, ca, cb);
            if (err < bestErr - 1e-15) {
                bestA = ca; bestB = cb; bestErr = err;
            } else if (Math.abs(err - bestErr) < 1e-15) {
                if (ca < bestA || (ca === bestA && cb < bestB)) {
                    bestA = ca; bestB = cb;
                }
            }
        }
    }

    // Check ±1 neighborhood
    for (let da = -1; da <= 1; da++) {
        for (let db = -1; db <= 1; db++) {
            const ca = bestA + da;
            const cb = bestB + db;
            const err = snapError(x, y, ca, cb);
            if (err < bestErr - 1e-15) {
                bestA = ca; bestB = cb; bestErr = err;
            } else if (Math.abs(err - bestErr) < 1e-15) {
                if (ca < bestA || (ca === bestA && cb < bestB)) {
                    bestA = ca; bestB = cb;
                }
            }
        }
    }

    return [bestA, bestB];
}

function main() {
    const data = JSON.parse(fs.readFileSync('corpus/snap_corpus.json', 'utf8'));
    
    let passed = 0, failed = 0;
    const errors = [];

    for (const c of data) {
        const [a, b] = eisensteinSnap(c.input.x, c.input.y);
        const err = snapError(c.input.x, c.input.y, a, b);

        let ok = true;
        if (a !== c.expected.a) {
            errors.push(`Case ${c.id}: a=${a}, expected=${c.expected.a}`);
            ok = false;
        }
        if (b !== c.expected.b) {
            errors.push(`Case ${c.id}: b=${b}, expected=${c.expected.b}`);
            ok = false;
        }
        if (err > c.snap_error_max + 1e-10) {
            errors.push(`Case ${c.id}: snap_error=${err} > max=${c.snap_error_max}`);
            ok = false;
        }

        if (ok) passed++; else failed++;
    }

    console.log(`Results: ${passed}/${data.length} passed, ${failed} failed`);

    if (errors.length > 0) {
        for (const e of errors.slice(0, 20)) {
            console.log(`  ${e}`);
        }
        if (errors.length > 20) {
            console.log(`  ... and ${errors.length - 20} more`);
        }
        process.exit(1);
    } else {
        console.log('All cases passed ✓');
    }
}

main();
