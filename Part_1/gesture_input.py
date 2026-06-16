import pyglet
from Part_1.recognizer import DollarRecognizer, Point
from pyglet.gl import GL_LINE_STRIP, GL_POINTS, GL_LINES, glColor3f, glPointSize, glLineWidth

pyglet.options["debug_gl"] = False

# ----------------------------
# WINDOWS
# ----------------------------

window = pyglet.window.Window(900, 700, "Gesture Input")
viz = pyglet.window.Window(1500, 500, "Visualization")

# ----------------------------
# GLOBAL STATE
# ----------------------------

rec = DollarRecognizer()
batch = pyglet.graphics.Batch()

stroke = None
current = []
steps = {}
matched_input = None
matched_template = None
result = "Draw a gesture"

# ----------------------------
# LABEL
# ----------------------------

label = pyglet.text.Label(
    result,
    x=10,
    y=670,
    font_size=16
)

# ----------------------------
# INPUT (mostly ai generated)
# ----------------------------

@window.event
def on_mouse_press(x, y, button, modifiers):
    global current, batch, stroke
    current = [Point(x, y)]
    batch = pyglet.graphics.Batch()
    stroke = None

@window.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    current.append(Point(x, y))
    update_stroke(current)

@window.event
def on_mouse_release(x, y, button, modifiers):
    global steps, result, matched_input, matched_template

    if len(current) < 2:
        return

    steps = rec.get_processing_steps(current)
    name, score, aligned_in, temp_pts = rec.recognize(current)

    matched_input = aligned_in
    matched_template = temp_pts
    result = f"{name} ({score:.2f})"
    label.text = result
    
    viz.dispatch_event('on_draw')

# ----------------------------
# STROKE UPDATE
# ----------------------------

def update_stroke(points):
    global batch, stroke
    batch = pyglet.graphics.Batch()

    if len(points) < 2:
        return

    vertices = []
    for p in points:
        vertices.extend([p.x, p.y])

    stroke = batch.add(
        len(points),
        GL_LINE_STRIP,
        None,
        ("v2f", vertices)
    )

@window.event
def on_draw():
    window.clear()
    label.draw()
    batch.draw()

# ----------------------------
# VISUALIZATION RENDERING (nearly completely ai generated)
# ----------------------------

layout = {
    "raw": (150, 220),
    "resampled": (450, 220),
    "rotated": (750, 220),
    "scaled": (1050, 220),
    "matching": (1350, 220),
}

viz_text_labels = {
    k: pyglet.text.Label(k.upper(), x=v[0], y=v[1] + 140, anchor_x='center', font_size=12, bold=True)
    for k, v in layout.items()
}

def draw_steps_with_points(points, ox, oy):
    """Draws pipeline stages showing distinct, scannable sample points."""
    if len(points) < 2:
        return

    cx = sum(p.x for p in points) / len(points)
    cy = sum(p.y for p in points) / len(points)

    vertices = []
    for p in points:
        vertices.extend([p.x - cx + ox, p.y - cy + oy])

    # Draw structural stroke path lines
    glColor3f(1.0, 1.0, 1.0)
    glLineWidth(1.5)
    pyglet.graphics.vertex_list(len(points), ("v2f", vertices)).draw(GL_LINE_STRIP)
    
    # Overlay high-contrast explicit sample dots
    glPointSize(5.0)
    pyglet.graphics.vertex_list(len(points), ("v2f", vertices)).draw(GL_POINTS)

def draw_matching_overlay(input_pts, template_pts, ox, oy):
    """Overlays the input with the template and generates error bar vectors."""
    if not input_pts or not template_pts:
        return

    # Both datasets are pre-centered at (0,0) by the engine, apply viewport translation offsets directly
    
    # 1. Render Point-to-Point Distance Vectors (Error Margin Bars)
    error_vertices = []
    for p1, p2 in zip(input_pts, template_pts):
        error_vertices.extend([p1.x + ox, p1.y + oy, p2.x + ox, p2.y + oy])
        
    glColor3f(0.8, 0.2, 0.2) # Crimson Red
    glLineWidth(1.0)
    pyglet.graphics.vertex_list(len(error_vertices) // 2, ("v2f", error_vertices)).draw(GL_LINES)
    
    # 2. Render Reference Target Template Structure
    t_vertices = []
    for p in template_pts:
        t_vertices.extend([p.x + ox, p.y + oy])
    glColor3f(0.0, 0.7, 1.0) # Vivid Cyan
    glLineWidth(2.0)
    pyglet.graphics.vertex_list(len(template_pts), ("v2f", t_vertices)).draw(GL_LINE_STRIP)
    glPointSize(4.0)
    pyglet.graphics.vertex_list(len(template_pts), ("v2f", t_vertices)).draw(GL_POINTS)

    # 3. Render Final Aligned Input Gesture Structure
    i_vertices = []
    for p in input_pts:
        i_vertices.extend([p.x + ox, p.y + oy])
    glColor3f(1.0, 1.0, 1.0) # White
    glLineWidth(2.0)
    pyglet.graphics.vertex_list(len(input_pts), ("v2f", i_vertices)).draw(GL_LINE_STRIP)
    glPointSize(4.0)
    pyglet.graphics.vertex_list(len(input_pts), ("v2f", i_vertices)).draw(GL_POINTS)

@viz.event
def on_draw():
    viz.clear()

    if not steps:
        return

    for name, (x, y) in layout.items():
        viz_text_labels[name].draw()
        
        if name == "matching":
            draw_matching_overlay(matched_input, matched_template, x, y)
        elif name in steps:
            draw_steps_with_points(steps[name], x, y)

# ----------------------------
# RUN
# ----------------------------
pyglet.app.run()