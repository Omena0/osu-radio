import tkinter.messagebox
from export import export_songs, reverse_replace_illegals
from cover_util import get_mp3_cover_and_duration
from PIL import Image
import customtkinter as tki
import sounddevice as sd
import soundfile as sf
import threading
import tkinter
import json
import os

files_path = os.path.join(os.environ['APPDATA'], 'osu!radio (lazer)')
config_path = os.path.join(files_path, 'config.json')
songs_path = os.path.join(files_path, 'songs')

class FastScrollableFrame(tki.CTkScrollableFrame):
    def _on_mousewheel(self, event):
        scroll_speed = 50
        # Increase scroll speed (platform independent)
        if event.delta:
            self._parent_canvas.yview_scroll(int(-1*(event.delta/120)*scroll_speed), "units")
        elif event.num == 4:
            self._parent_canvas.yview_scroll(-scroll_speed, "units")
        elif event.num == 5:
            self._parent_canvas.yview_scroll(scroll_speed, "units")

    def bind_scroll_speed(self):
        self._parent_canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        self._parent_canvas.bind_all('<Button-4>', self._on_mousewheel)
        self._parent_canvas.bind_all('<Button-5>', self._on_mousewheel)

def create_gui():
    global root
    root = tki.CTk()
    root.geometry("500x350")
    root.title("Osu!Radio (lazer)")
    root.resizable(False, False)

    if not config['osu_folder']:
        select_osu_folder_gui()
    elif not os.path.exists(songs_path):
        export_songs_gui()
    else:
        main_gui()

def main_gui():
    for widget in root.winfo_children():
        widget.destroy()

    # --- Song playback state ---
    global current_song, playback_thread, playback_event
    global paused, stream, queue, queue_index, song_buttons
    global queue_view, now_playing_view, queue_listbox
    global song_title_label, song_artist_label, song_files
    global song_index, switch_btn

    current_song = None
    playback_thread = None
    playback_event = threading.Event()
    paused = False
    stream = None
    queue = []
    queue_index = 0
    song_buttons = []

    # Place content_frame and player_controls directly in root
    content_frame = tki.CTkFrame(root, width=500, height=300, corner_radius=0)
    content_frame.pack(fill='both', expand=True)

    song_list = FastScrollableFrame(
        content_frame,
        width=180,
        height=350,
        corner_radius=0
    )
    song_list.pack(fill='y', side='left', expand=False)
    song_list.bind_scroll_speed()

    # --- Song info/queue view switching ---
    right_frame = tki.CTkFrame(content_frame, width=300, height=100, corner_radius=15, fg_color=("#23263a", "#23263a"))
    right_frame.pack(fill='both', expand=True, side='right', padx=10, pady=10)

    now_playing_view = tki.CTkFrame(right_frame, fg_color=right_frame.cget('fg_color'))
    now_playing_view.pack(fill='both', expand=True)
    queue_view = tki.CTkFrame(right_frame, fg_color="transparent")
    # queue_view.pack_forget() by default

    # Song title, artist, duration, and cover display
    global song_cover_label, song_duration_label
    song_cover_label = tki.CTkLabel(now_playing_view, text="", image=None)
    song_cover_label.pack(padx=16, pady=(18, 2))
    song_title_label = tki.CTkLabel(
        now_playing_view,
        text="No song playing",
        font=(None, 18, 'bold'),
        text_color="#f0f0f0",
        anchor='w'
    )
    song_title_label.pack(fill='x', padx=16, pady=(0, 2))
    song_artist_label = tki.CTkLabel(
        now_playing_view,
        text="",
        font=(None, 14),
        text_color="#b0b0b0",
        anchor='w'
    )
    song_artist_label.pack(fill='x', padx=16, pady=(0, 2))
    song_duration_label = tki.CTkLabel(
        now_playing_view,
        text="",
        font=(None, 12),
        text_color="#b0b0b0",
        anchor='w'
    )
    song_duration_label.pack(fill='x', padx=16, pady=(0, 10))

    # --- Queue view ---
    queue_listbox = tki.CTkTextbox(queue_view, font=(None, 13), width=260, height=120, fg_color="#23263a", text_color="#f0f0f0", border_width=0)
    queue_listbox.pack(fill='both', expand=True, padx=16, pady=16)
    queue_listbox.configure(state='disabled')

    # --- Player controls ---
    player_controls = tki.CTkFrame(
        right_frame,
        width=300,
        height=60,
        corner_radius=15,
        fg_color=("#181a24", "#181a24"),
        border_width=2,
        border_color=("#44475a", "#44475a")
    )
    player_controls.pack(fill='x', side='bottom', pady=10, padx=16)

    controls_inner = tki.CTkFrame(player_controls, fg_color="transparent")
    controls_inner.pack(expand=True, side='left')

    btn_style = dict(
        width=32,
        height=32,
        font=(None, 14, 'bold'),
        fg_color=("#23263a", "#23263a"),
        hover_color=("#3a3d4a", "#3a3d4a"),
        corner_radius=8,
        border_width=2,
        border_color=("#44475a", "#44475a"),
        text_color=("#f0f0f0", "#f0f0f0")
    )
    prev_btn = tki.CTkButton(controls_inner, text='⏮', command=lambda: play_prev_song(), **btn_style)
    play_btn = tki.CTkButton(controls_inner, text='▶', command=lambda: resume_song(), **btn_style)
    pause_btn = tki.CTkButton(controls_inner, text='⏸', command=lambda: pause_song(), **btn_style)
    next_btn = tki.CTkButton(controls_inner, text='⏭', command=lambda: play_next_song(), **btn_style)
    prev_btn.pack(side='left', padx=(8,4), pady=4)
    play_btn.pack(side='left', padx=4, pady=4)
    pause_btn.pack(side='left', padx=4, pady=4)
    next_btn.pack(side='left', padx=4, pady=4)

    # Settings and view switch button
    switch_btn = tki.CTkButton(player_controls, text='Q', command=lambda: switch_view(), **btn_style)
    switch_btn.pack(side='right', padx=4, pady=8)
    settings_btn = tki.CTkButton(player_controls, text='S', command=lambda: print('a'), **btn_style)
    settings_btn.pack(side='right', padx=4, pady=8)

    song_files = [f for f in os.listdir(songs_path) if f.lower().endswith('.mp3')]
    song_index = 0

    song_buttons.clear()
    for idx, song in enumerate(song_files):
        display_name = get_display_name(song)
        btn = tki.CTkButton(
            song_list,
            text=display_name,
            command=lambda i=idx: play_song_by_index(i),
            width=170,
            height=36,
            font=(None, 13, 'bold'),
            fg_color=("#23263a", "#23263a"),
            text_color=("#f0f0f0", "#f0f0f0"),
            corner_radius=10,
            anchor='w',
            hover_color=("#3a3d4a", "#3a3d4a"),
            border_width=2,
            border_color=("#44475a", "#44475a")
        )
        btn.pack(pady=5, padx=10, anchor='w', fill='x')
        btn.bind('<Button-3>', lambda e, i=idx: on_song_right_click(e, i))
        song_buttons.append(btn)

