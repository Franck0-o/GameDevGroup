from settings import *
from player import Player
from sprites import *
from pytmx.util_pygame import load_pygame
from groups import AllSprites
from random import choice

# ------------------------------------------------------------------ #
#  WAVE CONFIGURATION  (10 waves)                                      #
#  Each entry: (enemy_count, enemy_speed)                              #
#  Wave 10 is the final boss-rush: lots of fast enemies               #
# ------------------------------------------------------------------ #
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
   10:  {'count': 32, 'speed': 310},
}
MAX_WAVE = 10


class Game:
    def __init__(self):
        pygame.init()
        self.display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Shoot and Run')
        self.clock = pygame.time.Clock()
        self.running = True

        # ---- fonts ----
        self.font_large  = pygame.font.SysFont('Arial', 42, bold=True)
        self.font_medium = pygame.font.SysFont('Arial', 30, bold=True)
        self.font_small  = pygame.font.SysFont('Arial', 22, bold=True)

        # ---- game state ----
        # states: 'playing' | 'between_waves' | 'shop' | 'game_over' | 'victory'
        self.state = 'playing'

        # ---- score / coins ----
        self.score = 0
        self.coins = 0

        # ---- wave system ----
        self.current_wave   = 1
        self.enemies_to_spawn = WAVE_CONFIG[1]['count']
        self.enemies_spawned  = 0
        self.wave_enemy_speed = WAVE_CONFIG[1]['speed']

        # Spawn queue timer  (we drip-feed enemies, not all at once)
        self.spawn_timer    = 0
        self.spawn_interval = 0.6   # seconds between each enemy spawn

        # ---- groups ----
        self.all_sprites       = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.bullet_sprites    = pygame.sprite.Group()
        self.enemy_sprites     = pygame.sprite.Group()

        # ---- shooting ----
        self.can_shoot    = True
        self.shoot_time   = 0
        self.gun_cooldown = 600

        # ---- safe radius for spawns ----
        self.spawn_safe_radius = 250
        self.spawn_positions   = []

        # ---- audio ----
        self.shoot_sound  = pygame.mixer.Sound(join('audio', 'shoot.wav'))
        self.shoot_sound.set_volume(0.4)
        self.impact_sound = pygame.mixer.Sound(join('audio', 'impact.ogg'))
        self.music        = pygame.mixer.Sound(join('audio', 'music.wav'))
        self.music.set_volume(0.1)
        self.music.play(loops=-1)

        self.load_images()
        self.setup()
        self._build_ui_surfaces()

    # ================================================================ #
    #  LOAD                                                              #
    # ================================================================ #
    def load_images(self):
        self.bullet_surf = pygame.image.load(join('images', 'gun', 'bullet.png')).convert_alpha()

        # Enemy frames
        folders = list(walk(join('images', 'enemies')))[0][1]
        self.enemy_frames = {}
        for folder in folders:
            for folder_path, _, file_names in walk(join('images', 'enemies', folder)):
                self.enemy_frames[folder] = []
                for file_name in sorted(file_names, key=lambda n: int(n.split('.')[0])):
                    surf = pygame.image.load(join(folder_path, file_name)).convert_alpha()
                    self.enemy_frames[folder].append(surf)

        # HP bar — hud_0.png (full) … hud_5.png (empty)
        self.hp_frames = []
        for i in range(6):
            try:
                self.hp_frames.append(pygame.image.load(join('images', 'hud', f'hud_{i}.png')).convert_alpha())
            except FileNotFoundError:
                self.hp_frames.append(None)

        # Coin icon
        try:
            self.coin_icon = pygame.transform.scale(
                pygame.image.load(join('images', 'hud', 'coin.png')).convert_alpha(), (28, 28))
        except FileNotFoundError:
            self.coin_icon = None

        # Game-over art
        try:
            self.game_over_bg = pygame.image.load(join('images', 'hud', 'game_over.png')).convert_alpha()
        except FileNotFoundError:
            self.game_over_bg = None

    def setup(self):
        map_data = load_pygame(join('data', 'maps', 'world.tmx'))

        for x, y, image in map_data.get_layer_by_name('Ground').tiles():
            NonCollisionSprites((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)

        for obj in map_data.get_layer_by_name('Objects'):
            CollisionSprites((obj.x, obj.y), obj.image, (self.all_sprites, self.collision_sprites))

        for cs in map_data.get_layer_by_name('Collisions'):
            CollisionSprites((cs.x, cs.y), pygame.Surface((cs.width, cs.height)), self.collision_sprites)

        for obj in map_data.get_layer_by_name('Entities'):
            if obj.name == 'Player':
                self.player = Player((obj.x, obj.y), 400, self.all_sprites, self.collision_sprites)
                self.gun    = Gun(self.player, self.all_sprites)
            else:
                self.spawn_positions.append((obj.x, obj.y))

        # ---- Shop NPC ----
        # Position it near the first spawn point; move freely in Tiled later.
        shop_pos = (self.spawn_positions[0][0] - 120, self.spawn_positions[0][1]) if self.spawn_positions else (200, 200)
        self.shop_npc = ShopNPC(shop_pos, self.all_sprites)

    def _build_ui_surfaces(self):
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2

        # Reusable dark panel
        self.panel_surf = pygame.Surface((560, 340), pygame.SRCALPHA)
        self.panel_surf.fill((10, 10, 10, 210))

        # Restart / next buttons
        bw, bh = 210, 54
        self.restart_btn = pygame.Rect(cx - bw // 2, cy + 90, bw, bh)
        self.next_btn    = pygame.Rect(cx - bw // 2, cy + 20, bw, bh)
        self.close_shop_btn = pygame.Rect(cx - bw // 2, cy + 100, bw, bh)

    # ================================================================ #
    #  WAVE LOGIC                                                        #
    # ================================================================ #
    def _load_wave(self, wave):
        cfg = WAVE_CONFIG[wave]
        self.enemies_to_spawn = cfg['count']
        self.enemies_spawned  = 0
        self.wave_enemy_speed = cfg['speed']
        self.spawn_timer      = 0

    def enemies_remaining(self):
        """Enemies still alive OR still waiting to be spawned."""
        alive   = len([e for e in self.enemy_sprites if e.death_time == 0])
        pending = self.enemies_to_spawn - self.enemies_spawned
        return alive + pending

    def wave_cleared(self):
        return (self.enemies_spawned >= self.enemies_to_spawn
                and len([e for e in self.enemy_sprites if e.death_time == 0]) == 0)

    def _advance_wave(self):
        if self.current_wave >= MAX_WAVE:
            self.state = 'victory'
        else:
            self.current_wave += 1
            self._load_wave(self.current_wave)
            self.state = 'playing'

    # ================================================================ #
    #  INPUT / TIMERS                                                    #
    # ================================================================ #
    def input_playing(self):
        if pygame.mouse.get_pressed()[0] and self.can_shoot:
            self.shoot_sound.play()
            pos = self.gun.rect.center + self.gun.player_direction * 50
            Bullet(self.bullet_surf, pos, self.gun.player_direction, (self.all_sprites, self.bullet_sprites))
            self.can_shoot  = False
            self.shoot_time = pygame.time.get_ticks()

    def gun_timer(self):
        if not self.can_shoot:
            if pygame.time.get_ticks() - self.shoot_time >= self.gun_cooldown:
                self.can_shoot = True

    # ================================================================ #
    #  SPAWN                                                             #
    # ================================================================ #
    def safe_spawn_position(self):
        player_pos = pygame.Vector2(self.player.rect.center)
        candidates = [p for p in self.spawn_positions
                      if pygame.Vector2(p).distance_to(player_pos) >= self.spawn_safe_radius]
        if not candidates:
            candidates = sorted(self.spawn_positions,
                                key=lambda p: -pygame.Vector2(p).distance_to(player_pos))
        return choice(candidates)

    def update_spawn(self, dt):
        """Drip-feed enemies one by one using a timer."""
        if self.enemies_spawned >= self.enemies_to_spawn:
            return
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            pos = self.safe_spawn_position()
            Enemy(pos, choice(list(self.enemy_frames.values())),
                  (self.all_sprites, self.enemy_sprites),
                  self.player, self.collision_sprites,
                  speed=self.wave_enemy_speed)
            self.enemies_spawned += 1

    # ================================================================ #
    #  COLLISIONS                                                        #
    # ================================================================ #
    def bullet_collision(self):
        for bullet in list(self.bullet_sprites):
            hits = pygame.sprite.spritecollide(bullet, self.enemy_sprites, False, pygame.sprite.collide_mask)
            if hits:
                self.impact_sound.play()
                for enemy in hits:
                    if enemy.death_time == 0:
                        enemy.destroy()
                        self.score += 10
                        self.coins += 1
                bullet.kill()

    def player_collision(self):
        if pygame.sprite.spritecollide(self.player, self.enemy_sprites, False, pygame.sprite.collide_mask):
            self.player.take_damage()
            if self.player.is_dead:
                self.state = 'game_over'

    # ================================================================ #
    #  DRAW HELPERS                                                      #
    # ================================================================ #
    def _shadow_text(self, font, text, color, pos, anchor='topleft'):
        shadow = font.render(text, True, (0, 0, 0))
        main   = font.render(text, True, color)
        sr = shadow.get_rect(**{anchor: (pos[0] + 1, pos[1] + 1)})
        mr = main.get_rect(**{anchor: pos})
        self.display.blit(shadow, sr)
        self.display.blit(main, mr)

    def _draw_button(self, rect, text, font, hover_color=(80, 180, 80), base_color=(50, 140, 50)):
        color = hover_color if rect.collidepoint(pygame.mouse.get_pos()) else base_color
        pygame.draw.rect(self.display, color, rect, border_radius=10)
        pygame.draw.rect(self.display, (255, 255, 255), rect, 2, border_radius=10)
        label = font.render(text, True, (255, 255, 255))
        self.display.blit(label, label.get_rect(center=rect.center))

    # ================================================================ #
    #  HUD                                                               #
    # ================================================================ #
    def draw_hud(self):
        # HP bar
        frame_index = max(0, min(5, 5 - self.player.health))
        if self.hp_frames[frame_index]:
            scaled = pygame.transform.scale2x(self.hp_frames[frame_index])
            self.display.blit(scaled, (16, 16))
        else:
            for i in range(self.player.max_health):
                color = (220, 50, 50) if i < self.player.health else (60, 60, 60)
                pygame.draw.rect(self.display, color, (20 + i * 34, 20, 28, 28), border_radius=4)
                pygame.draw.rect(self.display, (255, 255, 255), (20 + i * 34, 20, 28, 28), 2, border_radius=4)

        # Wave info — top center
        wave_txt = f'Wave  {self.current_wave} / {MAX_WAVE}'
        self._shadow_text(self.font_medium, wave_txt, (255, 230, 100),
                          (WINDOW_WIDTH // 2, 14), anchor='midtop')

        # Enemies remaining — below wave
        rem = self.enemies_remaining()
        rem_txt = f'Enemies: {rem}'
        rem_color = (255, 100, 100) if rem > 0 else (100, 255, 100)
        self._shadow_text(self.font_small, rem_txt, rem_color,
                          (WINDOW_WIDTH // 2, 50), anchor='midtop')

        # "F to start next wave" hint when cleared
        if self.wave_cleared() and self.current_wave < MAX_WAVE:
            hint = 'Wave clear!  Press  F  to continue'
            self._shadow_text(self.font_medium, hint, (100, 255, 160),
                              (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50), anchor='midbottom')

        # Shop proximity hint
        if self.shop_npc.is_player_near(self.player.hitbox_rect) and self.state == 'playing':
            self._shadow_text(self.font_small, 'Press  E  to open shop',
                              (255, 240, 120),
                              (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 80), anchor='midbottom')

        # Score — top right
        self._shadow_text(self.font_small, f'Score: {self.score}',
                          (255, 255, 255),
                          (WINDOW_WIDTH - 20, 20), anchor='topright')

        # Coins — below score
        coin_txt = f'x {self.coins}'
        cx_pos   = WINDOW_WIDTH - 20
        cy_pos   = 50
        if self.coin_icon:
            self.display.blit(self.coin_icon, (cx_pos - self.font_small.size(coin_txt)[0] - 36, cy_pos - 2))
        self._shadow_text(self.font_small, coin_txt, (255, 220, 50),
                          (cx_pos, cy_pos), anchor='topright')

    # ================================================================ #
    #  OVERLAY SCREENS                                                   #
    # ================================================================ #
    def draw_game_over(self):
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        self.display.blit(dim, (0, 0))
        if self.game_over_bg:
            self.display.blit(self.game_over_bg, self.game_over_bg.get_rect(center=(cx, cy - 60)))
        self.display.blit(self.panel_surf, self.panel_surf.get_rect(center=(cx, cy)))
        self._shadow_text(self.font_large, 'GAME  OVER', (220, 60, 60), (cx, cy - 100), anchor='midtop')
        self._shadow_text(self.font_small,
                          f'Wave {self.current_wave}   Score: {self.score}   Coins: {self.coins}',
                          (200, 200, 200), (cx, cy - 40), anchor='midtop')
        self._draw_button(self.restart_btn, 'Play Again', self.font_small)

    def draw_victory(self):
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        self.display.blit(dim, (0, 0))
        self.display.blit(self.panel_surf, self.panel_surf.get_rect(center=(cx, cy)))
        self._shadow_text(self.font_large, 'YOU  WIN!', (80, 220, 120), (cx, cy - 100), anchor='midtop')
        self._shadow_text(self.font_small,
                          f'All {MAX_WAVE} waves cleared!   Score: {self.score}   Coins: {self.coins}',
                          (200, 200, 200), (cx, cy - 40), anchor='midtop')
        self._draw_button(self.restart_btn, 'Play Again', self.font_small)

    def draw_shop(self):
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        self.display.blit(dim, (0, 0))
        self.display.blit(self.panel_surf, self.panel_surf.get_rect(center=(cx, cy)))

        self._shadow_text(self.font_large, 'S H O P', (255, 220, 60), (cx, cy - 120), anchor='midtop')
        self._shadow_text(self.font_small, f'Coins: {self.coins}', (255, 220, 50), (cx, cy - 60), anchor='midtop')

        # Placeholder item slots
        slot_labels = ['Item slot 1', 'Item slot 2', 'Item slot 3']
        for i, label in enumerate(slot_labels):
            sx = cx - 180 + i * 130
            sy = cy - 10
            pygame.draw.rect(self.display, (60, 60, 80), (sx, sy, 110, 90), border_radius=8)
            pygame.draw.rect(self.display, (140, 140, 160), (sx, sy, 110, 90), 2, border_radius=8)
            txt = self.font_small.render(label, True, (160, 160, 160))
            self.display.blit(txt, txt.get_rect(center=(sx + 55, sy + 45)))

        self._shadow_text(self.font_small, '(Items coming soon)', (140, 140, 140), (cx, cy + 90), anchor='midtop')
        self._draw_button(self.close_shop_btn, 'Close  ( E )', self.font_small,
                          hover_color=(180, 80, 80), base_color=(140, 50, 50))

    # ================================================================ #
    #  RESET                                                             #
    # ================================================================ #
    def restart(self):
        self.state        = 'playing'
        self.score        = 0
        self.coins        = 0
        self.current_wave = 1
        self._load_wave(1)

        self.all_sprites.empty()
        self.collision_sprites.empty()
        self.bullet_sprites.empty()
        self.enemy_sprites.empty()
        self.spawn_positions = []
        self.can_shoot  = True
        self.shoot_time = 0

        self.setup()

    # ================================================================ #
    #  MAIN LOOP                                                         #
    # ================================================================ #
    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type == pygame.KEYDOWN:
                    # Next wave
                    if event.key == pygame.K_f and self.state == 'playing' and self.wave_cleared():
                        _advance = True
                        if self.current_wave < MAX_WAVE:
                            self._advance_wave()

                    # Open / close shop
                    if event.key == pygame.K_e:
                        if self.state == 'playing' and self.shop_npc.is_player_near(self.player.hitbox_rect):
                            self.state = 'shop'
                        elif self.state == 'shop':
                            self.state = 'playing'

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.state in ('game_over', 'victory') and self.restart_btn.collidepoint(event.pos):
                        self.restart()
                    if self.state == 'shop' and self.close_shop_btn.collidepoint(event.pos):
                        self.state = 'playing'

            # ---- update ----
            if self.state == 'playing':
                self.gun_timer()
                self.input_playing()
                self.update_spawn(dt)
                self.all_sprites.update(dt)
                self.bullet_collision()
                self.player_collision()

                # Auto-advance after wave 10 cleared
                if self.wave_cleared() and self.current_wave == MAX_WAVE:
                    self.state = 'victory'

            # ---- draw ----
            self.all_sprites.draw(self.player.rect.center)
            self.draw_hud()

            if self.state == 'game_over':
                self.draw_game_over()
            elif self.state == 'victory':
                self.draw_victory()
            elif self.state == 'shop':
                self.draw_shop()

            pygame.display.update()
        pygame.quit()


if __name__ == '__main__':
    game = Game()
    game.run()