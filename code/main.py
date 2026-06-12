from settings import *
from player import Player
from sprites import *
from pytmx.util_pygame import load_pygame
from groups import AllSprites

from random import randint, choice

class Game:
    def __init__(self):

        #setup
        pygame.init()
        self.display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Shoot and Run')
        self.clock = pygame.time.Clock()
        self.running = True

        #groups
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()
        #sprites

        self.can_shoot = True
        self.shoot_time = 0
        self.gun_cooldown = 600

        self.enemy_event = pygame.event.custom_type()
        pygame.time.set_timer(self.enemy_event, 300)
        self.spawn_positions = []

        #Audio is being imported here
        self.shoot_sound = pygame.mixer.Sound(join('audio', 'shoot.wav'))
        self.shoot_sound.set_volume(0.4)
        self.impact_sound = pygame.mixer.Sound(join('audio', 'impact.ogg'))
        self.music = pygame.mixer.Sound(join('audio', 'music.wav'))
        self.music.set_volume(0.1)
        self.music.play(loops= -1)

        #setup
        self.load_images()
        self.setup()

    def load_images(self):
        self.bullet_surf = pygame.image.load(join('images','gun','bullet.png')).convert_alpha()
        
        folders = list(walk(join('images','enemies')))[0][1]
        self.enemy_frames = {}
        for folder in folders:
            for folder_path, _, file_names in walk(join('images', 'enemies', folder)):
                self.enemy_frames[folder] = []
                for file_name in sorted(file_names, key=lambda name: int(name.split('.')[0])):
                    full_path = join(folder_path, file_name)
                    surf = pygame.image.load(full_path).convert_alpha()
                    self.enemy_frames[folder].append(surf)

    def input(self):
        if pygame.mouse.get_pressed()[0] and self.can_shoot:
            self.shoot_sound.play()
            pos = self.gun.rect.center + self.gun.player_direction * 50
            Bullet(self.bullet_surf, pos, self.gun.player_direction, (self.all_sprites, self.bullet_sprites))
            self.can_shoot = False
            self.shoot_time = pygame.time.get_ticks()

    def gun_timer(self):
        if not self.can_shoot:
            current_time = pygame.time.get_ticks()
            if current_time - self.shoot_time >= self.gun_cooldown:
                self.can_shoot = True

    def setup(self):
        #Here i am importing all sprites and deciding what layer it get
        map = load_pygame(join('data','maps','world.tmx'))
        
        #Here i do a for loop to get to all sprites images, x and y cords in the layer(ground)
        for x,y, image in map.get_layer_by_name('Ground').tiles():
            NonCollisionSprites((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)
        
        #Same for the layer(Objects)
        for obj in map.get_layer_by_name('Objects'):
            CollisionSprites((obj.x, obj.y), obj.image ,(self.all_sprites, self.collision_sprites))

        #Same for the layer(Collisions)
        for collision_surf in map.get_layer_by_name('Collisions'):
            CollisionSprites((collision_surf.x ,collision_surf.y), pygame.Surface((collision_surf.width,collision_surf.height)), self.collision_sprites)

        #I import the player and the gun, instance them to make them appear
        for obj in map.get_layer_by_name("Entities"):
            if obj.name == "Player":
                self.player = Player((obj.x, obj.y), 400, self.all_sprites, self.collision_sprites)
                self.gun = Gun(self.player, self.all_sprites)
            else:
                self.spawn_positions.append((obj.x , obj.y))

    def bullet_collision(self):
        if self.bullet_sprites:
            for bullet in self.bullet_sprites:
                collision_sprites = pygame.sprite.spritecollide(bullet, self.enemy_sprites, False, pygame.sprite.collide_mask)
                if collision_sprites:
                    self.impact_sound.play()
                    for sprite in collision_sprites:
                        sprite.destroy()
                    bullet.kill()
        
    def player_collision(self):
        if pygame.sprite.spritecollide(self.player, self.enemy_sprites, False, pygame.sprite.collide_mask):
            self.running = False

    def hitbox_draw_debug(self):
        pygame.draw.rect(self.display, (255,0,0) , self.player.hitbox_rect.move(self.all_sprites.offset) , 2)

#This is literally the code to make the game run, if u dont now this go study some pygame, it is in the front page of the documentation
    def run(self):
        while self.running:
            # deltatime 
            dt = self.clock.tick(60) / 1000

            #This checks if the player closes the game by pressing the x in the top
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == self.enemy_event:
                    Enemy(choice(self.spawn_positions), choice(list(self.enemy_frames.values())), (self.all_sprites, self.enemy_sprites), self.player, self.collision_sprites)
            #Update
            self.gun_timer()
            self.input()
            self.all_sprites.update(dt)
            self.bullet_collision()
            self.player_collision()
           
            #Draw
            self.all_sprites.draw(self.player.rect.center)

            #This create a red rect around the player
            self.hitbox_draw_debug()
        

            pygame.display.update()
        pygame.quit()

#This makes the only way to run the game, if u are in the main.py file
if __name__ == "__main__":
  game = Game()
  game.run()