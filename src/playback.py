def seek_song(position_seconds):
    """Seek to a position (in seconds) in the current song and resume playback."""
    if not state.current_song:
        return
    stop_song()
    def _seek_playback(state, on_end=None):
        try:
            with sf.SoundFile(state.current_song) as file, \
                sd.OutputStream(samplerate=file.samplerate, channels=file.channels, dtype='float32') as stream:
                state.stream = stream
                # Seek to the correct frame
                frame = int(position_seconds * file.samplerate)
                file.seek(frame)
                _playback_loop(state, file, stream)
            if on_end and not state.playback_event.is_set():
                on_end()
        except Exception as e:
            print(f"Seek playback error: {e}")
        finally:
            state.stream = None
    state.playback_event.clear()
    state.paused = False
    state.playback_thread = threading.Thread(target=_seek_playback, args=(state, None), daemon=True)
    state.playback_thread.start()

import sounddevice as sd
import soundfile as sf
import threading

class PlaybackState:
    def __init__(self):
        self.current_song = None
        self.playback_thread = None
        self.playback_event = threading.Event()
        self.paused = False
        self.stream = None
        self.volume = 1.0

state = PlaybackState()

def _playback_loop(state, f, s):
    while True:
        if state.playback_event.is_set():
            break

        if state.paused:
            sd.sleep(100)
            continue

        data = f.read(1024, dtype='float32')
        if len(data) == 0:
            break

        # Apply volume
        if state.volume != 1.0:
            data = data * state.volume

        s.write(data)

def set_volume(vol):
    """Set playback volume (0.0 to 1.0)."""
    state.volume = float(vol)

def _playback(state, on_end=None):
    try:
        with sf.SoundFile(state.current_song) as file, \
            sd.OutputStream(samplerate=file.samplerate, channels=file.channels, dtype='float32') as stream:
            state.stream = stream
            _playback_loop(state, file, stream)

        # Only call on_end if playback finished naturally (not stopped)
        print(f"[DEBUG] _playback: on_end={on_end}, playback_event={state.playback_event.is_set()}")
        if on_end and not state.playback_event.is_set():
            print("[DEBUG] on_end called after song finished.")
            on_end()

    except Exception as e:
        print(f"Playback error: {e}")

    finally:
        state.stream = None

def play_song(path, on_end=None):
    stop_song()

    state.current_song = path
    state.playback_event.clear()
    state.paused = False
    state.playback_thread = threading.Thread(target=_playback, args=(state, on_end), daemon=True)
    state.playback_thread.start()

def stop_song():
    import traceback
    traceback.print_stack()
    state.playback_event.set()
    if state.stream is not None:
        try:
            state.stream.abort()
        except Exception:
            pass
        state.stream = None
    if state.playback_thread is not None:
        state.playback_thread.join(timeout=0.2)
        state.playback_thread = None

def pause_song():
    state.paused = True

def resume_song():
    state.paused = False
