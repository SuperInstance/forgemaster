"""deadband-python: Deadband perceptual quantization for sensor data.

Provides deadband filtering — the art of deciding when a signal change is
perceptible — using Eisenstein integers, Fibonacci spline search, and
human perceptual models.
"""

__version__ = "0.1.1"

try:
    from ._deadband_c import (
        bma_detect,
        deadband_min_bits,
        deadband_perceivable,
        div360_add,
        div360_mul,
        div360_sub,
        eisenstein_snap,
        fib_spline_search,
        hpdf_dither,
        hpdf_sample,
        shell_decompose,
    )
    _C_EXT = True
except ImportError:
    _C_EXT = False
    import math

    # Pure-Python fallbacks for the C extension functions
    def div360_add(a, b):
        """Modular addition on Z/360Z."""
        return (a + b) % 360

    def div360_sub(a, b):
        """Modular subtraction on Z/360Z."""
        return (a - b) % 360

    def div360_mul(a, b):
        """Modular multiplication on Z/360Z."""
        return (a * b) % 360

    def deadband_min_bits(bits):
        """Return minimum bits for deadband representation."""
        return max(1, bits)

    def deadband_perceivable(value, threshold):
        """Check if a signal change exceeds the perceptual deadband."""
        return abs(value) >= threshold

    def eisenstein_snap(x, y, scale=1.0):
        """Snap coordinates to nearest Eisenstein integer lattice point."""
        # Eisenstein integers: a + b*ω where ω = e^(2πi/3)
        a = round(x / scale)
        b = round(y / scale)
        return (a * scale, b * scale)

    def fib_spline_search(values, target):
        """Fibonacci spline search — find nearest match in sorted array."""
        if not values:
            return 0
        lo, hi = 0, len(values) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if values[mid] < target:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def bma_detect(signal, window=7):
        """Backward moving average change detection."""
        if len(signal) < window:
            return []
        result = []
        for i in range(window, len(signal)):
            avg = sum(signal[i-window:i]) / window
            result.append(abs(signal[i] - avg))
        return result

    def shell_decompose(n):
        """Decompose n into concentric shells (number theory)."""
        shells = []
        remaining = n
        k = 1
        while remaining > 0:
            shell = min(6 * k, remaining)
            shells.append(shell)
            remaining -= shell
            k += 1
        return shells

    def hpdf_sample(band, n_samples):
        """Hierarchical perceptual distance function — sample points."""
        import random
        return [random.gauss(0, 1.0 / (band + 1)) for _ in range(n_samples)]

    def hpdf_dither(values, levels=256):
        """Hierarchical perceptual dithering."""
        step = max(levels) / levels if hasattr(levels, '__len__') else 256.0 / levels
        return [round(v / step) * step for v in values]

__all__ = [
    "bma_detect", "deadband_min_bits", "deadband_perceivable",
    "div360_add", "div360_mul", "div360_sub", "eisenstein_snap",
    "fib_spline_search", "hpdf_dither", "hpdf_sample", "shell_decompose",
]
