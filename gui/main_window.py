import os
import queue
import threading
from datetime import datetime

import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except Exception:
    HAS_DND = False

from PIL import Image, ImageTk

from core.metadata import (
    MetadataEngine,
    detect_media_type,
    FIELDS,
    TYPE_LABELS,
    ALL_EXT,
    human_size,
    format_duration,
)
from core.renamer import PRESETS, PLACEHOLDERS, build_name
from core.batch import BatchJob
from gui.theme import COLORS, FONT_UI, FONT_SMALL, apply_tree_style

CATEGORY_VALUES = ["Audio", "Imagen", "Video", "Todos"]

TYPE_ICON_COLORS = {
    "audio": "#7c5cff",
    "image": "#00b894",
    "video": "#e17055",
    "other": "#636e72",
}


_BaseDnD = TkinterDnD.DnDWrapper if HAS_DND else object


class MetadataStudioApp(ctk.CTk, _BaseDnD):
    def __init__(self):
        super().__init__()
        if HAS_DND:
            self.TkdndVersion = TkinterDnD._require(self)

        self.engine = MetadataEngine()
        self.items = []
        self.current_meta = None
        self.current_thumb = None
        self.field_entries = {}
        self.event_queue = queue.Queue()
        self.job = None
        self.job_ok = 0
        self.job_err = 0
        self.job_count = 0

        self.title("Metadata Studio")
        self.geometry("1280x780")
        self.minsize(1080, 640)
        self.configure(fg_color=COLORS["bg"])

        apply_tree_style()
        self._build_toolbar()
        self._build_main()
        self._build_bottombar()

        if HAS_DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_events)

        if not self.engine.available:
            messagebox.showerror(
                "ExifTool no encontrado",
                "No se encontró exiftool.exe junto a la aplicación.\n"
                "Copie la carpeta 'exiftool' al lado del ejecutable o defina\n"
                "la variable METADATASTUDIO_EXIFTOOL.",
            )
        else:
            ver = self.engine.version()
            if ver:
                self.title(f"Metadata Studio — ExifTool {ver}")

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=0, height=52)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkButton(
            bar, text="+ Agregar archivos", width=150, font=FONT_UI,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._pick_files,
        ).pack(side="left", padx=(14, 8), pady=10)

        ctk.CTkButton(
            bar, text="Agregar carpeta", width=140, font=FONT_UI,
            fg_color=COLORS["card"], hover_color=COLORS["entry"],
            border_width=1, border_color=COLORS["border"],
            command=self._pick_folder,
        ).pack(side="left", padx=8, pady=10)

        self.recursive_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            bar, text="Incluir subcarpetas", variable=self.recursive_var,
            font=FONT_SMALL, checkbox_width=18, checkbox_height=18,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["muted"],
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            bar, text="Quitar", width=90, font=FONT_UI,
            fg_color=COLORS["card"], hover_color=COLORS["entry"],
            border_width=1, border_color=COLORS["border"],
            command=self._remove_selected,
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            bar, text="Limpiar lista", width=110, font=FONT_UI,
            fg_color=COLORS["card"], hover_color=COLORS["entry"],
            border_width=1, border_color=COLORS["border"],
            command=self._clear_all,
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            bar, text="Seleccionar todo", width=130, font=FONT_UI,
            fg_color=COLORS["card"], hover_color=COLORS["entry"],
            border_width=1, border_color=COLORS["border"],
            command=self._select_all,
        ).pack(side="left", padx=8, pady=10)

        self.count_label = ctk.CTkLabel(
            bar, text="0 archivos", font=FONT_UI, text_color=COLORS["muted"],
        )
        self.count_label.pack(side="right", padx=16)

    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=12)
        main.grid_columnconfigure(0, weight=3, uniform="cols")
        main.grid_columnconfigure(1, weight=2, uniform="cols")
        main.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(main, fg_color=COLORS["panel"], corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        hint = ctk.CTkLabel(
            left, text="Arrastra archivos aquí o usa los botones superiores",
            font=FONT_SMALL, text_color=COLORS["muted"],
        )
        hint.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))

        columns = ("num", "name", "dir", "type", "fmt", "size", "status")
        self.tree = ttk.Treeview(
            left, columns=columns, show="headings", style="MS.Treeview",
            selectmode="extended",
        )
        headers = {
            "num": ("#", 42, "center"),
            "name": ("Nombre", 240, "w"),
            "dir": ("Carpeta", 160, "w"),
            "type": ("Tipo", 80, "center"),
            "fmt": ("Formato", 80, "center"),
            "size": ("Tamaño", 90, "e"),
            "status": ("Estado", 150, "w"),
        }
        for col, (text, width, anchor) in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor, stretch=(col in ("name", "dir")))
        self.tree.tag_configure("ok", foreground=COLORS["ok"])
        self.tree.tag_configure("err", foreground=COLORS["err"])

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(14, 0), pady=(0, 14))
        vsb.grid(row=1, column=1, sticky="ns", pady=(0, 14))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        right = ctk.CTkFrame(main, fg_color=COLORS["panel"], corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(
            right, fg_color="transparent",
            segmented_button_fg_color=COLORS["card"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["card"],
            segmented_button_unselected_hover_color=COLORS["entry"],
            text_color=COLORS["muted"],
        )
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self._build_meta_tab(self.tabs.add("Metadatos"))
        self._build_rename_tab(self.tabs.add("Renombrado"))
        self._build_log_tab(self.tabs.add("Resultados"))

    def _build_meta_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(tab, fg_color=COLORS["card"], corner_radius=10)
        info.pack(fill="x", padx=4, pady=(6, 8))
        info.grid_columnconfigure(1, weight=1)

        self.thumb_label = ctk.CTkLabel(
            info, text="", width=92, height=92, fg_color=COLORS["entry"],
            corner_radius=8, font=("Segoe UI", 20, "bold"), text_color=COLORS["muted"],
        )
        self.thumb_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

        self.info_name = ctk.CTkLabel(
            info, text="Sin archivo seleccionado", font=("Segoe UI Semibold", 13),
            text_color=COLORS["text"], anchor="w",
        )
        self.info_name.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(12, 2))

        self.info_detail = ctk.CTkLabel(
            info, text="Selecciona un archivo para ver y editar sus metadatos",
            font=FONT_SMALL, text_color=COLORS["muted"], anchor="w",
        )
        self.info_detail.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 12))

        self.category = ctk.CTkSegmentedButton(
            tab, values=CATEGORY_VALUES, font=FONT_SMALL,
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["card"],
            unselected_hover_color=COLORS["entry"],
            text_color=COLORS["text"],
            command=self._on_category_change,
        )
        self.category.pack(fill="x", padx=4, pady=(0, 6))
        self.category.set("Todos")

        self.fields_frame = ctk.CTkScrollableFrame(
            tab, fg_color="transparent", corner_radius=0,
        )
        self.fields_frame.pack(fill="both", expand=True, padx=4, pady=(0, 6))
        self.fields_frame.grid_columnconfigure(0, weight=1)
        self._rebuild_fields()

    def _build_rename_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        self.rename_mode = ctk.StringVar(value="keep")
        ctk.CTkRadioButton(
            tab, text="Conservar el nombre original", variable=self.rename_mode,
            value="keep", font=FONT_UI, text_color=COLORS["text"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._update_preview,
        ).pack(anchor="w", padx=14, pady=(14, 6))

        ctk.CTkRadioButton(
            tab, text="Renombrar con plantilla", variable=self.rename_mode,
            value="template", font=FONT_UI, text_color=COLORS["text"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._update_preview,
        ).pack(anchor="w", padx=14, pady=6)

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(2, 6))
        self.template_menu = ctk.CTkOptionMenu(
            row, values=PRESETS, width=320, font=FONT_SMALL,
            fg_color=COLORS["entry"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            dropdown_fg_color=COLORS["card"],
            dropdown_hover_color=COLORS["entry"],
            command=lambda _: self._update_preview(),
        )
        self.template_menu.pack(side="left")
        self.template_menu.set(PRESETS[0])

        ctk.CTkLabel(
            tab, text="Plantilla personalizada:", font=FONT_SMALL,
            text_color=COLORS["muted"], anchor="w",
        ).pack(anchor="w", padx=14, pady=(10, 2))

        self.custom_template = ctk.CTkEntry(
            tab, font=FONT_UI, fg_color=COLORS["entry"],
            border_color=COLORS["border"], text_color=COLORS["text"],
            placeholder_text="Ej: {Artista} - {Album} - {Pista} {Titulo}",
        )
        self.custom_template.pack(fill="x", padx=14, pady=(0, 8))
        self.custom_template.bind("<KeyRelease>", lambda e: self._update_preview())

        ph = ctk.CTkLabel(
            tab,
            text="Marcadores: " + "  ".join(PLACEHOLDERS),
            font=("Segoe UI", 9), text_color=COLORS["muted"], anchor="w", wraplength=430,
        )
        ph.pack(anchor="w", padx=14)

        self.preview_box = ctk.CTkFrame(tab, fg_color=COLORS["card"], corner_radius=10)
        self.preview_box.pack(fill="x", padx=14, pady=(12, 0))
        ctk.CTkLabel(
            self.preview_box, text="Vista previa del nombre", font=("Segoe UI Semibold", 12),
            text_color=COLORS["muted"], anchor="w",
        ).pack(anchor="w", padx=12, pady=(8, 0))
        self.preview_label = ctk.CTkLabel(
            self.preview_box, text="(se conserva el nombre original)",
            font=FONT_UI, text_color=COLORS["accent_hover"], anchor="w", wraplength=430,
        )
        self.preview_label.pack(anchor="w", padx=12, pady=(2, 10))

    def _build_log_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        self.log_box = ctk.CTkTextbox(
            tab, font=("Consolas", 10), fg_color=COLORS["card"],
            text_color=COLORS["text"], corner_radius=10,
            state="disabled", wrap="word",
        )
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def _build_bottombar(self):
        bar = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=0, height=64)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.backup_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            bar, text="Copia de seguridad", variable=self.backup_var,
            font=FONT_SMALL, checkbox_width=18, checkbox_height=18,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["muted"],
        ).pack(side="left", padx=(14, 10), pady=20)

        self.apply_selected_btn = ctk.CTkButton(
            bar, text="Aplicar a la selección (0)", width=190, font=FONT_UI,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=lambda: self._apply(only_selected=True),
        )
        self.apply_selected_btn.pack(side="left", padx=8, pady=16)

        self.apply_all_btn = ctk.CTkButton(
            bar, text="Aplicar a todos (0)", width=170, font=FONT_UI,
            fg_color=COLORS["card"], hover_color=COLORS["entry"],
            border_width=1, border_color=COLORS["border"],
            command=lambda: self._apply(only_selected=False),
        )
        self.apply_all_btn.pack(side="left", padx=8, pady=16)

        self.progress = ctk.CTkProgressBar(
            bar, width=220, fg_color=COLORS["entry"], progress_color=COLORS["accent"],
        )
        self.progress.pack(side="right", padx=16, pady=20)
        self.progress.set(0)

        self.progress_label = ctk.CTkLabel(
            bar, text="", font=FONT_SMALL, text_color=COLORS["muted"],
        )
        self.progress_label.pack(side="right", padx=(0, 10))

    def _pick_files(self):
        exts = " ".join(f"*.{e}" for e in sorted(ALL_EXT))
        paths = filedialog.askopenfilenames(
            title="Seleccionar archivos multimedia",
            filetypes=[
                ("Multimedia", exts),
                ("Todos los archivos", "*.*"),
            ],
        )
        if paths:
            self.add_paths(list(paths))

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta")
        if not folder:
            return
        paths = []
        if self.recursive_var.get():
            for root, _dirs, files in os.walk(folder):
                for f in files:
                    if os.path.splitext(f)[1].lstrip(".").lower() in ALL_EXT:
                        paths.append(os.path.join(root, f))
        else:
            for f in sorted(os.listdir(folder)):
                p = os.path.join(folder, f)
                if os.path.isfile(p) and os.path.splitext(f)[1].lstrip(".").lower() in ALL_EXT:
                    paths.append(p)
        if paths:
            self.add_paths(paths)
        else:
            messagebox.showinfo("Sin archivos", "No se encontraron archivos multimedia en esa carpeta.")

    def _on_drop(self, event):
        paths = self.tk.splitlist(event.data)
        self.add_paths(paths)

    def add_paths(self, paths):
        new_paths = []
        existing = {os.path.normcase(i["path"]) for i in self.items}
        for p in paths:
            try:
                p = os.path.normpath(p.strip().strip("{}"))
            except Exception:
                continue
            if os.path.isfile(p) and os.path.normcase(p) not in existing:
                new_paths.append(p)
        if not new_paths:
            return
        self._log(f"Agregando {len(new_paths)} archivo(s)...")
        threading.Thread(target=self._scan_paths, args=(new_paths,), daemon=True).start()

    def _scan_paths(self, paths):
        raws = self.engine.read_batch(paths) if self.engine.available else [{} for _ in paths]
        entries = []
        for path, raw in zip(paths, raws):
            norm = self.engine.normalize(raw) if raw else {}
            ext = os.path.splitext(path)[1].lstrip(".").lower()
            mtype = detect_media_type(path)
            fmt = (norm.get("FileType") or ext).upper()
            size = norm.get("FileSize") or os.path.getsize(path)
            entries.append({
                "path": path,
                "name": os.path.basename(path),
                "dir": os.path.dirname(path),
                "mtype": mtype,
                "fmt": fmt,
                "size": size,
                "status": "",
            })
        self.event_queue.put({"type": "add", "entries": entries})

    def _remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        idxs = sorted((int(i) for i in sel), reverse=True)
        for i in idxs:
            del self.items[i]
        self._refresh_table()

    def _clear_all(self):
        if not self.items:
            return
        if not messagebox.askyesno("Limpiar lista", "¿Quitar todos los archivos de la lista?"):
            return
        self.items.clear()
        self._refresh_table()

    def _select_all(self):
        if self.tree.get_children():
            self.tree.selection_set(self.tree.get_children())

    def _refresh_table(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for i, item in enumerate(self.items):
            vals = (
                i + 1,
                item["name"],
                item["dir"],
                TYPE_LABELS.get(item["mtype"], "Otro"),
                item["fmt"],
                human_size(item.get("size", "")),
                item.get("status", ""),
            )
            tags = ("ok",) if item.get("status", "").startswith("OK") else (
                ("err",) if item.get("status", "").startswith("Error") else ()
            )
            self.tree.insert("", "end", iid=str(i), values=vals, tags=tags)
        self._update_counts()

    def _update_counts(self):
        total = len(self.items)
        sel = len(self.tree.selection())
        self.count_label.configure(text=f"{total} archivo(s)")
        self.apply_selected_btn.configure(text=f"Aplicar a la selección ({sel})")
        self.apply_all_btn.configure(text=f"Aplicar a todos ({total})")

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        n = len(sel)
        self._update_counts()
        if n == 1:
            item = self.items[int(sel[0])]
            threading.Thread(target=self._load_single, args=(item,), daemon=True).start()
        else:
            self.current_meta = None
            self.info_name.configure(text=f"{n} archivos seleccionados")
            self.info_detail.configure(
                text="Se aplicarán los campos rellenados a todos los archivos seleccionados"
            )
            self._set_thumb(None, None)
            self._update_preview()

    def _load_single(self, item):
        raw = self.engine.read(item["path"]) if self.engine.available else {}
        meta = self.engine.normalize(raw) if raw else {}
        self.event_queue.put({"type": "load", "item": item, "meta": meta})

    def _set_thumb(self, path, mtype):
        self.current_thumb = None
        if path and mtype == "image":
            try:
                img = Image.open(path)
                img.thumbnail((84, 84))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                self.current_thumb = ImageTk.PhotoImage(img)
                self.thumb_label.configure(image=self.current_thumb, text="")
                return
            except Exception:
                pass
        letter = TYPE_LABELS.get(mtype, "?")[0]
        self.thumb_label.configure(
            image="", text=letter, text_color="#ffffff",
            fg_color=TYPE_ICON_COLORS.get(mtype, "#636e72"),
        )

    def _on_category_change(self, _value):
        try:
            saved = {label: e.get() for label, e in self.field_entries.items()}
            self._rebuild_fields()
            for label, e in self.field_entries.items():
                if label in saved and saved[label]:
                    e.insert(0, saved[label])
        except Exception as exc:
            self._log(f"[ERR] No se pudo mostrar la categoría: {exc}")
            messagebox.showerror(
                "Error de interfaz",
                f"No se pudo mostrar la categoría seleccionada:\n{exc}",
            )

    def _rebuild_fields(self):
        for w in self.fields_frame.winfo_children():
            w.destroy()
        self.field_entries = {}
        cat = self.category.get()
        if cat == "Todos":
            groups = list(FIELDS.items())
        else:
            key = {v: k for k, v in TYPE_LABELS.items() if v == cat}.get(cat)
            groups = [(key, FIELDS[key])] if key in FIELDS else []

        for gi, (gkey, fields) in enumerate(groups):
            if cat == "Todos":
                lbl = ctk.CTkLabel(
                    self.fields_frame, text=TYPE_LABELS.get(gkey, gkey).upper(),
                    font=("Segoe UI Semibold", 11), text_color=COLORS["accent_hover"],
                    anchor="w",
                )
                lbl.grid(row=self.fields_frame.grid_size()[1], column=0, sticky="ew", pady=(8 if gi else 0, 4))
            for field in fields:
                self._add_field_row(field["label"], field["tag"])
        self.after(60, self._reset_fields_scroll)

    def _reset_fields_scroll(self):
        try:
            self.fields_frame._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def _add_field_row(self, label, tag):
        row = self.fields_frame.grid_size()[1]
        lab = ctk.CTkLabel(
            self.fields_frame, text=label, font=FONT_SMALL, text_color=COLORS["muted"],
            anchor="w", width=210,
        )
        lab.grid(row=row, column=0, sticky="ew", padx=(2, 8), pady=3)
        entry = ctk.CTkEntry(
            self.fields_frame, font=FONT_UI, height=30,
            fg_color=COLORS["entry"], border_color=COLORS["border"],
            text_color=COLORS["text"],
        )
        entry.grid(row=row, column=1, sticky="ew", pady=3)
        self.field_entries[tag] = entry

    def _gather_assignments(self):
        cat = self.category.get()
        if cat == "Todos":
            groups = list(FIELDS.keys())
        else:
            key = {v: k for k, v in TYPE_LABELS.items() if v == cat}.get(cat)
            groups = [key] if key else []
        assignments = []
        for gkey in groups:
            for field in FIELDS[gkey]:
                entry = self.field_entries.get(field["tag"])
                if entry is None:
                    continue
                value = entry.get().strip()
                if value:
                    assignments.append((field["tag"], value, field["list"]))
        return assignments

    def _apply(self, only_selected):
        if self.job and self.job.is_alive():
            return
        if only_selected:
            sel = self.tree.selection()
            if not sel:
                messagebox.showinfo("Sin selección", "Selecciona al menos un archivo.")
                return
            items = [self.items[int(i)] for i in sel]
        else:
            items = list(self.items)
            if not items:
                messagebox.showinfo("Lista vacía", "Agrega archivos primero.")
                return
        assignments = self._gather_assignments()
        rename_template = None
        if self.rename_mode.get() == "template":
            custom = self.custom_template.get().strip()
            rename_template = custom or self.template_menu.get()
        if not assignments and not rename_template:
            messagebox.showinfo(
                "Nada que hacer",
                "Rellena al menos un campo de metadatos o elige una plantilla de renombrado.",
            )
            return
        if not self.engine.available:
            messagebox.showerror("Error", "ExifTool no disponible.")
            return

        self._log(
            f"Inicio: {len(items)} archivo(s), {len(assignments)} campo(s), "
            f"{'renombrado' if rename_template else 'sin renombrar'}, "
            f"backup {'sí' if self.backup_var.get() else 'no'}"
        )
        self.job_ok = 0
        self.job_err = 0
        self.job_count = len(items)
        self.progress.set(0)
        self.progress_label.configure(text=f"0/{self.job_count}")
        self.apply_selected_btn.configure(state="disabled")
        self.apply_all_btn.configure(state="disabled")
        self.job = BatchJob(
            items=items,
            assignments=assignments,
            rename_template=rename_template,
            backup=self.backup_var.get(),
            engine=self.engine,
            on_event=lambda ev: self.event_queue.put(ev),
        )
        self.job.start()

    def _poll_events(self):
        try:
            while True:
                ev = self.event_queue.get_nowait()
                self._handle_event(ev)
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _handle_event(self, ev):
        etype = ev.get("type")
        if etype == "add":
            self.items.extend(ev["entries"])
            self._refresh_table()
            self._log(f"{len(ev['entries'])} archivo(s) agregados a la lista.")
        elif etype == "load":
            item = ev["item"]
            meta = ev["meta"]
            self.current_meta = meta
            self.info_name.configure(text=item["name"])
            details = []
            if meta.get("FileType"):
                details.append(meta["FileType"])
            if meta.get("ImageWidth"):
                details.append(f"{meta['ImageWidth']}x{meta['ImageHeight']}")
            if meta.get("Duration"):
                details.append(format_duration(meta["Duration"]))
            if meta.get("FileSize"):
                details.append(human_size(meta["FileSize"]))
            self.info_detail.configure(text="  |  ".join(details) or item["dir"])
            self._set_thumb(item["path"], item["mtype"])
            cat = TYPE_LABELS.get(item["mtype"], "Otro")
            if cat in CATEGORY_VALUES and self.category.get() != cat:
                self.category.set(cat)
                self._on_category_change(cat)
            for field in FIELDS.get(item["mtype"], []):
                entry = self.field_entries.get(field["tag"])
                if entry is not None:
                    val = meta.get(field["tag"], "")
                    entry.delete(0, "end")
                    if val:
                        entry.configure(placeholder_text=f"Actual: {val}")
            self._update_preview()
        elif etype == "item":
            idx = ev["index"]
            item = self.items[idx] if idx < len(self.items) else None
            done = self.job_ok + self.job_err + 1
            if ev["status"] == "ok":
                self.job_ok += 1
                if item is not None:
                    suffix = f" → {ev['renamed']}" if ev.get("renamed") else ""
                    item["status"] = f"OK{suffix}"
                self._log(f"[OK] {ev.get('name', item['name'] if item else '')} {('→ ' + ev['renamed']) if ev.get('renamed') else ''}")
            else:
                self.job_err += 1
                name = item["name"] if item else "?"
                if item is not None:
                    item["status"] = f"Error: {ev.get('message', '')[:60]}"
                self._log(f"[ERR] {name}: {ev.get('message', '')}")
            self.tree.item(str(idx), values=self._row_values(idx))
            self.tree.item(
                str(idx),
                tags=("ok",) if ev["status"] == "ok" else ("err",),
            )
            self.progress.set(done / self.job_count if self.job_count else 1)
            self.progress_label.configure(text=f"{done}/{self.job_count}")
        elif etype == "done":
            self.apply_selected_btn.configure(state="normal")
            self.apply_all_btn.configure(state="normal")
            self.progress_label.configure(
                text=f"Completado: {self.job_ok} OK, {self.job_err} error(es)"
            )
            self._log(f"Proceso terminado: {self.job_ok} correctos, {self.job_err} errores.")
            self._update_counts()

    def _row_values(self, idx):
        item = self.items[idx]
        return (
            idx + 1,
            item["name"],
            item["dir"],
            TYPE_LABELS.get(item["mtype"], "Otro"),
            item["fmt"],
            human_size(item.get("size", "")),
            item.get("status", ""),
        )

    def _update_preview(self):
        if self.rename_mode.get() != "template":
            self.preview_label.configure(
                text="(se conserva el nombre original)", text_color=COLORS["muted"],
            )
            return
        template = self.custom_template.get().strip() or self.template_menu.get()
        meta = self.current_meta or {}
        first = None
        if not meta and self.items:
            first = self.items[0]
        if first:
            stem, ext = os.path.splitext(first["name"])
            name = build_name(template, meta, 1, ext.lstrip(".").lower(), stem)
            self.preview_label.configure(
                text=f"Ejemplo (primer archivo): {name}", text_color=COLORS["accent_hover"],
            )
        elif meta.get("FileName"):
            stem, ext = os.path.splitext(meta["FileName"])
            name = build_name(template, meta, 1, ext.lstrip(".").lower(), stem)
            self.preview_label.configure(text=f"Vista previa: {name}", text_color=COLORS["accent_hover"])
        else:
            self.preview_label.configure(
                text="Plantilla: " + template, text_color=COLORS["muted"],
            )

    def _log(self, text):
        self.log_box.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _on_close(self):
        if self.job and self.job.is_alive():
            if not messagebox.askyesno("Salir", "Hay un proceso en curso. ¿Salir de todos modos?"):
                return
        self.destroy()
