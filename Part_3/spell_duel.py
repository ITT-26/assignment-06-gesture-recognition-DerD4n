"""
SPELL DUEL — ASCII Wizard Gesture-Combat Game
================================================
Draw unistroke gestures to cast spells in a turn-based duel against an AI
wizard. The LSTM V2 model recognizes the gesture; its confidence
score determines how powerful (or whether) the cast lands.

Controls
--------
- Left-click and drag to draw your spell gesture.
- Release the mouse to attempt the cast.
- Just start drawing for the next spell
- Press R to restart after the duel ends.
- Press Q to quit.

Requires
--------
- spell_model_v2.keras   (trained LSTM V2, exported from the notebook)
- spell_label_encoder.pkl (the matching LabelEncoder)
- Part_1/recognizer.py   (DollarRecognizer + Point, for the $1 normalize pipeline)
"""

import os
import sys
import pickle
import random

import tensorflow as tf
import numpy as np
import pyglet
from pyglet.gl import GL_LINE_STRIP

import faulthandler

faulthandler.enable()
from spells import (
    SPELLS, SPELL_GESTURES, resolve_cast, apply_damage,
    ai_choose_spell, ai_simulated_confidence,
)

from art import (
    PLAYER_IDLE, PLAYER_CAST, PLAYER_HIT, 
    AI_IDLE_1, AI_CAST_1, AI_HIT_1,
    AI_IDLE_2, AI_CAST_2, AI_HIT_2, 
    fx_for
)

pyglet.options["debug_gl"] = False

# ----------------------------------------------------------------
# Locate and import the $1 recognizer (Point + DollarRecognizer) for normalize()
# ----------------------------------------------------------------
# same path searching code as in notebook
def _find_module_dir(module_filename):
    here = os.path.dirname(os.path.abspath(__file__))
    for root, dirs, files in os.walk(os.path.join(here, "..")):
        if module_filename in files:
            return root
        dirs[:] = [d for d in dirs if not d.startswith('.')]
    return None

_rec_dir = _find_module_dir("recognizer.py")
if _rec_dir is None:
    _rec_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Part_1")
    print(f"WARNING: recognizer.py not found automatically, falling back to {_rec_dir}")
if _rec_dir not in sys.path:
    sys.path.insert(0, _rec_dir)

from recognizer import DollarRecognizer, Point  # noqa: E402

# ----------------------------------------------------------------
# Load the trained LSTM model + label encoder
# ----------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "spell_model_v2.keras")
ENCODER_PATH = os.path.join(HERE, "spell_label_encoder.pkl")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Could not find {MODEL_PATH}. Run the 'save model for game' cell "
        f"in unistroke_gestures.ipynb first."
    )
if not os.path.exists(ENCODER_PATH):
    raise FileNotFoundError(
        f"Could not find {ENCODER_PATH}. Run the 'save model for game' cell "
        f"in unistroke_gestures.ipynb first."
    )

model = tf.keras.models.load_model(MODEL_PATH)
with open(ENCODER_PATH, "rb") as f:
    encoder = pickle.load(f)

CLASS_NAMES = list(encoder.classes_)
print(f"Loaded model. Classes: {CLASS_NAMES}")

_normaliser = DollarRecognizer(load_defaults=False)


def classify_gesture(points):
    """
    Flip the y axis (to match drawing coordinates)
    Run captured (x, y) points through the $1 normalize pipeline, then the
    LSTM model. Returns (predicted_label, confidence, full_probability_vector).
    """
    if len(points) < 2:
        return None, 0.0, None

    pts = [Point(x, WINDOW_H - y) for (x, y) in points]
    norm_pts = _normaliser.normalize(pts)

    seq = np.array([[p.x, p.y] for p in norm_pts], dtype=np.float32)
    seq = np.expand_dims(seq, axis=0)  # (1, 64, 2)

    probs = model.predict(seq, verbose=0)[0]
    best_idx = int(np.argmax(probs))
    label = encoder.inverse_transform([best_idx])[0]
    confidence = float(probs[best_idx])

    return label, confidence, probs


# ----------------------------------------------------------------
# GAME STATE (some ai code here)
# ----------------------------------------------------------------

