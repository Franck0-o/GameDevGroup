"""
world.py
========

Carrega o mapa do Tiled (.tmx) e cria todos os sprites do mundo:
chão, objetos com colisão, o player, a arma e o NPC da loja.

A função setup_world() é chamada tanto no __init__ do jogo quanto
em todo restart — ela espera que `game` já tenha os grupos de
sprites (all_sprites, collision_sprites etc) criados e vazios.
"""
from settings import *
from player import Player
from sprites import Gun, CollisionSprites, NonCollisionSprites, ShopNPC
from pytmx.util_pygame import load_pygame


def setup_world(game):
    """
    Popula os grupos de sprites de `game` a partir do mapa Tiled
    e define os seguintes atributos em `game`:

        game.player          -> instância de Player, controlada pelo usuário
        game.gun             -> instância de Gun, segue o player e o mouse
        game.shop_npc        -> instância de ShopNPC (loja)
        game.spawn_positions -> lista de (x, y) onde inimigos podem nascer
    """
    map_data = load_pygame(join('data', 'maps', 'world.tmx'))

    # Layer "Ground" — tiles de chão, puramente visuais (sem colisão).
    # NonCollisionSprites tem o atributo `ground`, usado pelo AllSprites
    # para desenhar o chão sempre atrás dos outros sprites.
    for x, y, image in map_data.get_layer_by_name('Ground').tiles():
        NonCollisionSprites((x * TILE_SIZE, y * TILE_SIZE), image, game.all_sprites)

    # Layer "Objects" — objetos do mapa (árvores, pedras, etc) que
    # bloqueiam o movimento do player e dos inimigos.
    for obj in map_data.get_layer_by_name('Objects'):
        CollisionSprites((obj.x, obj.y), obj.image,
                         (game.all_sprites, game.collision_sprites))

    # Layer "Collisions" — retângulos invisíveis usados só para
    # colisão (ex: limites do mapa, áreas bloqueadas sem sprite visual).
    for cs in map_data.get_layer_by_name('Collisions'):
        CollisionSprites((cs.x, cs.y),
                         pygame.Surface((cs.width, cs.height)),
                         game.collision_sprites)

    # Layer "Entities" — posição inicial do player e pontos onde
    # inimigos podem nascer (todo objeto que não se chama "Player").
    for obj in map_data.get_layer_by_name('Entities'):
        if obj.name == 'Player':
            game.player = Player((obj.x, obj.y), 400, game.all_sprites, game.collision_sprites)
            game.gun = Gun(game.player, game.all_sprites)
        else:
            game.spawn_positions.append((obj.x, obj.y))

    # NPC da loja: criado aqui, mas de propósito NÃO adicionado a
    # all_sprites ainda. Ele só fica visível durante o intervalo
    # entre waves — main.py controla isso com _show_npc().
    if game.spawn_positions:
        shop_pos = (game.spawn_positions[0][0] - 120, game.spawn_positions[0][1])
    else:
        shop_pos = (200, 200)

    game.shop_npc = ShopNPC(shop_pos, game.all_sprites)
