from settings import *
from player import Player
from sprites import CollisionSprites, NonCollisionSprites
from pytmx.util_pygame import load_pygame

class Game:
    def __init__(self):

        #setup
        pygame.init()
        self.display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Shoot and Run')
        self.clock = pygame.time.Clock()
        self.running = True

        #groups
        self.all_sprites = pygame.sprite.Group()
        self.collision_sprites = pygame.sprite.Group()

        #sprites
        self.setup()
        self.player = Player((400, 300), 400, self.all_sprites, self.collision_sprites)

    def setup(self):
        map = load_pygame(join('data','maps','world.tmx'))

        for x,y, image in map.get_layer_by_name('Ground').tiles():
            NonCollisionSprites((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)
        for obj in map.get_layer_by_name('Objects'):
            CollisionSprites((obj.x, obj.y), obj.image ,(self.all_sprites, self.collision_sprites))
        for collision_surf in map.get_layer_by_name('Collisions'):
            CollisionSprites((collision_surf.x ,collision_surf.y), pygame.Surface((collision_surf.width,collision_surf.height)), self.collision_sprites)



    def run(self):
        while self.running:
            # deltatime
            dt = self.clock.tick(60) / 1000

            #event loop
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            #update
            self.display.fill('black')
            self.all_sprites.update(dt)

            #draw
            self.all_sprites.draw(self.display)

            pygame.display.update()
        pygame.quit()

if __name__ == "__main__":
  game = Game()
  game.run()