class GameState:
    def __init__(self):
        self.player_hp = 100
        self.player_max_hp = 100
        self.ai_hp = 100
        self.ai_max_hp = 100
        self.player_shield = 0
        self.ai_shield = 0
        self.player_last_element = None
        self.ai_last_element = None
        self.turn = "player"          # "player" | "ai_turn" | "resolving" | "game_over"
        self.log_lines = ["A wild AI Wizard appears! Draw a gesture to cast your spell."]
        self.last_player_outcome = None
        self.last_ai_outcome = None
        self.winner = None
        self.player_anim = "idle"     # idle | cast | hit
        self.ai_anim = "idle"
        self.ai_skin = random.choice([1, 2])

    def log(self, text):
        self.log_lines.append(text)
        self.log_lines = self.log_lines[-6:]  # keep last 6 lines

    def ai_last_element_for_defense(self):
        return self.ai_last_element

state = GameState()

# ----------------------------------------------------------------
# WINDOW (also the window and label setup code is mostly ai generated (but needed a lot of tweaking to get right))
# ----------------------------------------------------------------

WINDOW_W, WINDOW_H = 1100, 750
window = pyglet.window.Window(WINDOW_W, WINDOW_H, "Spell Duel")

# Drawing canvas region (right side reserved for HUD/art, left for drawing)
CANVAS_X0, CANVAS_Y0 = 20, 60
CANVAS_X1, CANVAS_Y1 = 480, 420

current_points = []
draw_batch = pyglet.graphics.Batch()
is_drawing = False

# ----------------------------------------------------------------
# LABELS
# ----------------------------------------------------------------

title_label = pyglet.text.Label(
    "SPELL DUEL", x=WINDOW_W // 2, y=WINDOW_H - 30,
    anchor_x="center", font_size=22, bold=True
)

hp_player_label = pyglet.text.Label(
    "", x=20, y=WINDOW_H - 70, anchor_x="left", font_size=14, bold=True
)
hp_ai_label = pyglet.text.Label(
    "", x=WINDOW_W - 250, y=WINDOW_H - 70, anchor_x="center", font_size=14, bold=True
)

canvas_hint_label = pyglet.text.Label(
    "Draw your spell gesture here:", x=CANVAS_X0, y=CANVAS_Y1 + 15,
    font_size=12, color=(180, 180, 180, 255)
)

last_cast_label = pyglet.text.Label(
    "", x=CANVAS_X0, y=CANVAS_Y0 - 25, font_size=12, color=(220, 220, 100, 255)
)

log_labels = [
    pyglet.text.Label(
        "", x=WINDOW_W // 2 + 1, y=140 - i * 18,
        font_size=11, color=(210, 210, 210, 255), width=600, multiline=True
    )
    for i in range(6)
]

player_wizard_label = pyglet.text.Label(
    PLAYER_IDLE, x=180, y=WINDOW_H - 100, font_name="Courier New", font_size=11,
    anchor_x="center", multiline=True, width=300
)
ai_wizard_label = pyglet.text.Label(
    AI_IDLE_1, x=WINDOW_W - 250, y=WINDOW_H - 100, font_name="Courier New", font_size=11,
    anchor_x="center", multiline=True, width=300
)

fx_label = pyglet.text.Label(
    "", x=WINDOW_W // 2, y=WINDOW_H - 100, font_name="Courier New", font_size=12,
    anchor_x="center", multiline=True, width=300, color=(255, 200, 80, 255)
)

spell_list_label = pyglet.text.Label(
    "", x=WINDOW_W - 320, y=WINDOW_H - 320, font_size=11,
    color=(160, 200, 255, 255), width=300, multiline=True
)
spell_list_text = "Spell list:\n" + "\n".join(
    f"  {g:<8} -> {SPELLS[g]['name']} ({SPELLS[g]['element']})"
    for g in SPELL_GESTURES
)
spell_list_label.text = spell_list_text

game_over_label = pyglet.text.Label(
    "", x=WINDOW_W // 2, y=WINDOW_H // 2, anchor_x="center",
    font_size=28, bold=True, color=(255, 80, 80, 255)
)


def update_hp_labels():
    hp_player_label.text = f"YOU  {state.player_hp}/{state.player_max_hp} HP" + (
        f"  [Shield {state.player_shield}]" if state.player_shield > 0 else ""
    )
    hp_ai_label.text = f"AI WIZARD  {state.ai_hp}/{state.ai_max_hp} HP" + (
        f"  [Shield {state.ai_shield}]" if state.ai_shield > 0 else ""
    )

