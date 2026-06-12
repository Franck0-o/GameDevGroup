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
        self.player_direction= pygame.Vector2(1,0)

        #Gun sprite
        super().__init__(groups)
        self.sprite = pygame.image.load(join('images','gun','shotgun.png'))
        self.image = self.sprite
        self.rect = self.image.get_frect(center = self.player.rect.center + self.distance * self.player_direction)

    def get_distance(self):
        mouse_direction = pygame.Vector2(pygame.mouse.get_pos())
        player_direction = pygame.Vector2(WINDOW_WIDTH/2, WINDOW_HEIGHT/2)
        self.player_direction = (mouse_direction - player_direction).normalize()

    def rotate_gun(self):
        angle = degrees(atan2(self.player_direction.x, self.player_direction.y)) - 90
        if self.player_direction.x > 0:
            self.image = pygame.transform.rotozoom(self.sprite, angle, 1)
        else:

            self.image = pygame.transform.rotozoom(self.sprite, abs(angle), 1)
            self.image = pygame.transform.flip(self.image, False, True)

    def update(self, _):
        self.rotate_gun()
        self.get_distance()
        self.rect.center = self.player.rect.center + self.distance * self.player_direction

class Bullet(pygame.sprite.Sprite):
    def __init__(self, surf, pos, direction, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_frect(center = pos)

        #Other Atributes
        self.velocity = 1200
        self.direction = direction
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 1000

    def update(self, dt):
       self.rect.center += self.direction * self.velocity * dt

       if pygame.time.get_ticks() - self.spawn_time >= self.lifetime:
           self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, player, collision_sprites):
        super().__init__(groups)
        self.player = player

        self.frames, self.frame_index = frames, 0
        self.image = self.frames[self.frame_index]
        self.animation_speed = 6

        self.rect = self.image.get_frect(center = pos)
        self.hitbox_rect = self.rect.inflate(-20, -40)
        self.collision_sprites = collision_sprites
        self.direction = pygame.Vector2()
        self.speed = 200

        self.death_time = 0
        self.death_duration = 400

    def animate(self, dt):
        self.frame_index += self.animation_speed * dt
        self.image = self.frames[int(self.frame_index) % len(self.frames)]

    def move(self, dt):
        player_pos = pygame.Vector2(self.player.rect.center)
        enemy_pos = pygame.Vector2(self.rect.center)
        self.direction = (player_pos - enemy_pos).normalize()

        self.hitbox_rect.x += self.direction.x * self.speed * dt
        self.collision('Horizontal')
        self.hitbox_rect.y += self.direction.y * self.speed * dt
        self.collision('Vertical')
        self.rect.center = self.hitbox_rect.center

    def collision(self, direction):
        for sprite in self.collision_sprites:
                if sprite.rect.colliderect(self.hitbox_rect):
                    if direction == 'Horizontal':
                        if self.direction.x > 0: self.hitbox_rect.right = sprite.rect.left
                        if self.direction.x < 0: self.hitbox_rect.left = sprite.rect.right
                    if direction == 'Vertical':
                        if self.direction.y > 0: self.hitbox_rect.bottom = sprite.rect.top
                        if self.direction.y < 0: self.hitbox_rect.top = sprite.rect.bottom
    
    def destroy(self):
        self.death_time = pygame.time.get_ticks()

        surf = pygame.mask.from_surface(self.frames[0]).to_surface()
        surf.set_colorkey('black')
        self.image = surf

    def death_timer(self):
        if pygame.time.get_ticks() - self.death_time >= self.death_duration:
            self.kill()
        
    def update(self, dt):

        if self.death_time == 0:
            self.move(dt)
            self.animate(dt)
        else:
            self.death_timer()