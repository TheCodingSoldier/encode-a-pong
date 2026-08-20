# Encode-A-Pong — Technical Documentation

Detailed documentation for developers and tinkerers. If you just want to play, see the [README](README.md).

---

## Architecture Overview

The game is a single-file Python script (`pong.py`) using pygame. No external assets, no dependencies beyond `python3-pygame`. Everything is drawn at runtime.

```
Encoder (GPIO20/21) → uinput kernel module → /dev/input/eventX
    → SDL2 event queue → pygame.MOUSEWHEEL events → paddle movement
```

The encoder presents as a system mouse scroll wheel. Pygame reads `MOUSEWHEEL` events natively. No GPIO polling, no custom input drivers, no `evdev` hacks.

---

## Display Initialization

`init_display()` uses a triple-fallback strategy to work on any Pi display setup:

```
pygame.version.vernum >= (2, 0, 0)?
  ├─ YES → try SCALED + vsync=1
  │        ├─ success → best mode (hardware scaling, vsync, no tearing)
  │        ├─ TypeError → try SCALED alone (vsync param not supported)
  │        │              ├─ success → scaled, no vsync
  │        │              └─ pygame.error → plain set_mode() (framebuffer rejected SCALED)
  │        └─ pygame.error → try SCALED alone (same fallback as above)
  └─ NO  → plain set_mode() (pygame 1.x: SCALED doesn't exist)
```

### Why not HWSURFACE?

`HWSURFACE` has been non-functional since Pygame 2.0.0. The pygame docs explicitly state it should no longer be used. `SCALED` is the modern replacement — it provides hardware-accelerated scaling and works with `vsync=1` to synchronize to the display refresh.

### Why not force 16-bit depth?

The pygame docs' golden rule: "allow Pygame to choose the optimal bit depth, as requesting unsupported modes may force emulation and degrade performance." The code uses `depth=0` (the default), which lets pygame match the system's native framebuffer format. Forcing `depth=16` on a 32-bit driver would add a per-blit format conversion — making the game slower.

### Why `display.update()` instead of `display.flip()`?

Both are functionally identical when `update()` is called with no arguments. However, the pygame docs state that `display.update()` is "optimized for software displays" — which is exactly what the Pi's framebuffer is. It's the documented-correct function for this hardware.

---

## Rendering Pipeline

### Pre-rendered Background Surface

The black fill + dashed center line is drawn once into a cached `pygame.Surface` at startup, with `.convert()` called to match the display's pixel format. Each frame, this surface is blitted as a single operation:

```python
bg_surface = make_bg_surface()  # once at startup
screen.blit(bg_surface, (0, 0))  # one blit per frame
```

This replaces what would otherwise be `screen.fill(BLACK)` plus a 20-iteration `for` loop calling `pygame.draw.rect()` every frame. On a 1 GHz single-core ARM, eliminating 20 function calls per frame is a meaningful saving.

### Score Text Caching

The score surface is only re-rendered when the score actually changes:

```python
if (pscore, ascore) != last_score:
    score_surf = font.render(f"{pscore}  {ascore}", True, WHITE)
    last_score = (pscore, ascore)
screen.blit(score_surf, ...)
```

`font.render()` is one of the most expensive pygame operations. At 30 FPS with no caching, that's 30 renders per second for text that changes maybe once every 10-20 seconds.

### Pre-rendered Static Text

The "Press R to restart" text is rendered once at startup and reused every frame:

```python
r_text = small_font.render("Press R to restart", True, WHITE)  # once
```

### Ball Hidden During Serve Delay

When the ball is waiting at center after a score, the `draw.rect` call for the ball is skipped entirely:

```python
if serve_timer <= 0 or game_over:
    pygame.draw.rect(screen, WHITE, ball)
```

### Why Not Dirty Rects?

Dirty rect updates (`display.update(rect_list)`) only refresh changed regions instead of the full screen. The pygame newbieguide says this is "generally unnecessary for most modern 2D games" and that modern hardware can "refresh the entire display at 60 FPS or higher using `display.flip()`."

On the Pi Zero 2 W at 30 FPS on a 480×320 screen (153,600 pixels), a full-screen blit is trivial. Dirty rects would require:
- Tracking previous positions of every object each frame
- Blitting background over old positions to erase them
- Computing the union of old + new rects
- Passing the rect list to `display.update()`

This adds ~40 lines of rect-tracking complexity for ~1-2% CPU savings and a real risk of visual artifacts (ghost trails, missed updates). The tradeoff is not worth it for this hardware.

---

## Event Handling

### Event Filtering

```python
pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEWHEEL])
```

