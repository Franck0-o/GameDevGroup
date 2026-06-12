from settings import *
from math import atan2, degrees

class CollisionSprites(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect  = self.image.get_frect(topleft=pos)

class NonCollisionSprites(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image  = surf
        self.rect   = self.image.get_frect(topleft=pos)
        self.ground = True

class Gun(pygame.sprite.Sprite):
    def __init__(self, player, groups):
        self.player           = player
        self.distance         = 30
        self.player_direction = pygame.Vector2(1, 0)
        super().__init__(groups)
        self.sprite = pygame.image.load(join('images', 'gun', 'shotgun.png'))
        self.image  = self.sprite
        self.rect   = self.image.get_frect(
            center=self.player.rect.center + self.distance * self.player_direction)

    def get_distance(self):
        mouse  = pygame.Vector2(pygame.mouse.get_pos())
        centre = pygame.Vector2(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
        self.player_direction = (mouse - centre).normalize()

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
    def __init__(self, surf, pos, direction, groups, velocity=1200, piercing=False):
        super().__init__(groups)
        self.image     = surf
        self.rect      = self.image.get_frect(center=pos)
        self.velocity  = velocity
        self.direction = direction
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime  = 1000
        self.piercing  = piercing          # if True, passes through enemies

    def update(self, dt):
        self.rect.center += self.direction * self.velocity * dt
        if pygame.time.get_ticks() - self.spawn_time >= self.lifetime:
            self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, player, collision_sprites, speed=200):
        super().__init__(groups)
        self.player          = player
        self.frames          = frames
        self.frame_index     = 0
        self.image           = self.frames[0]
        self.animation_speed = 6
        self.rect            = self.image.get_frect(center=pos)
        self.hitbox_rect     = self.rect.inflate(-20, -40)
        self.collision_sprites = collision_sprites
        self.direction       = pygame.Vector2()
        self.speed           = speed
        self.death_time      = 0
        self.death_duration  = 400

    def animate(self, dt):
        self.frame_index += self.animation_speed * dt
        self.image = self.frames[int(self.frame_index) % len(self.frames)]

    def move(self, dt):
        player_pos = pygame.Vector2(self.player.rect.center)
        enemy_pos  = pygame.Vector2(self.rect.center)
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
                    if self.direction.x < 0: self.hitbox_rect.left  = sprite.rect.right
                if direction == 'Vertical':
                    if self.direction.y > 0: self.hitbox_rect.bottom = sprite.rect.top
                    if self.direction.y < 0: self.hitbox_rect.top    = sprite.rect.bottom

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


# ------------------------------------------------------------------ #
#  SHOP NPC                                                            #
# ------------------------------------------------------------------ #
class ShopNPC(pygame.sprite.Sprite):
    """
    Place your sprite at  images/npc/shop.png
    Falls back to a yellow '?' placeholder.
    Only added to all_sprites during wave intermissions.
    """
    INTERACT_RADIUS = 80

    def __init__(self, pos, groups):
        # NOTE: intentionally NOT passing groups here —
        # visibility is managed externally via _show_npc()
        super().__init__()

        try:
            raw        = pygame.image.load(join('images', 'npc', 'shop.png')).convert_alpha()
            self.image = pygame.transform.scale2x(raw)
        except FileNotFoundError:
            self.image = pygame.Surface((48, 64), pygame.SRCALPHA)
            self.image.fill((255, 200, 0))
            font  = pygame.font.SysFont('Arial', 32, bold=True)
            label = font.render('?', True, (40, 40, 40))
            self.image.blit(label, label.get_rect(center=(24, 32)))

        self.rect = self.image.get_frect(center=pos)

    def is_player_near(self, player_rect):
        return (pygame.Vector2(self.rect.center)
                .distance_to(pygame.Vector2(player_rect.center)) <= self.INTERACT_RADIUS)