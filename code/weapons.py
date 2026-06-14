"""
weapons.py
==========

Sistema de arma do jogador.

Contém duas classes:

GunStats
    Guarda o NÍVEL de cada upgrade comprado (spread, fire rate,
    bullet speed, piercing) e calcula, a partir desses níveis,
    os valores reais usados pelo jogo (cooldown em ms, quantas
    balas saem por tiro, velocidade da bala etc).

Weapon
    Usa o GunStats para de fato criar as balas na tela e controlar
    o cooldown entre tiros. É essa classe que o main.py chama
    todo frame.
"""
import math
from settings import *
from sprites import Bullet


class GunStats:
    """Guarda os níveis de upgrade e calcula os valores derivados."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Volta todos os upgrades para o nível 0 (jogo novo)."""
        self.spread_level   = 0   # 0=1 bala, 1=3, 2=5, 3=7
        self.fire_rate_lvl  = 0   # cada nível tira 80ms do cooldown
        self.bullet_spd_lvl = 0   # cada nível dá +20% de velocidade
        self.piercing       = False

    # ---- valores derivados, usados pela classe Weapon ---- #

    @property
    def cooldown(self):
        """Tempo (ms) entre um tiro e outro. Nunca cai abaixo de 100ms."""
        return max(100, 600 - self.fire_rate_lvl * 80)

    @property
    def bullet_count(self):
        """Quantas balas saem em cada disparo: 1, 3, 5 ou 7."""
        return 1 + self.spread_level * 2

    @property
    def spread_angle(self):
        """Ângulo (graus) entre cada bala quando há mais de uma."""
        return 12 if self.spread_level else 0

    @property
    def bullet_velocity(self):
        """Velocidade da bala em pixels/segundo."""
        return 1200 * (1 + self.bullet_spd_lvl * 0.20)

    def apply_upgrade(self, upgrade_id):
        """Sobe o nível do upgrade comprado na loja (chamado por main.py)."""
        if upgrade_id == 'spread_shot':
            self.spread_level = min(3, self.spread_level + 1)
        elif upgrade_id == 'fire_rate':
            self.fire_rate_lvl = min(5, self.fire_rate_lvl + 1)
        elif upgrade_id == 'bullet_speed':
            self.bullet_spd_lvl = min(4, self.bullet_spd_lvl + 1)
        elif upgrade_id == 'piercing':
            self.piercing = True


class Weapon:
    """
    Controla o disparo do jogador.

    Junta o "estado de cooldown" (pode atirar agora? quando foi
    o último tiro?) com o GunStats (quantas balas, que velocidade,
    etc) para criar as balas de fato.
    """

    def __init__(self):
        self.stats      = GunStats()
        self.can_shoot  = True
        self.shoot_time = 0

    def reset(self):
        """Usado no restart: zera upgrades e cooldown."""
        self.stats.reset()
        self.can_shoot  = True
        self.shoot_time = 0

    def update_cooldown(self):
        """Chamado todo frame: libera o próximo tiro quando o tempo passa."""
        if not self.can_shoot:
            if pygame.time.get_ticks() - self.shoot_time >= self.stats.cooldown:
                self.can_shoot = True

    def try_fire(self, game):
        """
        Chamado todo frame durante o gameplay.
        Se o botão esquerdo do mouse estiver pressionado e o cooldown
        já tiver acabado, dispara.
        """
        if pygame.mouse.get_pressed()[0] and self.can_shoot:
            self._fire(game)

    def _fire(self, game):
        """
        Cria as balas de acordo com os upgrades atuais.

        - bullet_count define quantas balas saem
        - spread_angle define o ângulo entre elas (em leque)
        - bullet_velocity e piercing vêm direto do GunStats
        """
        game.shoot_sound.play()

        origin   = game.gun.rect.center + game.gun.player_direction * 50
        base_dir = game.gun.player_direction
        count    = self.stats.bullet_count
        spread   = self.stats.spread_angle

        # Calcula os ângulos de cada bala em torno da direção base.
        # Exemplo: count=3, spread=12  ->  offsets = [-12, 0, 12]
        if count == 1:
            offsets = [0]
        else:
            offsets = [-spread * (count // 2) + spread * i for i in range(count)]

        for offset_deg in offsets:
            # Rotaciona o vetor direção pelo ângulo do offset
            rad = math.radians(offset_deg)
            cos_, sin_ = math.cos(rad), math.sin(rad)
            direction = pygame.Vector2(
                base_dir.x * cos_ - base_dir.y * sin_,
                base_dir.x * sin_ + base_dir.y * cos_
            )

            Bullet(game.bullet_surf, origin, direction,
                   (game.all_sprites, game.bullet_sprites),
                   velocity=self.stats.bullet_velocity,
                   piercing=self.stats.piercing)

        self.can_shoot  = False
        self.shoot_time = pygame.time.get_ticks()
