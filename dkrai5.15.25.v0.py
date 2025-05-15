import pygame
import sys
import random

# Constants
WIDTH, HEIGHT = 512, 480  # NES resolution
FPS = 60
PLATFORM_HEIGHT = 8
PLAYER_SIZE = 20
LADDER_WIDTH = 8
LADDER_HEIGHT = 56
BARREL_SIZE = 16
BARREL_SPEED = 3
PLAYER_SPEED = 3
JUMP_POWER = 10
GRAVITY = 0.5

# NES Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (188, 24, 24)
BLUE = (48, 80, 188)
BROWN = (140, 80, 48)
YELLOW = (252, 188, 116)
PINK = (255, 160, 192)
DK_BROWN = (92, 48, 0)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Donkey Kong NES Clone (No Media)")
clock = pygame.time.Clock()

# Platform and ladder layout for NES style
def create_nes_level():
    platforms = []
    ladders = []
    # Platform: (x, y, width, steps, step_height, direction)
    plat_data = [
        (64, 80, 384, 8, 2, 1),    # Top (shortest, right up)
        (32, 144, 448, 16, 2, -1), # 2nd (left up)
        (64, 208, 384, 8, 2, 1),   # 3rd (right up)
        (32, 272, 448, 16, 2, -1), # 4th (left up)
        (64, 336, 384, 8, 2, 1),   # 5th (right up)
        (32, 400, 448, 16, 2, -1), # Bottom (left up)
    ]
    for x, y, w, steps, step_h, direction in plat_data:
        # Simulate slant by stepping
        for s in range(steps):
            sx = x + (w // steps) * s
            sy = y + direction * step_h * s
            sw = w // steps
            platforms.append(pygame.Rect(sx, sy, sw, PLATFORM_HEIGHT))
    # Ladders: (x, y, height, broken)
    ladder_data = [
        (120, 80, 64, False), (248, 80, 64, True), (384, 80, 64, False),
        (64, 144, 64, False), (192, 144, 64, True), (320, 144, 64, False), (448, 144, 64, False),
        (120, 208, 64, False), (248, 208, 64, True), (384, 208, 64, False),
        (64, 272, 64, False), (192, 272, 64, True), (320, 272, 64, False), (448, 272, 64, False),
        (120, 336, 64, False), (248, 336, 64, True), (384, 336, 64, False),
        (64, 400, 64, False), (192, 400, 64, True), (320, 400, 64, False), (448, 400, 64, False),
    ]
    for x, y, h, broken in ladder_data:
        if broken:
            ladders.append({'rect': pygame.Rect(x, y + h//2, LADDER_WIDTH, h//2), 'broken': True})
        else:
            ladders.append({'rect': pygame.Rect(x, y, LADDER_WIDTH, h), 'broken': False})
    return platforms, ladders

platforms, ladders = create_nes_level()

# Player at bottom left
player = pygame.Rect(40, 400 - PLAYER_SIZE, PLAYER_SIZE, PLAYER_SIZE)
player_vel_y = 0
on_ground = False
on_ladder = False

# Pauline (goal) at top right
goal = pygame.Rect(400, 60, 20, 24)

# Donkey Kong at top left
dk_rect = pygame.Rect(64, 40, 32, 32)

# Barrels
barrels = []
barrel_timer = 0

# Barrel path: which y-levels to drop at
barrel_drop_ys = [144, 208, 272, 336, 400]

def spawn_barrel():
    barrels.append({'rect': pygame.Rect(dk_rect.x + 24, dk_rect.y + 24, BARREL_SIZE, BARREL_SIZE), 'dir': 1, 'level': 0, 'y_target': barrel_drop_ys[0]})

def move_barrels():
    for barrel in barrels:
        # Move horizontally
        barrel['rect'].x += BARREL_SPEED * barrel['dir']
        # Change direction at platform edges
        if barrel['rect'].x <= 32 or barrel['rect'].x + BARREL_SIZE >= WIDTH - 32:
            barrel['dir'] *= -1
            barrel['rect'].x += BARREL_SPEED * barrel['dir']
        # Drop down at ladder positions
        if barrel['level'] < len(barrel_drop_ys):
            for ladder in ladders:
                if not ladder['broken'] and abs(barrel['rect'].centerx - ladder['rect'].centerx) < 8:
                    if abs(barrel['rect'].bottom - ladder['rect'].y) < 8:
                        if random.random() < 0.12:
                            barrel['rect'].y = barrel_drop_ys[barrel['level']]
                            barrel['level'] += 1
                            break
        # Gravity if not on platform
        on_plat = False
        for plat in platforms:
            if barrel['rect'].colliderect(plat):
                on_plat = True
                break
        if not on_plat:
            barrel['rect'].y += int(GRAVITY * 8)
    # Remove barrels that fall off screen
    barrels[:] = [b for b in barrels if b['rect'].y < HEIGHT]

def draw():
    screen.fill(BLACK)
    # Draw platforms
    for plat in platforms:
        pygame.draw.rect(screen, RED, plat)
    # Draw ladders
    for ladder in ladders:
        color = BLUE if not ladder['broken'] else (120, 160, 255)
        pygame.draw.rect(screen, color, ladder['rect'])
    # Draw player (Mario)
    pygame.draw.rect(screen, YELLOW, player)
    pygame.draw.rect(screen, RED, (player.x, player.y, PLAYER_SIZE, PLAYER_SIZE//2))
    # Draw barrels
    for barrel in barrels:
        pygame.draw.ellipse(screen, BROWN, barrel['rect'])
    # Draw Donkey Kong
    pygame.draw.rect(screen, DK_BROWN, dk_rect)
    pygame.draw.rect(screen, BLACK, (dk_rect.x+8, dk_rect.y+8, 16, 16))
    # Draw Pauline (goal)
    pygame.draw.rect(screen, PINK, goal)
    # Instructions
    font = pygame.font.SysFont(None, 20)
    text = font.render('Reach Pauline! Arrows to move, Up/Down for ladders, Space to jump', True, WHITE)
    screen.blit(text, (10, 10))

def check_collision(rect1, rect2):
    return rect1.colliderect(rect2)

# Main game loop
game_over = False
win = False
while True:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    if not game_over and not win:
        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0
        on_ladder = False
        ladder_broken = False
        # Check if on ladder
        for ladder in ladders:
            if player.colliderect(ladder['rect']):
                on_ladder = True
                ladder_broken = ladder['broken']
                break
        # Movement
        if keys[pygame.K_LEFT]:
            dx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT]:
            dx = PLAYER_SPEED
        if on_ladder and not ladder_broken:
            if keys[pygame.K_w]:
                dy = -PLAYER_SPEED
            if keys[pygame.K_DOWN]:
                dy = PLAYER_SPEED
            player_vel_y = 0
        else:
            if on_ground and keys[pygame.K_SPACE]:
                player_vel_y = -JUMP_POWER
        # Apply gravity
        if not (on_ladder and not ladder_broken):
            player_vel_y += GRAVITY
            dy += player_vel_y
        # Move horizontally
        player.x += dx
        # Collide with platforms horizontally
        for plat in platforms:
            if player.colliderect(plat):
                if dx > 0:
                    player.right = plat.left
                if dx < 0:
                    player.left = plat.right
        # Move vertically
        player.y += dy
        # Collide with platforms vertically
        on_ground = False
        for plat in platforms:
            if player.colliderect(plat):
                if dy > 0:
                    player.bottom = plat.top
                    on_ground = True
                    player_vel_y = 0
                elif dy < 0:
                    player.top = plat.bottom
                    player_vel_y = 0
        # Stay in bounds
        player.x = max(0, min(WIDTH - PLAYER_SIZE, player.x))
        player.y = max(0, min(HEIGHT - PLAYER_SIZE, player.y))
        # Win condition
        if player.colliderect(goal):
            win = True
        # Barrel collision
        for barrel in barrels:
            if player.colliderect(barrel['rect']):
                game_over = True
        # Barrel spawning
        barrel_timer += 1
        if barrel_timer > 120:
            spawn_barrel()
            barrel_timer = 0
        move_barrels()
    draw()
    if game_over:
        font = pygame.font.SysFont(None, 48)
        text = font.render('GAME OVER', True, RED)
        screen.blit(text, (WIDTH//2 - 120, HEIGHT//2 - 24))
    if win:
        font = pygame.font.SysFont(None, 48)
        text = font.render('YOU WIN!', True, YELLOW)
        screen.blit(text, (WIDTH//2 - 100, HEIGHT//2 - 24))
    pygame.display.flip()