def play_fx(frames):
    pyglet.clock.unschedule(lambda dt: setattr(fx_label, "text", ""))

    frame_delay = 0.4

    for i, frame in enumerate(frames):
        pyglet.clock.schedule_once(
            lambda dt, f=frame: setattr(fx_label, "text", f),
            i * frame_delay
        )

    pyglet.clock.schedule_once(
        lambda dt: setattr(fx_label, "text", ""),
        len(frames) * frame_delay
    )

def update_log_labels():
    lines = state.log_lines[::-1]
    for i, lbl in enumerate(log_labels):
        lbl.text = lines[i] if i < len(lines) else ""


def set_player_anim(mode):
    state.player_anim = mode
    player_wizard_label.text = {"idle": PLAYER_IDLE, "cast": PLAYER_CAST, "hit": PLAYER_HIT}[mode]


def set_ai_anim(mode):
    state.ai_anim = mode
    if state.ai_skin == 1:
        frames = {"idle": AI_IDLE_1, "cast": AI_CAST_1, "hit": AI_HIT_1}
    else:
        frames = {"idle": AI_IDLE_2, "cast": AI_CAST_2, "hit": AI_HIT_2}
    ai_wizard_label.text = frames[mode]

update_hp_labels()
update_log_labels()
set_ai_anim("idle")
set_player_anim("idle")

# ----------------------------------------------------------------
# DRAWING INPUT (based on the same code from gesture_capture)
# ----------------------------------------------------------------


def in_canvas(x, y):
    return CANVAS_X0 <= x <= CANVAS_X1 and CANVAS_Y0 <= y <= CANVAS_Y1


@window.event
def on_mouse_press(x, y, button, modifiers):
    global current_points, draw_batch, is_drawing
    if state.turn != "player":
        return
    if not in_canvas(x, y):
        return
    is_drawing = True
    current_points = [(x, y)]
    draw_batch = pyglet.graphics.Batch()


@window.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    if not is_drawing:
        return
    current_points.append((x, y))
    _redraw_stroke()


def _redraw_stroke():
    global draw_batch
    draw_batch = pyglet.graphics.Batch()
    if len(current_points) < 2:
        return
    vertices = []
    for (px, py) in current_points:
        vertices.extend([px, py])
    draw_batch.add(len(current_points), GL_LINE_STRIP, None, ("v2f", vertices))


@window.event
def on_mouse_release(x, y, button, modifiers):
    global is_drawing
    if not is_drawing:
        return
    is_drawing = False

    if state.turn != "player" or len(current_points) < 2:
        return

    label, confidence, probs = classify_gesture(current_points)
    resolve_player_turn(label, confidence)


# ----------------------------------------------------------------
# TURN RESOLUTION (mostly ai generated, but needed a lot of tweaking to get the timing and fx right)
# ----------------------------------------------------------------


def resolve_player_turn(label, confidence):
    if label not in SPELLS:
        state.log(f"You drew '{label}' — that's not a known spell gesture. Try again.")
        update_log_labels()
        return

    set_player_anim("cast")
    outcome = resolve_cast(label, confidence)
    state.last_player_outcome = outcome

    if outcome["quality"] == "fizzle":
        state.log(
            f"You attempt {outcome['spell_name']} (conf {confidence:.2f}) — it FIZZLES! No effect."
        )
        last_cast_label.text = f"Your cast: {outcome['spell_name']} — FIZZLE (conf {confidence:.2f})"
        frames = fx_for("fizzle")
        play_fx(frames)
    else:
        if outcome["spell_key"] == "circle":
            state.player_shield += outcome["new_shield"]
            state.log(
                f"You cast {outcome['spell_name']} ({outcome['quality']}, conf {confidence:.2f}) "
                f"— Shield +{outcome['new_shield']}!"
            )
        else:
            dmg, new_ai_shield, mult = apply_damage(outcome, state.ai_last_element_for_defense(), state.ai_shield)
            state.ai_shield = new_ai_shield
            state.ai_hp = max(0, state.ai_hp - dmg)
            state.player_hp = min(state.player_max_hp, state.player_hp + outcome["heal"])

            bonus_text = ""
            if mult > 1.0:
                bonus_text = " (Super effective!)"
            elif mult < 1.0:
                bonus_text = " (Resisted...)"

            heal_text = f" You heal {outcome['heal']} HP." if outcome["heal"] > 0 else ""
            state.log(
                f"You cast {outcome['spell_name']} ({outcome['quality']}, conf {confidence:.2f}) "
                f"-> {dmg} dmg{bonus_text}.{heal_text}"
            )
            if dmg > 0:
                set_ai_anim("hit")

        state.player_last_element = outcome["element"]
        last_cast_label.text = f"Your cast: {outcome['spell_name']} ({outcome['quality']}, conf {confidence:.2f})"
        frames = fx_for(SPELLS[label]["art_key"])
        play_fx(frames)

    update_hp_labels()
    update_log_labels()

    if state.ai_hp <= 0:
        end_game("player")
        return

    state.turn = "ai_turn"
    pyglet.clock.schedule_once(lambda dt: do_ai_turn(), 1.2)


