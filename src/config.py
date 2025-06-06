import os
import json

FILES_PATH = os.path.join(os.environ.get('APPDATA', ''), 'osu!radio (lazer)')
CONFIG_PATH = os.path.join(FILES_PATH, 'config.json')
SONGS_PATH = os.path.join(FILES_PATH, 'songs')

DEFAULT_CONFIG = {
    "osu_folder": None,
    "custom_song_names": {}
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(DEFAULT_CONFIG, f)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f)
