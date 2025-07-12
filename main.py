import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pyautogui
import keyboard
import time
import threading
import json
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageTk
import os
import sys

# --- Helper for PyInstaller paths ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Global Vars ---
actions = []
recording = False
playing = False
paused = False
speed_multiplier = 1.0
repeat_count = 1
continuous = False
record_hotkey = 'f8'
play_hotkey = 'f9'
progress = None
progress_var = None
icon_images = {}
status_var = None
hotkey_handlers = []

# --- Recording ---
def record_actions():
    global recording, actions
    recording = True
    actions.clear()
    last_time = time.time()
    messagebox.showinfo("Recording", f"Recording started. Press {record_hotkey.upper()} again to stop.")

    def on_event(e):
        nonlocal last_time
        if not recording:
            return
        delay = time.time() - last_time
        last_time = time.time()
        if e.event_type == 'down':
            actions.append(('keydown', e.name, delay))
        elif e.event_type == 'up':
            actions.append(('keyup', e.name, delay))

    keyboard.hook(on_event)

    while recording:
        x, y = pyautogui.position()
        delay = time.time() - last_time
        last_time = time.time()
        actions.append(('move', x, y, delay))
        time.sleep(0.01)

    keyboard.unhook_all()
    save_file(auto=True)

# --- Playback ---
def playback_actions():
    global playing, paused
    if not actions:
        messagebox.showwarning("No actions", "No recorded actions found!")
        return
    playing = True
    total_actions = len(actions) * repeat_count
    completed = 0
    set_status("Playing...")
    while playing:
        for _ in range(repeat_count):
            for action in actions:
                while paused:
                    set_status("Paused...")
                    time.sleep(0.1)
                if not playing:
                    return
                act = action[0]
                delay = action[-1]
                if act == 'move':
                    _, x, y, delay = action
                    pyautogui.moveTo(x, y, duration=max(delay / speed_multiplier, 0.01))  # Smooth move
                elif act == 'click':
                    _, x, y, _ = action
                    pyautogui.click(x, y)
                elif act == 'keydown':
                    _, keyname, _ = action
                    keyboard.press(keyname)
                elif act == 'keyup':
                    _, keyname, _ = action
                    keyboard.release(keyname)
                else:
                    pass
                completed += 1
                update_progress(int((completed / total_actions) * 100))
                time.sleep(0.01)
            if not continuous:
                break
    playing = False
    update_progress(100)
    set_status("Idle")

# --- Controls ---
def start_recording(): threading.Thread(target=record_actions).start()
def stop_recording(): global recording; recording = False; set_status("Idle")
def start_playback(): threading.Thread(target=playback_actions).start()
def stop_playback(): global playing; playing = False; set_status("Stopped")
def pause_playback(): global paused; paused = True
def resume_playback(): global paused; paused = False; set_status("Resumed")
def set_speed(multiplier): global speed_multiplier; speed_multiplier = multiplier

def set_repeat():
    global repeat_count
    count = simple_input("Repeat Count", "Enter number of repetitions:")
    if count.isdigit():
        repeat_count = int(count)
    else:
        messagebox.showwarning("Invalid", "Please enter a valid number.")

def toggle_continuous():
    global continuous
    continuous = not continuous
    messagebox.showinfo("Loop", f"Loop is now {'ON' if continuous else 'OFF'}")

def save_file(auto=False):
    file_path = "last_macro.rec" if auto else filedialog.asksaveasfilename(defaultextension=".rec", filetypes=[("TinyTask File", "*.rec")])
    if file_path:
        with open(file_path, 'w') as f:
            json.dump(actions, f)

def open_file():
    global actions
    file_path = filedialog.askopenfilename(filetypes=[("TinyTask File", "*.rec")])
    if file_path:
        with open(file_path, 'r') as f:
            actions = json.load(f)

def load_last():
    global actions
    if os.path.exists("last_macro.rec"):
        with open("last_macro.rec", 'r') as f:
            actions = json.load(f)

def set_hotkeys():
    global record_hotkey, play_hotkey
    new_rec = simple_input("Set Record Hotkey", f"Current: {record_hotkey}. Enter new key:")
    new_play = simple_input("Set Play Hotkey", f"Current: {play_hotkey}. Enter new key:")
    if new_rec:
        record_hotkey = new_rec
    if new_play:
        play_hotkey = new_play
    register_hotkeys()
    messagebox.showinfo("Hotkeys", f"New Hotkeys Set:\nRecord = {record_hotkey.upper()}\nPlay = {play_hotkey.upper()}")

