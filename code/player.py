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

        #Player Movement
        self.direction = pygame.math.Vector2()
        self.speed = speed
        self.collision_group = collision_group

    def load_images(self):
        self.frames = {'left': [], 'right': [], 'up':[], 'down': []}

        for state in self.frames.keys():
            for folder_path, sub_folders, file_names in walk(join('images','player', state)):
                if file_names:
                    for file_name in sorted(file_names, key=lambda name: int(name.split('.')[0])):
                        full_path = join(folder_path, file_name)
                        surf = pygame.image.load(full_path).convert_alpha()
                        self.frames[state].append(surf)
        
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

    def animate(self,dt):
        #get state
        if self.direction.y != 0:
            if self.direction.y > 0:
                self.state = 'down' 
            else:
                self.state = 'up'
        if self.direction.x != 0:
            if self.direction.x > 0:
                self.state = 'right' 
            else:
                self.state = 'left'


        #animate
        if self.direction:
            self.frame_index = self.frame_index + 10 * dt
        else:
            self.frame_index = 0
        '''
        self.frames[self.state] - Get the current state (right, left, down or up)

        len(self.frames[self.state]) - Get the numbers of frames that the animation has

        int(self.frame_index) - It transform the serial number in an integer to be better used
        '''
        self.image = self.frames[self.state][int(self.frame_index) % len(self.frames[self.state])]
        self.image = pygame.transform.scale_by(self.image, 4)

    def update(self, dt):
        self.input()
        self.move(dt)
        self.animate(dt)
