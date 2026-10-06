import json
import os
import subprocess
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUDIO_EXT = {
    "mp3", "wav", "flac", "ogg", "oga", "opus", "m4a", "m4b", "aac",
    "aiff", "aif", "wma", "ape", "wv", "mpc", "amr", "ac3", "dts", "mka",
}

IMAGE_EXT = {
    "jpg", "jpeg", "jpe", "png", "webp", "gif", "bmp", "tif", "tiff",
    "heic", "heif", "avif", "jxl", "raw", "arw", "cr2", "cr3", "nef",
    "dng", "rw2", "orf", "raf", "pef", "srw", "ico",
}

VIDEO_EXT = {
    "mp4", "m4v", "mov", "mkv", "avi", "wmv", "webm", "mpg", "mpeg",
    "m2ts", "mts", "ts", "3gp", "3g2", "flv", "divx", "ogv", "vob",
}

ALL_EXT = AUDIO_EXT | IMAGE_EXT | VIDEO_EXT

FIELDS = {
    "audio": [
        {"label": "Título", "tag": "Title", "list": False},
        {"label": "Artista", "tag": "Artist", "list": False},
        {"label": "Álbum", "tag": "Album", "list": False},
        {"label": "Artista del álbum", "tag": "AlbumArtist", "list": False},
        {"label": "Número de pista", "tag": "Track", "list": False},
        {"label": "Número de disco", "tag": "DiscNumber", "list": False},
        {"label": "Año", "tag": "Year", "list": False},
        {"label": "Género", "tag": "Genre", "list": False},
        {"label": "Compositor", "tag": "Composer", "list": False},
        {"label": "Director de orquesta", "tag": "Conductor", "list": False},
        {"label": "Editor/Discográfica", "tag": "Publisher", "list": False},
        {"label": "Codificado por", "tag": "EncodedBy", "list": False},
        {"label": "Comentario", "tag": "Comment", "list": False},
        {"label": "Copyright", "tag": "Copyright", "list": False},
        {"label": "Letras", "tag": "Lyrics", "list": False},
        {"label": "BPM", "tag": "BPM", "list": False},
    ],
    "image": [
        {"label": "Título", "tag": "Title", "list": False},
        {"label": "Descripción", "tag": "Description", "list": False},
        {"label": "Autor", "tag": "Artist", "list": False},
        {"label": "Copyright", "tag": "Copyright", "list": False},
        {"label": "Palabras clave (separar por comas)", "tag": "Keywords", "list": True},
        {"label": "Calificación (0-5)", "tag": "Rating", "list": False},
        {"label": "Fabricante de cámara", "tag": "Make", "list": False},
        {"label": "Modelo de cámara", "tag": "Model", "list": False},
        {"label": "Modelo de lente", "tag": "LensModel", "list": False},
        {"label": "ISO", "tag": "ISO", "list": False},
        {"label": "Apertura (f/)", "tag": "FNumber", "list": False},
        {"label": "Exposición (s)", "tag": "ExposureTime", "list": False},
        {"label": "Distancia focal (mm)", "tag": "FocalLength", "list": False},
        {"label": "Fecha de captura (AAAA-MM-DD HH:MM:SS)", "tag": "DateTimeOriginal", "list": False},
        {"label": "Latitud GPS", "tag": "GPSLatitude", "list": False},
        {"label": "Longitud GPS", "tag": "GPSLongitude", "list": False},
        {"label": "Altitud GPS", "tag": "GPSAltitude", "list": False},
        {"label": "Ciudad", "tag": "City", "list": False},
        {"label": "Estado/Provincia", "tag": "State", "list": False},
        {"label": "País", "tag": "Country", "list": False},
        {"label": "Software", "tag": "Software", "list": False},
    ],
    "video": [
        {"label": "Título", "tag": "Title", "list": False},
        {"label": "Descripción", "tag": "Description", "list": False},
        {"label": "Director", "tag": "Director", "list": False},
        {"label": "Productor", "tag": "Producer", "list": False},
        {"label": "Guionista", "tag": "Writer", "list": False},
        {"label": "Actores (separar por comas)", "tag": "Actors", "list": True},
        {"label": "Programa/Show", "tag": "Show", "list": False},
        {"label": "Temporada", "tag": "Season", "list": False},
        {"label": "Número de episodio", "tag": "EpisodeNumber", "list": False},
        {"label": "Género", "tag": "Genre", "list": False},
        {"label": "Año", "tag": "Year", "list": False},
        {"label": "Copyright", "tag": "Copyright", "list": False},
        {"label": "Comentario", "tag": "Comment", "list": False},
    ],
}

