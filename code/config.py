"""
config.py
=========

Constantes de balanceamento do jogo "Shoot and Run".

Este arquivo NÃO contém lógica — só números e dados que controlam
a dificuldade e as opções da loja. Se quiser ajustar o jogo
(mais inimigos, upgrades mais caros, mais waves...), é aqui que
você edita, sem precisar tocar no resto do código.
"""

# ------------------------------------------------------------------ #
#  WAVES                                                               #
# ------------------------------------------------------------------ #
# Cada chave é o número da wave. 'count' = quantos inimigos vão nascer
# nessa wave, 'speed' = velocidade de movimento desses inimigos.
# A progressão foi pensada para ficar cada vez mais difícil até a
# wave 10, que é a última (vitória).
WAVE_CONFIG = {
    1:  {'count':  4, 'speed': 160},
    2:  {'count':  6, 'speed': 175},
    3:  {'count':  8, 'speed': 190},
    4:  {'count': 10, 'speed': 205},
    5:  {'count': 12, 'speed': 220},
    6:  {'count': 15, 'speed': 235},
    7:  {'count': 18, 'speed': 250},
    8:  {'count': 22, 'speed': 265},
    9:  {'count': 26, 'speed': 280},
    10: {'count': 32, 'speed': 310},
}

# Última wave do jogo. Ao limpar essa wave, o jogador vence.
MAX_WAVE = 10

# Nome do arquivo onde o high score é salvo entre execuções do jogo.
SAVE_FILE = 'save.json'


# ------------------------------------------------------------------ #
#  UPGRADES DA ARMA (loja)                                             #
# ------------------------------------------------------------------ #
# Cada dict descreve um upgrade comprável na loja:
#   id         -> identificador usado pelo código (GunStats.apply_upgrade)
#   name/desc  -> textos mostrados no card da loja
#   max_level  -> quantas vezes esse upgrade pode ser comprado
#   cost_base  -> preço do nível 1. O preço de cada compra é
#                 cost_base * (nível_atual + 1), ou seja, fica
#                 mais caro a cada compra.
#   icon/color -> usados só na interface (ui.py)
GUN_UPGRADES = [
    {
        'id':        'spread_shot',
        'name':      'Spread Shot',
        'desc':      'Fire 3 bullets in a cone',
        'max_level': 3,
        'cost_base': 3,
        'icon':      '»',
        'color':     (100, 200, 255),
    },
    {
        'id':        'fire_rate',
        'name':      'Fire Rate',
        'desc':      'Reduce cooldown by 80ms',
        'max_level': 5,
        'cost_base': 2,
        'icon':      '⚡',
        'color':     (255, 230, 80),
    },
    {
        'id':        'bullet_speed',
        'name':      'Bullet Speed',
        'desc':      'Bullets travel 20% faster',
        'max_level': 4,
        'cost_base': 2,
        'icon':      '↑',
        'color':     (160, 255, 160),
    },
    {
        'id':        'piercing',
        'name':      'Piercing',
        'desc':      'Bullets pass through enemies',
        'max_level': 1,
        'cost_base': 8,
        'icon':      '◈',
        'color':     (255, 140, 60),
    },
]
