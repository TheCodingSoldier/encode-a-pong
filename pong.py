#!/usr/bin/env python3
"""
Encode-A-Pong — Pong controlled by mouse scroll wheel.
Optimized for Raspberry Pi Zero 2 W + Kuman 3.5" display (480x320),
but also runs on any desktop (Windows, macOS, Linux) with a scroll wheel mouse.

Target: Raspberry Pi OS (Debian Trixie), Pi Zero 2 W (1 GHz ARM Cortex-A53).
Pygame >= 2.0.0 recommended (uses SCALED + vsync; falls back gracefully
on older versions).

Requires: python3-pygame
Run (Pi default):        python3 pong.py
Run (custom display):    python3 pong.py --width 800 --height 480
Run (desktop 60fps):     python3 pong.py --fps 60
"""

import sys
import os
import random
import argparse
import pygame

# ---------------------------------------------------------------------------
# CLI arguments — all defaults match original Pi values so existing usage
# is completely unaffected. Passing no arguments = identical behaviour.
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Encode-A-Pong")
    parser.add_argument("--width",  type=int, default=480,
                        help="Display width  in pixels (default: 480)")
    parser.add_argument("--height", type=int, default=320,
                        help="Display height in pixels (default: 320)")
    parser.add_argument("--fps",    type=int, default=30,
                        help="Target frame rate (default: 30)")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Configuration — gameplay constants (unchanged from original)
# ---------------------------------------------------------------------------
PADDLE_W, PADDLE_H = 8, 50
BALL_SIZE = 8
WIN_SCORE = 7
PADDLE_SPEED = 12              # Pixels per scroll tick
AI_SPEED = 2                   # AI paddle max pixels per frame
BALL_SPEED_X = 3
BALL_SPEED_Y = 2
MIN_BALL_VY = 1                # Prevents ball from going perfectly horizontal
SERVE_DELAY_MS = 800           # Pause before ball launches after a score

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)


def is_pi_framebuffer():
    """Return True when running on a Raspberry Pi framebuffer display.
    Detected by the presence of /dev/fb0 (Linux framebuffer device).
    On Windows / macOS / desktop Linux this will always return False."""
    return os.path.exists("/dev/fb0")


