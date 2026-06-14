"""
main.py
=======

Ponto de entrada do jogo "Shoot and Run".

A classe Game é responsável por:
    - inicializar pygame, janela, áudio e grupos de sprites
    - guardar o ESTADO atual do jogo e trocar entre estados
    - processar eventos de teclado/mouse e decidir o que fazer
      com eles dependendo do estado atual
    - rodar o loop principal (update -> draw -> mostrar na tela)

A lógica específica de cada sistema foi movida para outros
arquivos, então o Game funciona como um "maestro" que chama
cada um na hora certa:

    config.py    -> constantes de balanceamento (waves, upgrades)
    weapons.py   -> Weapon (cooldown + criação de balas)
    waves.py     -> WaveManager (spawn e progressão de dificuldade)
    world.py     -> setup_world() (carrega o mapa, cria player/npc)
    ui.py        -> UI (desenha HUD, menus, loja, overlays)
    save_data.py -> load_high_score() / save_high_score()


ESTADOS DO JOGO (self.state)
-----------------------------
    'menu'        -> tela inicial com Play/Quit
    'playing'     -> gameplay normal (tiro, movimento, spawn de inimigos)
    'wave_clear'  -> intervalo entre waves (loja disponível)
    'shop'        -> loja aberta (jogo "pausado" visualmente)
    'game_over'   -> jogador morreu
    'victory'     -> todas as MAX_WAVE waves foram vencidas
"""
from settings import *
from groups import AllSprites

from config import GUN_UPGRADES
from weapons import Weapon
from waves import WaveManager
from world import setup_world
from ui import UI
from save_data import load_high_score, save_high_score