The pygame event queue holds approximately 128 events. By default, every event type is allowed — `MOUSEMOTION`, `ACTIVEEVENT`, `WINDOWEXPOSED`, `TEXTINPUT`, etc. On the Pi, `MOUSEMOTION` events can flood the queue if a physical mouse is connected, causing `MOUSEWHEEL` events from the encoder to be dropped during fast spins.

Blocking all unused event types ensures `MOUSEWHEEL` events always reach the game loop.

### Scroll Accumulation Buffer

```python
elif event.type == pygame.MOUSEWHEEL:
    scroll_accum += getattr(event, "preciseY", event.y)
```

Multiple `MOUSEWHEEL` events can arrive within a single frame (the encoder can spin faster than 30 FPS). Instead of applying each one immediately, they're accumulated into a float and applied once:

```python
if scroll_accum != 0:
    player_paddle.y -= int(scroll_accum * PADDLE_SPEED)
    scroll_accum = 0.0
```

`preciseY` (float, pygame >= 2.1.3) gives sub-tick precision. On older pygame builds, it falls back to `y` (integer) via `getattr`.

---

## Collision Physics

### Tunneling Prevention

The most common pygame Pong bug: the ball gets stuck inside the paddle, bouncing back and forth within the paddle rect for multiple frames.

**Root cause:** `colliderect()` detects overlap, velocity is reversed, but the ball is still inside the paddle next frame. It collides again, reverses again, and oscillates.

**Fix:** After reversing velocity, the ball is physically repositioned outside the paddle:

```python
if is_player:
    ball.x = paddle.right + 1    # push to right edge of player paddle
else:
    ball.x = paddle.left - BALL_SIZE - 1  # push to left edge of AI paddle
```

This is more robust than the "hit flag" pattern from the official pygame Pong tutorial, which uses a boolean toggle to prevent re-collision. The flag approach can desync if the ball moves fast enough to clear the paddle in one frame (flag stays set, next legitimate collision is skipped).

### Wall Bounce Repositioning

```python
if ball.top <= 0:
    ball.top = 0      # snap to exact top edge
    bvy = -bvy
elif ball.bottom >= HEIGHT:
    ball.bottom = HEIGHT  # snap to exact bottom edge
    bvy = -bvy
```

Without repositioning, floating-point drift over many bounces can cause the ball to gradually sink into the wall. Snapping to the exact edge prevents this.

### Hit Angle Calculation

```python
hit = (ball.centery - paddle.centery) / (PADDLE_H / 2)
hit = max(-1.0, min(1.0, hit))  # clamp to [-1, 1]
bvy = int(hit * 3)
```

- `hit = -1`: ball hit the top edge of the paddle → sharp upward angle
- `hit = 0`: ball hit the center → straight horizontal bounce
- `hit = 1`: ball hit the bottom edge → sharp downward angle

The clamp prevents extreme velocities if the ball somehow hits beyond the paddle edges.

### Minimum Vertical Velocity

```python
MIN_BALL_VY = 1
```

If the ball hits the exact center of the paddle, `hit = 0`, so `bvy = int(0 * 3) = 0`. The ball would travel perfectly horizontally forever — making the game unwinnable if the AI paddle was aligned. `MIN_BALL_VY` enforces at least 1 pixel/frame of vertical movement.

This is checked in both `reset_ball()` (initial serve) and `bounce_ball()` (paddle hits).

### Direction-Guarded Collisions

```python
if ball.colliderect(player_paddle) and bvx < 0:   # ball moving LEFT
elif ball.colliderect(ai_paddle) and bvx > 0:       # ball moving RIGHT
```

The player paddle (left side) only bounces the ball when it's moving left (`bvx < 0`). The AI paddle (right side) only bounces when the ball is moving right (`bvx > 0`). This prevents double-bounces if the ball somehow overlaps both paddles or re-enters a paddle after a bounce.

---

## Frame Timing

```python
dt = clock.tick(FPS)  # caps at 30 FPS AND returns elapsed milliseconds
```

`clock.tick(30)` does two things:
1. **Caps the framerate** at 30 FPS by calling `SDL_Delay()` — which yields CPU time to the OS between frames, keeping the Pi responsive.
2. **Returns the elapsed milliseconds** since the last call — used directly as `dt` for the serve timer.

This is the standard pygame idiom from the official newbieguide. No separate `get_time()` or `get_fps()` calls needed.

### Serve Delay

After a score, the ball pauses at center for 800ms before launching:

```python
if serve_timer > 0:
    serve_timer -= dt  # count down using frame delta
else:
    ball.x += bvx     # ball only moves when timer expires
    ball.y += bvy
```