def make_bg_surface(width, height):
    """Pre-render the static background (center line + black fill) once.
    Blitting a cached surface every frame is far cheaper than redrawing
    primitives each tick — the single biggest pygame optimization for
    low-power hardware."""
    bg = pygame.Surface((width, height)).convert()
    bg.fill(BLACK)
    for y in range(0, height, 16):
        pygame.draw.rect(bg, WHITE, (width // 2 - 1, y, 2, 8))
    return bg


def reset_ball(width, height):
    """Return a fresh ball rect and random velocities.
    Guarantees non-zero vertical velocity so the ball never goes
    perfectly horizontal."""
    ball = pygame.Rect(
        width  // 2 - BALL_SIZE // 2,
        height // 2 - BALL_SIZE // 2,
        BALL_SIZE,
        BALL_SIZE,
    )
    bvx = random.choice([-BALL_SPEED_X, BALL_SPEED_X])
    bvy = random.choice([-BALL_SPEED_Y, BALL_SPEED_Y])
    if bvy == 0:
        bvy = MIN_BALL_VY
    return ball, bvx, bvy


def init_display(width, height):
    """Initialize the display with the best available mode.

    Tries SCALED + vsync first (pygame >= 2.0.0), falls back to
    SCALED alone, then to plain set_mode(). The game always starts.
    This fallback chain is identical to the original — no behaviour
    change on the Pi."""
    if pygame.version.vernum >= (2, 0, 0):
        try:
            screen = pygame.display.set_mode(
                (width, height), pygame.SCALED, vsync=1
            )
        except (pygame.error, TypeError):
            try:
                screen = pygame.display.set_mode(
                    (width, height), pygame.SCALED
                )
            except pygame.error:
                screen = pygame.display.set_mode((width, height))
    else:
        screen = pygame.display.set_mode((width, height))
    return screen


def clamp_paddle(paddle, height):
    """Keep a paddle rect within the screen bounds."""
    if paddle.y < 0:
        paddle.y = 0
    elif paddle.y > height - PADDLE_H:
        paddle.y = height - PADDLE_H


def bounce_ball(ball, paddle, bvx, bvy, is_player):
    """Handle ball-paddle collision: reverse x velocity, angle the ball
    based on where it hit the paddle, and push the ball outside the
    paddle to prevent it from getting stuck inside (tunneling/sticking).
    Logic is identical to the original — not changed."""
    hit = (ball.centery - paddle.centery) / (PADDLE_H / 2)
    hit = max(-1.0, min(1.0, hit))

    bvx = -bvx
    bvy = int(hit * 3)
    if abs(bvy) < MIN_BALL_VY:
        bvy = MIN_BALL_VY if bvy >= 0 else -MIN_BALL_VY

    if is_player:
        ball.x = paddle.right + 1
    else:
        ball.x = paddle.left - BALL_SIZE - 1

    return bvx, bvy


def run(width, height, fps):
    pygame.init()

    # Paddle X positions depend on width — must be calculated after args parsed
    player_paddle_x = 10
    ai_paddle_x     = width - 10 - PADDLE_W

    screen = init_display(width, height)
    pygame.display.set_caption("Encode-A-Pong")

    # Hide cursor on Pi framebuffer; show it on desktop so the OS cursor
    # doesn't disappear while the game window is open.
    pygame.mouse.set_visible(not is_pi_framebuffer())

    clock = pygame.time.Clock()
    font       = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)

    bg_surface = make_bg_surface(width, height)

    pygame.event.set_allowed(
        [pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEWHEEL]
    )

    r_text = small_font.render("Press R to restart", True, WHITE)

    player_paddle = pygame.Rect(player_paddle_x, height // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H)
    ai_paddle     = pygame.Rect(ai_paddle_x,     height // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H)
    ball, bvx, bvy = reset_ball(width, height)

    pscore     = 0
    ascore     = 0
    game_over  = False
    scroll_accum = 0.0

    # Use absolute timestamps for serve delay — avoids dt spike issues
    # on slower machines or first frame. 0 means ball is live immediately.
    serve_until = 0

    last_score = (-1, -1)
    score_surf = None

    while True:
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_r and game_over:
                    pscore = ascore = 0
                    game_over    = False
                    ball, bvx, bvy = reset_ball(width, height)
                    serve_until  = now + SERVE_DELAY_MS
                    last_score   = (-1, -1)
            elif event.type == pygame.MOUSEWHEEL:
                scroll_accum += getattr(event, "preciseY", event.y)

        if not game_over:
            # round() preserves small fractional scroll inputs that int()
            # would silently drop, making the paddle feel more responsive.
            if scroll_accum != 0:
                player_paddle.y -= round(scroll_accum * PADDLE_SPEED)
                scroll_accum = 0.0
                clamp_paddle(player_paddle, height)

            if now < serve_until:
                pass  # ball is frozen during serve delay
            else:
                ball.x += bvx
                ball.y += bvy

                if ball.top <= 0:
                    ball.top = 0
                    bvy = -bvy
                elif ball.bottom >= height:
                    ball.bottom = height
                    bvy = -bvy

                if ball.colliderect(player_paddle) and bvx < 0:
                    bvx, bvy = bounce_ball(ball, player_paddle, bvx, bvy, is_player=True)
                elif ball.colliderect(ai_paddle) and bvx > 0:
                    bvx, bvy = bounce_ball(ball, ai_paddle, bvx, bvy, is_player=False)

                if ball.left <= 0:
                    ascore += 1
                    ball, bvx, bvy = reset_ball(width, height)
                    serve_until = now + SERVE_DELAY_MS
                elif ball.right >= width:
                    pscore += 1
                    ball, bvx, bvy = reset_ball(width, height)
                    serve_until = now + SERVE_DELAY_MS

                if ai_paddle.centery < ball.centery:
                    ai_paddle.y += AI_SPEED
                elif ai_paddle.centery > ball.centery:
                    ai_paddle.y -= AI_SPEED
                clamp_paddle(ai_paddle, height)

                if pscore >= WIN_SCORE or ascore >= WIN_SCORE:
                    game_over = True

        screen.blit(bg_surface, (0, 0))
        pygame.draw.rect(screen, WHITE, player_paddle)
        pygame.draw.rect(screen, WHITE, ai_paddle)

        if now >= serve_until or game_over:
            pygame.draw.rect(screen, WHITE, ball)

        if (pscore, ascore) != last_score:
            score_surf = font.render(f"{pscore}  {ascore}", True, WHITE)
            last_score = (pscore, ascore)
        screen.blit(score_surf, (width // 2 - score_surf.get_width() // 2, 10))

        if game_over:
            winner = "YOU WIN!" if pscore >= WIN_SCORE else "CPU WINS"
            w_surf = font.render(winner, True, GREEN)
            screen.blit(w_surf, (width  // 2 - w_surf.get_width()  // 2, height // 2 - 20))
            screen.blit(r_text,  (width  // 2 - r_text.get_width()  // 2, height // 2 + 20))

        # display.update() is optimized for software framebuffer displays
        # (per pygame docs). Functionally identical to flip() with no args,
        # but the recommended path for the Pi's framebuffer driver.
        pygame.display.update()
        clock.tick(fps)


def main():
    args = parse_args()
    try:
        run(args.width, args.height, args.fps)
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
