from settings import *
from player import Player
from sprites import *
from pytmx.util_pygame import load_pygame
from groups import AllSprites
from random import choice, uniform
import json, os, math

# ------------------------------------------------------------------ #
#  WAVE CONFIG                                                         #
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
SAVE_FILE = 'save.json'

# ------------------------------------------------------------------ #
#  GUN UPGRADES                                                        #
# ------------------------------------------------------------------ #
# Each upgrade is a dict the shop reads and applies to GunStats.
# 'max_level': how many times it can be bought.
# 'cost_base': coins for level 1. Cost scales: base * (current_level+1)
GUN_UPGRADES = [
    {
        'id':        'spread_shot',
        'name':      'Spread Shot',
        'desc':      'Fire 3 bullets in a cone',
        'max_level': 3,
        'cost_base': 3,
        'icon':      '»',           # text icon placeholder
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


class GunStats:
    """Holds all mutable weapon stats; applied when firing."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.spread_level  = 0   # 0=single, 1=3 bullets, 2=5, 3=7
        self.fire_rate_lvl = 0   # each level -80ms cooldown (base 600)
        self.bullet_spd_lvl= 0   # each level +20% speed
        self.piercing      = False

    @property
    def cooldown(self):
        return max(100, 600 - self.fire_rate_lvl * 80)

    @property
    def bullet_count(self):
        return 1 + self.spread_level * 2   # 1 / 3 / 5 / 7

    @property
    def spread_angle(self):
        """Degrees between each bullet in a spread."""
        return 12 if self.spread_level else 0

    @property
    def bullet_velocity(self):
        return 1200 * (1 + self.bullet_spd_lvl * 0.20)

    def apply_upgrade(self, upgrade_id):
        if upgrade_id == 'spread_shot':
            self.spread_level = min(3, self.spread_level + 1)
        elif upgrade_id == 'fire_rate':
            self.fire_rate_lvl = min(5, self.fire_rate_lvl + 1)
        elif upgrade_id == 'bullet_speed':
            self.bullet_spd_lvl = min(4, self.bullet_spd_lvl + 1)
        elif upgrade_id == 'piercing':
            self.piercing = True


# ================================================================ #
#  GAME                                                              #
# ================================================================ #
class Game:
    def __init__(self):
        pygame.init()
        self.display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Shoot and Run')
        self.clock   = pygame.time.Clock()
        self.running = True

        # fonts
        self.font_title  = pygame.font.SysFont('Arial', 64, bold=True)
        self.font_large  = pygame.font.SysFont('Arial', 42, bold=True)
        self.font_medium = pygame.font.SysFont('Arial', 30, bold=True)
        self.font_small  = pygame.font.SysFont('Arial', 22, bold=True)
        self.font_tiny   = pygame.font.SysFont('Arial', 16)

        # persistent data
        self.high_score = self._load_high_score()

        # weapon stats (shared object passed everywhere)
        self.gun_stats     = GunStats()
        self.upgrade_levels = {u['id']: 0 for u in GUN_UPGRADES}

        # score / coins
        self.score = 0
        self.coins = 0

        # wave
        self.current_wave    = 1
        self.enemies_to_spawn = WAVE_CONFIG[1]['count']
        self.enemies_spawned  = 0
        self.wave_enemy_speed = WAVE_CONFIG[1]['speed']
        self.spawn_timer      = 0
        self.spawn_interval   = 0.6

        # state machine
        # 'menu' | 'playing' | 'wave_clear' | 'shop' | 'game_over' | 'victory'
        self.state = 'menu'

        # groups
        self.all_sprites       = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.bullet_sprites    = pygame.sprite.Group()
        self.enemy_sprites     = pygame.sprite.Group()

        # shooting
        self.can_shoot    = True
        self.shoot_time   = 0

        # spawn
        self.spawn_safe_radius = 250
        self.spawn_positions   = []

        # audio
        self.shoot_sound  = pygame.mixer.Sound(join('audio', 'shoot.wav'))
        self.shoot_sound.set_volume(0.4)
        self.impact_sound = pygame.mixer.Sound(join('audio', 'impact.ogg'))
        self.music        = pygame.mixer.Sound(join('audio', 'music.wav'))
        self.music.set_volume(0.1)
        self.music.play(loops=-1)

        self.load_images()
        self._build_ui_surfaces()

        # menu background — we set up the world once to draw it behind the menu
        self._setup_world()

    # ================================================================ #
    #  PERSISTENCE                                                       #
    # ================================================================ #
    def _load_high_score(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE) as f:
                    return json.load(f).get('high_score', 0)
            except Exception:
                pass
        return 0

    def _save_high_score(self):
        if self.score > self.high_score:
            self.high_score = self.score
        try:
            with open(SAVE_FILE, 'w') as f:
                json.dump({'high_score': self.high_score}, f)
        except Exception:
            pass

    # ================================================================ #
    #  LOAD IMAGES                                                       #
    # ================================================================ #
    def load_images(self):
        self.bullet_surf = pygame.image.load(join('images', 'gun', 'bullet.png')).convert_alpha()

        folders = list(walk(join('images', 'enemies')))[0][1]
        self.enemy_frames = {}
        for folder in folders:
            for folder_path, _, file_names in walk(join('images', 'enemies', folder)):
                self.enemy_frames[folder] = []
                for fn in sorted(file_names, key=lambda n: int(n.split('.')[0])):
                    surf = pygame.image.load(join(folder_path, fn)).convert_alpha()
                    self.enemy_frames[folder].append(surf)

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

        # Menu background art (optional)
        try:
            self.menu_bg = pygame.image.load(join('images', 'hud', 'menu_bg.png')).convert()
            self.menu_bg = pygame.transform.scale(self.menu_bg, (WINDOW_WIDTH, WINDOW_HEIGHT))
        except FileNotFoundError:
            self.menu_bg = None

    # ================================================================ #
    #  WORLD SETUP                                                       #
    # ================================================================ #
    def _setup_world(self):
        """Load map and create static sprites. Called once at init and on restart."""
        map_data = load_pygame(join('data', 'maps', 'world.tmx'))

        for x, y, image in map_data.get_layer_by_name('Ground').tiles():
            NonCollisionSprites((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)

        for obj in map_data.get_layer_by_name('Objects'):
            CollisionSprites((obj.x, obj.y), obj.image, (self.all_sprites, self.collision_sprites))

        for cs in map_data.get_layer_by_name('Collisions'):
            CollisionSprites((cs.x, cs.y),
                             pygame.Surface((cs.width, cs.height)),
                             self.collision_sprites)

        for obj in map_data.get_layer_by_name('Entities'):
            if obj.name == 'Player':
                self.player = Player((obj.x, obj.y), 400, self.all_sprites, self.collision_sprites)
                self.gun    = Gun(self.player, self.all_sprites)
            else:
                self.spawn_positions.append((obj.x, obj.y))

        # Shop NPC — hidden by default, shown only in wave_clear / shop states
        shop_pos = (self.spawn_positions[0][0] - 120,
                    self.spawn_positions[0][1]) if self.spawn_positions else (200, 200)
        self.shop_npc = ShopNPC(shop_pos, self.all_sprites)
        self.shop_npc.visible = False   # custom flag — we toggle visibility manually

    # ================================================================ #
    #  UI SURFACES & RECTS                                               #
    # ================================================================ #
    def _build_ui_surfaces(self):
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2

        self.panel_wide = pygame.Surface((700, 420), pygame.SRCALPHA)
        self.panel_wide.fill((10, 10, 10, 215))

        self.panel_narrow = pygame.Surface((520, 300), pygame.SRCALPHA)
        self.panel_narrow.fill((10, 10, 10, 215))

        bw, bh = 220, 54

        # menu
        self.play_btn    = pygame.Rect(cx - bw // 2, cy + 40,  bw, bh)
        self.quit_btn    = pygame.Rect(cx - bw // 2, cy + 110, bw, bh)

        # in-game overlays
        self.restart_btn     = pygame.Rect(cx - bw // 2, cy + 110, bw, bh)
        self.next_wave_btn   = pygame.Rect(cx - bw // 2, cy +  60, bw, bh)
        self.open_shop_btn   = pygame.Rect(cx - bw // 2, cy + 125, bw, bh)
        self.close_shop_btn  = pygame.Rect(cx - bw // 2, cy + 160, bw, bh)
        self.menu_btn        = pygame.Rect(cx - bw // 2, cy + 175, bw, bh)

        # shop upgrade slots (built dynamically in draw_shop)
        self.upgrade_rects = []

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
        alive   = sum(1 for e in self.enemy_sprites if e.death_time == 0)
        pending = max(0, self.enemies_to_spawn - self.enemies_spawned)
        return alive + pending

    def wave_cleared(self):
        return (self.enemies_spawned >= self.enemies_to_spawn and
                all(e.death_time != 0 for e in self.enemy_sprites))

    # ================================================================ #
    #  SHOOTING                                                          #
    # ================================================================ #
    def _fire(self):
        self.shoot_sound.play()
        origin    = self.gun.rect.center + self.gun.player_direction * 50
        base_dir  = self.gun.player_direction
        count     = self.gun_stats.bullet_count
        spread    = self.gun_stats.spread_angle

        # angles: e.g. count=3, spread=12 → [-12, 0, 12]
        offsets = [0] if count == 1 else [
            -spread * (count // 2) + spread * i for i in range(count)]

        for offset_deg in offsets:
            rad = math.radians(offset_deg)
            cos_, sin_ = math.cos(rad), math.sin(rad)
            d = pygame.Vector2(
                base_dir.x * cos_ - base_dir.y * sin_,
                base_dir.x * sin_ + base_dir.y * cos_
            )
            Bullet(self.bullet_surf, origin, d,
                   (self.all_sprites, self.bullet_sprites),
                   velocity=self.gun_stats.bullet_velocity,
                   piercing=self.gun_stats.piercing)

        self.can_shoot  = False
        self.shoot_time = pygame.time.get_ticks()

    def input_playing(self):
        if pygame.mouse.get_pressed()[0] and self.can_shoot:
            self._fire()

    def gun_timer(self):
        if not self.can_shoot:
            if pygame.time.get_ticks() - self.shoot_time >= self.gun_stats.cooldown:
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
        if self.enemies_spawned >= self.enemies_to_spawn:
            return
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            Enemy(self.safe_spawn_position(),
                  choice(list(self.enemy_frames.values())),
                  (self.all_sprites, self.enemy_sprites),
                  self.player, self.collision_sprites,
                  speed=self.wave_enemy_speed)
            self.enemies_spawned += 1

    # ================================================================ #
    #  COLLISIONS                                                        #
    # ================================================================ #
    def bullet_collision(self):
        for bullet in list(self.bullet_sprites):
            hits = pygame.sprite.spritecollide(
                bullet, self.enemy_sprites, False, pygame.sprite.collide_mask)
            if hits:
                self.impact_sound.play()
                for enemy in hits:
                    if enemy.death_time == 0:
                        enemy.destroy()
                        self.score += 10
                        self.coins += 1
                if not bullet.piercing:
                    bullet.kill()

    def player_collision(self):
        if pygame.sprite.spritecollide(
                self.player, self.enemy_sprites, False, pygame.sprite.collide_mask):
            self.player.take_damage()
            if self.player.is_dead:
                self._save_high_score()
                self.state = 'game_over'

    # ================================================================ #
    #  NPC VISIBILITY                                                    #
    # ================================================================ #
    def _show_npc(self, visible: bool):
        """Add/remove NPC from all_sprites to control visibility & y-sort."""
        if visible and self.shop_npc not in self.all_sprites:
            self.all_sprites.add(self.shop_npc)
        elif not visible and self.shop_npc in self.all_sprites:
            self.all_sprites.remove(self.shop_npc)

    # ================================================================ #
    #  DRAW HELPERS                                                      #
    # ================================================================ #
    def _shadow_text(self, font, text, color, pos, anchor='topleft'):
        sh = font.render(text, True, (0, 0, 0))
        tx = font.render(text, True, color)
        self.display.blit(sh, sh.get_rect(**{anchor: (pos[0]+1, pos[1]+1)}))
        self.display.blit(tx, tx.get_rect(**{anchor: pos}))

    def _draw_button(self, rect, text, font,
                     hover=(80, 180, 80), base=(50, 140, 50), border=(255,255,255)):
        col = hover if rect.collidepoint(pygame.mouse.get_pos()) else base
        pygame.draw.rect(self.display, col,    rect, border_radius=10)
        pygame.draw.rect(self.display, border, rect, 2, border_radius=10)
        lbl = font.render(text, True, (255, 255, 255))
        self.display.blit(lbl, lbl.get_rect(center=rect.center))

    def _dim_overlay(self, alpha=160):
        s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, alpha))
        self.display.blit(s, (0, 0))

    # ================================================================ #
    #  MENU                                                              #
    # ================================================================ #
    def draw_menu(self):
        # Background: blurred world or solid colour
        if self.menu_bg:
            self.display.blit(self.menu_bg, (0, 0))
        else:
            # Draw the world as a live background
            self.all_sprites.draw(self.player.rect.center)
            self._dim_overlay(120)

        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2

        # Title
        self._shadow_text(self.font_title, 'SHOOT AND RUN',
                          (255, 220, 60), (cx, cy - 160), anchor='midtop')

        # High score
        hs_txt = f'High Score:  {self.high_score}'
        self._shadow_text(self.font_medium, hs_txt, (200, 200, 255),
                          (cx, cy - 60), anchor='midtop')

        # Buttons
        self._draw_button(self.play_btn, 'Play', self.font_medium,
                          hover=(80, 200, 80), base=(50, 150, 50))
        self._draw_button(self.quit_btn, 'Quit', self.font_medium,
                          hover=(200, 80, 80), base=(150, 50, 50))

        # Controls hint
        self._shadow_text(self.font_tiny,
                          'WASD move  |  Mouse aim & shoot  |  F next wave  |  E shop',
                          (180, 180, 180), (cx, WINDOW_HEIGHT - 30), anchor='midbottom')

    # ================================================================ #
    #  HUD                                                               #
    # ================================================================ #
    def draw_hud(self):
        # HP bar
        fi = max(0, min(5, 5 - self.player.health))
        if self.hp_frames[fi]:
            self.display.blit(pygame.transform.scale2x(self.hp_frames[fi]), (16, 16))
        else:
            for i in range(self.player.max_health):
                col = (220, 50, 50) if i < self.player.health else (60, 60, 60)
                pygame.draw.rect(self.display, col, (20 + i*34, 20, 28, 28), border_radius=4)
                pygame.draw.rect(self.display, (255,255,255), (20+i*34, 20, 28, 28), 2, border_radius=4)

        # Wave — top centre
        self._shadow_text(self.font_medium, f'Wave {self.current_wave} / {MAX_WAVE}',
                          (255, 230, 100), (WINDOW_WIDTH//2, 14), anchor='midtop')

        # Enemies remaining
        rem = self.enemies_remaining()
        self._shadow_text(self.font_small, f'Enemies: {rem}',
                          (255, 100, 100) if rem else (100, 255, 100),
                          (WINDOW_WIDTH//2, 50), anchor='midtop')

        # Gun upgrades indicator (small icons bottom-left)
        self._draw_upgrade_bar()

        # Score / coins — top right
        self._shadow_text(self.font_small, f'Score: {self.score}',
                          (255, 255, 255), (WINDOW_WIDTH-20, 20), anchor='topright')
        coin_txt = f'x {self.coins}'
        if self.coin_icon:
            cx_ = WINDOW_WIDTH - 20 - self.font_small.size(coin_txt)[0] - 30
            self.display.blit(self.coin_icon, (cx_, 48))
        self._shadow_text(self.font_small, coin_txt,
                          (255, 220, 50), (WINDOW_WIDTH-20, 50), anchor='topright')

        # Shop proximity hint (only during wave_clear)
        if (self.state == 'wave_clear' and
                self.shop_npc in self.all_sprites and
                self.shop_npc.is_player_near(self.player.hitbox_rect)):
            self._shadow_text(self.font_small, 'Press  E  to open shop',
                              (255, 240, 120), (WINDOW_WIDTH//2, WINDOW_HEIGHT-80),
                              anchor='midbottom')

    def _draw_upgrade_bar(self):
        """Show active upgrade levels as small coloured badges at bottom-left."""
        x, y = 20, WINDOW_HEIGHT - 36
        for upg in GUN_UPGRADES:
            lvl = self.upgrade_levels[upg['id']]
            if lvl == 0:
                continue
            badge = self.font_tiny.render(f"{upg['icon']} {upg['name']} {lvl}", True, upg['color'])
            bg = pygame.Surface((badge.get_width()+8, badge.get_height()+4), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 140))
            self.display.blit(bg, (x-4, y-2))
            self.display.blit(badge, (x, y))
            x += badge.get_width() + 20

    # ================================================================ #
    #  WAVE CLEAR OVERLAY                                                #
    # ================================================================ #
    def draw_wave_clear(self):
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        self._dim_overlay(100)
        self.display.blit(self.panel_wide, self.panel_wide.get_rect(center=(cx, cy - 20)))

        self._shadow_text(self.font_large,
                          f'Wave {self.current_wave} Complete!',
                          (100, 255, 160), (cx, cy - 130), anchor='midtop')

        self._shadow_text(self.font_small,
                          f'Score: {self.score}   Coins: {self.coins}',
                          (200, 200, 200), (cx, cy - 75), anchor='midtop')

        if self.current_wave < MAX_WAVE:
            self._draw_button(self.next_wave_btn, f'Start Wave {self.current_wave+1}',
                              self.font_small, hover=(80,180,80), base=(50,140,50))
            self._draw_button(self.open_shop_btn, 'Open Shop  ( E )',
                              self.font_small, hover=(180,140,60), base=(140,100,30))
        else:
            # Last wave cleared → victory path handled separately, but show it anyway
            self._draw_button(self.next_wave_btn, 'Finish!',
                              self.font_small, hover=(80,180,80), base=(50,140,50))

    # ================================================================ #
    #  SHOP                                                              #
    # ================================================================ #
    def draw_shop(self):
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        self._dim_overlay(170)

        panel = self.panel_wide
        panel_rect = panel.get_rect(center=(cx, cy))
        self.display.blit(panel, panel_rect)

        self._shadow_text(self.font_large, 'S H O P', (255, 220, 60),
                          (cx, panel_rect.top + 14), anchor='midtop')
        self._shadow_text(self.font_medium, f'Coins:  {self.coins}',
                          (255, 220, 50), (cx, panel_rect.top + 66), anchor='midtop')

        # Build upgrade cards
        card_w, card_h = 140, 170
        cols = len(GUN_UPGRADES)
        total_w = cols * card_w + (cols-1) * 16
        start_x = cx - total_w // 2
        card_y  = panel_rect.top + 118
        self.upgrade_rects = []

        for i, upg in enumerate(GUN_UPGRADES):
            lvl     = self.upgrade_levels[upg['id']]
            maxed   = lvl >= upg['max_level']
            cost    = upg['cost_base'] * (lvl + 1)
            can_buy = not maxed and self.coins >= cost

            cx_ = start_x + i * (card_w + 16)
            rect = pygame.Rect(cx_, card_y, card_w, card_h)
            self.upgrade_rects.append(rect)

            # Card bg
            if maxed:
                bg_col = (40, 70, 40)
                border = (80, 160, 80)
            elif can_buy and rect.collidepoint(pygame.mouse.get_pos()):
                bg_col = (60, 60, 90)
                border = (200, 200, 255)
            else:
                bg_col = (35, 35, 55)
                border = (90, 90, 120)

            pygame.draw.rect(self.display, bg_col, rect, border_radius=10)
            pygame.draw.rect(self.display, border, rect, 2, border_radius=10)

            # Icon
            icon_surf = self.font_large.render(upg['icon'], True, upg['color'])
            self.display.blit(icon_surf, icon_surf.get_rect(midtop=(cx_+card_w//2, card_y+8)))

            # Name
            name_surf = self.font_tiny.render(upg['name'], True, (230, 230, 230))
            self.display.blit(name_surf, name_surf.get_rect(midtop=(cx_+card_w//2, card_y+54)))

            # Desc (word-wrap naive: split at space if >18 chars)
            desc = upg['desc']
            lines = []
            words = desc.split()
            line  = ''
            for w in words:
                if len(line)+len(w)+1 <= 18:
                    line = (line+' '+w).strip()
                else:
                    lines.append(line); line = w
            lines.append(line)
            for li, l in enumerate(lines):
                ls = self.font_tiny.render(l, True, (160,160,160))
                self.display.blit(ls, ls.get_rect(midtop=(cx_+card_w//2, card_y+72+li*16)))

            # Level pip dots
            pip_y = card_y + 118
            pip_x0 = cx_ + card_w//2 - upg['max_level']*10//2
            for p in range(upg['max_level']):
                col = upg['color'] if p < lvl else (60, 60, 60)
                pygame.draw.circle(self.display, col, (pip_x0 + p*10 + 4, pip_y), 4)

            # Price / maxed label
            if maxed:
                tag = self.font_tiny.render('MAXED', True, (80, 220, 80))
            elif can_buy:
                tag = self.font_tiny.render(f'{cost} coins', True, (255, 220, 50))
            else:
                tag = self.font_tiny.render(f'{cost} coins', True, (120, 100, 50))
            self.display.blit(tag, tag.get_rect(midbottom=(cx_+card_w//2, card_y+card_h-6)))

        # Close button
        self._draw_button(self.close_shop_btn, 'Close  ( E )', self.font_small,
                          hover=(180,80,80), base=(130,50,50))

    # ================================================================ #
    #  GAME OVER / VICTORY                                               #
    # ================================================================ #
    def draw_game_over(self):
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        self._dim_overlay(160)
        if self.game_over_bg:
            self.display.blit(self.game_over_bg,
                              self.game_over_bg.get_rect(center=(cx, cy-60)))
        self.display.blit(self.panel_narrow, self.panel_narrow.get_rect(center=(cx, cy)))
        self._shadow_text(self.font_large, 'GAME  OVER',
                          (220,60,60), (cx, cy-100), anchor='midtop')
        self._shadow_text(self.font_small,
                          f'Wave {self.current_wave}   Score: {self.score}   '
                          f'Best: {self.high_score}',
                          (200,200,200), (cx, cy-45), anchor='midtop')
        self._draw_button(self.restart_btn, 'Play Again', self.font_small)
        self._draw_button(self.menu_btn,    'Main Menu',  self.font_small,
                          hover=(80,80,180), base=(50,50,140))

    def draw_victory(self):
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        self._dim_overlay(150)
        self.display.blit(self.panel_narrow, self.panel_narrow.get_rect(center=(cx, cy)))
        self._shadow_text(self.font_large, 'YOU  WIN!',
                          (80,220,120), (cx, cy-100), anchor='midtop')
        self._shadow_text(self.font_small,
                          f'All {MAX_WAVE} waves cleared!   '
                          f'Score: {self.score}   Best: {self.high_score}',
                          (200,200,200), (cx, cy-45), anchor='midtop')
        self._draw_button(self.restart_btn, 'Play Again', self.font_small)
        self._draw_button(self.menu_btn,    'Main Menu',  self.font_small,
                          hover=(80,80,180), base=(50,50,140))

    # ================================================================ #
    #  RESET / START                                                     #
    # ================================================================ #
    def _full_restart(self):
        self.score        = 0
        self.coins        = 0
        self.current_wave = 1
        self._load_wave(1)
        self.gun_stats.reset()
        self.upgrade_levels = {u['id']: 0 for u in GUN_UPGRADES}

        self.all_sprites.empty()
        self.collision_sprites.empty()
        self.bullet_sprites.empty()
        self.enemy_sprites.empty()
        self.spawn_positions = []
        self.can_shoot  = True
        self.shoot_time = 0

        self._setup_world()
        self._show_npc(False)
        self.state = 'playing'

    def _go_to_menu(self):
        self._save_high_score()
        self.state = 'menu'

    # ================================================================ #
    #  MAIN LOOP                                                         #
    # ================================================================ #
    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._save_high_score()
                    self.running = False

                # ---- keyboard ----
                if event.type == pygame.KEYDOWN:
                    if self.state == 'playing' and event.key == pygame.K_f and self.wave_cleared():
                        if self.current_wave >= MAX_WAVE:
                            self._save_high_score()
                            self.state = 'victory'
                        else:
                            self.state = 'wave_clear'
                            self._show_npc(True)

                    if event.key == pygame.K_e:
                        if self.state == 'wave_clear' and self.shop_npc.is_player_near(self.player.hitbox_rect):
                            self.state = 'shop'
                        elif self.state == 'shop':
                            self.state = 'wave_clear'

                # ---- mouse ----
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mp = event.pos

                    if self.state == 'menu':
                        if self.play_btn.collidepoint(mp):
                            self._full_restart()
                        elif self.quit_btn.collidepoint(mp):
                            self._save_high_score()
                            self.running = False

                    elif self.state == 'wave_clear':
                        if self.next_wave_btn.collidepoint(mp):
                            self.current_wave += 1
                            self._load_wave(self.current_wave)
                            self._show_npc(False)
                            self.state = 'playing'
                        elif self.open_shop_btn.collidepoint(mp):
                            self.state = 'shop'

                    elif self.state == 'shop':
                        if self.close_shop_btn.collidepoint(mp):
                            self.state = 'wave_clear'
                        else:
                            for i, rect in enumerate(self.upgrade_rects):
                                if rect.collidepoint(mp):
                                    upg = GUN_UPGRADES[i]
                                    lvl = self.upgrade_levels[upg['id']]
                                    cost = upg['cost_base'] * (lvl + 1)
                                    if lvl < upg['max_level'] and self.coins >= cost:
                                        self.coins -= cost
                                        self.upgrade_levels[upg['id']] += 1
                                        self.gun_stats.apply_upgrade(upg['id'])

                    elif self.state in ('game_over', 'victory'):
                        if self.restart_btn.collidepoint(mp):
                            self._full_restart()
                        elif self.menu_btn.collidepoint(mp):
                            self._go_to_menu()

            # ---- update ----
            if self.state == 'playing':
                self.gun_timer()
                self.input_playing()
                self.update_spawn(dt)
                self.all_sprites.update(dt)
                self.bullet_collision()
                self.player_collision()

                # Auto-detect clear to show F hint
                if self.wave_cleared() and self.state == 'playing':
                    pass   # hint drawn in HUD

            elif self.state == 'wave_clear':
                # Player can still move during intermission; gun stays active
                self.gun_timer()
                self.input_playing()
                self.all_sprites.update(dt)

            elif self.state == 'shop':
                self.all_sprites.update(dt)

            # ---- draw ----
            if self.state == 'menu':
                self.draw_menu()
            else:
                self.all_sprites.draw(self.player.rect.center)
                self.draw_hud()

                if self.state == 'wave_clear':
                    self.draw_wave_clear()
                elif self.state == 'shop':
                    self.draw_shop()
                elif self.state == 'game_over':
                    self.draw_game_over()
                elif self.state == 'victory':
                    self.draw_victory()

                # F hint during playing when wave is clear
                if self.state == 'playing' and self.wave_cleared():
                    self._shadow_text(self.font_medium,
                                      'Wave clear!  Press  F  to continue',
                                      (100, 255, 160),
                                      (WINDOW_WIDTH//2, WINDOW_HEIGHT-50),
                                      anchor='midbottom')

            pygame.display.update()
        pygame.quit()


if __name__ == '__main__':
    game = Game()
    game.run()