def simple_input(title, prompt):
    input_win = tk.Toplevel(root)
    input_win.title(title)
    tk.Label(input_win, text=prompt).pack()
    entry = tk.Entry(input_win)
    entry.pack()
    entry.focus_set()
    val = tk.StringVar()
    def submit(): val.set(entry.get()); input_win.destroy()
    tk.Button(input_win, text="OK", command=submit).pack()
    root.wait_window(input_win)
    return val.get()

def update_progress(val):
    if progress_var:
        progress_var.set(val)
    root.update_idletasks()

def set_status(text):
    if status_var:
        status_var.set(f"Status: {text}")

def register_hotkeys():
    global hotkey_handlers
    for handler in hotkey_handlers:
        keyboard.remove_hotkey(handler)
    hotkey_handlers = []
    h1 = keyboard.add_hotkey(record_hotkey, lambda: threading.Thread(target=start_recording).start())
    h2 = keyboard.add_hotkey(play_hotkey, lambda: threading.Thread(target=start_playback).start())
    hotkey_handlers.extend([h1, h2])

def create_tray():
    def on_quit(icon, item): icon.stop(); root.quit()
    image = Image.new('RGB', (64, 64), color=(0, 102, 204))
    menu = (item('Quit', on_quit),)
    tray_icon = pystray.Icon("TinyTaskClone", image, "TinyTask Clone", menu)
    threading.Thread(target=tray_icon.run).start()

def load_icon(name):
    path = resource_path(os.path.join("icons", name))
    img = Image.open(path).resize((48, 48))  # Larger icon for bigger button
    photo = ImageTk.PhotoImage(img)
    icon_images[name] = photo
    return photo

# --- GUI ---
root = tk.Tk()
root.title("TinyTask PRO Clone")
root.iconbitmap(default=resource_path("icon.ico"))
root.configure(bg="white")
frame = tk.Frame(root, bg="white", bd=2, relief="ridge")
frame.pack(padx=10, pady=10)
toolbar = tk.Frame(frame, bg="white")
toolbar.pack(pady=10)

# --- Big Main Buttons ---
btns = [
    ("Open", open_file, "open.png"),
    ("Save", lambda: save_file(False), "save.png"),
    ("Rec", start_recording, "rec.png"),
    ("Stop Rec", stop_recording, "stoprec.png"),
    ("Play", start_playback, "play.png"),
    ("Stop", stop_playback, "stop.png"),
    ("Pause", pause_playback, "pause.png"),
    ("Resume", resume_playback, "resume.png")
]

for label, command, icon_file in btns:
    try:
        icon = load_icon(icon_file)
        tk.Button(toolbar, image=icon, command=command, bg="white", relief="flat", width=64, height=64).pack(side="left", padx=6)
    except:
        tk.Button(toolbar, text=label, command=command, bg="white", width=8, height=2).pack(side="left", padx=6)

# --- Other Menu ---
other_menu = tk.Menubutton(toolbar, text="Other", relief="raised", bg="white")
other_menu.menu = tk.Menu(other_menu, tearoff=0)
other_menu["menu"] = other_menu.menu
other_menu.menu.add_command(label="x0.5 Speed", command=lambda: set_speed(0.5))
other_menu.menu.add_command(label="x1 Speed", command=lambda: set_speed(1.0))
other_menu.menu.add_command(label="x2 Speed", command=lambda: set_speed(2.0))
other_menu.menu.add_command(label="x8 Speed", command=lambda: set_speed(8.0))
other_menu.menu.add_command(label="x100 Speed", command=lambda: set_speed(100.0))
other_menu.menu.add_command(label="Repeat", command=set_repeat)
other_menu.menu.add_command(label="Loop", command=toggle_continuous)
other_menu.menu.add_command(label="Set Hotkeys", command=set_hotkeys)
other_menu.pack(side="left", padx=6)

# --- Progress ---
progress_var = tk.IntVar()
progress = ttk.Progressbar(frame, variable=progress_var, maximum=100, length=1150)
progress.pack(pady=5)

status_var = tk.StringVar(value="Status: Idle")
tk.Label(root, textvariable=status_var, bg="white", fg="blue").pack()

root.geometry("1220x240")
register_hotkeys()
create_tray()
load_last()
root.mainloop()
