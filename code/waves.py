"""
waves.py
========

Sistema de waves (ondas de inimigos).

A classe WaveManager cuida de:

  - saber em qual wave o jogo está e qual a configuração dela
    (quantidade/velocidade de inimigos, vindas de config.py)
  - fazer o "drip-feed": em vez de criar todos os inimigos de
    uma vez, cria um por vez a cada `spawn_interval` segundos
  - responder "a wave já acabou?" (wave_cleared)
  - escolher uma posição de spawn que não esteja muito perto
    do player (safe_spawn_position)
"""
from random import choice
from settings import *
from sprites import Enemy
from config import WAVE_CONFIG, MAX_WAVE


class WaveManager:
    def __init__(self):
        # Configurações fixas de spawn (não mudam entre waves)
        self.spawn_safe_radius = 250   # distância mínima do player para spawn
        self.spawn_interval    = 0.6   # segundos entre cada inimigo spawnado

        self.current_wave = 1
        self._load_wave(1)

    # ---------------------------------------------------------------- #
    #  CONTROLE DE WAVE                                                  #
    # ---------------------------------------------------------------- #
    def _load_wave(self, wave):
        """Lê a config da wave (config.py) e zera os contadores de spawn."""
        cfg = WAVE_CONFIG[wave]
        self.enemies_to_spawn = cfg['count']
        self.enemies_spawned  = 0
        self.enemy_speed      = cfg['speed']
        self.spawn_timer      = 0

    def advance(self):
        """Avança para a próxima wave (chamado ao apertar F / Start Wave)."""
        self.current_wave += 1
        self._load_wave(self.current_wave)

    def reset(self):
        """Volta para a wave 1 — usado no restart do jogo."""
        self.current_wave = 1
        self._load_wave(1)

    def is_last_wave(self):
        return self.current_wave >= MAX_WAVE

    # ---------------------------------------------------------------- #
    #  STATUS DA WAVE                                                    #
    # ---------------------------------------------------------------- #
    def enemies_remaining(self, enemy_sprites):
        """
        Inimigos que ainda contam para a wave atual:
        os que já estão na tela (vivos) + os que ainda vão nascer.
        """
        alive   = sum(1 for e in enemy_sprites if e.death_time == 0)
        pending = max(0, self.enemies_to_spawn - self.enemies_spawned)
        return alive + pending

    def wave_cleared(self, enemy_sprites):
        """
        True quando:
          - todos os inimigos da wave já nasceram, E
          - nenhum deles está mais vivo (todos com death_time != 0)
        """
        return (self.enemies_spawned >= self.enemies_to_spawn and
                all(e.death_time != 0 for e in enemy_sprites))

    # ---------------------------------------------------------------- #
    #  SPAWN                                                             #
    # ---------------------------------------------------------------- #
    def safe_spawn_position(self, game):
        """
        Escolhe um ponto de spawn (definido no Tiled) que esteja a
        pelo menos `spawn_safe_radius` pixels do player — assim o
        inimigo não nasce "em cima" do jogador.

        Se o mapa for pequeno e nenhum ponto estiver longe o
        suficiente, usa o ponto mais distante disponível.
        """
        player_pos = pygame.Vector2(game.player.rect.center)

        candidates = [
            p for p in game.spawn_positions
            if pygame.Vector2(p).distance_to(player_pos) >= self.spawn_safe_radius
        ]

        if not candidates:
            candidates = sorted(
                game.spawn_positions,
                key=lambda p: -pygame.Vector2(p).distance_to(player_pos)
            )

        return choice(candidates)

    def update_spawn(self, dt, game):
        """
        Chamado todo frame durante o gameplay.

        Acumula `dt` em spawn_timer; quando passa de
        `spawn_interval`, cria um inimigo novo e zera o timer.
        Para quando já nasceram todos os inimigos da wave.
        """
        if self.enemies_spawned >= self.enemies_to_spawn:
            return

        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0

            Enemy(self.safe_spawn_position(game),
                  choice(list(game.enemy_frames.values())),
                  (game.all_sprites, game.enemy_sprites),
                  game.player, game.collision_sprites,
                  speed=self.enemy_speed)

            self.enemies_spawned += 1
