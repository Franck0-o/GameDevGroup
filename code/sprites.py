from settings import *
from math import atan2, degrees

class CollisionSprites(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_frect(topleft=pos)

class NonCollisionSprites(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_frect(topleft=pos)
        self.ground = True

class Gun(pygame.sprite.Sprite):
    def __init__(self, player, groups):
        self.player = player
        self.distance = 30
        self.player_position = pygame.Vector2(1,0)

        #Gun sprite
        super().__init__(groups)
        self.sprite = pygame.image.load(join('images','gun','shotgun.png'))
        self.image = self.sprite
        self.rect = self.image.get_frect(center = self.player.rect.center + self.distance * self.player_position)

    def get_distance(self):
        mouse_position = pygame.Vector2(pygame.mouse.get_pos())
        player_position = pygame.Vector2(WINDOW_WIDTH/2, WINDOW_HEIGHT/2)
        self.player_position = (mouse_position - player_position).normalize()

    def rotate_gun(self):
        angle = degrees(atan2(self.player_position.x, self.player_position.y)) - 90
        if self.player_position.x > 0:
            self.image = pygame.transform.rotozoom(self.sprite, angle, 1)
        else:

            self.image = pygame.transform.rotozoom(self.sprite, abs(angle), 1)
            self.image = pygame.transform.flip(self.image, False, True)

    def update(self, _):
        self.rotate_gun()
        self.get_distance()
        self.rect.center = self.player.rect.center + self.distance * self.player_position

class bullet(pygame.sprite.Sprite):
    def __init__(self, pos):
        self.sprite = pygame.image.load(join('images', 'gun','bullet.png'))
        self.image = self.sprite
        self.rect = self.image.get_frect(center = pos)

    