class Game:
    def __init__(self):
        # ---- janela / clock ----
        pygame.init()
        self.display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Shoot and Run')
        self.clock   = pygame.time.Clock()
        self.running = True

        # ---- progresso salvo entre execuções ----
        self.high_score = load_high_score()

        # ---- progresso da partida atual ----
        self.score = 0
        self.coins = 0
        self.upgrade_levels = {u['id']: 0 for u in GUN_UPGRADES}

        # ---- máquina de estados ----
        self.state = 'menu'

        # ---- grupos de sprites ----
        self.all_sprites       = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.bullet_sprites    = pygame.sprite.Group()
        self.enemy_sprites     = pygame.sprite.Group()
        self.spawn_positions   = []

        # ---- sistemas auxiliares ----
        self.weapon = Weapon()
        self.waves  = WaveManager()

        # ---- áudio ----
        self.shoot_sound  = pygame.mixer.Sound(join('audio', 'shoot.wav'))
        self.shoot_sound.set_volume(0.4)
        self.impact_sound = pygame.mixer.Sound(join('audio', 'impact.ogg'))
        self.music        = pygame.mixer.Sound(join('audio', 'music.wav'))
        self.music.set_volume(0.1)
        self.music.play(loops=-1)

        # ---- assets do jogo (balas/inimigos) ----
        self._load_game_assets()

        # ---- mundo (mapa, player, arma, npc) ----
        setup_world(self)

        # ---- interface (precisa do player já existir para o menu) ----
        self.ui = UI(self)

    # ================================================================ #
    #  CARREGAMENTO DE ASSETS                                            #
    # ================================================================ #
    def _load_game_assets(self):
        """
        Carrega imagens usadas pelo gameplay (não pela UI):
        sprite da bala e frames de animação dos inimigos.
        """
        self.bullet_surf = pygame.image.load(join('images', 'gun', 'bullet.png')).convert_alpha()

        # Cada subpasta dentro de images/enemies/ é um "tipo" de inimigo
        folders = list(walk(join('images', 'enemies')))[0][1]
        self.enemy_frames = {}
        for folder in folders:
            for folder_path, _, file_names in walk(join('images', 'enemies', folder)):
                self.enemy_frames[folder] = []
                for fn in sorted(file_names, key=lambda n: int(n.split('.')[0])):
                    surf = pygame.image.load(join(folder_path, fn)).convert_alpha()
                    self.enemy_frames[folder].append(surf)

    # ================================================================ #
    #  CONTROLE DO NPC DA LOJA                                           #
    # ================================================================ #
    def _show_npc(self, visible: bool):
        """
        Adiciona/remove o ShopNPC de all_sprites.

        O NPC só deve aparecer durante o intervalo entre waves
        ('wave_clear' / 'shop'); fora disso ele fica "escondido"
        simplesmente não estando no grupo de desenho.
        """
        if visible and self.shop_npc not in self.all_sprites:
            self.all_sprites.add(self.shop_npc)
        elif not visible and self.shop_npc in self.all_sprites:
            self.all_sprites.remove(self.shop_npc)

    # ================================================================ #
    #  COLISÕES                                                          #
    # ================================================================ #
    def bullet_collision(self):
        """Bala atinge inimigo -> inimigo morre, ganha score e coin."""
        for bullet in list(self.bullet_sprites):
            hits = pygame.sprite.spritecollide(
                bullet, self.enemy_sprites, False, pygame.sprite.collide_mask)

            if hits:
                self.impact_sound.play()
                for enemy in hits:
                    if enemy.death_time == 0:   # ignora inimigos já morrendo
                        enemy.destroy()
                        self.score += 10
                        self.coins += 1

                # Balas com piercing atravessam; as outras são destruídas
                if not bullet.piercing:
                    bullet.kill()

    def player_collision(self):
        """Inimigo toca o player -> player recebe dano (com cooldown interno)."""
        if pygame.sprite.spritecollide(
                self.player, self.enemy_sprites, False, pygame.sprite.collide_mask):
            self.player.take_damage()
            if self.player.is_dead:
                self.high_score = save_high_score(self.score, self.high_score)
                self.state = 'game_over'

    # ================================================================ #
    #  RESET / TRANSIÇÕES DE ESTADO                                      #
    # ================================================================ #
    def _full_restart(self):
        """Reinicia uma partida nova a partir do menu ou da tela de game over."""
        self.score = 0
        self.coins = 0
        self.upgrade_levels = {u['id']: 0 for u in GUN_UPGRADES}

        self.waves.reset()
        self.weapon.reset()

        # Esvazia todos os grupos e recria o mundo do zero
        self.all_sprites.empty()
        self.collision_sprites.empty()
        self.bullet_sprites.empty()
        self.enemy_sprites.empty()
        self.spawn_positions = []

        setup_world(self)
        self._show_npc(False)

        self.state = 'playing'

    def _go_to_menu(self):
        """Salva o high score e volta para a tela inicial."""
        self.high_score = save_high_score(self.score, self.high_score)
        self.state = 'menu'

    # ================================================================ #
    #  EVENTOS                                                           #
    # ================================================================ #
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.high_score = save_high_score(self.score, self.high_score)
                self.running = False

            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouseclick(event.pos)

    def _handle_keydown(self, event):
        """Teclas: F avança de wave, E abre/fecha a loja."""
        # F -> avança de wave (só se a wave atual já foi limpa)
        if (self.state == 'playing' and event.key == pygame.K_f
                and self.waves.wave_cleared(self.enemy_sprites)):

            if self.waves.is_last_wave():
                self.high_score = save_high_score(self.score, self.high_score)
                self.state = 'victory'
            else:
                self.state = 'wave_clear'
                self._show_npc(True)   # NPC aparece só no intervalo

        # E -> abre/fecha a loja quando perto do NPC
        if event.key == pygame.K_e:
            if self.state == 'wave_clear' and self.shop_npc.is_player_near(self.player.hitbox_rect):
                self.state = 'shop'
            elif self.state == 'shop':
                self.state = 'wave_clear'

    def _handle_mouseclick(self, pos):
        """Roteia o clique do mouse de acordo com o estado atual."""
        if self.state == 'menu':
            self._click_menu(pos)
        elif self.state == 'wave_clear':
            self._click_wave_clear(pos)
        elif self.state == 'shop':
            self._click_shop(pos)
        elif self.state in ('game_over', 'victory'):
            self._click_end_screen(pos)

    def _click_menu(self, pos):
        if self.ui.play_btn.collidepoint(pos):
            self._full_restart()
        elif self.ui.quit_btn.collidepoint(pos):
            self.high_score = save_high_score(self.score, self.high_score)
            self.running = False

    def _click_wave_clear(self, pos):
        if self.ui.next_wave_btn.collidepoint(pos):
            self.waves.advance()
            self._show_npc(False)
            self.state = 'playing'
        elif self.ui.open_shop_btn.collidepoint(pos):
            self.state = 'shop'

    def _click_shop(self, pos):
        if self.ui.close_shop_btn.collidepoint(pos):
            self.state = 'wave_clear'
            return

        # Verifica se algum card de upgrade foi clicado
        for i, rect in enumerate(self.ui.upgrade_rects):
            if rect.collidepoint(pos):
                upg   = GUN_UPGRADES[i]
                level = self.upgrade_levels[upg['id']]
                cost  = upg['cost_base'] * (level + 1)

                if level < upg['max_level'] and self.coins >= cost:
                    self.coins -= cost
                    self.upgrade_levels[upg['id']] += 1
                    self.weapon.stats.apply_upgrade(upg['id'])

    def _click_end_screen(self, pos):
        if self.ui.restart_btn.collidepoint(pos):
            self._full_restart()
        elif self.ui.menu_btn.collidepoint(pos):
            self._go_to_menu()

    # ================================================================ #
    #  UPDATE                                                            #
    # ================================================================ #
    def _update(self, dt):
        if self.state == 'playing':
            self.weapon.update_cooldown()
            self.weapon.try_fire(self)
            self.waves.update_spawn(dt, self)
            self.all_sprites.update(dt)
            self.bullet_collision()
            self.player_collision()

        elif self.state == 'wave_clear':
            # Durante o intervalo o player ainda pode andar e atirar
            # (ex: testar os upgrades recém-comprados), mas não
            # nascem novos inimigos.
            self.weapon.update_cooldown()
            self.weapon.try_fire(self)
            self.all_sprites.update(dt)

        elif self.state == 'shop':
            # Jogo "congelado" visualmente, mas sprites continuam
            # animando (ex: idle do player) para não dar a sensação
            # de tela travada.
            self.all_sprites.update(dt)

        # 'menu', 'game_over' e 'victory' não precisam de update —
        # são telas estáticas.

    # ================================================================ #
    #  DRAW                                                              #
    # ================================================================ #
    def _draw(self):
        if self.state == 'menu':
            self.ui.draw_menu()
            return

        # Todo o resto dos estados desenha o mundo + HUD por baixo
        self.all_sprites.draw(self.player.rect.center)
        self.ui.draw_hud()

        if self.state == 'wave_clear':
            self.ui.draw_wave_clear()
        elif self.state == 'shop':
            self.ui.draw_shop()
        elif self.state == 'game_over':
            self.ui.draw_game_over()
        elif self.state == 'victory':
            self.ui.draw_victory()

    # ================================================================ #
    #  LOOP PRINCIPAL                                                    #
    # ================================================================ #
    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000   # delta time em segundos

            self._handle_events()
            self._update(dt)
            self._draw()

            pygame.display.update()

        pygame.quit()


if __name__ == '__main__':
    game = Game()
    game.run()
