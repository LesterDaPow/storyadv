import os
import struct
import random
import moderngl
import numpy as np
from pyrr import Matrix44, Vector3
from PIL import Image
import glfw

# -----------------------------
# Config
# -----------------------------
WAD_FILE = "game_data.wad"
FORCE_GENERATE_WAD = True
SECRET_ROOM_CHANCE = 0.15
RIDDLE_ROOM_CHANCE = 0.7
WINDOW_SIZE = (800, 600)

# -----------------------------
# Helpers to read/write custom WAD
# -----------------------------
def generate_default_wad(path):
    temple = [f"Room {i}: A dimly lit hall with strange carvings." for i in range(1, 21)]
    riddles = [
        ("I am red and grow on trees. What am I?", "apple"),
        ("What can you catch but not throw?", "a cold"),
        ("What has keys but can't open locks?", "a keyboard"),
        ("I am tall, green, and made of wood. What am I?", "tree"),
        ("I have a face but no eyes. What am I?", "clock"),
        ("I fly without wings. What am I?", "time"),
        ("I run but never walk. What am I?", "water"),
        ("I am round and roll on the ground. What am I?", "ball"),
        ("I get wetter the more I dry. What am I?", "towel"),
        ("I have a spine but no bones. What am I?", "book")
    ]
    questions = [q for q, a in riddles]
    answers = [a for q, a in riddles]
    treasure = [f"Treasure chest {i}: You find gold and relics!" for i in range(1, 6)]

    lumps = {
        "TEMPLE": temple,
        "QUESTIONS": questions,
        "ANSWERS": answers,
        "TREASURE": treasure
    }

    with open(path, "wb") as f:
        for name, lines in lumps.items():
            data = "\n".join(lines).encode("utf-8")
            f.write(struct.pack("B", len(name)))
            f.write(name.encode("utf-8"))
            f.write(struct.pack("<I", len(data)))
            f.write(data)
    print(f"Custom WAD generated at {path}")

def load_wad(path):
    lumps = {}
    with open(path, "rb") as f:
        while True:
            name_len_bytes = f.read(1)
            if not name_len_bytes:
                break
            name_len = struct.unpack("B", name_len_bytes)[0]
            name = f.read(name_len).decode("utf-8")
            data_len = struct.unpack("<I", f.read(4))[0]
            data = f.read(data_len).decode("utf-8").split("\n")
            lumps[name] = data
    return lumps

# -----------------------------
# Setup WAD
# -----------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
wad_path = os.path.join(script_dir, WAD_FILE)

if FORCE_GENERATE_WAD or not os.path.exists(wad_path):
    generate_default_wad(wad_path)

lumps = load_wad(wad_path)
temple = lumps.get("TEMPLE", ["[No temple data]"])
questions = lumps.get("QUESTIONS", [])
answers = lumps.get("ANSWERS", [])
treasure = lumps.get("TREASURE", ["[No treasure data]"])
challenges = [{"description": q, "answer": a} for q, a in zip(questions, answers)]
random_challenges = challenges.copy()
random.shuffle(random_challenges)

# -----------------------------
# Moderngl + GLFW init
# -----------------------------
if not glfw.init():
    raise Exception("GLFW init failed")

window = glfw.create_window(WINDOW_SIZE[0], WINDOW_SIZE[1], "3D WAD Adventure", None, None)
glfw.make_context_current(window)

ctx = moderngl.create_context()
ctx.enable(moderngl.DEPTH_TEST)

# Simple shader for cubes (rooms)
vertex_shader = """
#version 330
in vec3 in_position;
uniform mat4 mvp;
void main() {
    gl_Position = mvp * vec4(in_position, 1.0);
}
"""
fragment_shader = """
#version 330
out vec4 f_color;
void main() {
    f_color = vec4(0.6, 0.6, 0.8, 1.0);
}
"""
prog = ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

# Cube vertices for rooms
cube_vertices = np.array([
    # front face
    -1,-1, 1, 1,-1, 1, 1, 1, 1, -1, 1, 1,
    # back face
    -1,-1,-1,-1, 1,-1, 1, 1,-1, 1,-1,-1,
    # left face
    -1,-1,-1,-1,-1, 1,-1, 1, 1,-1, 1,-1,
    # right face
    1,-1,-1, 1, 1,-1, 1, 1, 1, 1,-1, 1,
    # top face
    -1,1,-1,-1,1,1,1,1,1,1,1,-1,
    # bottom face
    -1,-1,-1,1,-1,-1,1,-1,1,-1,-1,1,
], dtype='f4')

vbo = ctx.buffer(cube_vertices.tobytes())
vao = ctx.simple_vertex_array(prog, vbo, 'in_position')

# -----------------------------
# Adventure state
# -----------------------------
room_idx = 0
challenge_idx = 0
visited = set()

camera_pos = Vector3([0,0,5])
look_dir = Vector3([0,0,-1])

def draw_room():
    # Simple MVP
    mvp = Matrix44.perspective_projection(60.0, WINDOW_SIZE[0]/WINDOW_SIZE[1], 0.1, 100.0)
    view = Matrix44.look_at(camera_pos, camera_pos + look_dir, Vector3([0,1,0]))
    model = Matrix44.from_translation([0,0,0])
    prog['mvp'].write((mvp * view * model).astype('f4').tobytes())
    vao.render()

def show_text(text):
    # Simple placeholder: print to console for now
    print("\n" + text)

# -----------------------------
# Game loop
# -----------------------------
while not glfw.window_should_close(window):
    ctx.clear(0.1, 0.1, 0.15)
    draw_room()

    if room_idx >= len(temple):
        for t in treasure:
            show_text(t)
        break

    room_name = f"Room{room_idx}"
    if room_name in visited:
        room_idx += 1
        continue
    visited.add(room_name)

    doors = random.randint(1,3)
    room_text = temple[room_idx]

    # Random riddle
    challenge = None
    if random.random() < RIDDLE_ROOM_CHANCE and challenge_idx < len(random_challenges):
        challenge = random_challenges[challenge_idx]
        challenge_idx += 1

    show_text(room_text + f"\nDoors in this room: {doors}")
    if challenge:
        show_text("\nRiddle: " + challenge["description"])
        solved = False
        while not solved:
            user_input = input("Answer the riddle: ").strip().lower()
            if user_input == challenge["answer"].lower():
                print("Correct!")
                solved = True
            else:
                print("Incorrect! Try again.")

    # Secret room jump
    if random.random() < SECRET_ROOM_CHANCE:
        secret_room = random.randint(0, len(temple)-1)
        if f"Room{secret_room}" not in visited:
            room_idx = secret_room
            continue

    room_idx += 1

    glfw.swap_buffers(window)
    glfw.poll_events()

glfw.terminate()
