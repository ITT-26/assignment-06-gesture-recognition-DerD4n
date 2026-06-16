"""
Gesture Capture Tool
=====================
Draw your own unistroke gesture dataset using the mouse in a pyglet window.

Walks through 16 gesture classes (matching the Wobbrock $1 dataset categories),
prompting you to draw 10 samples of each. Saves every stroke as an XML file in
the same format used by Wobbrock et al.'s logs:

    <Gesture Name="arrow01">
        <Point X="123" Y="456" T="0"/>
        ...
    </Gesture>

Controls
--------
- Left-click and drag to draw a gesture.
- Release the mouse to save the sample and move to the next one.
- Press 'r' to redo (discard) the last saved sample.
- Press 'q' or close the window to quit early.

Output
------
Files are written to OUTPUT_DIR, one XML file per sample, named:
    <classname><sample_index>.xml      e.g. arrow01.xml ... arrow10.xml
This is mostly ai generated
"""

import os
import time
from matplotlib import lines
from matplotlib import lines
import pyglet
from pyglet.gl import GL_LINE_STRIP

# ----------------------------
# CONFIG
# ----------------------------

OUTPUT_DIR = "./datasets/my_gestures"
SAMPLES_PER_CLASS = 10

# 16 classes — same set used by Wobbrock et al.'s unistroke gesture study
GESTURE_CLASSES = [
    "arrow", "caret", "check", "circle", "delete_mark", "left_curly_brace",
    "left_sq_bracket", "pigtail", "question_mark", "rectangle",
    "right_curly_brace", "right_sq_bracket", "star", "triangle",
    "v", "x",
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------
# STATE
# ----------------------------

window = pyglet.window.Window(900, 700, "Gesture Capture Tool")

current_points = []   # list of (x, y, t) while drawing
batch = pyglet.graphics.Batch()
stroke_vertex_list = None

class_idx = 0
sample_idx = 1   # 1-indexed, matches Wobbrock naming (e.g. arrow01)
start_time = None

status_label = pyglet.text.Label(
    "", x=20, y=660, font_size=18, bold=True
)
progress_label = pyglet.text.Label(
    "", x=20, y=625, font_size=13, color=(180, 180, 180, 255)
)
hint_label = pyglet.text.Label(
    "Draw with the mouse. Release to save. 'r' = redo last. 'q' = quit.",
    x=20, y=20, font_size=11, color=(140, 140, 140, 255)
)


def current_class():
    return GESTURE_CLASSES[class_idx]


def update_labels():
    if class_idx >= len(GESTURE_CLASSES):
        status_label.text = "All done! You can close the window."
        progress_label.text = f"Saved samples in: {OUTPUT_DIR}"
        return
    status_label.text = f"Draw: {current_class()}  (sample {sample_idx}/{SAMPLES_PER_CLASS})"
    progress_label.text = f"Class {class_idx + 1}/{len(GESTURE_CLASSES)}"


update_labels()

# ----------------------------
# DRAWING / INPUT
# ----------------------------


@window.event
def on_mouse_press(x, y, button, modifiers):
    global current_points, batch, stroke_vertex_list, start_time
    if class_idx >= len(GESTURE_CLASSES):
        return

    start_time = time.perf_counter()

    # store RAW coordinates (no flip)
    current_points = [(x, y, 0.0)]

    batch = pyglet.graphics.Batch()
    stroke_vertex_list = None

@window.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    if class_idx >= len(GESTURE_CLASSES) or start_time is None:
        return

    t = time.perf_counter() - start_time

    # store RAW coordinates (no flip)
    current_points.append((x, y, t))

    _redraw_stroke()

def _redraw_stroke():
    global batch, stroke_vertex_list
    batch = pyglet.graphics.Batch()
    if len(current_points) < 2:
        return
    vertices = []
    for (px, py, _) in current_points:
        vertices.extend([px, py])
    stroke_vertex_list = batch.add(
        len(current_points), GL_LINE_STRIP, None, ("v2f", vertices)
    )


@window.event
def on_mouse_release(x, y, button, modifiers):
    global sample_idx, class_idx
    if class_idx >= len(GESTURE_CLASSES):
        return
    if len(current_points) < 2:
        return  # ignore accidental clicks

    save_sample(current_class(), sample_idx, current_points)

    sample_idx += 1
    if sample_idx > SAMPLES_PER_CLASS:
        sample_idx = 1
        class_idx += 1

    update_labels()


@window.event
def on_key_press(symbol, modifiers):
    global sample_idx, class_idx
    if symbol == pyglet.window.key.Q:
        pyglet.app.exit()
    elif symbol == pyglet.window.key.R:
        redo_last_sample()


def redo_last_sample():
    """Delete the most recently saved file and step back one sample."""
    global sample_idx, class_idx
    if class_idx >= len(GESTURE_CLASSES):
        class_idx -= 1
        sample_idx = SAMPLES_PER_CLASS
    elif sample_idx == 1 and class_idx > 0:
        class_idx -= 1
        sample_idx = SAMPLES_PER_CLASS
    else:
        sample_idx = max(1, sample_idx - 1)

    fname = os.path.join(
        OUTPUT_DIR, f"{GESTURE_CLASSES[class_idx]}{sample_idx:02d}.xml"
    )
    if os.path.exists(fname):
        os.remove(fname)
        print(f"Deleted {fname} — redo this sample.")
    update_labels()


@window.event
def on_draw():
    window.clear()
    status_label.draw()
    progress_label.draw()
    hint_label.draw()
    batch.draw()


# ----------------------------
# XML SAVING (Wobbrock format)
# ----------------------------


def save_sample(label, idx, points):
    """Write one gesture sample to an XML file matching the Wobbrock log format."""
    fname = os.path.join(OUTPUT_DIR, f"{label}{idx:02d}.xml")

    now = time.localtime()
    duration_ms = int((points[-1][2] - points[0][2]) * 1000) if len(points) > 1 else 0
    base_t_ms = int(time.time() * 1000)  # arbitrary absolute ms timestamp base

    lines = [
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>',
        (
            f'<Gesture Name="{label}{idx:02d}" Subject="1" Speed="medium" '
            f'Number="{idx}" NumPts="{len(points)}" Millseconds="{duration_ms}" '
            f'AppName="GestureCapture" AppVer="1.0.0.0" '
            f'Date="{time.strftime("%A, %B %d, %Y", now)}" '
            f'TimeOfDay="{time.strftime("%I:%M:%S %p", now)}">'
        ),
    ]
    for (x, y, t) in points:
        flipped_y = window.height - y  # flip ONLY here
        t_ms = base_t_ms + int(t * 1000)
        lines.append(
            f'<Point X="{int(round(x))}" Y="{int(round(flipped_y))}" T="{t_ms}" />'
        )
    lines.append("</Gesture>")

    with open(fname, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Saved {fname}  ({len(points)} points)")


# ----------------------------
# RUN
# ----------------------------

if __name__ == "__main__":
    print(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")
    print(f"Classes: {GESTURE_CLASSES}")
    pyglet.app.run()