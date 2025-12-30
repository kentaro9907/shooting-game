# config.py
# =====================
# 基本設定
# =====================

WIDTH, HEIGHT = 480, 640
FPS = 60

# =====================
# プレイヤー・弾
# =====================

PLAYER_W, PLAYER_H = 40, 20
BULLET_W, BULLET_H = 4, 10

# =====================
# 敵サイズ
# =====================

ENEMY_W, ENEMY_H = 40, 20
TANK_W, TANK_H = 54, 28

# =====================
# 敵弾
# =====================

EB_W, EB_H = 6, 12
ENEMY_BULLET_SPEED = 6
ENEMY_SHOOT_CHANCE = 0.015

# =====================
# HP / 無敵
# =====================

MAX_HP = 7
INVINCIBLE_TIME = 90

# =====================
# パワーアップ
# =====================

POWERUP_W, POWERUP_H = 20, 20
POWERUP_DROP_CHANCE = 0.25
HEAL_DROP_CHANCE = 0.10
POWERUP_FALL_SPEED = 3

RAPID_DURATION = 6 * FPS
SPREAD_DURATION = 6 * FPS
PIERCE_DURATION = 6 * FPS

RAPID_SHOT_COOLDOWN = 8
NORMAL_SHOT_COOLDOWN = 14

SPREAD_VX = 4
BULLET_SPEED_Y = 8

# =====================
# 難易度
# =====================

BASE_ENEMY_SPEED = 2.5
SPEED_UP_PER_LEVEL = 0.3
BASE_SPAWN_INTERVAL = 40
MIN_SPAWN_INTERVAL = 14
LEVEL_UP_SCORE = 50

# =====================
# ボス
# =====================

BOSS_TRIGGER_SCORE_BASE = 500
BOSS_TRIGGER_SCORE_STEP = 300

BOSS_W, BOSS_H = 140, 50
BOSS_HP_MAX = 50
BOSS_SPEED = 3
BOSS_BULLET_SPEED = 6
BOSS_SHOOT_INTERVAL = 28
BOSS_BONUS_SCORE = 500
