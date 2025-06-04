import io
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from PIL import Image

def get_mp3_cover_and_duration(path):
    """
    Returns (cover_image, duration_seconds)
    cover_image is a PIL Image or None
    duration_seconds is a float
    """
    audio = MP3(path)
    duration = audio.info.length
    cover = None
    try:
        tags = ID3(path)
        for tag in tags.values():
            if isinstance(tag, APIC):
                cover = Image.open(io.BytesIO(tag.data))
                break
    except Exception:
        pass
    return cover, duration
