# Encode-A-Pong

Pong controlled by a rotary encoder. Built for Raspberry Pi Zero 2 W.

## Quick Start

```bash
# 1. Install pygame
sudo apt install python3-pygame

# 2. Download the game
git clone https://github.com/TheCodingSoldier/encode-a-pong.git

# 3. Play
cd encode-a-pong
python3 pong.py
```

That's it. Scroll your encoder to move the paddle.

## Controls

| Action | Input |
|---|---|
| Move paddle | Scroll wheel up / down |
| Restart | Press `R` |
| Quit | Press `ESC` or `Ctrl+C` |

## How It Works

Your rotary encoder is already configured as a system scroll wheel via `uinput`. This game reads `pygame.MOUSEWHEEL` events — the same events your encoder produces. No custom drivers, no GPIO polling, no code changes needed.

## Hardware

- **Board:** Raspberry Pi Zero 2 W
- **OS:** Raspberry Pi OS (Debian Trixie)
- **Display:** Kuman 3.5" touchscreen (480x320)
- **Input:** Rotary encoder → `uinput` scroll wheel (A=GPIO20, B=GPIO21, Switch=GPIO6)

## Troubleshooting

**Blank screen?** Run from the desktop, not headless. If using Pi OS Lite, enable KMS: `sudo raspi-config` → Advanced → GL Driver → GL (Fake KMS).

**Encoder not moving the paddle?** Check your `uinput` service is running:
```bash
sudo evtest /dev/input/eventX
```
Scroll the encoder — you should see events.

**`Ctrl+C` left the terminal weird?** Fixed — the game always calls `pygame.quit()` on exit.

## Technical Docs

For architecture details, optimization explanations, collision physics, memory analysis, and tunable constants, see [DOCUMENTATION.md](DOCUMENTATION.md).

## License

**All Rights Reserved.** See [LICENSE](LICENSE).

Copyright (c) 2026 TheCodingSoldier. No copying, modification, distribution, or forking without written permission.
