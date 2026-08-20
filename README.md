# Encode-A-Pong

A lightweight Pong game controlled entirely by a **mouse scroll wheel** — built for the Raspberry Pi Zero 2 W with a rotary encoder mapped to scroll-wheel input via `uinput`.

## How It Works

This game reads `pygame.MOUSEWHEEL` events to move the player paddle up and down. No keyboard, no mouse cursor, no joystick — just the scroll wheel. It is a perfect match for a rotary encoder that has been configured as a system scroll-wheel device.

## Hardware

| Component | Spec |
|---|---|
| **Board** | Raspberry Pi Zero 2 W |
| **OS** | Raspberry Pi OS (Debian Trixie) |
| **Display** | Kuman 3.5" touchscreen (480x320) |
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

## Optimization Notes

- `HWSURFACE | DOUBLEBUF` display flags for hardware-accelerated rendering
- Capped at 30 FPS — smooth for Pong, light on the Pi Zero 2 W CPU
- No external image/font/audio assets — everything is drawn at runtime
- Scroll accumulation buffer handles fast multi-tick encoder rotations
- Minimal per-frame draw calls (3 rects + dashed line + text)

## License

**All Rights Reserved.** See [LICENSE](LICENSE) for full terms.

Copyright (c) 2026 TheCodingSoldier. Unauthorized copying, modification, distribution, or forking of this project is strictly prohibited without written permission from the copyright holder.
