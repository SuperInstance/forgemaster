```atari_2600.guard
# Atari 2600 TIA Scanline Cycle Guardrails
# The 6507 CPU has exactly 76 clock cycles per visible scanline
# Skip too few or many cycles and the TV will emit invalid sync pulses—
# like a vintage jukebox that skips tracks if its timing drifts off.
# Enforces strict cycle alignment for proper CRT television output.
constraint cycles_per_scanline in [0, 76]
```

```genesis_audio.guard
# Sega Genesis Z80 Audio Hardware Guardrails
# The Z80 sound processor has only 8KB of dedicated WRAM for sound code and sample buffers
# Max sample rate is locked to ~31.8 kHz by the Genesis' 10.7386 MHz master clock
# Overflowing RAM will corrupt YM2612 voice data, like a cassette tape running over its reel limit.
constraint audio_ram_bytes in [0, 8192]
constraint sample_rate in [0, 32000]
```

```snes_mode7.guard
# SNES Mode 7 Affine Transformation Guardrails
# Mode 7 uses 16-bit Q8.8 fixed-point values for affine matrix coefficients
# Each 8-bit integer/fractional pair maps directly to the PPU's register set
# Going outside 0-255 will break perspective distortion, like a stuck zoom lens.
# All four matrix coefficients share the same hard register limit.
constraint affine_a in [0, 255]
constraint affine_b in [0, 255]
constraint affine_c in [0, 255]
constraint affine_d in [0, 255]
```

```n64_microcode.guard
# N64 RSP Microcode Guardrails
# The Reality Signal Processor has 4096 bytes of dedicated instruction memory (I-MEM)
# Each RSP microcode instruction is 32-bits (4 bytes), so max 1024 total instructions
# Overflowing either limit will crash the RSP, like a floppy disk that can't fit extra files.
constraint microcode_size in [0, 4096]
constraint instruction_count in [0, 1024]
```

```neogeo_sprites.guard
# Neo Geo AES/MVS Sprite Hardware Guardrails
# The Neo Geo's video hardware supports a maximum of 380 total sprites across all scanlines
# Sprite VRAM is capped at 64KB for all sprite tile data—overrunning corrupts palette and tiles
# Think of this like a pinball backglass: only so many playfield pieces fit before running out of space.
constraint sprite_count in [0, 380]
constraint vram_usage in [0, 65536]
```

```amiga_copper.guard
# Commodore Amiga Copper List Guardrails
# The Amiga's custom Copper co-processor can only run during vertical blanking periods
# Total allowed PAL VBlank cycles is exactly 2836 for safe screen updates
# Each Copper instruction consumes 2-3 cycles, so we cap total instructions to avoid missing sync
# Exceeding either limit will break display, like a typewriter that can't finish a line before carriage resets.
constraint copper_list_cycles in [0, 2836]
constraint copper_instructions in [0, 200]
```