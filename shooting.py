import pygame
import sys
import random
import math
import array
from pathlib import Path

from game_config import *

# =====================
# 背景（星スクロール）
# =====================
STAR_COUNT = 80

def make_stars():
    stars = []
    for _ in range(STAR_COUNT):
        x = random.randint(0, WIDTH - 1)
        y = random.randint(0, HEIGHT - 1)
        speed = random.choice([1, 2, 3])     # 速度の違いで奥行き感
        size = 1 if speed <= 2 else 2        # 速い星は少し大きく
        stars.append({"x": x, "y": y, "speed": speed, "size": size})
    return stars



# =====================
# 効果音
# =====================
def make_beep_sound(freq=440, duration_ms=120, volume=0.4, sample_rate=44100):
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array.array("h")
    amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        buf.append(int(amp * math.sin(2 * math.pi * freq * t)))
    return pygame.mixer.Sound(buffer=buf.tobytes())

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Shooting Game")
clock = pygame.time.Clock()

font = pygame.font.Font(None, 48)
small_font = pygame.font.Font(None, 28)
hud_font = pygame.font.Font(None, 28)

try:
    shoot_sound = make_beep_sound(880, 60, 0.35)
    hit_sound = make_beep_sound(520, 90, 0.45)
    over_sound = make_beep_sound(220, 220, 0.5)
    enemy_shot_sound = make_beep_sound(700, 60, 0.25)
    powerup_sound = make_beep_sound(980, 120, 0.35)
    heal_sound = make_beep_sound(1040, 140, 0.35)
    explosion_sound = make_beep_sound(320, 140, 0.5)
    damage_sound = make_beep_sound(120, 400, 0.95)  # ★追加：低音「ボン」
    # ★追加：ボス被弾（小さめ・低音・やや長め）
    boss_hit_sound = make_beep_sound(200, 180, 0.75)

    # ★追加：ボス撃破（さらに低音・長め・大きめ）
    boss_die_sound = make_beep_sound(140, 260, 0.90)

    sound_ok = True
    
except pygame.error:
    sound_ok = False
    shoot_sound = hit_sound = over_sound = enemy_shot_sound = powerup_sound = heal_sound = explosion_sound = None
    boss_hit_sound = boss_die_sound = None
def play(sound):
    if sound_ok and sound:
        sound.play()



# 敵の出現比率（合計1.0でなくてもOK、相対比）
ENEMY_WEIGHTS = [
    ("NORMAL", 0.65),
    ("ZIGZAG", 0.25),
    ("TANK",   0.10),
]

def choose_enemy_type():
    r = random.random()
    acc = 0.0
    total = sum(w for _, w in ENEMY_WEIGHTS)
    for t, w in ENEMY_WEIGHTS:
        acc += w / total
        if r <= acc:
            return t
    return "NORMAL"



# =====================
# 画像読み込み
# =====================
ASSET_DIR = Path(__file__).parent / "assets" / "images"

def load_image(name, size):
    path = ASSET_DIR / name
    if path.exists():
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img, size)
    return None

player_img = load_image("player.png", (PLAYER_W, PLAYER_H))
bullet_img = load_image("bullet.png", (BULLET_W, BULLET_H))
enemy_bullet_img = load_image("enemy_bullet.png", (EB_W, EB_H))

# 敵画像（任意：無ければ色分けで表示）
enemy_normal_img = load_image("enemy.png", (ENEMY_W, ENEMY_H))
enemy_zigzag_img = load_image("enemy_zigzag.png", (ENEMY_W, ENEMY_H))
enemy_tank_img = load_image("enemy_tank.png", (TANK_W, TANK_H))

powerup_rapid_img = load_image("powerup_rapid.png", (POWERUP_W, POWERUP_H))
powerup_spread_img = load_image("powerup_spread.png", (POWERUP_W, POWERUP_H))
powerup_pierce_img = load_image("powerup_pierce.png", (POWERUP_W, POWERUP_H))
powerup_heal_img = load_image("powerup_heal.png", (POWERUP_W, POWERUP_H))

def draw_rect_or_img(rect, img, color):
    if img:
        screen.blit(img, rect.topleft)
    else:
        pygame.draw.rect(screen, color, rect)

