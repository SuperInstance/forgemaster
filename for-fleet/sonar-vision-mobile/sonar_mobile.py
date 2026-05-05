"""
SonarVision Mobile — Smartphone-based acoustic imaging engine.
Self-supervised sonar using off-the-shelf phone speakers + microphones.

Inherits physics from the FLUX engine in sonar-sim-pipeline.
"""

import numpy as np
from typing import List, Tuple, Optional
from scipy import signal


class SonarVisionMobile:
    """Self-supervised acoustic imaging engine for mobile devices.

    Uses coded ultrasonic chirps (18-22kHz) emitted from a phone speaker,
    received on the phone's microphone array, to reconstruct scene geometry
    through physics-constrained self-supervised learning.
    """

    def __init__(
        self,
        fs: int = 48000,
        chirp_duration: float = 0.05,
        f_start: float = 18000.0,
        f_end: float = 22000.0,
        sound_speed: float = 343.0,
    ):
        self.fs = fs
        self.sound_speed = sound_speed
        self.tx_chirp = self.generate_chirp(f_start, f_end, chirp_duration, fs)

    # ── Chirp Generation ──────────────────────────────────────────────

    def generate_chirp(
        self,
        f_start: float = 18000.0,
        f_end: float = 22000.0,
        duration: float = 0.05,
        fs: int = 48000,
    ) -> np.ndarray:
        """Generate a linear FM chirp with Hanning window.

        Downward-sweeping LFM chirp: energy spreads over frequency,
        then compresses to a sharp peak via matched filtering.

        Returns:
            Float32 array of shape (n_samples,) in [-1, 1].
        """
        n = int(duration * fs)
        t = np.arange(n, dtype=np.float64) / fs
        # Phase: integral of frequency
        k = (f_end - f_start) / duration  # sweep rate (Hz/s)
        phase = 2.0 * np.pi * (f_start * t + 0.5 * k * t ** 2)
        chirp = np.sin(phase)
        # Hanning window
        window = np.hanning(n)
        chirp = chirp * window
        # Normalize
        max_val = np.max(np.abs(chirp))
        if max_val > 0:
            chirp = chirp / max_val
        return chirp.astype(np.float32)

    # ── Matched Filter / Pulse Compression ────────────────────────────

    def matched_filter(
        self, rx_signal: np.ndarray, tx_chirp: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """Pulse compression via cross-correlation.

        The chirp sweeps from f_start to f_end over duration seconds.
        Correlation compresses the spread energy into a sharp peak
        at the time delay corresponding to the target range.

        Returns:
            Correlation (float32) same length as rx_signal.
            Peak at index d corresponds to echo delayed by d samples.
        """
        if tx_chirp is None:
            tx_chirp = self.tx_chirp
        # Cross-correlation of rx_signal with time-reversed tx_chirp
        # For a real-valued LFM chirp, this is equivalent to matched filtering
        corr = signal.correlate(rx_signal, tx_chirp[::-1], mode="same", method="fft")
        # Normalize by energy of tx_chirp
        corr = corr.astype(np.float64) / (np.linalg.norm(tx_chirp) + 1e-12)
        return corr.astype(np.float32)

    # ── Envelope Detection ────────────────────────────────────────────

    def envelope(self, x: np.ndarray, fc: float = 300.0) -> np.ndarray:
        """Envelope detection via Hilbert transform + low-pass filter.

        The analytic signal magnitude gives the envelope.
        A final low-pass smooths it to avoid spurious peaks.

        Args:
            x: Input signal
            fc: Low-pass cutoff (Hz). Default 300Hz.

        Returns:
            Envelope array float32 same shape as x.
        """
        analytic = signal.hilbert(x)
        env = np.abs(analytic)
        # Low-pass filter to smooth
        sos = signal.butter(4, fc / (self.fs / 2), btype="low", output="sos")
        env = signal.sosfiltfilt(sos, env)
        return env.astype(np.float32)

    # ── Range Profile Extraction ──────────────────────────────────────

    def range_profile(
        self,
        rx_signal: np.ndarray,
        tx_chirp: Optional[np.ndarray] = None,
        fs: Optional[int] = None,
        sound_speed: Optional[float] = None,
        peak_threshold: float = 0.3,
        max_range_m: float = 10.0,
        min_peak_distance_samples: int = 10,
    ) -> List[Tuple[float, float]]:
        """Extract range profile from received signal.

        Pipeline:
        1. Matched filter (pulse compression)
        2. Envelope detection
        3. Peak detection (scipy find_peaks)
        4. Convert sample indices to distances: d = t * c / 2

        Args:
            rx_signal: Received audio signal (n_samples,)
            tx_chirp: Transmitted chirp (uses self.tx_chirp if None)
            fs: Sample rate (defaults to self.fs)
            sound_speed: Speed of sound m/s (defaults to self.sound_speed)
            peak_threshold: Min height as fraction of envelope max
            max_range_m: Maximum range to report (m)
            min_peak_distance_samples: Minimum samples between peaks

        Returns:
            List of (distance_m, amplitude) sorted by amplitude descending.
        """
        if fs is None:
            fs = self.fs
        if sound_speed is None:
            sound_speed = self.sound_speed
        if tx_chirp is None:
            tx_chirp = self.tx_chirp

        # Matched filter
        corr = self.matched_filter(rx_signal, tx_chirp)
        # Envelope
        env = self.envelope(corr)

        # signal.correlate(a, b, mode='same') returns len(a) samples
        # centered on the full correlation. For len(a) >= len(b):
        #   same[0] = full[(len(b)-1)//2]
        #   zero-lag (full[delay + len(b)-1]) maps to same[delay + len(b)//2]
        # So the zero-lag offset in 'same' coordinates is:
        #   actual_delay = peak_idx - len(tx_chirp)//2
        zero_lag_idx = len(tx_chirp) // 2

        # Peak detection
        threshold = peak_threshold * np.max(env)
        peaks, properties = signal.find_peaks(
            env,
            height=threshold,
            distance=min_peak_distance_samples,
        )

        results: List[Tuple[float, float]] = []
        max_actual_delay = int(max_range_m * 2 * fs / sound_speed)
        for idx, height in zip(peaks, properties["peak_heights"]):
            # Convert sample index to distance
            # idx = zero_lag + actual_delay
            # actual_delay = idx - zero_lag_idx
            actual_delay = idx - zero_lag_idx
            if actual_delay < 0:
                continue
            delay_s = actual_delay / fs
            range_m = delay_s * sound_speed / 2.0
            if range_m <= max_range_m and actual_delay <= max_actual_delay:
                results.append((float(range_m), float(height)))

        # Sort by amplitude descending
        results.sort(key=lambda x: -x[1])
        return results

    # ── Two-Microphone Beamforming ────────────────────────────────────

    def beamform_two_mic(
        self,
        rx1: np.ndarray,
        rx2: np.ndarray,
        tx_chirp: Optional[np.ndarray] = None,
        mic_spacing: float = 0.15,
        fs: Optional[int] = None,
        sound_speed: Optional[float] = None,
        theta_resolution: int = 181,
    ) -> Tuple[np.ndarray, float]:
        """Delay-and-sum beamformer for two microphones.

        For a plane wave arriving at angle θ from boresight:

            τ = d * sin(θ) / c   (seconds, positive = mic2 receives later)

        Approach: delay the RAW signal, then matched filter.
        This is the correct pipeline — delaying the raw signal and THEN
        applying the matched filter preserves the pulse compression gain.
        Delaying the matched filter output loses angular resolution because
        the envelope is as wide as the chirp (50ms ≈ 8.5m in range).

        For each candidate θ:
        1. Time-align the two raw channels by delaying rx1 by τ
        2. Sum the aligned raw signals
        3. Matched filter the summed signal
        4. Compute RMS power of the matched filter output

        Args:
            rx1: Mic1 signal (n_samples,)
            rx2: Mic2 signal (n_samples,)
            tx_chirp: Optional, used for matched filtering
            mic_spacing: Distance between mics (m). Default 0.15m
            fs: Sample rate
            sound_speed: Speed of sound (m/s)
            theta_resolution: Number of angle bins. Default 181.

        Returns:
            (beam_power, estimated_bearing_deg)
            beam_power: (theta_resolution,) array, normalized 0-1
            estimated_bearing_deg: angle of peak (degrees)
        """
        if fs is None:
            fs = self.fs
        if sound_speed is None:
            sound_speed = self.sound_speed

        tx = tx_chirp if tx_chirp is not None else self.tx_chirp
        angles = np.linspace(-90.0, 90.0, theta_resolution)
        beam_power = np.zeros(theta_resolution, dtype=np.float64)
        n_orig = len(rx1)

        # Pre-compute raw signal FFTs for fast fractional delay
        pad = int(mic_spacing / sound_speed * fs * 1.5) + 64
        s1 = np.pad(rx1.astype(np.float64), (pad, pad), mode='constant')
        s2 = np.pad(rx2.astype(np.float64), (pad, pad), mode='constant')
        n_pad = len(s1)
        n_fft = 1
        while n_fft < n_pad + len(tx):
            n_fft *= 2
        X1 = np.fft.fft(s1, n=n_fft)
        k = np.arange(n_fft, dtype=np.float64)

        # Pre-compute matched filter kernel in frequency domain
        mf_kernel = np.fft.fft(
            np.pad(tx[::-1].astype(np.float64), (0, n_fft - len(tx)), mode='constant'),
            n=n_fft
        )

        # In-phase reference for each channel (no delay summed)
        # This sets the baseline — if both signals are identical (0° target),
        # the sum of raw signals doubles the chirp amplitude
        ref_raw_sum = s1 + s2
        ref_mf = np.fft.ifft(np.fft.fft(ref_raw_sum, n=n_fft) * mf_kernel)[:n_pad].real
        ref_power = float(np.sum(ref_mf ** 2))

        for i, theta_deg in enumerate(angles):
            theta = np.deg2rad(theta_deg)
            # Delay rx1 by τ = d*sin(θ)/c to align with rx2
            # For θ > 0: mic2 receives later, so delay mic1 to align
            delay_samples = mic_spacing * np.sin(theta) / sound_speed * fs

            if abs(delay_samples) < 0.5:
                raw_sum = s1 + s2
            else:
                # Delay raw channel (not MF output)
                phase = np.exp(-2j * np.pi * k * delay_samples / n_fft)
                s1_delayed = np.fft.ifft(X1 * phase)[:n_pad].real
                raw_sum = s1_delayed + s2

            # Matched filter the summed signal
            mf_sum = np.fft.ifft(np.fft.fft(raw_sum, n=n_fft) * mf_kernel)[:n_pad].real
            # Power in the original signal region
            signal_region = mf_sum[pad:-pad]
            beam_power[i] = float(np.sum(signal_region ** 2))

        # Normalize
        max_power = np.max(beam_power)
        if max_power > 0:
            beam_power = beam_power / max_power

        est_idx = int(np.argmax(beam_power))
        estimated_bearing = float(angles[est_idx])

        return beam_power.astype(np.float32), estimated_bearing

    def _fractional_delay(self, signal: np.ndarray, delay_samples: float, n: int) -> np.ndarray:
        """Fractional delay via FFT phase shift.

        A delay in time domain is a linear phase ramp in frequency domain.
        y[t] = x[t - d]  ↔  Y[ω] = X[ω] * exp(-jωd)

        Uses enough FFT length + post-windowing to avoid artifacts.

        Args:
            signal: Input signal (n,)
            delay_samples: Delay in samples (positive = shift right / later)
            n: Output length

        Returns:
            Delayed signal (n,)
        """
        if abs(delay_samples) < 0.5:
            return signal[:n].copy()

        Nfft = n
        sig = signal[:n].astype(np.float64)
        X = np.fft.fft(sig, n=Nfft)
        k = np.arange(Nfft, dtype=np.float64)
        phase_ramp = np.exp(-2j * np.pi * k * delay_samples / Nfft)
        Y = X * phase_ramp
        delayed = np.fft.ifft(Y)[:n].real
        return delayed

    # ── Multi-Mic Range-Bearing Map ───────────────────────────────────

    def range_bearing_map(
        self,
        rx_signals: List[np.ndarray],
        tx_chirp: Optional[np.ndarray] = None,
        mic_positions: Optional[List[Tuple[float, float, float]]] = None,
        fs: Optional[int] = None,
        sound_speed: Optional[float] = None,
        range_bins: int = 100,
        angle_bins: int = 181,
        max_range_m: float = 5.0,
    ) -> np.ndarray:
        """Multi-microphone range-bearing imaging.

        Back-projects range profiles from all mic pairs into a
        common range × bearing grid via delay estimation.

        Args:
            rx_signals: List of N mic signals, each (n_samples,)
            tx_chirp: Transmitted chirp
            mic_positions: 3D positions of each mic (N, 3).
                           If None, assumes linear array with 15cm spacing.
            fs: Sample rate
            sound_speed: Speed of sound
            range_bins: Number of range bins in output
            angle_bins: Number of angle bins in output
            max_range_m: Maximum range (m)

        Returns:
            (range_bins, angle_bins) heatmap float32
        """
        if fs is None:
            fs = self.fs
        if sound_speed is None:
            sound_speed = self.sound_speed
        if tx_chirp is None:
            tx_chirp = self.tx_chirp

        n_mics = len(rx_signals)
        if n_mics < 2:
            raise ValueError("Need at least 2 microphones")

        # Default positions: linear array
        if mic_positions is None:
            mic_positions = [(0, 0, i * 0.15) for i in range(n_mics)]

        ranges = np.linspace(0, max_range_m, range_bins)
        angles = np.linspace(-90, 90, angle_bins)
        heatmap = np.zeros((range_bins, angle_bins), dtype=np.float64)

        # For each mic pair, compute range profile and back-project
        for i in range(n_mics):
            for j in range(i + 1, n_mics):
                rx_i = rx_signals[i]
                rx_j = rx_signals[j]

                # Matched filter each
                mf_i = self.matched_filter(rx_i, tx_chirp)
                mf_j = self.matched_filter(rx_j, tx_chirp)

                # Envelope
                env_i = self.envelope(mf_i)
                env_j = self.envelope(mf_j)

                # Vector from mic_i to mic_j
                p_i = np.array(mic_positions[i])
                p_j = np.array(mic_positions[j])
                baseline = np.linalg.norm(p_j - p_i)

                # For each range bin, search over angles
                for ri, r_m in enumerate(ranges):
                    if r_m < 0.1:
                        continue
                    # Time index in signal
                    delay_samples = int(2.0 * r_m / sound_speed * fs)
                    if delay_samples >= len(env_i):
                        continue

                    for ai, theta_deg in enumerate(angles):
                        theta = np.deg2rad(theta_deg)
                        # Expected delay difference between mics
                        delta_t = baseline * np.sin(theta) / sound_speed
                        delta_samples = int(delta_t * fs)
                        # Sample amplitude from env_i at range, env_j with offset
                        idx_i = delay_samples
                        idx_j = delay_samples + delta_samples
                        amp = 0.0
                        if 0 <= idx_i < len(env_i):
                            amp += env_i[idx_i]
                        if 0 <= idx_j < len(env_j):
                            amp += env_j[idx_j]
                        heatmap[ri, ai] += amp

        # Normalize
        max_val = np.max(heatmap)
        if max_val > 0:
            heatmap = heatmap / max_val

        return heatmap.astype(np.float32)

    # ── Breathing Extraction ──────────────────────────────────────────

    def extract_breathing(
        self,
        range_profiles: np.ndarray,
        target_range_idx: int,
        fs_profiles: float = 10.0,
        band_min: float = 0.1,
        band_max: float = 0.8,
    ) -> Tuple[float, np.ndarray]:
        """Extract breathing rate from sequential range profiles.

        Tracks amplitude at a specific range bin over time,
        bandpass filters for respiration frequencies (0.1-0.8 Hz),
        and finds the dominant frequency via FFT.

        Args:
            range_profiles: (n_profiles, n_range_bins) amplitude matrix.
                Each profile is a full range scan.
            target_range_idx: Index of range bin to monitor (chest position).
            fs_profiles: Sampling rate of profiles (Hz).
            band_min: Min respiration frequency (Hz). Default 0.1 (6 BPM).
            band_max: Max respiration frequency (Hz). Default 0.8 (48 BPM).

        Returns:
            (breathing_rate_bpm, filtered_waveform)
        """
        n_profiles = range_profiles.shape[0]
        if n_profiles < 10:
            return 0.0, np.zeros(n_profiles)

        # Extract amplitude at target range over time
        raw_signal = range_profiles[:, target_range_idx].copy()

        # Remove DC
        raw_signal = raw_signal - np.mean(raw_signal)

        # Bandpass filter
        nyquist = fs_profiles / 2.0
        sos = signal.butter(
            4,
            [band_min / nyquist, band_max / nyquist],
            btype="band",
            output="sos",
        )
        filtered = signal.sosfiltfilt(sos, raw_signal)

        # FFT to find dominant frequency
        n_fft = max(1024, n_profiles)
        fft_mag = np.abs(np.fft.rfft(filtered, n=n_fft))
        freqs = np.fft.rfftfreq(n_fft, d=1.0 / fs_profiles)

        # Find peak in respiration band
        mask = (freqs >= band_min) & (freqs <= band_max)
        if np.sum(mask) == 0:
            return 0.0, filtered

        peak_idx = int(np.argmax(fft_mag[mask]))
        peak_freq = float(freqs[mask][peak_idx])
        breathing_rate_bpm = peak_freq * 60.0

        return breathing_rate_bpm, filtered

    # ── Self-Supervised Loss ──────────────────────────────────────────

    def self_supervised_loss(
        self,
        camera_depth_map: np.ndarray,
        acoustic_range_profile: np.ndarray,
        camera_K: np.ndarray,
        device_pose: np.ndarray,
    ) -> float:
        """Cross-modal consistency loss between camera and acoustic.

        Projects acoustic range-bearing returns into the camera's
        coordinate frame and computes MSE against camera depth.

        Args:
            camera_depth_map: (H, W) depth map from camera (meters)
            acoustic_range_profile: (N_angles, N_range_bins) heatmap.
                Angles span [-90°, 90°], ranges span [0, max_range].
            camera_K: 3x3 camera intrinsics matrix.
            device_pose: 4x4 camera-to-world transform.

        Returns:
            Float MSE loss.

        Note:
            This is a simplified version. Full implementation would
            use proper sensor fusion and uncertainty weighting.
        """
        H, W = camera_depth_map.shape[:2]
        n_angles, n_ranges = acoustic_range_profile.shape

        # Build angle and range axes (must match how heatmap was built)
        # Assuming heatmap[angle_idx, range_idx] centered at:
        angles = np.linspace(-90, 90, n_angles)
        ranges = np.linspace(0, 5.0, n_ranges)  # match max_range in range_bearing_map

        # For each acoustic return above threshold, project into camera
        threshold = 0.3 * np.max(acoustic_range_profile)
        acoustic_depths: List[float] = []
        camera_depths: List[float] = []

        for ai in range(n_angles):
            theta_deg = angles[ai]
            theta = np.deg2rad(theta_deg)
            for ri in range(n_ranges):
                if acoustic_range_profile[ai, ri] < threshold:
                    continue
                r_m = ranges[ri]

                # 3D point in device frame:
                # Assume device x=forward, y=right, z=up
                # Acoustic return from angle θ (yaw) and range r
                x = r_m * np.cos(theta)
                y = r_m * np.sin(theta)
                z = 0.0  # Assume same height as device
                pt_device = np.array([x, y, z, 1.0], dtype=np.float64)

                # Transform to camera frame
                pt_cam = np.linalg.inv(device_pose) @ pt_device
                if pt_cam[2] <= 0:  # Behind camera
                    continue

                # Project to pixel
                pixel = camera_K @ pt_cam[:3]
                u = int(pixel[0] / pixel[2])
                v = int(pixel[1] / pixel[2])

                if 0 <= u < W and 0 <= v < H:
                    d_cam = float(camera_depth_map[v, u])
                    if d_cam > 0 and d_cam < 10.0:
                        acoustic_depths.append(r_m)
                        camera_depths.append(d_cam)

        if len(acoustic_depths) < 5:
            return 0.0  # Not enough correspondences

        # MSE loss
        acoustic_arr = np.array(acoustic_depths, dtype=np.float64)
        camera_arr = np.array(camera_depths, dtype=np.float64)
        loss = float(np.mean((acoustic_arr - camera_arr) ** 2))

        return loss

    # ── Physics-Constrained Predict ───────────────────────────────────

    def physics_constrained_predict(
        self,
        latent_scene_params: dict,
        temp: float = 20.0,
        humidity: float = 50.0,
    ) -> np.ndarray:
        """Predict expected acoustic return from latent scene parameters
        using the FLUX acoustic propagation model.

        This is the key self-supervised signal: the predicted return
        is compared against the actual received signal.

        Args:
            latent_scene_params: Scene parameters dict with keys:
                - room_dims: (L, W, H) in meters
                - wall_reflectivity: float [0, 1]
                - person_range: distance to person (m)
                - person_angle: bearing to person (deg)
                - breathing_amplitude: chest displacement (m)
            temp: Temperature (°C) for sound speed calculation
            humidity: Relative humidity (%) for absorption

        Returns:
            Predicted return waveform (n_samples,) float32 matching chirp length.
        """
        # Sound speed from temperature
        c = 331.3 * np.sqrt(1.0 + temp / 273.15)
        n = len(self.tx_chirp)

        # Build predicted return as sum of reflections
        predicted = np.zeros(n, dtype=np.float64)

        room_dims = latent_scene_params.get("room_dims", (3.0, 4.0, 2.5))
        wall_reflectivity = latent_scene_params.get("wall_reflectivity", 0.3)
        person_range = latent_scene_params.get("person_range", 2.0)
        person_angle = latent_scene_params.get("person_angle", 0.0)
        breathing_amplitude = latent_scene_params.get("breathing_amplitude", 0.003)

        # 1. Direct path reflection from person (primary return)
        travel_time = 2.0 * person_range / c
        delay_samples = int(travel_time * self.fs)
        if delay_samples < n:
            # Reflectivity: ~0.5 for human body at 20kHz
            person_reflectivity = 0.5
            atten = person_reflectivity / (person_range ** 2 + 0.1)
            shifted = np.zeros(n, dtype=np.float64)
            shift_end = min(n - delay_samples, len(self.tx_chirp))
            shifted[delay_samples:delay_samples + shift_end] = (
                self.tx_chirp[:shift_end] * atten
            )
            predicted += shifted

        # 2. Breathing modulation (phase shift due to chest movement)
        if person_range > 0.5:
            breathing_period_samples = int(self.fs / 0.3)  # ~18 BPM
            if breathing_period_samples > 0:
                # Sinusoidal delay modulation
                mod_amplitude_samples = int(
                    2.0 * breathing_amplitude / c * self.fs
                )
                for t in range(0, n, breathing_period_samples):
                    mod_t = np.arange(min(breathing_period_samples, n - t))
                    phase = 2.0 * np.pi * mod_t / breathing_period_samples
                    mod_delay = int(mod_amplitude_samples * np.sin(phase).mean())
                    if 0 <= t + mod_delay < n and delay_samples + mod_delay < n:
                        idx = delay_samples + t + mod_delay
                        if idx < n:
                            predicted[idx] += predicted[delay_samples + t] * 0.05

        # 3. Nearest wall reflection
        nearest_wall = min(room_dims) / 2.0
        wall_time = 2.0 * nearest_wall / c
        wall_delay = int(wall_time * self.fs)
        if 0 < wall_delay < n:
            wall_shifted = np.zeros(n, dtype=np.float64)
            shift_end = min(n - wall_delay, len(self.tx_chirp))
            wall_shifted[wall_delay:wall_delay + shift_end] = (
                self.tx_chirp[:shift_end] * wall_reflectivity / (nearest_wall ** 2)
            )
            predicted += wall_shifted

        # 4. Absorption at 20kHz (standard atmosphere)
        # Approximate: α ≈ 1.2 dB/m at 20kHz, 50% RH
        alpha = 1.2  # dB/m
        for d_samples in range(n):
            distance = d_samples / self.fs * c / 2.0
            absorption = 10.0 ** (-alpha * distance / 20.0)
            predicted[d_samples] *= absorption

        # Normalize to match typical received signal energy
        rx_energy = np.sum(predicted ** 2)
        chirp_energy = np.sum(self.tx_chirp.astype(np.float64) ** 2)
        if rx_energy > 0 and chirp_energy > 0:
            predicted = predicted * np.sqrt(chirp_energy / rx_energy) * 0.01

        return predicted.astype(np.float32)
