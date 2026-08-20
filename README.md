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

## Game Features

- First to 7 points wins
- Ball angles based on where it hits the paddle (center = straight, edges = sharp angle)
- 800ms serve delay after each score — ball pauses at center before launching
- AI opponent with speed-capped tracking (beatable but challenging)
- Ball is hidden during serve delay for a clean visual reset
- Ball never goes perfectly horizontal (minimum vertical velocity enforced)

## Optimization Details

Every optimization is specifically tuned for the Pi Zero 2 W's single-core ARM CPU and the Kuman 3.5" framebuffer:

### Display
- **`pygame.SCALED` + `vsync=1`** instead of the obsolete `HWSURFACE` flag (non-functional since Pygame 2.0.0). Vsync syncs to the display refresh, eliminating screen tearing and preventing wasted CPU cycles.
- **Triple fallback**: If `vsync` isn't supported (older pygame), falls back to `SCALED` alone. If `SCALED` is rejected by the Pi's framebuffer, falls back to plain `set_mode()`. The game always starts.
- **Mouse cursor hidden** — no cursor is needed since the encoder is the only input.

### Rendering
- **Pre-rendered background surface**: Black fill + dashed center line drawn once into a cached `Surface` with `.convert()`, blitted as a single operation each frame.
- **Pre-rendered static text**: "Press R to restart" rendered once at startup.
- **Score text caching**: Score is only re-rendered when it actually changes, not every frame.
- **Ball hidden during serve delay**: Skips a `draw.rect` call when ball is waiting to launch.
- **Minimal draw calls**: Only 3-4 `pygame.draw.rect()` calls per frame.
- **30 FPS cap** with `Clock.tick(30)` yields CPU time to the OS between frames.

### Event Handling
- **`pygame.event.set_allowed()`**: Blocks all event types except `QUIT`, `KEYDOWN`, and `MOUSEWHEEL`. Prevents the ~128-event queue from filling with junk and dropping scroll events during fast encoder spins.
- **Scroll accumulation buffer**: Multiple `MOUSEWHEEL` events within one frame are accumulated as a float and applied once.
- **Font objects created once** at startup.

### Collision Physics
- **Tunneling prevention**: After a paddle bounce, the ball is physically repositioned outside the paddle rect (`paddle.right + 1` for player, `paddle.left - BALL_SIZE - 1` for AI). This prevents the ball from getting stuck inside the paddle and bouncing repeatedly — a well-known pygame Pong bug documented in the official pygame tutorial and SDL forums.
- **Wall bounce repositioning**: Ball is snapped to the exact wall edge (`ball.top = 0` / `ball.bottom = HEIGHT`) on wall collisions, preventing it from sinking into the wall over multiple frames.
- **Hit angle clamping**: The hit position (-1 to +1) is clamped before calculating the bounce angle, preventing extreme velocity values.
- **Minimum vertical velocity**: `MIN_BALL_VY = 1` ensures the ball always has some vertical movement, preventing it from going perfectly horizontal and making the game unwinnable.
- **Direction-guarded collisions**: Player paddle only bounces when `bvx < 0` (ball moving left), AI paddle only when `bvx > 0` (ball moving right), preventing double-bounces.

### Code Structure
- `init_display()` — triple fallback display initialization.
- `reset_ball()` — centralized ball reset with velocity guarantees.
- `make_bg_surface()` — caches static background once.
- `clamp_paddle()` — reusable paddle bounds enforcement.
- `bounce_ball()` — collision response with repositioning and angle calculation.
- All tunable constants at the top of the file.

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
This should not happen with the current code — the `bounce_ball()` function repositions the ball outside the paddle on every collision. If you still see it, increase `BALL_SPEED_X` or `PADDLE_W`.

## License

**All Rights Reserved.** See [LICENSE](LICENSE) for full terms.

Copyright (c) 2026 TheCodingSoldier. Unauthorized copying, modification, distribution, or forking of this project is strictly prohibited without written permission from the copyright holder.