def do_ai_turn():
    set_player_anim("idle")
    spell_key = ai_choose_spell(state.ai_hp, state.player_last_element)
    confidence = ai_simulated_confidence()

    set_ai_anim("cast")
    outcome = resolve_cast(spell_key, confidence)
    state.last_ai_outcome = outcome

    if outcome["quality"] == "fizzle":
        state.log(f"AI attempts {outcome['spell_name']} — it FIZZLES!")
        frames = fx_for("fizzle")
        play_fx(frames)
    else:
        if spell_key == "circle":
            state.ai_shield += outcome["new_shield"]
            state.log(f"AI casts {outcome['spell_name']} — Shield +{outcome['new_shield']}!")
        else:
            dmg, new_player_shield, mult = apply_damage(
                outcome, state.player_last_element or "neutral", state.player_shield
            )
            state.player_shield = new_player_shield
            state.player_hp = max(0, state.player_hp - dmg)
            state.ai_hp = min(state.ai_max_hp, state.ai_hp + outcome["heal"])

            bonus_text = ""
            if mult > 1.0:
                bonus_text = " (Super effective!)"
            elif mult < 1.0:
                bonus_text = " (Resisted...)"
            state.log(f"AI casts {outcome['spell_name']} -> {dmg} dmg{bonus_text}.")
            if dmg > 0:
                set_player_anim("hit")

        state.ai_last_element = outcome["element"]
        play_fx(fx_for(SPELLS[spell_key]["art_key"]))

    update_hp_labels()
    update_log_labels()

    if state.player_hp <= 0:
        end_game("ai")
        return

    pyglet.clock.schedule_once(lambda dt: _reset_to_player_turn(), 1.0)


def _reset_to_player_turn():
    set_ai_anim("idle")
    set_player_anim("idle")
    state.turn = "player"
    fx_label.text = ""
    state.log("Your turn — draw a gesture to cast.")
    update_log_labels()


def end_game(winner):
    state.turn = "game_over"
    state.winner = winner
    if winner == "player":
        game_over_label.text = "VICTORY! Press R to play again."
        game_over_label.color = (100, 255, 100, 255)
    else:
        game_over_label.text = "DEFEAT! Press R to play again."
        game_over_label.color = (255, 80, 80, 255)


def restart_game():
    global state
    state = GameState()
    update_hp_labels()
    update_log_labels()
    set_player_anim("idle")
    set_ai_anim("idle")
    fx_label.text = ""
    game_over_label.text = ""


# ----------------------------------------------------------------
# KEYBOARD
# ----------------------------------------------------------------


@window.event
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.Q:
        pyglet.app.exit()
    elif symbol == pyglet.window.key.R and state.turn == "game_over":
        restart_game()


# ----------------------------------------------------------------
# DRAW
# ----------------------------------------------------------------


@window.event
def on_draw():
    window.clear()
    title_label.draw()
    hp_player_label.draw()
    hp_ai_label.draw()
    canvas_hint_label.draw()
    last_cast_label.draw()

    # Canvas border
    pyglet.shapes.BorderedRectangle(
        CANVAS_X0, CANVAS_Y0, CANVAS_X1 - CANVAS_X0, CANVAS_Y1 - CANVAS_Y0,
        border=2, color=(20, 20, 20), border_color=(120, 120, 120)
    ).draw()

    draw_batch.draw()

    player_wizard_label.draw()
    ai_wizard_label.draw()
    fx_label.draw()
    spell_list_label.draw()

    for lbl in log_labels:
        lbl.draw()

    if state.turn == "game_over":
        game_over_label.draw()


if __name__ == "__main__":
    pyglet.app.run()