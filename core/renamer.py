import re

PLACEHOLDERS = [
    "{Titulo}", "{Artista}", "{Album}", "{Pista}", "{Disco}",
    "{Año}", "{Genero}", "{Fecha}", "{Hora}", "{Secuencia}",
    "{Ext}", "{Nombre}",
]

PRESETS = [
    "{Titulo} - {Artista}",
    "{Pista} - {Titulo}",
    "{Artista} - {Album} - {Pista} {Titulo}",
    "{Fecha}_{Secuencia}",
    "{Año} - {Titulo}",
    "{Nombre} - {Año}",
    "{Titulo} [{Genero}]",
]

INVALID = re.compile(r'[\\/:*?"<>|\r\n]+')


def _clean(text):
    return INVALID.sub("", str(text or "")).strip(" .")


def build_name(template, meta, counter, ext, original_stem):
    fecha, hora = "", ""
    dt = meta.get("DateTimeOriginal") or meta.get("CreateDate") or ""
    if dt:
        m = re.match(
            r"(\d{4})[-:](\d{2})[-:](\d{2})(?:[ T](\d{2})[:.]?(\d{2})[:.]?(\d{2}))?",
            str(dt),
        )
        if m:
            fecha = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            if m.group(4):
                hora = f"{m.group(4)}{m.group(5)}{m.group(6)}"
    values = {
        "{Titulo}": _clean(meta.get("Title")),
        "{Artista}": _clean(meta.get("Artist")),
        "{Album}": _clean(meta.get("Album")),
        "{Pista}": _clean(meta.get("Track")),
        "{Disco}": _clean(meta.get("DiscNumber")),
        "{Año}": _clean(meta.get("Year")),
        "{Genero}": _clean(meta.get("Genre")),
        "{Fecha}": fecha,
        "{Hora}": hora,
        "{Secuencia}": f"{counter:03d}",
        "{Ext}": ext,
        "{Nombre}": _clean(original_stem),
    }
    out = template
    for ph, val in values.items():
        out = out.replace(ph, val)
    out = _clean(out)
    if not out:
        out = original_stem
    return f"{out}.{ext}"
