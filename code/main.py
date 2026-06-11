from settings import *
from player import Player
from sprites import *
from pytmx.util_pygame import load_pygame
from groups import AllSprites

class Game:
    def __init__(self):

        #setup
        pygame.init()
        self.display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Shoot and Run')
        self.clock = pygame.time.Clock()
        self.running = True
        self.load_images()

        #groups
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        #sprites
        self.setup()

        self.can_shoot = True
        self.shoot_time = 0
        self.gun_cooldown = 800

    def load_images(self):
        self.bullet_surf = pygame.image.load(join('images','gun','bullet.png')).convert_alpha()

    def input(self):
        if pygame.mouse.get_pressed()[0] and self.can_shoot:
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

            #Update
            self.gun_timer()
            self.input()
            self.all_sprites.update(dt)
           
            #Draw
            self.all_sprites.draw(self.player.rect.center)

            #This create a red rect around the player
            self.hitbox_draw_debug()

        

            pygame.display.update()
        pygame.quit()

#This makes the onlu way to run the game, if u are in the main.py file
if __name__ == "__main__":
  game = Game()
  game.run()