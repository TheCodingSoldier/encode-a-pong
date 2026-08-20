#!/usr/bin/env python3
"""
Encode-A-Pong — Pong controlled by mouse scroll wheel.
Optimized for Raspberry Pi Zero 2 W + Kuman 3.5" display (480x320).

Requires: python3-pygame
Run: python3 pong.py
"""

import pygame
import sys
import random

WIDTH, HEIGHT = 480, 320
FPS = 30
PADDLE_W, PADDLE_H = 8, 50
BALL_SIZE = 8
WIN_SCORE = 7

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)


def main():
    pygame.init()
    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF
    )
    pygame.display.set_caption("Encode-A-Pong")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)

    player_paddle = pygame.Rect(10, HEIGHT // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H)
    ai_paddle = pygame.Rect(
        WIDTH - 10 - PADDLE_W, HEIGHT // 2 - PADDLE_H // 2, PADDLE_W, PADDLE_H
    )
    ball = pygame.Rect(
        WIDTH // 2 - BALL_SIZE // 2, HEIGHT // 2 - BALL_SIZE // 2, BALL_SIZE, BALL_SIZE
    )

    bvx = random.choice([-3, 3])
    bvy = random.choice([-2, 2])
    pscore = 0
    ascore = 0
    game_over = False
    scroll_accum = 0

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
                    ball.center = (WIDTH // 2, HEIGHT // 2)
                    bvx = random.choice([-3, 3])
                    bvy = random.choice([-2, 2])
            elif event.type == pygame.MOUSEWHEEL:
                scroll_accum += event.y

        if not game_over:
            # Apply accumulated scroll to paddle (handles fast multi-tick scrolls)
            if scroll_accum != 0:
                player_paddle.y -= scroll_accum * 12
                scroll_accum = 0
                if player_paddle.y < 0:
                    player_paddle.y = 0
                elif player_paddle.y > HEIGHT - PADDLE_H:
                    player_paddle.y = HEIGHT - PADDLE_H

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
                ball.center = (WIDTH // 2, HEIGHT // 2)
                bvx = random.choice([-3, 3])
                bvy = random.choice([-2, 2])
            elif ball.right >= WIDTH:
                pscore += 1
                ball.center = (WIDTH // 2, HEIGHT // 2)
                bvx = random.choice([-3, 3])
                bvy = random.choice([-2, 2])

            # AI tracks ball
            if ai_paddle.centery < ball.centery:
                ai_paddle.y += 2
            elif ai_paddle.centery > ball.centery:
                ai_paddle.y -= 2
            ai_paddle.y = max(0, min(ai_paddle.y, HEIGHT - PADDLE_H))

            if pscore >= WIN_SCORE or ascore >= WIN_SCORE:
                game_over = True

        screen.fill(BLACK)

        # Dashed center line
        for y in range(0, HEIGHT, 16):
            pygame.draw.rect(screen, WHITE, (WIDTH // 2 - 1, y, 2, 8))

        pygame.draw.rect(screen, WHITE, player_paddle)
        pygame.draw.rect(screen, WHITE, ai_paddle)
        pygame.draw.rect(screen, WHITE, ball)

        score_surf = font.render(f"{pscore}  {ascore}", True, WHITE)
        screen.blit(score_surf, (WIDTH // 2 - score_surf.get_width() // 2, 10))

        if game_over:
            winner = "YOU WIN!" if pscore >= WIN_SCORE else "CPU WINS"
            w_surf = font.render(winner, True, GREEN)
            screen.blit(w_surf, (WIDTH // 2 - w_surf.get_width() // 2, HEIGHT // 2 - 20))
            r_surf = small_font.render("Press R to restart", True, WHITE)
            screen.blit(r_surf, (WIDTH // 2 - r_surf.get_width() // 2, HEIGHT // 2 + 20))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
