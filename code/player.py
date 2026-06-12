from settings import *

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, speed, groups, collision_group):
        super().__init__(groups)
        self.load_images()
        self.state, self.frame_index = "down", 0
        self.image = pygame.transform.scale_by(pygame.image.load(join('images', 'player','down','0.png')).convert_alpha(), 4)
        self.rect = self.image.get_frect(center = pos)
        self.hitbox_rect = self.rect.inflate(-90, -65)
        self.display_surface = pygame.display.get_surface()

        # Player Movement
        self.direction = pygame.math.Vector2()
        self.speed = speed
        self.collision_group = collision_group

        # Health system
        self.health = 5
        self.max_health = 5
        self.is_dead = False

        # Damage cooldown (invincibility frames)
        self.can_take_damage = True
        self.damage_time = 0
        self.damage_cooldown = 1500  # 1.5 seconds of invincibility

        # Hit flash effect
        self.hit_flash = False
        self.flash_time = 0
        self.flash_duration = 100  # ms each flash blink
        self.flash_count = 0
        self.max_flashes = 6       # number of blinks during cooldown

    def load_images(self):
        self.frames = {'left': [], 'right': [], 'up':[], 'down': []}

        for state in self.frames.keys():
            for folder_path, sub_folders, file_names in walk(join('images','player', state)):
                if file_names:
                    for file_name in sorted(file_names, key=lambda name: int(name.split('.')[0])):
                        full_path = join(folder_path, file_name)
                        surf = pygame.image.load(full_path).convert_alpha()
                        self.frames[state].append(surf)

    def take_damage(self):
        if self.can_take_damage and not self.is_dead:
            self.health -= 1
            self.can_take_damage = False
            self.damage_time = pygame.time.get_ticks()

            # Start flash effect
            self.hit_flash = True
            self.flash_time = pygame.time.get_ticks()
            self.flash_count = 0

            if self.health <= 0:
                self.health = 0
                self.is_dead = True

    def damage_timer(self):
        if not self.can_take_damage:
            current_time = pygame.time.get_ticks()
            if current_time - self.damage_time >= self.damage_cooldown:
                self.can_take_damage = True
                self.hit_flash = False

    def apply_flash(self, surface):
        """Returns a white version of the surface for the hit flash effect."""
        if not self.hit_flash:
            return surface

        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.flash_time

        # Alternate between white and normal every flash_duration ms
        blink_index = int(elapsed / self.flash_duration)

        if blink_index >= self.max_flashes:
            self.hit_flash = False
            return surface

        # On even blinks show white, on odd blinks show normal
        if blink_index % 2 == 0:
            white_surf = pygame.mask.from_surface(surface).to_surface()
            white_surf.set_colorkey('black')
            return white_surf

        return surface

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

    def animate(self, dt):
        # get state
        if self.direction.y != 0:
            self.state = 'down' if self.direction.y > 0 else 'up'
        if self.direction.x != 0:
            self.state = 'right' if self.direction.x > 0 else 'left'

        # animate
        if self.direction:
            self.frame_index = self.frame_index + 10 * dt
        else:
            self.frame_index = 0

        base_image = self.frames[self.state][int(self.frame_index) % len(self.frames[self.state])]
        base_image = pygame.transform.scale_by(base_image, 4)

        # Apply flash effect on top of the final scaled image
        self.image = self.apply_flash(base_image)

    def update(self, dt):
        self.input()
        self.move(dt)
        self.animate(dt)
        self.damage_timer()