TYPE_LABELS = {"audio": "Audio", "image": "Imagen", "video": "Video", "other": "Otro"}


def resource_path(rel):
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", ""), rel)
    return os.path.join(APP_DIR, rel)


def _find_exiftool():
    env = os.environ.get("METADATASTUDIO_EXIFTOOL")
    if env and os.path.isfile(env):
        return env
    cand = resource_path(os.path.join("exiftool", "exiftool.exe"))
    if os.path.isfile(cand):
        return cand
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = os.path.join(d, "exiftool.exe")
        if os.path.isfile(p):
            return p
    return None


def detect_media_type(path):
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if ext in AUDIO_EXT:
        return "audio"
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    return "other"


def human_size(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def format_duration(value):
    try:
        secs = float(value)
    except (TypeError, ValueError):
        return ""
    if secs < 0:
        return ""
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class MetadataEngine:
    def __init__(self):
        self.exe = _find_exiftool()

    @property
    def available(self):
        return bool(self.exe)

    def version(self):
        if not self.available:
            return ""
        try:
            r = subprocess.run(
                [self.exe, "-ver"],
                capture_output=True, text=True, timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return r.stdout.strip()
        except Exception:
            return ""

    def _run(self, args, timeout=120):
        proc = subprocess.run(
            [self.exe] + args,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return proc

    def read(self, path):
        if not self.available:
            return {}
        try:
            proc = self._run(["-j", "-G1", "-s", "-a", "--", path])
            out = proc.stdout.strip()
            if not out:
                return {}
            data = json.loads(out)
            return data[0] if data else {}
        except Exception:
            return {}

    def read_batch(self, paths):
        if not self.available or not paths:
            return [{} for _ in paths]
        try:
            proc = self._run(["-j", "-G1", "-s", "-a", "--"] + list(paths), timeout=300)
            out = proc.stdout.strip()
            if not out:
                return [{} for _ in paths]
            data = json.loads(out)
            return data if isinstance(data, list) else [data]
        except Exception:
            return [{} for _ in paths]

    def normalize(self, raw):
        tagmap = {}
        for k, v in raw.items():
            t = k.rsplit(":", 1)[-1].lower()
            tagmap.setdefault(t, v)

        def val(tag):
            v = tagmap.get(tag.lower())
            if v in (None, "") and tag.lower() in ("comment", "lyrics", "composer"):
                for k, kv in tagmap.items():
                    if k.startswith(tag.lower() + "-"):
                        v = kv
                        break
            if v is None:
                return ""
            if isinstance(v, list):
                return ", ".join(str(x) for x in v)
            return str(v).strip()

        norm = {
            "Title": val("Title"),
            "Artist": val("Artist"),
            "Album": val("Album"),
            "AlbumArtist": val("AlbumArtist"),
            "Track": val("Track").split("/")[0].strip() or val("TrackNumber").split("/")[0].strip(),
            "DiscNumber": val("DiscNumber").split("/")[0].strip() or val("Disc").split("/")[0].strip(),
            "Year": val("Year") or val("Date")[:4] or val("DateTimeOriginal")[:4] or val("CreateDate")[:4],
            "Genre": val("Genre"),
            "Composer": val("Composer"),
            "Conductor": val("Conductor"),
            "Publisher": val("Publisher"),
            "EncodedBy": val("EncodedBy"),
            "Comment": val("Comment"),
            "Copyright": val("Copyright"),
            "Lyrics": val("Lyrics"),
            "BPM": val("BPM") or val("Bpm"),
            "Description": val("Description"),
            "Keywords": val("Keywords"),
            "Rating": val("Rating"),
            "Make": val("Make"),
            "Model": val("Model"),
            "LensModel": val("LensModel"),
            "ISO": val("ISO"),
            "FNumber": val("FNumber"),
            "ExposureTime": val("ExposureTime"),
            "FocalLength": val("FocalLength"),
            "DateTimeOriginal": val("DateTimeOriginal"),
            "GPSLatitude": val("GPSLatitude"),
            "GPSLongitude": val("GPSLongitude"),
            "GPSAltitude": val("GPSAltitude"),
            "City": val("City"),
            "State": val("State"),
            "Country": val("Country"),
            "Software": val("Software"),
            "Director": val("Director"),
            "Producer": val("Producer"),
            "Writer": val("Writer"),
            "Actors": val("Actors"),
            "Show": val("Show"),
            "Season": val("Season"),
            "EpisodeNumber": val("EpisodeNumber"),
            "FileName": val("FileName"),
            "Directory": val("Directory"),
            "FileType": val("FileType"),
            "MIMEType": val("MIMEType"),
            "FileSize": val("FileSize"),
            "ImageWidth": val("ImageWidth"),
            "ImageHeight": val("ImageHeight"),
            "Duration": val("Duration"),
        }
        return norm

    def write(self, path, assignments):
        ext = os.path.splitext(path)[1].lstrip(".").lower()
        if ext in MUTAGEN_AUDIO_EXT:
            return write_audio_tags(path, assignments)
        if not self.available:
            return False, "ExifTool no disponible"
        args = ["-overwrite_original", "-m", "-P"]
        for tag, value, is_list in assignments:
            if is_list:
                parts = [
                    p.strip() for p in str(value).replace(";", ",").split(",")
                    if p.strip()
                ]
                if not parts:
                    continue
                args.append(f"-{tag}={parts[0]}")
                for p in parts[1:]:
                    args.append(f"-{tag}+={p}")
            else:
                args.append(f"-{tag}={value}")
        args += ["--", path]
        try:
            proc = self._run(args)
            if proc.returncode == 0:
                return True, "OK"
            msg = (proc.stderr or "Error desconocido").strip().splitlines()
            return False, msg[-1] if msg else "Error de ExifTool"
        except subprocess.TimeoutExpired:
            return False, "Tiempo de espera agotado"
        except Exception as e:
            return False, str(e)


MUTAGEN_AUDIO_EXT = {
    "mp3", "wav", "aiff", "aif", "flac", "ogg", "oga", "opus",
    "wma", "ape", "aac", "mpc", "wv",
}


def write_audio_tags(path, assignments):
    try:
        import mutagen
    except ImportError:
        return False, "Biblioteca mutagen no disponible"

    values = {}
    for tag, value, is_list in assignments:
        if is_list:
            values[tag] = ", ".join(
                p.strip() for p in str(value).replace(";", ",").split(",") if p.strip()
            )
        else:
            values[tag] = str(value).strip()

    ext = os.path.splitext(path)[1].lstrip(".").lower()
    try:
        if ext in ("mp3", "wav", "aiff", "aif", "aac"):
            _write_id3(path, values, mutagen)
        elif ext in ("flac", "ogg", "oga", "opus"):
            _write_vorbis(path, values, mutagen)
        elif ext == "wma":
            _write_asf(path, values, mutagen)
        elif ext in ("ape", "mpc", "wv"):
            _write_apev2(path, values, mutagen)
        else:
            return False, f"Escritura no soportada para .{ext}"
        return True, "OK"
    except Exception as e:
        return False, f"Error de escritura: {e}"


def _split_num(value):
    parts = str(value).split("/")
    num = parts[0].strip()
    try:
        num = str(int(num))
    except ValueError:
        num = ""
    if not num:
        return None
    total = None
    if len(parts) > 1:
        try:
            total = str(int(parts[1].strip()))
        except ValueError:
            total = None
    return (num, total)


def _write_id3(path, values, mutagen):
    from mutagen.id3 import (
        ID3, TIT2, TPE1, TALB, TPE2, TRCK, TPOS, TDRC, TCON,
        TCOM, TPE3, TPUB, TENC, COMM, TCOP, USLT, TBPM,
    )
    from mutagen.wave import WAVE
    from mutagen.aiff import AIFF
    from mutagen.aac import AAC

    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if ext == "wav":
        audio = WAVE(path)
        tags = audio.tags if audio.tags is not None else ID3()
    elif ext in ("aiff", "aif"):
        audio = AIFF(path)
        tags = audio.tags if audio.tags is not None else ID3()
    elif ext == "aac":
        audio = AAC(path)
        tags = audio.tags if audio.tags is not None else ID3()
    else:
        audio = mutagen.File(path)
        tags = audio.tags if audio.tags is not None else ID3()

    def text_frame(cls, val):
        return cls(encoding=3, text=[val])

    frames = {
        "Title": (TIT2, None),
        "Artist": (TPE1, None),
        "Album": (TALB, None),
        "AlbumArtist": (TPE2, None),
        "Track": (TRCK, "track"),
        "DiscNumber": (TPOS, "track"),
        "Year": (TDRC, "date"),
        "Genre": (TCON, None),
        "Composer": (TCOM, None),
        "Conductor": (TPE3, None),
        "Publisher": (TPUB, None),
        "EncodedBy": (TENC, None),
        "Copyright": (TCOP, None),
        "BPM": (TBPM, "bpm"),
    }
    for key, (cls, kind) in frames.items():
        if key not in values or not values[key]:
            continue
        if kind == "track":
            pair = _split_num(values[key])
            if pair is None:
                continue
            num, total = pair
            text = f"{num}/{total}" if total else num
        elif kind == "date":
            text = values[key]
        elif kind == "bpm":
            try:
                text = str(int(round(float(values[key]))))
            except ValueError:
                text = values[key]
            tags.delall("TBPM")
            tags.add(TBPM(encoding=0, text=[text]))
            continue
        else:
            text = values[key]
        tags.setall(cls.__name__, [text_frame(cls, text)])
    if values.get("Comment"):
        tags.delall("COMM")
        tags.add(COMM(encoding=3, lang="spa", desc="", text=[values["Comment"]]))
    if values.get("Lyrics"):
        tags.delall("USLT")
        tags.add(USLT(encoding=3, lang="spa", desc="", text=values["Lyrics"]))
    if ext == "wav":
        if audio.tags is None:
            audio.add_tags(tags)
    elif ext in ("aiff", "aif"):
        if audio.tags is None:
            audio.add_tags(tags)
    else:
        audio.tags = tags
    audio.save()


def _write_vorbis(path, values, mutagen):
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
    from mutagen.oggopus import OggOpus

    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if ext == "flac":
        audio = FLAC(path)
    elif ext == "opus":
        audio = OggOpus(path)
    else:
        audio = OggVorbis(path)

    vmap = {
        "Title": "title", "Artist": "artist", "Album": "album",
        "AlbumArtist": "albumartist", "Track": "tracknumber",
        "DiscNumber": "discnumber", "Year": "date", "Genre": "genre",
        "Composer": "composer", "Conductor": "conductor",
        "Publisher": "organization", "EncodedBy": "encodedby",
        "Comment": "comment", "Copyright": "copyright",
        "Lyrics": "lyrics", "BPM": "bpm",
    }
    for key, vkey in vmap.items():
        if key in values and values[key]:
            audio[vkey] = values[key]
    audio.save()


def _write_asf(path, values, mutagen):
    from mutagen.asf import ASF

    audio = ASF(path)
    amap = {
        "Title": "Title", "Artist": "Author", "Album": "WM/AlbumTitle",
        "AlbumArtist": "WM/AlbumArtist", "Track": "WM/TrackNumber",
        "Year": "WM/Year", "Genre": "WM/Genre", "Composer": "WM/Composer",
        "Conductor": "WM/Conductor", "Publisher": "WM/Publisher",
        "EncodedBy": "WM/EncodedBy", "Comment": "Description",
        "Copyright": "Copyright", "Lyrics": "WM/Lyrics",
        "BPM": "WM/BeatsPerMinute",
    }
    for key, akey in amap.items():
        if key in values and values[key]:
            audio[akey] = values[key]
    audio.save()


def _write_apev2(path, values, mutagen):
    from mutagen.apev2 import APEv2

    amap = {
        "Title": "Title", "Artist": "Artist", "Album": "Album",
        "AlbumArtist": "Album Artist", "Track": "Track",
        "DiscNumber": "Disc", "Year": "Year", "Genre": "Genre",
        "Composer": "Composer", "Conductor": "Conductor",
        "Publisher": "Publisher", "EncodedBy": "Encoded By",
        "Comment": "Comment", "Copyright": "Copyright",
        "Lyrics": "Lyrics", "BPM": "BPM",
    }
    try:
        tags = APEv2(path)
    except Exception:
        tags = APEv2()
    for key, akey in amap.items():
        if key in values and values[key]:
            tags[akey] = values[key]
    tags.save(path)