This gives the player time to reposition after a score. The ball is hidden during the delay for a clean visual reset.

---

## Shutdown Handling

```python
def main():
    try:
        run()
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()
    sys.exit(0)
```

`run()` contains the game loop and uses bare `return` to exit cleanly (on QUIT or ESC). `main()` wraps it in a `try/except/finally` that guarantees `pygame.quit()` is always called — even on `Ctrl+C` (SIGINT from SSH), an uncaught exception, or a normal return.

Without this, interrupting the game via `Ctrl+C` in a terminal would dump a Python traceback and potentially leave the Pi's display in a bad state (SDL not properly deinitialized, input grab not released).

---

## Memory Usage

| Object | 32-bit (worst case) | 16-bit (likely Pi TFT) |
|---|---|---|
| Display surface (480×320) | 600 KB | 300 KB |
| Background surface (cached) | 600 KB | 300 KB |
| Built-in font (shared, both sizes) | 8.4 KB | 8.4 KB |
| Score text surface (1, cached) | 7 KB | 3.5 KB |
| "Press R" text (pre-rendered once) | 10.2 KB | 5.1 KB |
| Winner text (transient, GC'd) | 10.5 KB | 5.3 KB |
| Game state (Rects, ints, floats) | 0.5 KB | 0.5 KB |
| **Total** | **1.2 MB** | **0.6 MB** |

Pi Zero 2 W has 512 MB RAM. The game uses **0.23%** worst case (32-bit) or **0.12%** (16-bit). No RAM optimization is needed or possible without removing required surfaces.

---

## Code Structure

| Function | Purpose |
|---|---|
| `make_bg_surface()` | Pre-renders black fill + dashed center line into a cached Surface with `.convert()` |
| `reset_ball()` | Returns a fresh ball Rect with randomized velocities, guarantees non-zero vertical velocity |
| `init_display()` | Version-guarded triple-fallback display initialization (SCALED+vsync → SCALED → plain) |
| `clamp_paddle(paddle)` | Clamps a paddle Rect to screen bounds (0 to HEIGHT-PADDLE_H) |
| `bounce_ball(ball, paddle, bvx, bvy, is_player)` | Collision response: reverses x velocity, calculates angle from hit position, repositions ball outside paddle |
| `run()` | Main game loop: event handling, physics, rendering |
| `main()` | Entry point: wraps `run()` in exception handling for clean shutdown |

---

## Tunable Constants

All game parameters are at the top of `pong.py`:

| Constant | Default | Effect |
|---|---|---|
| `WIDTH, HEIGHT` | 480, 320 | Screen resolution (matches Kuman 3.5") |
| `FPS` | 30 | Frame rate cap (yields CPU between frames) |
| `PADDLE_W, PADDLE_H` | 8, 50 | Paddle dimensions in pixels |
| `BALL_SIZE` | 8 | Ball dimensions in pixels (square) |
| `WIN_SCORE` | 7 | Points needed to win |
| `PADDLE_SPEED` | 12 | Pixels moved per scroll tick |
| `AI_SPEED` | 2 | AI paddle max pixels per frame (lower = easier) |
| `BALL_SPEED_X` | 3 | Ball horizontal speed |
| `BALL_SPEED_Y` | 2 | Ball vertical speed (base, modified by hit angle) |
| `MIN_BALL_VY` | 1 | Minimum vertical velocity (prevents horizontal-only ball) |
| `SERVE_DELAY_MS` | 800 | Milliseconds before ball launches after a score |

---

## Optional: CPU Governor Tuning

The Pi Zero 2 W defaults to the `ondemand` CPU governor, which scales clock speed based on load. This can cause brief latency spikes when the CPU ramps up from idle. For perfectly consistent frame pacing, switch to `performance` mode:

```bash
sudo sh -c "echo performance > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor"
```

This is optional — the game runs fine on `ondemand`. To revert:

```bash
sudo sh -c "echo ondemand > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor"
```

---

## Version Compatibility

| Pygame Version | Display Mode | Notes |
|---|---|---|
| >= 2.0.0 | SCALED + vsync=1 (best) | Hardware scaling, vsync, no tearing |
| >= 2.0.0 (no vsync support) | SCALED alone | Hardware scaling, no vsync |
| >= 2.0.0 (framebuffer rejects SCALED) | plain set_mode() | Always works |
| < 2.0.0 (pygame 1.x) | plain set_mode() | SCALED doesn't exist, handled by vernum check |

The `pygame.version.vernum >= (2, 0, 0)` check prevents `AttributeError` on pygame 1.x. The `TypeError` catch handles pygame 2.x builds that don't support the `vsync` parameter.
