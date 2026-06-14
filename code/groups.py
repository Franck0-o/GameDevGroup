"""
groups.py
=========

AllSprites: grupo de sprites com câmera + ordenação por profundidade.

- Câmera: calcula um offset para que `target_pos` (geralmente o
  player) fique sempre centralizado na tela.
- Y-sort: sprites de "chão" (com atributo `ground`, ex: NonCollisionSprites)
  são desenhados primeiro, sempre atrás de tudo. Os demais sprites
  são ordenados pelo centro Y do rect — quanto mais para baixo na
  tela, mais "na frente" é desenhado. Isso dá a ilusão de profundidade
  (ex: o player passar por trás de uma árvore).
"""
from settings import *

class AllSprites(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.Vector2()

    def draw(self, target_pos):
        self.offset.x = -(target_pos[0] - WINDOW_WIDTH/2)
        self.offset.y = -(target_pos[1] - WINDOW_HEIGHT/2)

        ground_sprites = [sprite for sprite in self if hasattr(sprite, 'ground')]
        object_sprites = [sprite for sprite in self if not hasattr(sprite, 'ground')]

        for layer in [ground_sprites, object_sprites]:
            for sprite in sorted(layer, key=lambda sprite: sprite.rect.centery):
                self.display_surface.blit(sprite.image, sprite.rect.topleft + self.offset)