# =====================
# 初期化
# =====================
def reset_game():
    return {
        "player": pygame.Rect(WIDTH//2 - PLAYER_W//2, HEIGHT-60, PLAYER_W, PLAYER_H),
        "bullets": [],  # {"rect": Rect, "vx": int, "vy": int, "pierce": bool}
        "enemies": [],  # ★敵オブジェクトのリスト（Rectではない）
        "enemy_bullets": [],
        "powerups": [],
        "explosions": [],  # {"x": int, "y": int, "r": float, "max_r": float, "life": int}
        "enemy_timer": 0,
        "score": 0,
        "level": 1,
        "hp": MAX_HP,
        "invincible": 0,
        "game_over": False,
        "boss": None,              # {"rect": Rect, "hp": int, "dir": int, "timer": int}
        "boss_active": False,
        "win": False,
        "shot_cooldown": 0,
        "stage": 1,
        "stage_score": 0,   # ★ステージ内スコア（ボス出現判定用）
        "rapid_timer": 0,
        "rapid_cooldown": 0,
        "spread_timer": 0,
        "pierce_timer": 0,
        "win_timer": 0,   # ★ボス撃破後の待ち時間（フレーム）
    }

def start_next_stage():
    # ステージを進める
    state["stage"] += 1
    state["stage_score"] = 0

    # 盤面をクリアして再開準備
    state["win"] = False
    state["boss_active"] = False
    state["boss"] = None

    state["enemies"].clear()
    state["enemy_bullets"].clear()
    state["powerups"].clear()
    state["bullets"].clear()
    state["explosions"].clear()

    # タイマー類をリセット
    state["enemy_timer"] = 0
    state["shot_cooldown"] = 0
    state["rapid_timer"] = 0
    state["rapid_cooldown"] = 0
    state["win_timer"] = 0
    state["spread_timer"] = 0
    state["pierce_timer"] = 0

    # 自機を初期位置へ（HPを回復するならここで）
    state["player"].x = WIDTH//2 - PLAYER_W//2
    state["player"].y = HEIGHT - 60
    state["invincible"] = INVINCIBLE_TIME
    state["hp"] = MAX_HP  # ★クリア報酬：全回復（不要なら削除）


state = reset_game()
stars = make_stars()

player_speed = 6
def add_explosion(x, y, big=False, scale=1.0, life_scale=1.0):
    if big:
        max_r = 38
        life = 18
    else:
        max_r = 26
        life = 14

    max_r = int(max_r * scale)
    life = int(life * life_scale)

    state["explosions"].append({
        "x": int(x),
        "y": int(y),
        "r": 2.0,
        "max_r": float(max_r),
        "life": int(life),
    })


# =====================
# 弾生成
# =====================
def add_bullet(x, y, vx, vy):
    rect = pygame.Rect(x - BULLET_W//2, y, BULLET_W, BULLET_H)
    pierce = (state["pierce_timer"] > 0)
    state["bullets"].append({"rect": rect, "vx": vx, "vy": vy, "pierce": pierce})

def shoot_once():
    cx = state["player"].centerx
    top = state["player"].top
    if state["spread_timer"] > 0:
        add_bullet(cx, top, 0, -BULLET_SPEED_Y)
        add_bullet(cx, top, -SPREAD_VX, -BULLET_SPEED_Y)
        add_bullet(cx, top, +SPREAD_VX, -BULLET_SPEED_Y)
    else:
        add_bullet(cx, top, 0, -BULLET_SPEED_Y)
    play(shoot_sound)

# =====================
# 敵生成
# =====================
def spawn_enemy(level):
    etype = choose_enemy_type()

    if etype == "TANK":
        w, h = TANK_W, TANK_H
    else:
        w, h = ENEMY_W, ENEMY_H

    x = random.randint(0, WIDTH - w)
    rect = pygame.Rect(x, -h, w, h)

    if etype == "NORMAL":
        return {"type": "NORMAL", "rect": rect, "hp": 1, "phase": 0.0}
    if etype == "ZIGZAG":
        # phaseを進めてsinで左右移動
        return {"type": "ZIGZAG", "rect": rect, "hp": 1, "phase": random.random() * math.tau}
    # TANK
    return {"type": "TANK", "rect": rect, "hp": 3, "phase": 0.0}

def enemy_img_and_color(enemy):
    t = enemy["type"]
    if t == "NORMAL":
        return enemy_normal_img, (255, 0, 0)
    if t == "ZIGZAG":
        return enemy_zigzag_img, (255, 120, 0)
    # TANK
    return enemy_tank_img, (180, 180, 255)

def enemy_score_value(enemy):
    t = enemy["type"]
    if t == "TANK":
        return 30
    if t == "ZIGZAG":
        return 15
    return 10

def spawn_boss():
    rect = pygame.Rect(WIDTH//2 - BOSS_W//2, 80, BOSS_W, BOSS_H)
    return {"rect": rect, "hp": BOSS_HP_MAX, "dir": 1, "timer": 0}

# =====================
# メインループ
# =====================
running = True
while running:
    clock.tick(FPS)

    # -------- イベント --------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            # ★勝利(win)でもゲームオーバーでも、Rで必ずリスタートできる
            if (state["game_over"] or state.get("win", False)) and event.key == pygame.K_r:
                state = reset_game()
                # 必要なら背景もリセット（好み）
                # stars = make_stars()
                continue
            # YOU WIN中：Nで次ステージ
            if state.get("win", False) and event.key == pygame.K_n:
                start_next_stage()
                continue

            # ★単発（保険）：SPACEで1発は必ず撃てる
            if (not state["game_over"]) and (not state.get("win", False)) and event.key == pygame.K_SPACE:
                shoot_once()
    

    # -------- 更新 --------

    # ★勝利演出中：タイマーだけ減らす（操作・敵生成などは停止）
    if (not state["game_over"]) and state.get("win_timer", 0) > 0:
        state["win_timer"] -= 1
        if state["win_timer"] <= 0:
            state["win"] = True

    # 爆発エフェクト更新
    for ex in state["explosions"][:]:
        ex["r"] += 2.5          # 半径を増やす（分かりやすく固定増加に）
        ex["life"] -= 1
        if ex["life"] <= 0:
            state["explosions"].remove(ex)

    if (not state["game_over"]) and (not state.get("win", False)) and state.get("win_timer", 0) == 0:


        # タイマー減少
        if state["rapid_timer"] > 0:
            state["rapid_timer"] -= 1
        else:
            state["rapid_cooldown"] = 0

        if state["spread_timer"] > 0:
            state["spread_timer"] -= 1

        if state["pierce_timer"] > 0:
            state["pierce_timer"] -= 1

        # レベルと敵速度
        state["level"] = 1 + state["stage_score"] // LEVEL_UP_SCORE
        level = state["level"]

        enemy_speed = BASE_ENEMY_SPEED + (level - 1) * SPEED_UP_PER_LEVEL
        shoot_chance = ENEMY_SHOOT_CHANCE + (level - 1) * 0.002

         # ボス出現条件
        trigger = BOSS_TRIGGER_SCORE_BASE + (state["stage"] - 1) * BOSS_TRIGGER_SCORE_STEP
        if (not state["boss_active"]) and (not state.get("win", False)) and state["stage_score"] >= trigger:
            state["boss_active"] = True
            state["boss"] = spawn_boss()

            
        # ボス中は通常敵を出さない（敵タイマー処理の前に入れる）

                # 自機移動
        keys = pygame.key.get_pressed()

        # Shiftで低速移動
        speed = 3 if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else player_speed

        # -----------------
        # 射撃（ボス中でも必ず動く：shot_cooldown方式に統一）
        # -----------------
        if state["shot_cooldown"] > 0:
            state["shot_cooldown"] -= 1

        if keys[pygame.K_SPACE] and state["shot_cooldown"] == 0 and (not state.get("win", False)):
            shoot_once()
            if state["rapid_timer"] > 0:
                state["shot_cooldown"] = RAPID_SHOT_COOLDOWN
            else:
                state["shot_cooldown"] = NORMAL_SHOT_COOLDOWN

        # 左右
        if keys[pygame.K_LEFT] and state["player"].left > 0:
            state["player"].x -= speed
        if keys[pygame.K_RIGHT] and state["player"].right < WIDTH:
            state["player"].x += speed

        # 上下
        if keys[pygame.K_UP] and state["player"].top > 0:
            state["player"].y -= speed
        if keys[pygame.K_DOWN] and state["player"].bottom < HEIGHT:
            state["player"].y += speed

        # 画面内（または下半分）に制限
        state["player"].clamp_ip(pygame.Rect(0, HEIGHT // 2, WIDTH, HEIGHT // 2))

        # 敵生成（ボス中は停止）※ここだけを止める
        if not state["boss_active"]:
            state["enemy_timer"] += 1
            spawn_interval = max(MIN_SPAWN_INTERVAL, BASE_SPAWN_INTERVAL - level * 2)
            if state["enemy_timer"] > spawn_interval:
                state["enemies"].append(spawn_enemy(level))
                state["enemy_timer"] = 0


        
        # 自機弾移動
        for b in state["bullets"][:]:
            b["rect"].x += b["vx"]
            b["rect"].y += b["vy"]
            if b["rect"].bottom < 0 or b["rect"].right < 0 or b["rect"].left > WIDTH:
                state["bullets"].remove(b)

        # 敵移動 + 敵の発射
        for enemy in state["enemies"][:]:
            rect = enemy["rect"]
            t = enemy["type"]

            # 種類別の動き
            if t == "NORMAL":
                rect.y += enemy_speed
            elif t == "ZIGZAG":
                rect.y += enemy_speed * 0.95
                enemy["phase"] += 0.12
                rect.x += int(math.sin(enemy["phase"]) * 3)  # 左右揺れ幅
                rect.x = max(0, min(WIDTH - rect.width, rect.x))
            else:  # TANK
                rect.y += enemy_speed * 0.65

            # 画面外
            if rect.top > HEIGHT:
                state["enemies"].remove(enemy)
                continue

            # 発射確率（TANKは少し高め）
            chance = shoot_chance
            if t == "TANK":
                chance *= 1.5

            if random.random() < chance:
                eb = pygame.Rect(rect.centerx - EB_W//2, rect.bottom, EB_W, EB_H)
                state["enemy_bullets"].append(eb)
                play(enemy_shot_sound)

        # 敵弾移動
        for eb in state["enemy_bullets"][:]:
            eb.y += ENEMY_BULLET_SPEED
            if eb.top > HEIGHT:
                state["enemy_bullets"].remove(eb)
        # ボス更新
        if state["boss_active"] and state["boss"] and (not state.get("win", False)):
            br = state["boss"]["rect"]
            state["boss"]["timer"] += 1

            # 左右移動
            br.x += BOSS_SPEED * state["boss"]["dir"]
            if br.left <= 0 or br.right >= WIDTH:
                state["boss"]["dir"] *= -1

            # 3-way発射（enemy_bullets を流用）
            if state["boss"]["timer"] % BOSS_SHOOT_INTERVAL == 0:
                # 中央・左・右の3本
                for vx in (0, -2, 2):
                    eb = pygame.Rect(br.centerx - EB_W//2, br.bottom, EB_W, EB_H)
                    # enemy_bullets は Rect だけなので、vx対応したい場合は別管理が必要
                    # まずPhase1は直下のみ（vx無し）にする
                    state["enemy_bullets"].append(eb)
                play(enemy_shot_sound)

        # パワーアップ移動
        for pu in state["powerups"][:]:
            pu["rect"].y += POWERUP_FALL_SPEED
            if pu["rect"].top > HEIGHT:
                state["powerups"].remove(pu)
       
        
        # 衝突（弾→敵）HP制の敵に対応
        for enemy in state["enemies"][:]:
            rect = enemy["rect"]
            for b in state["bullets"][:]:
                if rect.colliderect(b["rect"]):
                    enemy["hp"] -= 1
                    play(hit_sound)

                    # 貫通でない場合のみ弾を消す
                    if not b["pierce"]:
                        state["bullets"].remove(b)

                    # 倒したらスコア・ドロップ
                    if enemy["hp"] <= 0:
                        state["enemies"].remove(enemy)
                        state["score"] += enemy_score_value(enemy)
                        gain = enemy_score_value(enemy)
                        state["score"] += gain
                        state["stage_score"] += gain
                        add_explosion(rect.centerx, rect.centery, big=(enemy["type"] == "TANK"))
                        play(explosion_sound)
                    else:
                        play(hit_sound)

                        # 回復抽選（別枠）
                        if random.random() < HEAL_DROP_CHANCE:
                            pu_rect = pygame.Rect(rect.centerx - POWERUP_W//2, rect.centery - POWERUP_H//2, POWERUP_W, POWERUP_H)
                            state["powerups"].append({"rect": pu_rect, "type": "HEAL"})
                        else:
                            if random.random() < POWERUP_DROP_CHANCE:
                                pu_type = random.choice(["RAPID", "SPREAD", "PIERCE"])
                                pu_rect = pygame.Rect(rect.centerx - POWERUP_W//2, rect.centery - POWERUP_H//2, POWERUP_W, POWERUP_H)
                                state["powerups"].append({"rect": pu_rect, "type": pu_type})
                    break  # 1弾につき1回判定で十分
        # 衝突（弾→ボス）
        if state["boss_active"] and state["boss"] and (not state.get("win", False)):
            br = state["boss"]["rect"]
            for b in state["bullets"][:]:
                if br.colliderect(b["rect"]):

                    # ★被弾エフェクト（小）：当たった位置に出す
                    add_explosion(b["rect"].centerx, b["rect"].centery, big=False)
                    play(boss_hit_sound)

                    state["boss"]["hp"] -= 1

                    if not b["pierce"]:
                        state["bullets"].remove(b)

                    # ★ボス撃破（大）
                    if state["boss"]["hp"] <= 0:
                        for _ in range(6):
                            ox = random.randint(-40, 40)
                            oy = random.randint(-15, 15)
                            add_explosion(
                                br.centerx + ox,
                                br.centery + oy,
                                big=False,
                                scale=1.3,
                                life_scale=12.0   # ★14*12=168フレーム ≒ 2.8秒
                            )

                        play(boss_die_sound)
                        state["win_timer"] = WIN_DELAY
                        state["score"] += 300 + state["hp"] * 50
                        state["enemies"].clear()
                        state["enemy_bullets"].clear()
                        state["powerups"].clear()
                        state["score"] += BOSS_BONUS_SCORE
                        state["boss_active"] = False
                        state["boss"] = None

                    break  # 当たった弾があった場合のみ、その1発で処理終了



        # 被弾処理
        def take_damage():
            state["hp"] -= 1
            state["invincible"] = INVINCIBLE_TIME
            play(damage_sound)
            if state["hp"] <= 0:
                state["game_over"] = True
                play(over_sound)

        # 無敵カウント
        if state["invincible"] > 0:
            state["invincible"] -= 1

        # 衝突（自機←敵本体）
        if state["invincible"] == 0:
            for enemy in state["enemies"]:
                if enemy["rect"].colliderect(state["player"]):
                    take_damage()
                    break

        # 衝突（自機←敵弾）
        if state["invincible"] == 0 and (not state["game_over"]):
            for eb in state["enemy_bullets"][:]:
                if eb.colliderect(state["player"]):
                    state["enemy_bullets"].remove(eb)
                    take_damage()
                    break

        # 衝突（自機←パワーアップ）
        for pu in state["powerups"][:]:
            if pu["rect"].colliderect(state["player"]):
                state["powerups"].remove(pu)
                if pu["type"] == "RAPID":
                    state["rapid_timer"] = RAPID_DURATION
                    state["rapid_cooldown"] = 0
                    play(powerup_sound)
                elif pu["type"] == "SPREAD":
                    state["spread_timer"] = SPREAD_DURATION
                    play(powerup_sound)
                elif pu["type"] == "PIERCE":
                    state["pierce_timer"] = PIERCE_DURATION
                    play(powerup_sound)
                else:
                    # HEAL
                    state["hp"] += 1
                    play(heal_sound)

    # -------- 描画 --------
    screen.fill((0, 0, 0))
    pygame.draw.rect(screen, (255, 255, 255), (10, 10, 30, 30))

    # 星を更新（背景スクロール）
    for s in stars:
        s["y"] += s["speed"]
        if s["y"] >= HEIGHT:
            s["y"] = 0
            s["x"] = random.randint(0, WIDTH - 1)

    # 星を描画
    for s in stars:
        pygame.draw.circle(screen, (255, 255, 255), (s["x"], s["y"]), s["size"])
    
    # 爆発エフェクト描画（確実に見える：塗りつぶし）
    for ex in state["explosions"]:
        r = max(2, int(ex["r"]))
        pygame.draw.circle(screen, (255, 200, 80), (ex["x"], ex["y"]), r)  # 塗りつぶし
        pygame.draw.circle(screen, (255, 255, 255), (ex["x"], ex["y"]), max(1, r // 2), 1)  # 芯

        
    # 無敵中点滅
    blink = (state["invincible"] // 5) % 2 == 0
    if state["invincible"] == 0 or blink:
        draw_rect_or_img(state["player"], player_img, (0, 255, 0))

    # 自機弾
    for b in state["bullets"]:
        if b["pierce"]:
            draw_rect_or_img(b["rect"], bullet_img, (255, 220, 120))
        else:
            draw_rect_or_img(b["rect"], bullet_img, (255, 255, 255))

    # 敵
    for enemy in state["enemies"]:
        img, color = enemy_img_and_color(enemy)
        draw_rect_or_img(enemy["rect"], img, color)
        # TANKはHPを表示（見やすい）
        if enemy["type"] == "TANK":
            hp_text = hud_font.render(str(enemy["hp"]), True, (255, 255, 255))
            screen.blit(hp_text, (enemy["rect"].x + 4, enemy["rect"].y + 2))
    # ボス描画
    if state["boss"]:
        br = state["boss"]["rect"]
        pygame.draw.rect(screen, (200, 60, 200), br)  # 画像があれば差し替え可

        # HPバー
        bar_w = 300
        bar_h = 12
        x0 = (WIDTH - bar_w) // 2
        y0 = 40
        pygame.draw.rect(screen, (80, 80, 80), (x0, y0, bar_w, bar_h))
        hp_ratio = max(0, state["boss"]["hp"]) / BOSS_HP_MAX
        pygame.draw.rect(screen, (255, 80, 80), (x0, y0, int(bar_w * hp_ratio), bar_h))

    # 敵弾
    for eb in state["enemy_bullets"]:
        draw_rect_or_img(eb, enemy_bullet_img, (255, 255, 0))

    # パワーアップ
    for pu in state["powerups"]:
        t = pu["type"]
        if t == "RAPID":
            draw_rect_or_img(pu["rect"], powerup_rapid_img, (0, 255, 255))
        elif t == "SPREAD":
            draw_rect_or_img(pu["rect"], powerup_spread_img, (255, 0, 255))
        elif t == "PIERCE":
            draw_rect_or_img(pu["rect"], powerup_pierce_img, (255, 220, 120))
        else:
            draw_rect_or_img(pu["rect"], powerup_heal_img, (0, 255, 0))

    # HUD
    screen.blit(hud_font.render(f"SCORE: {state['score']}", True, (255, 255, 255)), (10, 10))
    screen.blit(hud_font.render(f"LEVEL: {state['level']}", True, (255, 255, 255)), (WIDTH - 110, 10))
    screen.blit(hud_font.render("HP: " + "♥" * state["hp"], True, (255, 100, 100)), (10, HEIGHT - 30))
    screen.blit(hud_font.render(f"STAGE: {state['stage']}", True, (255, 255, 255)), (WIDTH // 2 - 50, 10))

    y = 36
    if state["rapid_timer"] > 0:
        sec = state["rapid_timer"] / FPS
        screen.blit(hud_font.render(f"RAPID: {sec:0.1f}s", True, (0, 255, 255)), (10, y)); y += 22
    if state["spread_timer"] > 0:
        sec = state["spread_timer"] / FPS
        screen.blit(hud_font.render(f"SPREAD: {sec:0.1f}s", True, (255, 0, 255)), (10, y)); y += 22
    if state["pierce_timer"] > 0:
        sec = state["pierce_timer"] / FPS
        screen.blit(hud_font.render(f"PIERCE: {sec:0.1f}s", True, (255, 220, 120)), (10, y))

    if state["game_over"]:
        screen.blit(font.render("GAME OVER", True, (255, 255, 255)), (120, 250))
        screen.blit(small_font.render(f"FINAL SCORE: {state['score']}", True, (200, 200, 200)), (150, 295))
        screen.blit(small_font.render("Press R to Restart / ESC to Quit", True, (200, 200, 200)), (90, 325))
    
    if state.get("win", False):
        screen.blit(font.render("YOU WIN!", True, (255, 255, 255)), (150, 250))
        screen.blit(small_font.render("Press N for Next Stage", True, (200, 200, 200)), (140, 295))
        screen.blit(small_font.render("Press R to Restart / ESC to Quit", True, (200, 200, 200)), (90, 325))

    pygame.display.flip()

pygame.quit()
sys.exit()

