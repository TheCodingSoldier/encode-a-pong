#!/usr/bin/env python3
"""
Encode-A-Pong — Pong controlled by mouse scroll wheel.
Optimized for Raspberry Pi Zero 2 W + Kuman 3.5" display (480x320).

Target: Raspberry Pi OS (Debian Trixie), Pi Zero 2 W (1 GHz ARM Cortex-A53).
Pygame >= 2.0.0 (HWSURFACE is non-functional since 2.0; use SCALED + vsync).

Requires: python3-pygame
Run: python3 pong.py
"""

import os
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
PADDLE_SPEED = 12
AI_SPEED = 2
BALL_SPEED_X = 3
BALL_SPEED_Y = 2

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)


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
    """Return a fresh ball rect and random velocities."""
    ball = pygame.Rect(
        WIDTH // 2 - BALL_SIZE // 2,
        HEIGHT // 2 - BALL_SIZE // 2,
        BALL_SIZE,
        BALL_SIZE,
    )
    bvx = random.choice([-BALL_SPEED_X, BALL_SPEED_X])
    bvy = random.choice([-BALL_SPEED_Y, BALL_SPEED_Y])
    return ball, bvx, bvy


def main():
    pygame.init()

    # Pygame >= 2.0: HWSURFACE is non-functional. Use SCALED + vsync=1
    # for a hardware-friendly path on the Pi framebuffer. vsync syncs
    # to the display refresh, eliminating tearing and saving CPU cycles.
    try:
        screen = pygame.display.set_mode(
            (WIDTH, HEIGHT), pygame.SCALED, vsync=1
        )
    except pygame.error:
        # Fallback for framebuffer setups that reject SCALED
        screen = pygame.display.set_mode((WIDTH, HEIGHT))

    pygame.display.set_caption("Encode-A-Pong")
    pygame.mouse.set_visible(False)

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)

    # Pre-render static background surface (one blit replaces fill + loop)
    bg_surface = make_bg_surface()

    # Block all event types except the three we actually use.
    # This prevents the ~128-event queue from filling with junk
    # (MOUSEMOTION, ACTIVEEVENT, etc.) and dropping MOUSEWHEEL on
    # fast encoder rotation.
    pygame.event.set_allowed(
        [pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEWHEEL]
    )

    # Pre-render static "Press R to restart" text
    r_text = small_font.render("Press R to restart", True, WHITE)

    # Game state
    player_paddle = pygame.Rect(10, HEIGHT // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H)
    ai_paddle = pygame.Rect(
        WIDTH - 10 - PADDLE_W, HEIGHT // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H
    )
    ball, bvx, bvy = reset_ball()
    pscore = 0
    ascore = 0
    game_over = False
    scroll_accum = 0.0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_r and game_over:
                    pscore = ascore = 0
                    game_over = False
                    ball, bvx, bvy = reset_ball()
            elif event.type == pygame.MOUSEWHEEL:
                # preciseY (float, pygame >= 2.1.3) gives sub-tick precision.
                # Falls back to y (int) on older builds. Accumulate so
                # multi-tick spins within one frame are not lost.
                scroll_accum += getattr(event, "preciseY", event.y)

        if not game_over:
            # Apply accumulated scroll to paddle
            if scroll_accum != 0:
                player_paddle.y -= int(scroll_accum * PADDLE_SPEED)
                scroll_accum = 0.0
                if player_paddle.y < 0:
                    player_paddle.y = 0
                elif player_paddle.y > HEIGHT - PADDLE_H:
                    player_paddle.y = HEIGHT - PADDLE_H

            # Ball physics
            ball.x += bvx
            ball.y += bvy

            if ball.top <= 0 or ball.bottom >= HEIGHT:
                bvy = -bvy

            if ball.colliderect(player_paddle) and bvx < 0:
                bvx = -bvx
                hit = (ball.centery - player_paddle.centery) / (PADDLE_H / 2)
                bvy = int(hit * 3)
            elif ball.colliderect(ai_paddle) and bvx > 0:
                bvx = -bvx
                hit = (ball.centery - ai_paddle.centery) / (PADDLE_H / 2)
                bvy = int(hit * 3)

            if ball.left <= 0:
                ascore += 1
                ball, bvx, bvy = reset_ball()
            elif ball.right >= WIDTH:
                pscore += 1
                ball, bvx, bvy = reset_ball()

            # AI tracking with speed cap
            if ai_paddle.centery < ball.centery:
                ai_paddle.y += AI_SPEED
            elif ai_paddle.centery > ball.centery:
                ai_paddle.y -= AI_SPEED
            ai_paddle.y = max(0, min(ai_paddle.y, HEIGHT - PADDLE_H))

            if pscore >= WIN_SCORE or ascore >= WIN_SCORE:
                game_over = True

        # ---- Render ----
        screen.blit(bg_surface, (0, 0))
        pygame.draw.rect(screen, WHITE, player_paddle)
        pygame.draw.rect(screen, WHITE, ai_paddle)
        pygame.draw.rect(screen, WHITE, ball)

        score_surf = font.render(f"{pscore}  {ascore}", True, WHITE)
        screen.blit(score_surf, (WIDTH // 2 - score_surf.get_width() // 2, 10))

        if game_over:
            winner = "YOU WIN!" if pscore >= WIN_SCORE else "CPU WINS"
            w_surf = font.render(winner, True, GREEN)
            screen.blit(w_surf, (WIDTH // 2 - w_surf.get_width() // 2, HEIGHT // 2 - 20))
            screen.blit(r_text, (WIDTH // 2 - r_text.get_width() // 2, HEIGHT // 2 + 20))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
