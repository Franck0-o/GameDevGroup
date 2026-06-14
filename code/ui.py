from settings import *
from config import GUN_UPGRADES, MAX_WAVE


class UI:
    def __init__(self, game):
        self.game    = game
        self.display = game.display

        # ---- fontes (criadas uma única vez) ----
        self.font_title  = pygame.font.SysFont('Arial', 64, bold=True)
        self.font_large  = pygame.font.SysFont('Arial', 42, bold=True)
        self.font_medium = pygame.font.SysFont('Arial', 30, bold=True)
        self.font_small  = pygame.font.SysFont('Arial', 22, bold=True)
        self.font_tiny   = pygame.font.SysFont('Arial', 16)

        self._load_images()
        self._build_surfaces_and_rects()

    def _load_images(self):
        self.hp_frames = []
        for i in range(6):
            try:
                self.hp_frames.append(
                    pygame.image.load(join('images', 'hud', f'hud_{i}.png')).convert_alpha())
            except FileNotFoundError:
                self.hp_frames.append(None)

        try:
            self.coin_icon = pygame.transform.scale(
                pygame.image.load(join('images', 'hud', 'coin.png')).convert_alpha(), (24, 24))
        except FileNotFoundError:
            self.coin_icon = None

        try:
            self.game_over_bg = pygame.image.load(join('images', 'hud', 'game_over.png')).convert_alpha()
        except FileNotFoundError:
            self.game_over_bg = None

        try:
            self.menu_bg = pygame.image.load(join('images', 'hud', 'menu_bg.png')).convert()
            self.menu_bg = pygame.transform.scale(self.menu_bg, (WINDOW_WIDTH, WINDOW_HEIGHT))
        except FileNotFoundError:
            self.menu_bg = None

    def _build_surfaces_and_rects(self):
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2

        self.panel_wide = pygame.Surface((700, 420), pygame.SRCALPHA)
        self.panel_wide.fill((10, 10, 10, 215))

        self.panel_narrow = pygame.Surface((520, 300), pygame.SRCALPHA)
        self.panel_narrow.fill((10, 10, 10, 215))

        bw, bh = 220, 54

        self.play_btn = pygame.Rect(cx - bw // 2, cy + 40,  bw, bh)
        self.quit_btn = pygame.Rect(cx - bw // 2, cy + 110, bw, bh)

        self.restart_btn    = pygame.Rect(cx - bw // 2, cy + 110, bw, bh)
        self.next_wave_btn  = pygame.Rect(cx - bw // 2, cy +  60, bw, bh)
        self.open_shop_btn  = pygame.Rect(cx - bw // 2, cy + 125, bw, bh)
        self.close_shop_btn = pygame.Rect(cx - bw // 2, cy + 160, bw, bh)
        self.menu_btn       = pygame.Rect(cx - bw // 2, cy + 175, bw, bh)

        self.upgrade_rects = []

    def shadow_text(self, font, text, color, pos, anchor='topleft'):
        shadow = font.render(text, True, (0, 0, 0))
        main   = font.render(text, True, color)
        self.display.blit(shadow, shadow.get_rect(**{anchor: (pos[0] + 1, pos[1] + 1)}))
        self.display.blit(main,   main.get_rect(**{anchor: pos}))

    def draw_button(self, rect, text, font,
                     hover=(80, 180, 80), base=(50, 140, 50), border=(255, 255, 255)):
        color = hover if rect.collidepoint(pygame.mouse.get_pos()) else base
        pygame.draw.rect(self.display, color,  rect, border_radius=10)
        pygame.draw.rect(self.display, border, rect, 2, border_radius=10)
        label = font.render(text, True, (255, 255, 255))
        self.display.blit(label, label.get_rect(center=rect.center))

    def dim_overlay(self, alpha=160):
        s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, alpha))
        self.display.blit(s, (0, 0))

    @staticmethod
    def _wrap_text(text, max_chars):
        lines, line = [], ''
        for word in text.split():
            if len(line) + len(word) + 1 <= max_chars:
                line = (line + ' ' + word).strip()
            else:
                lines.append(line)
                line = word
        lines.append(line)
        return lines

    def draw_menu(self):
        game = self.game
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2

        if self.menu_bg:
            self.display.blit(self.menu_bg, (0, 0))
        else:
            game.all_sprites.draw(game.player.rect.center)
            self.dim_overlay(120)

        self.shadow_text(self.font_title, 'SHOOT AND RUN',
                          (255, 220, 60), (cx, cy - 160), anchor='midtop')

        self.shadow_text(self.font_medium, f'High Score:  {game.high_score}',
                          (200, 200, 255), (cx, cy - 60), anchor='midtop')

        self.draw_button(self.play_btn, 'Play', self.font_medium,
                          hover=(80, 200, 80), base=(50, 150, 50))
        self.draw_button(self.quit_btn, 'Quit', self.font_medium,
                          hover=(200, 80, 80), base=(150, 50, 50))

    def draw_hud(self):
        game = self.game

        self._draw_health_bar()
        self._draw_wave_info()
        self.draw_upgrade_bar()
        self._draw_score_and_coins()
        self._draw_contextual_hints()

    def _draw_health_bar(self):
        """Barra de vida no canto superior esquerdo (5 níveis -> 6 sprites)."""
        game = self.game

        # health vai de 5 (cheia) a 0 (morto); frame correto = 5 - health
        frame_index = max(0, min(5, 5 - game.player.health))

        if self.hp_frames[frame_index]:
            self.display.blit(pygame.transform.scale2x(self.hp_frames[frame_index]), (16, 16))
        else:
            # Fallback: quadradinhos vermelhos/cinza caso as imagens não existam
            for i in range(game.player.max_health):
                color = (220, 50, 50) if i < game.player.health else (60, 60, 60)
                pygame.draw.rect(self.display, color, (20 + i * 34, 20, 28, 28), border_radius=4)
                pygame.draw.rect(self.display, (255, 255, 255), (20 + i * 34, 20, 28, 28), 2, border_radius=4)

    def _draw_wave_info(self):
        """Número da wave atual e contagem de inimigos, no topo central."""
        game = self.game

        self.shadow_text(self.font_medium,
                          f'Wave {game.waves.current_wave} / {MAX_WAVE}',
                          (255, 230, 100), (WINDOW_WIDTH // 2, 14), anchor='midtop')

        remaining = game.waves.enemies_remaining(game.enemy_sprites)
        self.shadow_text(self.font_small, f'Enemies: {remaining}',
                          (255, 100, 100) if remaining else (100, 255, 100),
                          (WINDOW_WIDTH // 2, 50), anchor='midtop')

    def _draw_score_and_coins(self):
        """Score e moedas no canto superior direito."""
        game = self.game

        self.shadow_text(self.font_small, f'Score: {game.score}',
                          (255, 255, 255), (WINDOW_WIDTH - 20, 20), anchor='topright')

        coin_txt = f'x {game.coins}'
        if self.coin_icon:
            icon_x = WINDOW_WIDTH - 20 - self.font_small.size(coin_txt)[0] - 30
            self.display.blit(self.coin_icon, (icon_x, 48))
        self.shadow_text(self.font_small, coin_txt,
                          (255, 220, 50), (WINDOW_WIDTH - 20, 50), anchor='topright')

    def _draw_contextual_hints(self):
        """Mensagens que aparecem só em certas situações (loja perto, wave limpa)."""
        game = self.game

        # Dica para abrir a loja — só durante o intervalo entre waves
        if (game.state == 'wave_clear' and
                game.shop_npc in game.all_sprites and
                game.shop_npc.is_player_near(game.player.hitbox_rect)):
            self.shadow_text(self.font_small, 'Press  E  to open shop',
                              (255, 240, 120), (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 80),
                              anchor='midbottom')

        # Dica para avançar de wave — só quando a wave atual já acabou
        if game.state == 'playing' and game.waves.wave_cleared(game.enemy_sprites):
            self.shadow_text(self.font_medium,
                              'Wave clear!  Press  F  to continue',
                              (100, 255, 160),
                              (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50),
                              anchor='midbottom')

    def draw_upgrade_bar(self):
        """
        Mostra, no canto inferior esquerdo, um "badge" para cada
        upgrade que o jogador já comprou (ícone + nome + nível).
        Upgrades no nível 0 não aparecem.
        """
        game = self.game
        x, y = 20, WINDOW_HEIGHT - 36

        for upg in GUN_UPGRADES:
            level = game.upgrade_levels[upg['id']]
            if level == 0:
                continue

            badge = self.font_tiny.render(f"{upg['icon']} {upg['name']} {level}", True, upg['color'])

            # Fundo escuro semi-transparente para o texto ficar legível
            bg = pygame.Surface((badge.get_width() + 8, badge.get_height() + 4), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 140))
            self.display.blit(bg, (x - 4, y - 2))
            self.display.blit(badge, (x, y))

            x += badge.get_width() + 20   # próximo badge à direita

    # ================================================================ #
    #  TELA DE INTERVALO ENTRE WAVES                                     #
    # ================================================================ #
    def draw_wave_clear(self):
        game = self.game
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2

        self.dim_overlay(100)
        self.display.blit(self.panel_wide, self.panel_wide.get_rect(center=(cx, cy - 20)))

        self.shadow_text(self.font_large, f'Wave {game.waves.current_wave} Complete!',
                          (100, 255, 160), (cx, cy - 130), anchor='midtop')

        self.shadow_text(self.font_small, f'Score: {game.score}   Coins: {game.coins}',
                          (200, 200, 200), (cx, cy - 75), anchor='midtop')

        if not game.waves.is_last_wave():
            self.draw_button(self.next_wave_btn, f'Start Wave {game.waves.current_wave + 1}',
                              self.font_small, hover=(80, 180, 80), base=(50, 140, 50))
            self.draw_button(self.open_shop_btn, 'Open Shop  ( E )',
                              self.font_small, hover=(180, 140, 60), base=(140, 100, 30))
        else:
            self.draw_button(self.next_wave_btn, 'Finish!',
                              self.font_small, hover=(80, 180, 80), base=(50, 140, 50))

    # ================================================================ #
    #  LOJA                                                              #
    # ================================================================ #
    def draw_shop(self):
        game = self.game
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        self.dim_overlay(170)

        panel_rect = self.panel_wide.get_rect(center=(cx, cy))
        self.display.blit(self.panel_wide, panel_rect)

        self.shadow_text(self.font_large, 'S H O P', (255, 220, 60),
                          (cx, panel_rect.top + 14), anchor='midtop')
        self.shadow_text(self.font_medium, f'Coins:  {game.coins}',
                          (255, 220, 50), (cx, panel_rect.top + 66), anchor='midtop')

        # Layout dos cards: distribuídos lado a lado, centralizados no painel
        card_w, card_h = 140, 170
        cols    = len(GUN_UPGRADES)
        total_w = cols * card_w + (cols - 1) * 16
        start_x = cx - total_w // 2
        card_y  = panel_rect.top + 118

        # Recalculado a cada frame: main.py usa essa lista para
        # detectar em qual card o jogador clicou.
        self.upgrade_rects = []

        for i, upg in enumerate(GUN_UPGRADES):
            level   = game.upgrade_levels[upg['id']]
            maxed   = level >= upg['max_level']
            cost    = upg['cost_base'] * (level + 1)
            can_buy = not maxed and game.coins >= cost

            card_x = start_x + i * (card_w + 16)
            rect = pygame.Rect(card_x, card_y, card_w, card_h)
            self.upgrade_rects.append(rect)

            self._draw_upgrade_card(rect, upg, level, maxed, cost, can_buy)

        self.draw_button(self.close_shop_btn, 'Close  ( E )', self.font_small,
                          hover=(180, 80, 80), base=(130, 50, 50))

    def _draw_upgrade_card(self, rect, upg, level, maxed, cost, can_buy):
        """
        Desenha um único card de upgrade: fundo, ícone, nome,
        descrição (com quebra de linha), bolinhas de nível e preço.
        """
        # Cor do card depende do estado: maxed / pode comprar / não pode
        if maxed:
            bg_color, border_color = (40, 70, 40), (80, 160, 80)
        elif can_buy and rect.collidepoint(pygame.mouse.get_pos()):
            bg_color, border_color = (60, 60, 90), (200, 200, 255)
        else:
            bg_color, border_color = (35, 35, 55), (90, 90, 120)

        pygame.draw.rect(self.display, bg_color, rect, border_radius=10)
        pygame.draw.rect(self.display, border_color, rect, 2, border_radius=10)

        cx_ = rect.centerx

        # Ícone grande no topo do card
        icon_surf = self.font_large.render(upg['icon'], True, upg['color'])
        self.display.blit(icon_surf, icon_surf.get_rect(midtop=(cx_, rect.top + 8)))

        # Nome do upgrade
        name_surf = self.font_tiny.render(upg['name'], True, (230, 230, 230))
        self.display.blit(name_surf, name_surf.get_rect(midtop=(cx_, rect.top + 54)))

        # Descrição — quebrada em linhas de até 18 caracteres
        for li, line in enumerate(self._wrap_text(upg['desc'], 18)):
            line_surf = self.font_tiny.render(line, True, (160, 160, 160))
            self.display.blit(line_surf, line_surf.get_rect(midtop=(cx_, rect.top + 72 + li * 16)))

        # Bolinhas mostrando nível atual / nível máximo
        pip_y  = rect.top + 118
        pip_x0 = cx_ - upg['max_level'] * 10 // 2
        for p in range(upg['max_level']):
            color = upg['color'] if p < level else (60, 60, 60)
            pygame.draw.circle(self.display, color, (pip_x0 + p * 10 + 4, pip_y), 4)

        # Preço (ou "MAXED" se já está no nível máximo)
        if maxed:
            tag = self.font_tiny.render('MAXED', True, (80, 220, 80))
        elif can_buy:
            tag = self.font_tiny.render(f'{cost} coins', True, (255, 220, 50))
        else:
            tag = self.font_tiny.render(f'{cost} coins', True, (120, 100, 50))
        self.display.blit(tag, tag.get_rect(midbottom=(cx_, rect.bottom - 6)))

    # ================================================================ #
    #  GAME OVER / VITÓRIA                                               #
    # ================================================================ #
    def draw_game_over(self):
        game = self.game
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        self.dim_overlay(160)

        if self.game_over_bg:
            self.display.blit(self.game_over_bg, self.game_over_bg.get_rect(center=(cx, cy - 60)))

        self.display.blit(self.panel_narrow, self.panel_narrow.get_rect(center=(cx, cy)))
        self.shadow_text(self.font_large, 'GAME  OVER', (220, 60, 60), (cx, cy - 100), anchor='midtop')
        self.shadow_text(self.font_small,
                          f'Wave {game.waves.current_wave}   Score: {game.score}   Best: {game.high_score}',
                          (200, 200, 200), (cx, cy - 45), anchor='midtop')

        self.draw_button(self.restart_btn, 'Play Again', self.font_small)
        self.draw_button(self.menu_btn, 'Main Menu', self.font_small,
                          hover=(80, 80, 180), base=(50, 50, 140))

    def draw_victory(self):
        game = self.game
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        self.dim_overlay(150)

        self.display.blit(self.panel_narrow, self.panel_narrow.get_rect(center=(cx, cy)))
        self.shadow_text(self.font_large, 'YOU  WIN!', (80, 220, 120), (cx, cy - 100), anchor='midtop')
        self.shadow_text(self.font_small,
                          f'All {MAX_WAVE} waves cleared!   Score: {game.score}   Best: {game.high_score}',
                          (200, 200, 200), (cx, cy - 45), anchor='midtop')

        self.draw_button(self.restart_btn, 'Play Again', self.font_small)
        self.draw_button(self.menu_btn, 'Main Menu', self.font_small,
                          hover=(80, 80, 180), base=(50, 50, 140))
