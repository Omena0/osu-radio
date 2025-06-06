from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import mutagen
import chardet
import shutil
import os

def get_path_from_hash(hash, files_dir):
    a,b,c = hash[0], hash[:2], hash

    return os.path.join(files_dir, a, b, c)

song_min_size = 1024**2

replacements = {
    '?': '？',  # Fullwidth Question Mark U+FF1F
    '*': '＊',  # Fullwidth Asterisk U+FF0A
    '<': '＜',  # Fullwidth Less-Than U+FF1C
    '>': '＞',  # Fullwidth Greater-Than U+FF1E
    ':': '：',  # Fullwidth Colon U+FF1A
    '"': '＂',  # Fullwidth Quotation Mark U+FF02
    '\\': '＼', # Fullwidth Reverse Solidus U+FF3C
    '/': '／',  # Fullwidth Solidus U+FF0F
    '|': '｜',  # Fullwidth Vertical Line U+FF5C
}

def replace_illegals(filename:str):
    for old, new in replacements.items():
        filename = filename.replace(old, new)
    return filename

def reverse_replace_illegals(filename:str):
    for old, new in replacements.items():
        filename = filename.replace(new, old)
    return filename

def list_hashes(files_dir):
    hashes = []
    for file in os.listdir(files_dir):
        path = os.path.join(files_dir, file)
        if os.path.isdir(path):
            hashes.extend(list_hashes(path))
        elif len(file) == 64:
            if os.path.getsize(path) > song_min_size:
                hashes.append(file)

    return hashes

def export_songs(files_dir, export_dir, callback=None):
    files_dir = os.path.join(files_dir, 'files')
    hashes = list_hashes(files_dir)

    if not hashes: return []

    os.makedirs(export_dir, exist_ok=True)

    for i, hash in enumerate(hashes):
        try:
            path = get_path_from_hash(hash, files_dir)
            path = os.path.normpath(path)

            audio = EasyID3(path)
            title = audio.get('title', [hash])[0]
            artist = audio.get('artist', [None])[0]

            if artist:
                dest = f'{title}.{artist}.mp3'
            else:
                dest = f'{title}.mp3'

            dest = replace_illegals(dest)

            dest = os.path.join(export_dir, dest)

            shutil.copy(path, dest)

            if callback:
                callback(i, len(hashes))

        except mutagen.id3._util.ID3NoHeaderError:
            ...

        except Exception as e:
            print(f"Error processing {hash}: {e}")

    return os.listdir(export_dir)
