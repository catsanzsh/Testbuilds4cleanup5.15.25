import pygame
import sys
import random
import math
import struct

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

class SoundEngine:
    def __init__(self):
        try:
            import pyaudio
            self.pyaudio_instance = pyaudio.PyAudio()
            self.stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=44100,
                output=True
            )
        except Exception as e:
            print(f"Failed to initialize PyAudio stream: {e}")
            self.stream = None

    def play_tone(self, frequency: float, duration_ms: int, volume: float = 0.1) -> None:
        if not self.stream:
            return

        sample_rate = 44100
        num_samples = int(sample_rate * duration_ms / 1000.0)
        wave_data = b''
        for i in range(num_samples):
            value = volume * math.sin(2 * math.pi * frequency * i / sample_rate)
            wave_data += struct.pack('f', value)

        try:
            self.stream.write(wave_data)
        except Exception as e:
            print(f"Error playing tone: {e}")

    def play_jump_sound(self) -> None:
        self.play_tone(frequency=660, duration_ms=80, volume=0.05)

    def play_land_sound(self) -> None:
        self.play_tone(frequency=220, duration_ms=50, volume=0.05)

    def play_barrel_break_sound(self) -> None:
        self.play_tone(frequency=150, duration_ms=150, volume=0.08)

    def play_mario_hit_sound(self) -> None:
        self.play_tone(frequency=100, duration_ms=300, volume=0.1)
        self.play_tone(frequency=80, duration_ms=200, volume=0.1)

    def play_win_sound(self) -> None:
        self.play_tone(frequency=880, duration_ms=100, volume=0.07)
        self.play_tone(frequency=1046, duration_ms=100, volume=0.07)
        self.play_tone(frequency=1318, duration_ms=150, volume=0.07)

    def play_climb_sound(self) -> None:
        self.play_tone(frequency=440, duration_ms=30, volume=0.03)

    def cleanup(self) -> None:
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'pyaudio_instance'):
            self.pyaudio_instance.terminate()

class DonkeyKongGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Donkey Kong NES Clone")
        self.clock = pygame.time.Clock()
        self.sound_engine = SoundEngine()

        self.platforms, self.ladders = self.create_nes_level()
        self.player = pygame.Rect(40, 400 - PLAYER_SIZE, PLAYER_SIZE, PLAYER_SIZE)
        self.player_vel_y = 0
        self.on_ground = False
        self.on_ladder = False
        self.climbing_sound_timer = 0

        self.goal = pygame.Rect(400, 60, 20, 24)
        self.dk_rect = pygame.Rect(64, 40, 32, 32)
        self.barrels = []
        self.barrel_timer = 0
        self.game_over = False
        self.win = False
        self.stage_clear_active = False
        self.stage_clear_timer = 0
        self.STAGE_CLEAR_DURATION = 180

    def create_nes_level(self):
        platforms = []
        ladders = []

        plat_data = [
            (64, 80, 384, 8, 2, 1),
            (32, 144, 448, 16, 2, -1),
            (64, 208, 384, 8, 2, 1),
            (32, 272, 448, 16, 2, -1),
            (64, 336, 384, 8, 2, 1),
            (32, 400, 448, 16, 2, -1),
        ]

        for x, y, w, steps, step_h, direction in plat_data:
            for s in range(steps):
                sx = x + (w // steps) * s
                sy = y + direction * step_h * s
                sw = w // steps
                platforms.append(pygame.Rect(sx, sy, sw, PLATFORM_HEIGHT))

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

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.sound_engine.cleanup()
                pygame.quit()
                sys.exit()

    def update(self) -> None:
        if not self.game_over and not self.win:
            keys = pygame.key.get_pressed()

            dx = 0
            dy = 0
            prev_on_ground = self.on_ground
            on_ladder_prev = self.on_ladder

            self.on_ladder = False
            ladder_broken = False
            for ladder_obj in self.ladders:
                if self.player.colliderect(ladder_obj['rect']):
                    self.on_ladder = True
                    ladder_broken = ladder_obj['broken']
                    break

            if keys[pygame.K_LEFT]:
                dx = -PLAYER_SPEED
            if keys[pygame.K_RIGHT]:
                dx = PLAYER_SPEED

            is_climbing = False
            if self.on_ladder and not ladder_broken:
                if keys[pygame.K_w]:
                    dy = -PLAYER_SPEED
                    is_climbing = True
                if keys[pygame.K_s]:
                    dy = PLAYER_SPEED
                    is_climbing = True
                self.player_vel_y = 0
            else:
                if self.on_ground and keys[pygame.K_SPACE]:
                    self.player_vel_y = -JUMP_POWER
                    self.on_ground = False
                    self.sound_engine.play_jump_sound()

            if is_climbing:
                self.climbing_sound_timer -= 1
                if self.climbing_sound_timer <= 0:
                    self.sound_engine.play_climb_sound()
                    self.climbing_sound_timer = 10  # Changed to a fixed value
            else:
                self.climbing_sound_timer = 0

            if not (self.on_ladder and not ladder_broken):
                self.player_vel_y += GRAVITY
                dy += self.player_vel_y

            self.player.x += dx
            for plat in self.platforms:
                if self.player.colliderect(plat):
                    if dx > 0:
                        self.player.right = plat.left
                    if dx < 0:
                        self.player.left = plat.right

            self.player.y += dy
            on_ground_after_move = False
            for plat in self.platforms:
                if self.player.colliderect(plat):
                    if dy > 0:
                        self.player.bottom = plat.top
                        on_ground_after_move = True
                        self.player_vel_y = 0
                    elif dy < 0:
                        self.player.top = plat.bottom
                        self.player_vel_y = 0

            if not prev_on_ground and on_ground_after_move:
                self.sound_engine.play_land_sound()
            self.on_ground = on_ground_after_move

            self.player.x = max(0, min(WIDTH - PLAYER_SIZE, self.player.x))
            self.player.y = max(0, min(HEIGHT - PLAYER_SIZE, self.player.y))

            if self.player.colliderect(self.goal):
                self.win = True
                self.stage_clear_active = True
                self.stage_clear_timer = 0
                self.sound_engine.play_win_sound()

            for barrel in self.barrels:
                if self.player.colliderect(barrel['rect']):
                    self.game_over = True
                    self.sound_engine.play_mario_hit_sound()

            self.barrel_timer += 1
            if self.barrel_timer > 120:
                self.spawn_barrel()
                self.barrel_timer = 0
            self.move_barrels()

        if self.stage_clear_active:
            self.stage_clear_timer += 1
            if self.stage_clear_timer > self.STAGE_CLEAR_DURATION:
                self.reset_level()

    def draw(self) -> None:
        if self.stage_clear_active:
            self.screen.fill(BLACK)
            font = pygame.font.SysFont(None, 60)
            text = font.render('STAGE CLEAR!', True, YELLOW)
            self.screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - text.get_height()//2))
        else:
            self.screen.fill(BLACK)
            for plat in self.platforms:
                pygame.draw.rect(self.screen, RED, plat)
            for ladder_obj in self.ladders:
                color = BLUE if not ladder_obj['broken'] else (120, 160, 255)
                pygame.draw.rect(self.screen, color, ladder_obj['rect'])
            pygame.draw.rect(self.screen, YELLOW, self.player)
            pygame.draw.rect(self.screen, RED, (self.player.x, self.player.y, PLAYER_SIZE, PLAYER_SIZE//2))
            for barrel in self.barrels:
                pygame.draw.ellipse(self.screen, BROWN, barrel['rect'])
            pygame.draw.rect(self.screen, DK_BROWN, self.dk_rect)
            pygame.draw.rect(self.screen, BLACK, (self.dk_rect.x+8, self.dk_rect.y+8, 16, 16))
            pygame.draw.rect(self.screen, PINK, self.goal)
            font = pygame.font.SysFont(None, 20)
            text = font.render('Reach Pauline! W/Arrows to move, Space to jump', True, WHITE)
            self.screen.blit(text, (10, 10))

            if self.game_over:
                font = pygame.font.SysFont(None, 48)
                text = font.render('GAME OVER', True, RED)
                self.screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - text.get_height()//2))
                font = pygame.font.SysFont(None, 24)
                text = font.render('Press R to restart', True, WHITE)
                self.screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - text.get_height()//2 + 50))

        pygame.display.flip()

    def spawn_barrel(self) -> None:
        self.barrels.append({'rect': pygame.Rect(self.dk_rect.x + 24, self.dk_rect.y + 24, BARREL_SIZE, BARREL_SIZE), 'dir': 1, 'level': 0})

    def move_barrels(self) -> None:
        for barrel in self.barrels:
            barrel['rect'].x += BARREL_SPEED * barrel['dir']
            if barrel['rect'].x <= 32 or barrel['rect'].x + BARREL_SIZE >= WIDTH - 32:
                barrel['dir'] *= -1
                barrel['rect'].x += BARREL_SPEED * barrel['dir']

            if barrel['level'] < 5: # len([144, 208, 272, 336, 400]):
                y_targets = [144, 208, 272, 336, 400]
                for ladder_obj in self.ladders:
                    if not ladder_obj['broken'] and abs(barrel['rect'].centerx - ladder_obj['rect'].centerx) < 8:
                        if abs(barrel['rect'].bottom - ladder_obj['rect'].y) < 8:
                            if random.random() < 0.12:
                                barrel['rect'].y = y_targets[barrel['level']]
                                barrel['level'] += 1
                                self.sound_engine.play_barrel_break_sound()
                                break

            on_plat = False
            for plat in self.platforms:
                if barrel['rect'].colliderect(plat):
                    on_plat = True
                    break
            if not on_plat:
                barrel['rect'].y += int(GRAVITY * 8)

        self.barrels = [b for b in self.barrels if b['rect'].y < HEIGHT]

    def reset_level(self) -> None:
        self.player.x = 40
        self.player.y = 400 - PLAYER_SIZE
        self.player_vel_y = 0
        self.on_ground = False
        self.on_ladder = False
        self.climbing_sound_timer = 0
        self.barrels = []
        self.barrel_timer = 0
        self.game_over = False
        self.win = False
        self.stage_clear_active = False

    def run(self) -> None:
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

            keys = pygame.key.get_pressed()
            if self.game_over and keys[pygame.K_r]:
                self.reset_level()

if __name__ == "__main__":
    game = DonkeyKongGame()
    game.run()
