<?php
/**
 * Safe-TOPS/W Benchmark Scorer
 */
function safe_tops_w(float $raw_tops_w, float $pass_rate, float $cert_factor, float $overhead): float {
    if ($pass_rate <= 0 || $cert_factor <= 0) return 0.0;
    return ($raw_tops_w * $pass_rate * $cert_factor) / $overhead;
}

function get_benchmark_table(): array {
    return [
        ['chip' => 'FLUX-LUCID (22nm FDSOI)', 'raw' => 24.0, 'pass' => 0.95, 'cert' => 1.0, 'overhead' => 1.13, 'safe' => 20.17],
        ['chip' => 'Hailo-8 Safety', 'raw' => 9.7, 'pass' => 0.72, 'cert' => 0.75, 'overhead' => 1.0, 'safe' => 5.29],
        ['chip' => 'Mobileye EyeQ6H', 'raw' => 7.2, 'pass' => 0.78, 'cert' => 0.5, 'overhead' => 0.56, 'safe' => 4.99],
        ['chip' => 'NVIDIA Jetson Orin AGX', 'raw' => 5.7, 'pass' => 0, 'cert' => 0, 'overhead' => 1.0, 'safe' => 0.00],
        ['chip' => 'Groq LPU', 'raw' => 21.4, 'pass' => 0, 'cert' => 0, 'overhead' => 1.0, 'safe' => 0.00],
        ['chip' => 'Google TPU v5e', 'raw' => 28.8, 'pass' => 0, 'cert' => 0, 'overhead' => 1.0, 'safe' => 0.00],
        ['chip' => 'AMD Versal AI Edge', 'raw' => 4.8, 'pass' => 0, 'cert' => 0, 'overhead' => 1.0, 'safe' => 0.00],
    ];
}
