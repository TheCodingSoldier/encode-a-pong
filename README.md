# Encode-A-Pong

A lightweight Pong game controlled entirely by a **mouse scroll wheel** — built for the Raspberry Pi Zero 2 W with a rotary encoder mapped to scroll-wheel input via `uinput`.

## How It Works

This game reads `pygame.MOUSEWHEEL` events to move the player paddle up and down. No keyboard, no mouse cursor, no joystick — just the scroll wheel. It is a perfect match for a rotary encoder that has been configured as a system scroll-wheel device.

The game uses `preciseY` (float precision, pygame >= 2.1.3) with a scroll accumulation buffer, so fast multi-tick encoder rotations are never lost between frames.

## Hardware

| Component | Spec |
|---|---|
| **Board** | Raspberry Pi Zero 2 W (1 GHz ARM Cortex-A53, 512 MB RAM) |
| **OS** | Raspberry Pi OS (Debian Trixie) |
| **Display** | Kuman 3.5" touchscreen (480x320, framebuffer) |
| **Input** | Rotary encoder → `uinput` scroll wheel (A=GPIO20, B=GPIO21, Switch=GPIO6) |

## Requirements

```bash
sudo apt install python3-pygame
```

## Run

```bash
python3 pong.py
```

## Controls

| Action | Input |
|---|---|
| Move paddle up | Scroll wheel up |
| Move paddle down | Scroll wheel down |
| Restart (after game over) | Press `R` |
| Quit | Press `ESC` or close window |

## Optimization Details

Every optimization is specifically tuned for the Pi Zero 2 W's single-core ARM CPU and the Kuman 3.5" framebuffer:

### Display
- **`pygame.SCALED` + `vsync=1`** instead of the obsolete `HWSURFACE` flag (non-functional since Pygame 2.0.0). Vsync syncs to the display refresh, eliminating screen tearing and preventing wasted CPU cycles from rendering faster than the panel can show.
- **Triple fallback**: If `vsync` isn't supported (older pygame), falls back to `SCALED` alone. If `SCALED` is rejected by the Pi's framebuffer, falls back to plain `set_mode()`. The game always starts.
- **Mouse cursor hidden** (`pygame.mouse.set_visible(False)`) — no cursor is needed since the encoder is the only input, and hiding it skips a per-frame blit.

### Rendering
- **Pre-rendered background surface**: The black fill + dashed center line is drawn once into a cached `Surface` (with `.convert()` for pixel-format matching) and blitted as a single operation each frame. This replaces a `screen.fill()` plus a 20-iteration `for` loop every tick.
- **Pre-rendered static text**: The "Press R to restart" text is rendered once at startup, not every frame.
- **Minimal draw calls**: Only 3 `pygame.draw.rect()` calls per frame (two paddles + ball) plus the score text. Everything else is the cached background blit.
- **30 FPS cap**: Smooth for Pong, and keeps the Pi Zero 2 W CPU well under load. The `Clock.tick(30)` call also yields CPU time to the OS between frames.

### Event Handling
- **`pygame.event.set_allowed()`**: Blocks all event types except `QUIT`, `KEYDOWN`, and `MOUSEWHEEL`. The pygame event queue holds ~128 events — blocking `MOUSEMOTION`, `ACTIVEEVENT`, etc. prevents the queue from filling with junk and dropping `MOUSEWHEEL` events during fast encoder spins.
- **Scroll accumulation buffer**: Multiple `MOUSEWHEEL` events within a single frame are accumulated into a float (`preciseY` when available) and applied once, so rapid encoder rotation never loses ticks.
- **Font objects created once**: `pygame.font.Font` construction is expensive; both font sizes are created at startup and reused.

### Code Structure
- `init_display()` helper with triple fallback for maximum Pi compatibility.
- `reset_ball()` helper to avoid duplicating ball-reset logic in 3 places.
- `make_bg_surface()` caches the static background once at startup.
- All tunable constants at the top of the file for easy adjustment.

## Troubleshooting

### Game window is blank / invisible
This should not happen with the current code, but if you previously had issues: do NOT set `SDL_VIDEODRIVER=offscreen` — that renders to a virtual buffer with no visible output. On Raspberry Pi OS desktop, the default `x11` driver works fine. On Pi OS Lite (console-only), you need `kmsdrm` (not `fbcon`, which doesn't exist in SDL2).

### `pygame.error: video system not initialized`
Make sure you're running from the desktop (X11) or have KMSDRM enabled via `raspi-config` → Advanced Options → GL Driver → GL (Fake KMS).

### MOUSEWHEEL events not registering
Verify your encoder's `uinput` service is running and emitting scroll events:
```bash
sudo evtest /dev/input/eventX   # find your encoder's event device
```

## License

**All Rights Reserved.** See [LICENSE](LICENSE) for full terms.

Copyright (c) 2026 TheCodingSoldier. Unauthorized copying, modification, distribution, or forking of this project is strictly prohibited without written permission from the copyright holder.
