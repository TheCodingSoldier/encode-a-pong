#!/usr/bin/env python3
"""
Encode-A-Pong — Pong controlled by mouse scroll wheel.
Optimized for Raspberry Pi Zero 2 W + Kuman 3.5" display (480x320).

Target: Raspberry Pi OS (Debian Trixie), Pi Zero 2 W (1 GHz ARM Cortex-A53).
Pygame >= 2.0.0 recommended (uses SCALED + vsync; falls back gracefully
on older versions).

Requires: python3-pygame
Run: python3 pong.py
"""

import sys
import random
import pygame

# ---------------------------------------------------------------------------
# Configuration — tuned for Pi Zero 2 W + Kuman 3.5" (480x320) framebuffer
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 480, 320
FPS = 30
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

# Pre-calculated paddle edges (avoid repeated arithmetic in the loop)
PLAYER_PADDLE_X = 10
AI_PADDLE_X = WIDTH - 10 - PADDLE_W


def make_bg_surface():
    """Pre-render the static background (center line + black fill) once.
    Blitting a cached surface every frame is far cheaper than redrawing
    primitives each tick — the single biggest pygame optimization for
    low-power hardware."""
    bg = pygame.Surface((WIDTH, HEIGHT)).convert()
    bg.fill(BLACK)
    for y in range(0, HEIGHT, 16):
        pygame.draw.rect(bg, WHITE, (WIDTH // 2 - 1, y, 2, 8))
    return bg


def reset_ball():
    """Return a fresh ball rect and random velocities.
    Guarantees non-zero vertical velocity so the ball never goes
    perfectly horizontal."""
    ball = pygame.Rect(
        WIDTH // 2 - BALL_SIZE // 2,
        HEIGHT // 2 - BALL_SIZE // 2,
        BALL_SIZE,
        BALL_SIZE,
    )
    bvx = random.choice([-BALL_SPEED_X, BALL_SPEED_X])
    bvy = random.choice([-BALL_SPEED_Y, BALL_SPEED_Y])
    if bvy == 0:
        bvy = MIN_BALL_VY
    return ball, bvx, bvy


def init_display():
    """Initialize the display with the best available mode for the Pi.

    Uses pygame.version.vernum to check for SCALED support (added in
    pygame 2.0.0) before attempting to use it. This avoids an
    AttributeError crash on pygame 1.x.

    Tries SCALED + vsync first, falls back to SCALED alone, then to
    plain set_mode(). The game always starts."""
    if pygame.version.vernum >= (2, 0, 0):
        try:
            screen = pygame.display.set_mode(
                (WIDTH, HEIGHT), pygame.SCALED, vsync=1
            )
        except (pygame.error, TypeError):
            try:
                screen = pygame.display.set_mode(
                    (WIDTH, HEIGHT), pygame.SCALED
                )
            except pygame.error:
                screen = pygame.display.set_mode((WIDTH, HEIGHT))
    else:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
    return screen


def clamp_paddle(paddle):
    """Keep a paddle rect within the screen bounds."""
    if paddle.y < 0:
        paddle.y = 0
    elif paddle.y > HEIGHT - PADDLE_H:
        paddle.y = HEIGHT - PADDLE_H


def bounce_ball(ball, paddle, bvx, bvy, is_player):
    """Handle ball-paddle collision: reverse x velocity, angle the ball
    based on where it hit the paddle, and push the ball outside the
    paddle to prevent it from getting stuck inside (tunneling/sticking)."""
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


def run():
    pygame.init()

    screen = init_display()
    pygame.display.set_caption("Encode-A-Pong")
    pygame.mouse.set_visible(False)

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)

    bg_surface = make_bg_surface()

    pygame.event.set_allowed(
        [pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEWHEEL]
    )

    r_text = small_font.render("Press R to restart", True, WHITE)

    player_paddle = pygame.Rect(PLAYER_PADDLE_X, HEIGHT // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H)
    ai_paddle = pygame.Rect(AI_PADDLE_X, HEIGHT // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H)
    ball, bvx, bvy = reset_ball()
    pscore = 0
    ascore = 0
    game_over = False
    scroll_accum = 0.0
    serve_timer = 0

    last_score = (-1, -1)
    score_surf = None
    dt = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_r and game_over:
                    pscore = ascore = 0
                    game_over = False
                    ball, bvx, bvy = reset_ball()
                    serve_timer = SERVE_DELAY_MS
                    last_score = (-1, -1)
            elif event.type == pygame.MOUSEWHEEL:
                scroll_accum += getattr(event, "preciseY", event.y)

        if not game_over:
            if scroll_accum != 0:
                player_paddle.y -= int(scroll_accum * PADDLE_SPEED)
                scroll_accum = 0.0
                clamp_paddle(player_paddle)

            if serve_timer > 0:
                serve_timer -= dt
            else:
                ball.x += bvx
                ball.y += bvy

                if ball.top <= 0:
                    ball.top = 0
                    bvy = -bvy
                elif ball.bottom >= HEIGHT:
                    ball.bottom = HEIGHT
                    bvy = -bvy

                if ball.colliderect(player_paddle) and bvx < 0:
                    bvx, bvy = bounce_ball(ball, player_paddle, bvx, bvy, is_player=True)
                elif ball.colliderect(ai_paddle) and bvx > 0:
                    bvx, bvy = bounce_ball(ball, ai_paddle, bvx, bvy, is_player=False)

                if ball.left <= 0:
                    ascore += 1
                    ball, bvx, bvy = reset_ball()
                    serve_timer = SERVE_DELAY_MS
                elif ball.right >= WIDTH:
                    pscore += 1
                    ball, bvx, bvy = reset_ball()
                    serve_timer = SERVE_DELAY_MS

                if ai_paddle.centery < ball.centery:
                    ai_paddle.y += AI_SPEED
                elif ai_paddle.centery > ball.centery:
                    ai_paddle.y -= AI_SPEED
                clamp_paddle(ai_paddle)

                if pscore >= WIN_SCORE or ascore >= WIN_SCORE:
                    game_over = True

        screen.blit(bg_surface, (0, 0))
        pygame.draw.rect(screen, WHITE, player_paddle)
        pygame.draw.rect(screen, WHITE, ai_paddle)

        if serve_timer <= 0 or game_over:
            pygame.draw.rect(screen, WHITE, ball)

        if (pscore, ascore) != last_score:
            score_surf = font.render(f"{pscore}  {ascore}", True, WHITE)
            last_score = (pscore, ascore)
        screen.blit(score_surf, (WIDTH // 2 - score_surf.get_width() // 2, 10))

        if game_over:
            winner = "YOU WIN!" if pscore >= WIN_SCORE else "CPU WINS"
            w_surf = font.render(winner, True, GREEN)
            screen.blit(w_surf, (WIDTH // 2 - w_surf.get_width() // 2, HEIGHT // 2 - 20))
            screen.blit(r_text, (WIDTH // 2 - r_text.get_width() // 2, HEIGHT // 2 + 20))

        # display.update() is optimized for software framebuffer displays
        # (per pygame docs). Functionally identical to flip() with no args,
        # but the recommended path for the Pi's framebuffer driver.
        pygame.display.update()
        dt = clock.tick(FPS)


def main():
    try:
        run()
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
