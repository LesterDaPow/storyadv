import os
import struct
import random

# -----------------------------
# Config
# -----------------------------
WAD_FILE = "game_data.wad"
FORCE_GENERATE_WAD = False  # Set to True to regenerate WAD every run

# -----------------------------
# Helpers to read/write custom WAD
# -----------------------------
def generate_default_wad(path):
    temple = [f"Room {i}: A dimly lit hall with strange carvings." for i in range(1, 101)]
    for i in range(5, 101, 5):
        temple.append(f"Room {i} secret: A hidden alcove glows faintly.")

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

    treasure = [f"Treasure chest {i}: You find gold and relics!" for i in range(1, 11)]

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

def add_to_lump(wad_file, lump_name, new_lines):
    """Helper to add new lines to a lump (modding)."""
    lumps = load_wad(wad_file)
    if lump_name not in lumps:
        lumps[lump_name] = []
    lumps[lump_name].extend(new_lines)
    with open(wad_file, "wb") as f:
        for name, lines in lumps.items():
            data = "\n".join(lines).encode("utf-8")
            f.write(struct.pack("B", len(name)))
            f.write(name.encode("utf-8"))
            f.write(struct.pack("<I", len(data)))
            f.write(data)
    print(f"Added {len(new_lines)} lines to {lump_name} in {wad_file}")

# -----------------------------
# Setup
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

# -----------------------------
# Adventure generator
# -----------------------------
def adventure_generator():
    visited = set()
    challenge_idx = 0
    room_idx = 0

    while room_idx < len(temple):
        room_name = f"Room{room_idx}"
        if room_name in visited:
            room_idx += 1
            continue
        visited.add(room_name)

        doors = random.randint(1, 3)
        room_text = temple[room_idx]
        challenge = challenges[challenge_idx] if challenge_idx < len(challenges) else None

        solved = False
        while not solved:
            user_solved = yield {"room": room_text, "challenge": challenge, "doors": doors}
            if user_solved:
                solved = True
                if challenge_idx < len(challenges) - 1:
                    challenge_idx += 1

        # Random secret room jump
        if random.random() < 0.2:
            secret_room = random.randint(0, len(temple) - 1)
            if f"Room{secret_room}" not in visited:
                room_idx = secret_room
                continue

        room_idx += 1

    # Treasures at the end
    for t in treasure:
        yield {"room": None, "challenge": None, "doors": 0, "treasure": t}

# -----------------------------
# Game loop
# -----------------------------
def play_adventure():
    gen = adventure_generator()
    step = next(gen)
    while step:
        room = step.get("room")
        challenge = step.get("challenge")
        treasure_msg = step.get("treasure")
        doors = step.get("doors", 0)

        if room:
            print("\n" + room)
            print(f"Doors in this room: {doors}")

        user_solved = False
        if challenge:
            print("\nRiddle: " + challenge["description"])
            while not user_solved:
                user_input = input("What do you want to do? (type 'answer', 'search', or 'exit') ").strip().lower()
                if user_input == "answer":
                    answer = input("Your answer: ").strip().lower()
                    if answer == challenge["answer"].lower():
                        print("Correct! You solved the riddle.")
                        user_solved = True
                    else:
                        print("Incorrect! Try again.")
                elif user_input == "search":
                    print("You search the room and find nothing special.")
                elif user_input == "exit":
                    print("You flee the adventure. Game over!")
                    return
        elif treasure_msg:
            print("\n" + treasure_msg)

        # Advance generator and tell it if the riddle was solved
        try:
            step = gen.send(user_solved)
        except StopIteration:
            break

# -----------------------------
# Start game
# -----------------------------
play_adventure()