def switch_view():
    if now_playing_view.winfo_ismapped():
        now_playing_view.pack_forget()
        queue_view.pack(fill='both', expand=True)
        switch_btn.configure(text='Now Playing')
        update_queue_view()
    else:
        queue_view.pack_forget()
        now_playing_view.pack(fill='both', expand=True)
        switch_btn.configure(text='Queue')

def update_queue_view():
    queue_listbox.configure(state='normal')
    queue_listbox.delete('1.0', 'end')
    for i, song in enumerate(queue):
        song_name = get_display_name(song)
        queue_listbox.insert('end', f'{i+1}. {song_name}\n')
    queue_listbox.configure(state='disabled')

def get_display_name(song):
        # Use config custom_song_names if present
        base = reverse_replace_illegals(song).removesuffix('.mp3')
        if base in config.get('custom_song_names', {}):
            return config['custom_song_names'][base]
        if is_hash(base):
            base = base[:8]
        if '.' in base:
            base, artist = base.rsplit('.',1)
        max_len = 18
        if len(base) > max_len:
            base = base[:max_len-3] + '...'
        return base

def on_song_right_click(event, idx):
    print(idx)
    menu = tkinter.Menu(root, tearoff=0)

    menu.add_command(label="Play", command=lambda: [menu.destroy(), play_song_by_index(idx)])
    menu.add_command(label="Add to queue", command=lambda: [menu.destroy(), add_to_queue(idx)])
    menu.add_command(label="Rename", command=lambda: [menu.destroy(), rename_song(idx)])

    menu.post(event.x_root, event.y_root)

def add_to_queue(idx):
    song = song_files[idx]
    if song not in queue:
        queue.append(song)
        update_queue_view()

def rename_song(idx):
    song = song_files[idx]
    base = reverse_replace_illegals(song).removesuffix('.mp3')

    new_name = tkinter.simpledialog.askstring('Rename Song', f'Enter new name for "{get_display_name(song)}":', parent=root)

    if new_name:
        config['custom_song_names'][base] = new_name
        save_config()
        for b in song_buttons:
            b.configure(text=get_display_name(song_files[song_buttons.index(b)]))
        update_queue_view()

def highlight_now_playing(idx):
    for i, b in enumerate(song_buttons):
        if i == idx:
            b.configure(border_color="#00bfff", border_width=3)
        else:
            b.configure(border_color="#44475a", border_width=2)

def play_song_by_index(idx):
    global song_index
    song_index = idx
    play_song(os.path.join(songs_path, song_files[song_index]))
    highlight_now_playing(song_index)

def play_next_song():
    global song_index
    if song_files:
        song_index = (song_index + 1) % len(song_files)
        play_song_by_index(song_index)

def play_prev_song():
    global song_index
    if song_files:
        song_index = (song_index - 1) % len(song_files)
        play_song_by_index(song_index)

