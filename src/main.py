# Entry point for osu!radio (lazer)
from config import load_config, save_config
from discordrp import Presence, PresenceError
import gui as gui
import time


CLIENT_ID = '1379860077980160091'

def main():
    config = load_config()
    if config['discord_rpc']:
        print('a')
        try:
            with Presence(CLIENT_ID) as rpc:
                print('b')
                start_time = time.time()-2
                rpc.start_time = start_time
                rpc.current = {
                    "type": 2,
                    "details": "Listening to osu!radio",
                    "state": 'In the menus',
                    "start": start_time,
                    "end": None,
                    "buttons": [
                        {
                            "label": "Get osu!radio (lazer)",
                            "url": "https://github.com/Omena0/osu!radio"
                        }
                    ]
                }
                rpc.set(rpc.current)

                try:
                    gui.run_app(config, rpc)
                finally:
                    save_config(config)
        except Exception as e:
            print(f"Discord RPC unavailable: {e}")
            rpc = None
            try:
                gui.run_app(config, rpc)
            finally:
                save_config(config)
    else:
        rpc = None
        try:
            gui.run_app(config, rpc)
        finally:
            save_config(config)


if __name__ == "__main__":
    main()
