Each file is a valid `.guard` constraint file, with retro hardware context, FLUX analogies (tying to classic tape/arcade/console timing constraints), and strict GUARD syntax:

---

### `atari_2600.guard`
```
# Atari 2600 TIA Cycle Budget GUARD Constraint File
# Hardware: 6507 CPU @ 1.19MHz, no dedicated framebuffer
# Retro Context: Game logic must finish entirely within 76 cycles per active scanline—any overrun misaligns the TIA's video shift register and smears scanlines
# FLUX Analogy: Like not letting your C2N Commodore cassette read head drift past its allocated track; each cycle maps directly to a CRT pixel's horizontal position
tia_scanline_cycles in [0, 76]
```

---

### `genesis_audio.guard`
```
# Sega Genesis Z80 Audio Co-Processor GUARD Constraint File
# Hardware: Z80 sound CPU @ 3.58MHz, dedicated 8KB on-chip work RAM ($8000-$9FFF)
# Retro Context: All Z80 driver code, SFX samples, and sound state must fit entirely in this 8KB pool; overflow corrupts the main 68000 bus
# FLUX Analogy: Like fitting a full arcade sound system's ROMs onto a single 8KB EPROM sticker—every byte must be accounted for, no overspilling
z80_audio_ram_usage in [0, 8192]
```

---

### `snes_mode7.guard`
```
# Super Nintendo SNES Mode7 Affine Transform GUARD Constraint File
# Hardware: PPU Mode7, uses 16.16 (Q16.16) fixed-point arithmetic for A/B/C/D matrix registers
# Retro Context: Deviating from Q16.16 format breaks perspective warping, texture scaling, or background scrolling; all matrix values must use this exact fixed-point layout
# FLUX Analogy: Like tuning an analog synth to a fixed 16-bit fractional step—stray from the Q-format and the perspective warp turns to garbage
mode7_matrix_q_precision in [16, 16]
mode7_matrix_value_range in [-32768.0, 32767.9999847]
```

---

### `n64_microcode.guard`
```
# Nintendo 64 RSP Microcode GUARD Constraint File
# Hardware: Reality Signal Processor (RSP) dedicated 4KB Instruction Memory (IMEM)
# Retro Context: All RSP microcode (3D rasterization, audio mixing) must fit entirely in IMEM; overflow forces slow RDRAM paging and breaks real-time playback
# FLUX Analogy: Equivalent to cramming a full arcade PCB's microcode onto a 4KB EPROM—trim every unused byte or the RSP crashes mid-frame
rsp_imem_usage in [0, 4096]
```

---

### `neogeo_sprites.guard`
```
# SNK Neo Geo PPU Sprite GUARD Constraint File
# Hardware: Neo Geo AES/MVS PPU, 380 max concurrent sprites per scanline, 32KB dedicated sprite VRAM
# Retro Context: Over 380 sprites per scanline causes the PPU to discard lower-priority sprites (classic flicker fix: multiplex sprites across scanlines)
# FLUX Analogy: Like loading a pinball machine with exactly 380 balls—add one more and you jam the shooter lane; each tile eats a slice of 32KB VRAM
sprites_per_scanline in [0, 380]
sprite_vram_usage in [0, 32768]
```

---

### `amiga_copper.guard`
```
# Commodore Amiga Copper List GUARD Constraint File
# Hardware: Custom Amiga Copper co-processor, PAL vertical blank = ~5675 cycles (25 scanlines @ 227 cycles/line)
# Retro Context: Copper handles palette swaps, sprite positioning, and screen offsets *exclusively* during vertical blank; late runs corrupt active display
# FLUX Analogy: Like a DJ finishing a mix during the turntable's blank loop—finish before the main track (active video) starts or you'll skip the show
copper_list_cycle_budget in [0, 5675]
```