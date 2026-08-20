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

Or via pip (recommended version >= 2.0.0 for SCALED + vsync support):

```bash
pip install -r requirements.txt
```

## Run

```bash
python3 pong.py
```

Press `Ctrl+C` in the terminal or `ESC` in-game to quit cleanly — both are handled gracefully and always release the display properly.

## Controls

| Action | Input |
|---|---|
| Move paddle up | Scroll wheel up |
| Move paddle down | Scroll wheel down |
| Restart (after game over) | Press `R` |
| Quit | Press `ESC`, close window, or `Ctrl+C` in terminal |

## Game Features

- First to 7 points wins
- Ball angles based on where it hits the paddle (center = straight, edges = sharp angle)
- 800ms serve delay after each score — ball pauses at center before launching
- AI opponent with speed-capped tracking (beatable but challenging)
- Ball is hidden during serve delay for a clean visual reset
- Ball never goes perfectly horizontal (minimum vertical velocity enforced)

## Compatibility

The game works on **pygame 1.x and 2.x**. It checks `pygame.version.vernum` before using the `SCALED` flag (added in 2.0.0) to avoid an `AttributeError` crash on older installs. On pygame 1.x, it falls back to plain `set_mode()`. On pygame 2.x, it tries `SCALED + vsync`, then `SCALED` alone, then plain mode — the game always starts.

## Optimization Details

Every optimization is specifically tuned for the Pi Zero 2 W's single-core ARM CPU and the Kuman 3.5" framebuffer:

### Display
- **`pygame.SCALED` + `vsync=1`** instead of the obsolete `HWSURFACE` flag (non-functional since Pygame 2.0.0). Vsync syncs to the display refresh, eliminating tearing and preventing wasted CPU cycles.
- **Version-guarded**: `pygame.version.vernum >= (2, 0, 0)` check before accessing `pygame.SCALED` prevents `AttributeError` on pygame 1.x.
- **Triple fallback**: If `vsync` isn't supported, falls back to `SCALED` alone. If `SCALED` is rejected by the Pi's framebuffer, falls back to plain `set_mode()`. The game always starts.
- **Mouse cursor hidden** — no cursor is needed since the encoder is the only input.

### Rendering
- **Pre-rendered background surface**: Black fill + dashed center line drawn once into a cached `Surface`, blitted as a single operation each frame.
- **Pre-rendered static text**: "Press R to restart" rendered once at startup.
- **Score text caching**: Score is only re-rendered when it actually changes.
- **Ball hidden during serve delay**: Skips a `draw.rect` call when ball is waiting to launch.
- **Minimal draw calls**: Only 3-4 `pygame.draw.rect()` calls per frame.
- **30 FPS cap** via `clock.tick(FPS)`, which both caps the framerate and returns elapsed milliseconds — the standard pygame idiom, used directly as `dt` for the serve timer.

### Event Handling
- **`pygame.event.set_allowed()`**: Blocks all event types except `QUIT`, `KEYDOWN`, and `MOUSEWHEEL`. Prevents the ~128-event queue from filling with junk and dropping scroll events during fast encoder spins.
- **Scroll accumulation buffer**: Multiple `MOUSEWHEEL` events within one frame are accumulated as a float and applied once.
- **Font objects created once** at startup.

### Collision Physics
- **Tunneling prevention**: After a paddle bounce, the ball is physically repositioned outside the paddle rect. Prevents the ball from getting stuck inside the paddle — a well-known pygame Pong bug documented in the official pygame tutorial and SDL forums.
- **Wall bounce repositioning**: Ball is snapped to the exact wall edge on collision, preventing it from sinking into the wall over multiple frames.
- **Hit angle clamping**: The hit position is clamped to [-1, 1] before calculating the bounce angle.
- **Minimum vertical velocity**: `MIN_BALL_VY = 1` ensures the ball always has vertical movement, preventing an unwinnable perfectly-horizontal ball.
- **Direction-guarded collisions**: Player paddle only bounces when the ball moves left, AI paddle only when it moves right, preventing double-bounces.

### Shutdown Handling
- **Graceful `Ctrl+C`**: `run()` is wrapped in a `try/except KeyboardInterrupt` inside `main()`, with `pygame.quit()` called in a `finally` block. Interrupting the script from the terminal (e.g. via SSH) exits cleanly instead of dumping a traceback and potentially leaving the display in a bad state.

### Code Structure
- `init_display()` — version-guarded triple fallback display initialization.
- `reset_ball()` — centralized ball reset with velocity guarantees.
- `make_bg_surface()` — caches static background once.
- `clamp_paddle()` — reusable paddle bounds enforcement.
- `bounce_ball()` — collision response with repositioning and angle calculation.
- `run()` / `main()` split — separates game logic from top-level exception handling.
- All tunable constants at the top of the file.

## Further Performance Tuning (Optional)

If you want to squeeze out extra headroom on the Pi Zero 2 W, set the CPU governor to `performance` (uses more power, but eliminates frequency-scaling lag during gameplay):

```bash
sudo sh -c "echo performance > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor"
```

To make this persistent across reboots, add it to a systemd service or `/etc/rc.local`. This is optional — the game is light enough to run fine on the default `ondemand` governor.

## Troubleshooting

### Game window is blank / invisible
Do NOT set `SDL_VIDEODRIVER=offscreen` — that renders to a virtual buffer with no visible output. On Raspberry Pi OS desktop, the default `x11` driver works fine. On Pi OS Lite (console-only), you need `kmsdrm` (not `fbcon`, which doesn't exist in SDL2).

### `pygame.error: video system not initialized`
Make sure you're running from the desktop (X11) or have KMSDRM enabled via `raspi-config` → Advanced Options → GL Driver → GL (Fake KMS).

### MOUSEWHEEL events not registering
Verify your encoder's `uinput` service is running and emitting scroll events:
```bash
sudo evtest /dev/input/eventX   # find your encoder's event device
```

### Ball gets stuck inside a paddle
This should not happen — `bounce_ball()` repositions the ball outside the paddle on every collision.

### Ctrl+C leaves the terminal in a weird state
This is handled: `main()` always calls `pygame.quit()` in a `finally` block before exiting, even on `KeyboardInterrupt`.

### AttributeError: module 'pygame' has no attribute 'SCALED'
This should not happen — the code checks `pygame.version.vernum >= (2, 0, 0)` before accessing `pygame.SCALED`. If you see this, you're on pygame 1.x and the version check failed somehow.

## License

**All Rights Reserved.** See [LICENSE](LICENSE) for full terms.

Copyright (c) 2026 TheCodingSoldier. Unauthorized copying, modification, distribution, or forking of this project is strictly prohibited without written permission from the copyright holder.
