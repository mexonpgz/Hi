
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
import sys
import os

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

def record_actions():
    global recording, actions
    recording = True
    actions.clear()
    last_time = time.time()
    messagebox.showinfo("Recording", f"Recording started. Press {record_hotkey.upper()} again to stop.")
    while recording:
        x, y = pyautogui.position()
        delay = time.time() - last_time
        last_time = time.time()
        actions.append(('move', x, y, delay))
        if pyautogui.mouseDown():
            actions.append(('click', x, y, delay))
        time.sleep(0.01)

def playback_actions():
    global playing, paused
    if not actions:
        messagebox.showwarning("No actions", "No recorded actions found!")
        return
    playing = True
    total_actions = len(actions) * repeat_count
    completed = 0
    while playing:
        for _ in range(repeat_count):
            for action in actions:
                while paused:
                    time.sleep(0.1)
                if not playing:
                    return
                act, x, y, delay = action
                time.sleep(delay / speed_multiplier)
                if act == 'move':
                    pyautogui.moveTo(x, y)
                elif act == 'click':
                    pyautogui.click(x, y)
                completed += 1
                update_progress(int((completed / total_actions) * 100))
        if not continuous:
            break
    playing = False
    update_progress(100)

def start_recording(): threading.Thread(target=record_actions).start()
def stop_recording():  global recording; recording = False
def start_playback(): threading.Thread(target=playback_actions).start()
def stop_playback(): global playing; playing = False
def pause_playback(): global paused; paused = True
def resume_playback(): global paused; paused = False
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

def save_file():
    file_path = filedialog.asksaveasfilename(defaultextension=".rec", filetypes=[("TinyTask File", "*.rec")])
    if file_path:
        with open(file_path, 'w') as f:
            json.dump(actions, f)

def open_file():
    global actions
    file_path = filedialog.askopenfilename(filetypes=[("TinyTask File", "*.rec")])
    if file_path:
        with open(file_path, 'r') as f:
            actions = json.load(f)

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
    if progress_var: progress_var.set(val); root.update_idletasks()

def register_hotkeys():
    keyboard.add_hotkey(record_hotkey, lambda: threading.Thread(target=start_recording).start())
    keyboard.add_hotkey(play_hotkey, lambda: threading.Thread(target=start_playback).start())

def create_tray():
    def on_quit(icon, item): icon.stop(); root.quit()
    image = Image.new('RGB', (64, 64), color=(0, 102, 204))
    menu = (item('Quit', on_quit),)
    tray_icon = pystray.Icon("TinyTaskClone", image, "TinyTask Clone", menu)
    threading.Thread(target=tray_icon.run).start()

def load_icon(name):
    path = os.path.join("icons", name)
    img = Image.open(path).resize((24, 24))
    photo = ImageTk.PhotoImage(img)
    icon_images[name] = photo
    return photo

root = tk.Tk()
root.title("TinyTask Python Clone")
root.iconbitmap("icon.ico")
root.configure(bg="white")
frame = tk.Frame(root, bg="white", bd=2, relief="ridge")
frame.pack(padx=10, pady=10)
toolbar = tk.Frame(frame, bg="white")
toolbar.pack(pady=10)

btns = [
    ("Open", open_file, "open.png"), ("Save", save_file, "save.png"),
    ("Rec", start_recording, "rec.png"), ("Stop Rec", stop_recording, "stoprec.png"),
    ("Play", start_playback, "play.png"), ("Stop", stop_playback, "stop.png"),
    ("Pause", pause_playback, "pause.png"), ("Resume", resume_playback, "resume.png"),
    ("x0.5", lambda: set_speed(0.5), "half.png"), ("x1", lambda: set_speed(1.0), "one.png"),
    ("x2", lambda: set_speed(2.0), "two.png"), ("x8", lambda: set_speed(8.0), "eight.png"),
    ("x100", lambda: set_speed(100.0), "hundred.png"), ("Repeat", set_repeat, "repeat.png"),
    ("Loop", toggle_continuous, "loop.png")
]

for label, command, icon_file in btns:
    try:
        icon = load_icon(icon_file)
        tk.Button(toolbar, image=icon, command=command, bg="white", relief="flat").pack(side="left", padx=4)
    except:
        tk.Button(toolbar, text=label, command=command, bg="white").pack(side="left", padx=4)

progress_var = tk.IntVar()
progress = ttk.Progressbar(frame, variable=progress_var, maximum=100, length=1150)
progress.pack(pady=5)
root.geometry("1220x180")
register_hotkeys()
create_tray()
root.mainloop()
