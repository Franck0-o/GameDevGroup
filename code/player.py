from settings import *

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, speed, groups, collision_group):
        super().__init__(groups)
        self.image = pygame.image.load(join('../images', 'player','down','0.png')).convert_alpha()
        self.rect = self.image.get_frect(center = pos)
        self.hitbox_rect = self.rect.inflate(-60, -0)

        #Player Movement
        self.direction = pygame.math.Vector2()
        self.speed = speed
        self.collision_group = collision_group

    def input(self):
        keys = pygame.key.get_pressed()
        self.direction.x = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        self.direction.y = int(keys[pygame.K_s]) - int(keys[pygame.K_w])
        self.direction = self.direction.normalize() if self.direction else self.direction

    def move(self, dt):
        self.hitbox_rect.x += self.speed * self.direction.x * dt
        self.collision('Horizontal')
        self.hitbox_rect.y += self.speed * self.direction.y * dt
        self.collision('Vertical')
        self.rect.center = self.hitbox_rect.center

    def collision(self, direction):
        for sprite in self.collision_group:
            if sprite.rect.colliderect(self.hitbox_rect):
                if direction == 'Horizontal':
                    if self.direction.x > 0: self.hitbox_rect.right = sprite.rect.left
                    if self.direction.x < 0: self.hitbox_rect.left = sprite.rect.right
                if direction == 'Vertical':
                    if self.direction.y > 0: self.hitbox_rect.bottom = sprite.rect.top
                    if self.direction.y < 0: self.hitbox_rect.top = sprite.rect.bottom


    def update(self, dt):
        self.input()
        self.move(dt)
