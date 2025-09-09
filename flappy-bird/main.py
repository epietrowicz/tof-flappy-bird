from adafruit_extended_bus import ExtendedI2C
from pygame.locals import *
import os
import adafruit_vl53l0x
import pygame, random, time

# VARIABLES
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
SPEED = 15
GRAVITY = 3
GAME_SPEED = 15

GROUND_WIDTH = 2 * SCREEN_WIDTH
GROUND_HEIGHT = 100

PIPE_WIDTH = 80
PIPE_HEIGHT = 500
PIPE_GAP = 200
PIPE_SPACING = 320  # smaller = more frequent


DEBOUNCE_MM = 20
NEAR_MM = 220  # become "near" when closer than this
COOLDOWN_MS = 250  # minimum time between bumps

wing = "assets/audio/wing.wav"
hit = "assets/audio/hit.wav"

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

pygame.mixer.init()


class ToFUpDetector:
    def __init__(self, i2c_bus=2):
        i2c = ExtendedI2C(i2c_bus)  # /dev/i2c-2
        self.vl53 = adafruit_vl53l0x.VL53L0X(i2c)

        self.is_near = False
        self.last_change_ms = 0
        self.last_rng_mm = 9999
        self.last_bump_ms = 0

    def read_range_mm(self):
        try:
            r = int(self.vl53.range)  # mm
            return r if r > 0 else 9999
        except Exception:
            return 9999

    def up_event(self, now_ms):
        rng = self.read_range_mm()
        if (
            rng < NEAR_MM
            and (self.last_rng_mm - rng) >= DEBOUNCE_MM
            and (now_ms - self.last_bump_ms) >= COOLDOWN_MS
        ):
            self.last_bump_ms = now_ms
            return True
        self.last_rng_mm = rng
        return False


class Bird(pygame.sprite.Sprite):

    def __init__(self):
        pygame.sprite.Sprite.__init__(self)

        self.images = [
            pygame.image.load("assets/sprites/bluebird-upflap.png").convert_alpha(),
            pygame.image.load("assets/sprites/bluebird-midflap.png").convert_alpha(),
            pygame.image.load("assets/sprites/bluebird-downflap.png").convert_alpha(),
        ]

        self.speed = SPEED

        self.current_image = 0
        self.image = pygame.image.load(
            "assets/sprites/bluebird-upflap.png"
        ).convert_alpha()
        self.mask = pygame.mask.from_surface(self.image)

        self.rect = self.image.get_rect()
        self.rect[0] = SCREEN_WIDTH / 6
        self.rect[1] = SCREEN_HEIGHT / 2

    def update(self):
        self.current_image = (self.current_image + 1) % 3
        self.image = self.images[self.current_image]
        self.speed += GRAVITY

        # UPDATE HEIGHT
        self.rect[1] += self.speed

    def bump(self):
        self.speed = -SPEED

    def begin(self):
        self.current_image = (self.current_image + 1) % 3
        self.image = self.images[self.current_image]


class Pipe(pygame.sprite.Sprite):

    def __init__(self, inverted, xpos, ysize):
        pygame.sprite.Sprite.__init__(self)

        self.image = pygame.image.load("assets/sprites/pipe-green.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (PIPE_WIDTH, PIPE_HEIGHT))

        self.rect = self.image.get_rect()
        self.rect[0] = xpos

        if inverted:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect[1] = -(self.rect[3] - ysize)
        else:
            self.rect[1] = SCREEN_HEIGHT - ysize

        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.rect[0] -= GAME_SPEED


class Ground(pygame.sprite.Sprite):

    def __init__(self, xpos):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load("assets/sprites/base.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (GROUND_WIDTH, GROUND_HEIGHT))

        self.mask = pygame.mask.from_surface(self.image)

        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        self.rect[1] = SCREEN_HEIGHT - GROUND_HEIGHT

    def update(self):
        self.rect[0] -= GAME_SPEED


def is_off_screen(sprite):
    return sprite.rect[0] < -(sprite.rect[2])


def get_random_pipes(xpos):
    size = random.randint(100, 300)
    pipe = Pipe(False, xpos, size)
    pipe_inverted = Pipe(True, xpos, SCREEN_HEIGHT - size - PIPE_GAP)
    return pipe, pipe_inverted


pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Flappy Bird")

BACKGROUND = pygame.image.load("assets/sprites/background-day.png")
BACKGROUND = pygame.transform.scale(BACKGROUND, (SCREEN_WIDTH, SCREEN_HEIGHT))
BEGIN_IMAGE = pygame.image.load("assets/sprites/message.png").convert_alpha()

bird_group = pygame.sprite.Group()
bird = Bird()
bird_group.add(bird)

ground_group = pygame.sprite.Group()

for i in range(2):
    ground = Ground(GROUND_WIDTH * i)
    ground_group.add(ground)

pipe_group = pygame.sprite.Group()
for i in range(2):
    pipes = get_random_pipes(SCREEN_WIDTH * i + 800)
    pipe_group.add(pipes[0])
    pipe_group.add(pipes[1])


clock = pygame.time.Clock()

# Initialize ToF
tof = ToFUpDetector(i2c_bus=2)

begin = True

while begin:

    clock.tick(15)
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()

    # ToF “up” to start
    if tof.up_event(now):
        bird.bump()
        pygame.mixer.music.load(wing)
        pygame.mixer.music.play()
        begin = False

    screen.blit(BACKGROUND, (0, 0))
    screen.blit(BEGIN_IMAGE, (120, 150))

    if is_off_screen(ground_group.sprites()[0]):
        ground_group.remove(ground_group.sprites()[0])

        new_ground = Ground(GROUND_WIDTH - 20)
        ground_group.add(new_ground)

    bird.begin()
    ground_group.update()

    bird_group.draw(screen)
    ground_group.draw(screen)

    pygame.display.update()


while True:

    clock.tick(15)
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()

    if tof.up_event(now):
        bird.bump()
        pygame.mixer.music.load(wing)
        pygame.mixer.music.play()
        begin = False

    screen.blit(BACKGROUND, (0, 0))

    if is_off_screen(ground_group.sprites()[0]):
        ground_group.remove(ground_group.sprites()[0])

        new_ground = Ground(GROUND_WIDTH - 20)
        ground_group.add(new_ground)

    if is_off_screen(pipe_group.sprites()[0]):
        pipe_group.remove(pipe_group.sprites()[0])
        pipe_group.remove(pipe_group.sprites()[0])

        pipes = get_random_pipes(SCREEN_WIDTH * 2)

        pipe_group.add(pipes[0])
        pipe_group.add(pipes[1])

    bird_group.update()
    ground_group.update()
    pipe_group.update()

    bird_group.draw(screen)
    pipe_group.draw(screen)
    ground_group.draw(screen)

    pygame.display.update()

    if pygame.sprite.groupcollide(
        bird_group, ground_group, False, False, pygame.sprite.collide_mask
    ) or pygame.sprite.groupcollide(
        bird_group, pipe_group, False, False, pygame.sprite.collide_mask
    ):
        pygame.mixer.music.load(hit)
        pygame.mixer.music.play()
        time.sleep(1)
        break
