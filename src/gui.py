from playback import play_song, pause_song, resume_song, set_volume, state as playback_state, seek_song
from export import export_songs, reverse_replace_illegals
from cover_util import get_mp3_cover_and_duration
from config import SONGS_PATH
from utils import is_hash
import customtkinter as tki
import tkinter.messagebox
import threading
import tkinter
import random
import json
import time
import os
# Only import numpy as np if used (for silence detection)
try:
    import numpy as np
except ImportError:
    np = None

STATE_FILE = os.path.join(os.path.dirname(__file__), '..', '.dev_state.json')

# --- State ---
root = None
config = None
song_files = []
song_buttons = []
queue = []
song_index = 0
queue_index = 0

now_playing_view = None
queue_view = None
queue_listbox = None
song_title_label = None
song_artist_label = None
song_duration_label = None
song_cover_label = None
switch_btn = None

# Add shuffle bag state
temp_bag = []

# --- GUI Functions ---
def save_dev_state():
    try:
        state = {
            'song_index': song_index,
            'queue_index': queue_index,
            'queue': queue,
            'current_song': song_files[song_index] if song_files else None,
            'volume': config.get('volume', 1.0),
            'paused': playback_state.paused if 'playback_state' in globals() else False
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print('Failed to save dev state:', e)

def load_dev_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
            return state
    except Exception as e:
        print('Failed to load dev state:', e)
    return None

# Wrap run_app to restore state if available
def run_app(config_, rich_presence_):
    global config, rpc, song_index, queue_index, queue
    config = config_
    rpc = rich_presence_

    # Restore state if available
    state = load_dev_state()
    if state:
        song_index = state.get('song_index', 0)
        queue_index = state.get('queue_index', 0)
        queue = state.get('queue', [])
        config['volume'] = state.get('volume', 1.0)

    create_gui()

    root.mainloop()

def create_gui():
    global root
    root = tki.CTk()
    root.geometry("500x350")
    root.title("Osu!Radio (lazer)")
    root.resizable(False, False)

    if not config["osu_folder"]:
        select_osu_folder_gui()

    elif not os.path.exists(SONGS_PATH):
        export_songs_gui()

    else:
        main_gui()

def main_gui():
    global song_files, song_buttons, song_index, now_playing_view
    global queue_view, queue_listbox, song_title_label, song_artist_label
    global song_duration_label, song_cover_label, switch_btn
    for widget in root.winfo_children():
        widget.destroy()

    song_files = [f for f in os.listdir(SONGS_PATH) if f.lower().endswith(".mp3")]
    song_index = 0
    song_buttons.clear()

    # Layout
    content_frame = tki.CTkFrame(root, width=500, height=300, corner_radius=0)
    content_frame.pack(fill="both", expand=True)
    song_list = tki.CTkScrollableFrame(
        content_frame, width=180, height=350, corner_radius=0
    )
    song_list.pack(fill="y", side="left", expand=False)
    bind_fast_scroll(song_list)

    # Song info/queue view
    right_frame = tki.CTkFrame(
        content_frame,
        width=300,
        height=100,
        corner_radius=15,
        fg_color=("#23263a", "#23263a"),
    )
    right_frame.pack(fill="both", expand=True, side="right", padx=10, pady=10)
    now_playing_view = tki.CTkFrame(right_frame, fg_color=right_frame.cget("fg_color"))
    now_playing_view.pack(fill="both", expand=True)
    queue_view = tki.CTkFrame(right_frame, fg_color="transparent")

    # Song info labels
    song_cover_label = tki.CTkLabel(now_playing_view, text="", image=None)
    song_cover_label.pack(padx=16, pady=(18, 2))
    song_title_label = tki.CTkLabel(
        now_playing_view,
        text="No song playing",
        font=(None, 18, "bold"),
        text_color="#f0f0f0",
        anchor="w",
    )
    song_title_label.pack(fill="x", padx=16, pady=(0, 2))
    song_artist_label = tki.CTkLabel(
        now_playing_view, text="", font=(None, 14), text_color="#b0b0b0", anchor="w"
    )
    song_artist_label.pack(fill="x", padx=16, pady=(0, 2))
    song_duration_label = tki.CTkLabel(
        now_playing_view, text="", font=(None, 12), text_color="#b0b0b0", anchor="w"
    )
    song_duration_label.pack(fill="x", padx=16, pady=(0, 10))

    # Queue view
    queue_listbox = tki.CTkTextbox(
        queue_view,
        font=(None, 13),
        width=260,
        height=120,
        fg_color="#23263a",
        text_color="#f0f0f0",
        border_width=0,
    )
    queue_listbox.pack(fill="both", expand=True, padx=16, pady=16)
    queue_listbox.configure(state="disabled")

    # Player controls
    player_controls = tki.CTkFrame(
        right_frame,
        width=300,
        height=60,
        corner_radius=15,
        fg_color=("#181a24", "#181a24"),
        border_width=2,
        border_color=("#44475a", "#44475a"),
    )
    player_controls.pack(fill="x", side="bottom", pady=10, padx=16)



    # --- Player Controls Layout ---
    controls_inner = tki.CTkFrame(player_controls, fg_color="transparent")
    controls_inner.pack(expand=True, fill=None, padx=8, pady=4)

    # Left: Switcher button
    leftmost_controls = tki.CTkFrame(controls_inner, fg_color="transparent")
    leftmost_controls.pack(side="left", padx=(0, 6), pady=0)
    switch_btn = tki.CTkButton(
        leftmost_controls,
        text="≡",
        width=24,
        height=24,
        font=(None, 16, "bold"),
        fg_color=("#23263a", "#23263a"),
        hover_color=("#3a3d4a", "#3a3d4a"),
        corner_radius=8,
        border_width=2,
        border_color=("#44475a", "#44475a"),
        text_color=("#f0f0f0", "#f0f0f0"),
        command=switch_view
    )
    switch_btn.pack(side="left", padx=0, pady=8)

    # Center: prev/play/pause/next
    left_controls = tki.CTkFrame(controls_inner, fg_color="transparent")
    left_controls.pack(side="left", padx=0, pady=0)
    btn_style = dict(
        width=24,
        height=24,
        font=(None, 12, "bold"),
        fg_color=("#23263a", "#23263a"),
        hover_color=("#3a3d4a", "#3a3d4a"),
        corner_radius=8,
        border_width=2,
        border_color=("#44475a", "#44475a"),
        text_color=("#f0f0f0", "#f0f0f0"),
    )
    prev_btn = tki.CTkButton(left_controls, text="⏮", command=play_prev_song, **btn_style)
    prev_btn.pack(side="left", padx=(0, 2), pady=8)
    play_btn = tki.CTkButton(left_controls, text="▶", command=resume_song, **btn_style)
    play_btn.pack(side="left", padx=2, pady=8)
    pause_btn = tki.CTkButton(left_controls, text="⏸", command=pause_song, **btn_style)
    pause_btn.pack(side="left", padx=2, pady=8)
    next_btn = tki.CTkButton(left_controls, text="⏭", command=play_next_song, **btn_style)
    next_btn.pack(side="left", padx=2, pady=8)

    # Right: settings button
    right_controls = tki.CTkFrame(controls_inner, fg_color="transparent")
    right_controls.pack(side="right", padx=(6, 0), pady=0)
    settings_btn = tki.CTkButton(
        right_controls,
        text="⚙",
        width=24,
        height=24,
        font=(None, 16, "bold"),
        fg_color=("#23263a", "#23263a"),
        hover_color=("#3a3d4a", "#3a3d4a"),
        corner_radius=8,
        border_width=2,
        border_color=("#44475a", "#44475a"),
        text_color=("#f0f0f0", "#f0f0f0"),
        command=open_settings_dialog
    )
    settings_btn.pack(side="right", padx=0, pady=8)

    # Progress bar and time below controls (use grid to prevent overflow)
    progress_frame = tki.CTkFrame(player_controls, fg_color="transparent")
    progress_frame.pack(fill="x", padx=16, pady=(0, 4))
    progress_var = tki.DoubleVar(value=0)
    progress_bar = tki.CTkProgressBar(progress_frame, variable=progress_var, height=8)
    progress_bar.grid(row=0, column=0, sticky="ew", padx=0)
    progress_time = tki.CTkLabel(progress_frame, text="0:00 / 0:00", width=75, anchor="e")
    progress_time.grid(row=0, column=1, sticky="e", padx=0)
    progress_frame.grid_rowconfigure(0, weight=0)
    progress_frame.grid_columnconfigure(0, weight=1)
    progress_frame.grid_columnconfigure(1, weight=0)

    def on_progress_click(event):
        # Calculate position in song
        bar_width = progress_bar.winfo_width()
        rel_x = event.x / bar_width
        rel_x = max(0, min(rel_x, 1))
        dur = playback_duration[0]
        if dur > 0:
            seek_time = rel_x * dur
            seek_song(seek_time)
            playback_start_time[0] = time.time() - seek_time

    progress_bar.bind('<Button-1>', on_progress_click)

    # --- Song progress state and progress bar drag-to-seek support ---
    playback_start_time = [None]
    playback_duration = [0]
    dragging = {'active': False}

    def on_song_start(path):
        try:
            import soundfile as sf
            with sf.SoundFile(path) as f:
                playback_duration[0] = f.frames / f.samplerate
        except Exception:
            playback_duration[0] = 0
        playback_start_time[0] = time.time()

    # Patch play_song_by_index to call on_song_start
    orig_play_song_by_index = play_song_by_index
    def patched_play_song_by_index(idx, on_end=None):
        path = os.path.join(SONGS_PATH, song_files[idx])
        on_song_start(path)
        orig_play_song_by_index(idx) if on_end is None else orig_play_song_by_index(idx, on_end=on_end)
    globals()['play_song_by_index'] = patched_play_song_by_index

    def on_progress_press(event):
        dragging['active'] = True
        update_drag(event)

    def on_progress_release(event):
        dragging['active'] = False
        update_drag(event, seek=True)

    def on_progress_motion(event):
        if dragging['active']:
            update_drag(event)

    def update_drag(event, seek=False):
        bar_width = progress_bar.winfo_width()
        rel_x = event.x / bar_width
        rel_x = max(0, min(rel_x, 1))
        dur = playback_duration[0]
        if dur and dur > 0:
            seek_time = rel_x * dur
            mins, secs = divmod(int(seek_time), 60)
            mins2, secs2 = divmod(int(dur), 60)
            progress_var.set(rel_x)
            progress_time.configure(text=f"{mins}:{secs:02d} / {mins2}:{secs2:02d}")
            if seek:
                seek_song(seek_time)
                playback_start_time[0] = time.time() - seek_time
        else:
            progress_var.set(0)
            progress_time.configure(text="0:00 / 0:00")

    progress_bar.bind('<Button-1>', on_progress_press)
    progress_bar.bind('<B1-Motion>', on_progress_motion)
    progress_bar.bind('<ButtonRelease-1>', on_progress_release)

    def update_progress():
        if dragging['active']:
            player_controls.after(1000, update_progress)
            return
        dur = playback_duration[0]
        if playback_state.stream and dur and dur > 0 and playback_start_time[0]:
            pos = max(0, min(time.time() - playback_start_time[0], dur))
            progress_var.set(pos / dur)
            mins, secs = divmod(int(pos), 60)
            mins2, secs2 = divmod(int(dur), 60)
            progress_time.configure(text=f"{mins}:{secs:02d} / {mins2}:{secs2:02d}")
            # Update Discord RPC with progress
            if rpc:
                rpc.current['start'] = time.time() - pos
                rpc.current['end'] = rpc.current['start'] + dur
                rpc.set(rpc.current)
        else:
            progress_var.set(0)
            progress_time.configure(text="0:00 / 0:00")
        player_controls.after(1000, update_progress)

    update_progress()

    # Song list buttons
    for idx, song in enumerate(song_files):
        display_name = get_display_name(song)
        btn = tki.CTkButton(
            song_list,
            text=display_name,
            command=lambda i=idx: play_song_by_index(i),
            width=170,
            height=36,
            font=(None, 13, "bold"),
            fg_color=("#23263a", "#23263a"),
            text_color=("#f0f0f0", "#f0f0f0"),
            corner_radius=10,
            anchor="w",
            hover_color=("#3a3d4a", "#3a3d4a"),
            border_width=2,
            border_color=("#44475a", "#44475a"),
        )
        btn.pack(pady=5, padx=10, anchor="w", fill="x")
        btn.bind("<Button-3>", lambda e, i=idx: on_song_right_click(e, i))
        song_buttons.append(btn)

def select_osu_folder_gui():
    for widget in root.winfo_children():
        widget.destroy()
    if config.get("osu_folder"):
        export_songs_gui()
        return
    set_title("Select osu!lazer folder")
    tki.CTkLabel(
        root, text="Welcome to Osu!Radio (lazer)", font=(None, 30, "bold")
    ).pack(pady=20)
    tki.CTkLabel(
        root,
        text="To begin exporting songs, please select your osu!lazer folder.",
        font=(None, 15),
    ).pack(pady=20)
    tki.CTkButton(
        root,
        text="Select osu!lazer folder",
        command=select_folder,
        width=200,
        height=50,
        font=(None, 15),
    ).pack(pady=20)

def export_songs_gui():
    set_title("Export Songs")
    for widget in root.winfo_children():
        widget.destroy()
    root.update_idletasks()
    tki.CTkLabel(root, text="Export Songs", font=(None, 30, "bold")).pack(pady=20)
    tki.CTkLabel(
        root,
        text="Click the button below to export songs from your osu!lazer folder.",
        font=(None, 15),
    ).pack(pady=20)
    bar = tki.CTkProgressBar(
        root, mode="determinate", width=300, height=8, corner_radius=3
    )
    bar.set(-1)
    bar.pack(pady=5)

    def do_export():
        try:
            export_songs(
                config["osu_folder"],
                SONGS_PATH,
                callback=lambda i, total: bar.set((i + 1) / total),
            )
            main_gui()
        except Exception as e:
            tkinter.messagebox.showerror("Export Error", str(e))

    tki.CTkButton(
        root,
        text="Export Songs",
        command=do_export,
        width=200,
        height=50,
        font=(None, 15),
    ).pack(pady=20)

def switch_view():
    if now_playing_view.winfo_ismapped():
        now_playing_view.pack_forget()
        queue_view.pack(fill="both", expand=True)
        # Always keep icon, do not change text
        update_queue_view()
    else:
        queue_view.pack_forget()
        now_playing_view.pack(fill="both", expand=True)
        # Always keep icon, do not change text

def update_queue_view():
    queue_listbox.configure(state="normal")
    queue_listbox.delete("1.0", "end")
    for i, song in enumerate(queue):
        song_name = get_display_name(song)
        queue_listbox.insert("end", f"{i+1}. {song_name}\n")
    queue_listbox.configure(state="disabled")

def get_display_name(song):
    base = reverse_replace_illegals(song).removesuffix(".mp3")
    if base in config.get("custom_song_names", {}):
        return config["custom_song_names"][base]
    if is_hash(base):
        base = base[:8]
    if "." in base:
        base, _ = base.rsplit(".", 1)
    max_len = 18
    if len(base) > max_len:
        base = base[: max_len - 3] + "..."
    return base

def on_song_right_click(event, idx):
    menu = tkinter.Menu(root, tearoff=0)
    menu.add_command(
        label="Play", command=lambda: [menu.destroy(), play_song_by_index(idx)]
    )
    menu.add_command(
        label="Add to queue", command=lambda: [menu.destroy(), add_to_queue(idx)]
    )
    menu.add_command(label="Rename", command=lambda: [menu.destroy(), rename_song(idx)])
    menu.post(event.x_root, event.y_root)

def add_to_queue(idx):
    song = song_files[idx]
    if song not in queue:
        queue.append(song)
        update_queue_view()

def rename_song(idx):
    song = song_files[idx]
    base = reverse_replace_illegals(song).removesuffix(".mp3")
    new_name = tkinter.simpledialog.askstring(
        "Rename Song", f'Enter new name for "{get_display_name(song)}":', parent=root
    )
    if new_name:
        config["custom_song_names"][base] = new_name
        for b in song_buttons:
            b.configure(text=get_display_name(song_files[song_buttons.index(b)]))
        update_queue_view()

def highlight_now_playing(idx):
    # Defensive: clamp idx to valid range
    if not song_buttons:
        return
    idx = max(0, min(idx, len(song_buttons) - 1))
    for i, b in enumerate(song_buttons):
        if i == idx:
            b.configure(border_color="#00bfff", border_width=3)
        else:
            b.configure(border_color="#44475a", border_width=2)

def play_song_by_index(idx):
    global song_index
    song_index = idx

    path = os.path.join(SONGS_PATH, song_files[song_index])
    # Set playback volume from config before starting playback
    set_volume(config.get('volume', 1.0))
    # Determine on_end if not provided
    on_end = play_next_song if config.get('autoplay') else reset_rich_presence
    print(f'[DEBUG] play_song_by_index: idx={idx}, on_end={on_end}')
    play_song(path, on_end=on_end)

    update_now_playing_view(path)
    highlight_now_playing(song_index)

    # Discord RPC update
    if rpc:
        try:
            filename = os.path.basename(path)
            base = reverse_replace_illegals(filename).removesuffix('.mp3')
            if base in config.get('custom_song_names', {}):
                song_name = config['custom_song_names'][base]
            else:
                song_name = base[:8] if is_hash(base) else base.split('.',1)[0]

            artist = base.rsplit('.',1)[1] if '.' in base else "Unknown Artist"

            cover, duration = get_mp3_cover_and_duration(path)

            rpc.current['state'] = f'By {artist}'
            rpc.current['details'] = f'Listening to {song_name}'
            rpc.current['start'] = time.time()-1
            rpc.current['end'] = time.time()+duration*60
            rpc.set(rpc.current)

        except Exception as e:
            print(e)

def reset_rich_presence():
    if rpc:
        rpc.current['state'] = 'In the menus'
        rpc.current['details'] = 'Listening to osu!radio'
        rpc.current['start'] = rpc.start_time
        rpc.current['end'] = None
        rpc.set(rpc.current)

def update_now_playing_view(path):
    try:
        filename = os.path.basename(path)
        base = reverse_replace_illegals(filename).removesuffix(".mp3")
        if base in config.get("custom_song_names", {}):
            song_name = config["custom_song_names"][base]
        else:
            song_name = base[:8] if is_hash(base) else base.split(".", 1)[0]
        artist = base.rsplit(".", 1)[1] if "." in base else "Unknown Artist"
        cover, duration = get_mp3_cover_and_duration(path)
        if cover:
            cover.thumbnail((96, 96))
            try:
                ctkimg = tki.CTkImage(
                    light_image=cover, dark_image=cover, size=cover.size
                )
                song_cover_label.configure(image=ctkimg, text="")
                song_cover_label.image = ctkimg
            except Exception:
                song_cover_label.configure(image=None, text="")
                song_cover_label.image = None
        else:
            song_cover_label.configure(image=None, text="")
            song_cover_label.image = None
        mins = int(duration // 60) if duration else 0
        secs = int(duration % 60) if duration else 0
        song_duration_label.configure(text=f"{mins}:{secs:02d}" if duration else "")
        song_title_label.configure(text=song_name)
        song_artist_label.configure(text=artist)
    except Exception:
        song_title_label.configure(text="Unknown")
        song_artist_label.configure(text="")
        song_duration_label.configure(text="")
        song_cover_label.configure(image=None, text="")
        song_cover_label.image = None

def play_next_song():
    global song_index, queue_index, temp_bag
    # If queue is not empty, play next in queue
    if queue:
        queue_index = (queue_index + 1) % len(queue)
        next_song = queue[queue_index]
        if next_song in song_files:
            song_index = song_files.index(next_song)
        play_song_by_index(song_index)
        return
    # Shuffle mode
    if config.get('shuffle', False):
        if not temp_bag:
            temp_bag = list(range(len(song_files)))
            random.shuffle(temp_bag)
        song_index = temp_bag.pop()
        play_song_by_index(song_index)
        return
    # Default: next in list
    if song_files:
        song_index = (song_index + 1) % len(song_files)
        play_song_by_index(song_index)

def play_prev_song():
    global song_index
    if song_files:
        song_index = (song_index - 1) % len(song_files)
        play_song_by_index(song_index)

def set_title(title):
    root.title(f"Osu!Radio (lazer) - {title}")

def select_folder():
    folder = tki.filedialog.askdirectory(
        mustexist=True,
        title="Select osu!lazer folder",
        initialdir=os.path.expanduser("~"),
    )
    if not folder:
        return
    # Check if the user picked the files/ directory, not the root osu!lazer folder
    if folder and os.path.basename(folder) == "files":
        folder = os.path.dirname(folder)
    config["osu_folder"] = folder
    export_songs_gui()

def bind_fast_scroll(frame):
    def _on_mousewheel(event):
        scroll_speed = 50
        canvas = (
            frame._parent_canvas if hasattr(frame, "_parent_canvas") else frame._canvas
        )
        if event.delta:
            canvas.yview_scroll(int(-1 * (event.delta / 120) * scroll_speed), "units")
        elif event.num == 4:
            canvas.yview_scroll(-scroll_speed, "units")
        elif event.num == 5:
            canvas.yview_scroll(scroll_speed, "units")

    frame._parent_canvas.bind_all("<MouseWheel>", _on_mousewheel)
    frame._parent_canvas.bind_all("<Button-4>", _on_mousewheel)
    frame._parent_canvas.bind_all("<Button-5>", _on_mousewheel)

def delete_all_songs():
    if tkinter.messagebox.askyesno(
        "Delete All Songs",
        "Are you sure you want to delete all exported songs? This cannot be undone.",
    ):
        for f in os.listdir(SONGS_PATH):
            try:
                os.remove(os.path.join(SONGS_PATH, f))
            except Exception:
                pass
        tkinter.messagebox.showinfo("Deleted", "Deleted all exported songs.")

def open_settings_dialog():
    settings_win = tki.CTkToplevel(root)
    settings_win.title("Settings")
    settings_win.geometry("340x380")
    settings_win.resizable(False, False)
    settings_win.lift()  # Bring to front
    settings_win.attributes('-topmost', True)
    settings_win.after(100, lambda: settings_win.attributes('-topmost', False))
    tki.CTkLabel(settings_win, text="Settings", font=(None, 18, "bold")).pack(pady=12)

    # Volume slider
    def set_volume_gui(val):
        rounded = round(float(val), 4)
        config["volume"] = rounded
        try:
            set_volume(rounded)
        except Exception:
            pass

    tki.CTkLabel(settings_win, text="Volume").pack()
    vol = config.get("volume", 1.0)
    slider = tki.CTkSlider(
        settings_win, from_=0, to=1, number_of_steps=100, command=lambda v: (set_volume_gui(v), config.update({'volume': round(float(v), 4)})), width=200
    )
    slider.set(vol)
    slider.pack(pady=2)

    # Select osu folder
    tki.CTkButton(
        settings_win,
        text="Select osu!lazer folder",
        command=lambda: (settings_win.destroy(), select_osu_folder_gui()),
    ).pack(pady=8)

    # Silence cut-off toggle
    def toggle_silence():
        config["cut_silence"] = not config.get("cut_silence", True)
        silence_btn.configure(
            text=f"Cut silence at start: {'On' if config['cut_silence'] else 'Off'}"
        )

    silence_btn = tki.CTkButton(
        settings_win,
        text=f"Cut silence at start: {'On' if config.get('cut_silence', True) else 'Off'}",
        command=toggle_silence,
    )
    silence_btn.pack(pady=8)

    # Discord Rich Presence toggle (placeholder)
    def toggle_rpc():
        config["discord_rpc"] = not config.get("discord_rpc", False)
        rpc_btn.configure(
            text=f"Discord Rich Presence: {'On' if config['discord_rpc'] else 'Off'}"
        )

    rpc_btn = tki.CTkButton(
        settings_win,
        text=f"Discord Rich Presence: {'On' if config.get('discord_rpc', False) else 'Off'}",
        command=toggle_rpc,
    )
    rpc_btn.pack(pady=8)

    # Auto play toggle
    def toggle_autoplay():
        config["autoplay"] = not config.get("autoplay", False)
        autoplay_btn.configure(
            text=f"Auto play: {'On' if config['autoplay'] else 'Off'}"
        )

    autoplay_btn = tki.CTkButton(
        settings_win,
        text=f"Auto play: {'On' if config.get('autoplay', False) else 'Off'}",
        command=toggle_autoplay,
    )
    autoplay_btn.pack(pady=8)

    # Shuffle toggle
    def toggle_shuffle():
        config["shuffle"] = not config.get("shuffle", False)
        shuffle_btn.configure(text=f"Shuffle: {'On' if config['shuffle'] else 'Off'}")

    shuffle_btn = tki.CTkButton(
        settings_win,
        text=f"Shuffle: {'On' if config.get('shuffle', False) else 'Off'}",
        command=toggle_shuffle,
    )
    shuffle_btn.pack(pady=8)

    # Re-export songs
    tki.CTkButton(
        settings_win,
        text="Re-export Songs",
        command=lambda: (settings_win.destroy(), reexport_songs()),
    ).pack(pady=8)
    tki.CTkButton(settings_win, text="Close", command=settings_win.destroy).pack(pady=8)

    # Delete all exported songs
    tki.CTkButton(
        settings_win,
        text="Delete all exported songs",
        fg_color="#b22222",
        hover_color="#ff4444",
        text_color="#fff",
        command=delete_all_songs,
    ).pack(pady=8)

def reexport_songs():
    export_songs_gui()

def cut_silence_at_start(
    audio_data, threshold=0.01, min_silence_sec=0.2, samplerate=44100
):
    min_silence_samples = int(min_silence_sec * samplerate)
    abs_audio = np.abs(audio_data)
    for i in range(0, len(abs_audio) - min_silence_samples):
        if np.max(abs_audio[i : i + min_silence_samples]) > threshold:
            return audio_data[i:]
    return audio_data