def play_song(path):
    global current_song, playback_thread, playback_event, paused, stream, song_buttons, song_files, song_index
    stop_song()
    current_song = path
    playback_event.clear()
    paused = False

    # Update song info UI
    try:
        filename = os.path.basename(path)
        base = reverse_replace_illegals(filename).removesuffix('.mp3')
        if base in config.get('custom_song_names', {}):
            song_name = config['custom_song_names'][base]
        else:
            song_name = base[:8] if is_hash(base) else base.split('.',1)[0]
        artist = base.rsplit('.',1)[1] if '.' in base else "Unknown Artist"
        # Get cover and duration
        cover, duration = get_mp3_cover_and_duration(path)
        if cover:
            cover.thumbnail((96, 96))
            try:
                import customtkinter
                ctkimg = customtkinter.CTkImage(light_image=cover, dark_image=cover, size=cover.size)
                song_cover_label.configure(image=ctkimg, text="")
                song_cover_label.image = ctkimg
            except Exception:
                song_cover_label.configure(image=None, text="")
        else:
            song_cover_label.configure(image=None, text="")
        mins = int(duration // 60) if duration else 0
        secs = int(duration % 60) if duration else 0
        song_duration_label.configure(text=f"{mins}:{secs:02d}" if duration else "")
        song_title_label.configure(text=song_name)
        song_artist_label.configure(text=artist)
        # Highlight now playing
        if song_index < len(song_buttons):
            highlight_now_playing(song_index)
    except Exception:
        song_title_label.configure(text="Unknown")
        song_artist_label.configure(text="")
        song_duration_label.configure(text="")
        song_cover_label.configure(image=None, text="")

    def playback():
        try:
            with sf.SoundFile(current_song) as f:
                with sd.OutputStream(samplerate=f.samplerate, channels=f.channels, dtype='float32') as s:
                    global stream
                    stream = s
                    while True:
                        if playback_event.is_set():
                            break
                        if paused:
                            sd.sleep(100)
                            continue
                        data = f.read(1024, dtype='float32')
                        if len(data) == 0:
                            break
                        s.write(data)
        except Exception as e:
            print(f"Playback error: {e}")
    playback_thread = threading.Thread(target=playback, daemon=True)
    playback_thread.start()

def stop_song():
    global playback_event, playback_thread, stream
    playback_event.set()
    if stream is not None:
        try:
            stream.abort()
        except Exception:
            pass
        stream = None
    if playback_thread is not None:
        playback_thread.join(timeout=0.2)
        playback_thread = None

def pause_song():
    global paused
    paused = True

def resume_song():
    global paused
    paused = False


def select_osu_folder_gui():
    for widget in root.winfo_children():
        widget.destroy()
    if config.get('osu_folder'):
        export_songs_gui()
        return

    set_title('Select osu!lazer folder')
    tki.CTkLabel(
        root,
        text="Welcome to Osu!Radio (lazer)",
        font=(None, 30, 'bold')
    ).pack(pady=20)

    tki.CTkLabel(
        root,
        text="To begin exporting songs, please select your osu!lazer folder.",
        font=(None, 15)
    ).pack(pady=20)

    tki.CTkButton(
        root,
        text="Select osu!lazer folder",
        command=lambda: select_folder(),
        width=200,
        height=50,
        font=(None, 15)
    ).pack(pady=20)

def export_songs_gui():
    set_title('Export Songs')
    for widget in root.winfo_children():
        widget.destroy()

    root.update_idletasks()

    tki.CTkLabel(
        root,
        text="Export Songs",
        font=(None, 30, 'bold')
    ).pack(pady=20)

    tki.CTkLabel(
        root,
        text="Click the button below to export songs from your osu!lazer folder.",
        font=(None, 15)
    ).pack(pady=20)

    tki.CTkButton(
        root,
        text="Export Songs",
        command=lambda: (export_songs(config['osu_folder'], songs_path, callback=lambda i, total: bar.set((i+1) / total)), main_gui()),
        width=200,
        height=50,
        font=(None, 15)
    ).pack(pady=20)

    bar = tki.CTkProgressBar(
        root,
        mode='determinate',
        width=300,
        height=8,
        corner_radius=3
    )
    bar.set(-1)
    bar.pack(pady=5)

def load_config():
    global config
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        config = {
            "osu_folder": None,
            "custom_song_names": {}
        }

        with open(config_path, 'w') as f:
            json.dump(config, f)
        return config

    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

def set_title(title):
    root.title(f"Osu!Radio (lazer) - {title}")

def select_folder():
    folder = tki.filedialog.askdirectory(mustexist=True, title='Select osu!lazer folder', initialdir=os.path.expanduser("~"))

    if not folder:
        return

    # Check if the user picked the files/ directory, not the root osu!lazer folder
    if folder and os.path.basename(folder) == 'files':
        folder = os.path.dirname(folder)

    config['osu_folder'] = folder

    export_songs_gui()

def save_config():
    global config
    with open(config_path, 'w') as f:
        json.dump(config, f)

def is_hash(text:str):
    return len(text) == 64 and all(c in '0123456789abcdef' for c in text)

load_config()
create_gui()

try:
    root.mainloop()
finally:
    save_config()
