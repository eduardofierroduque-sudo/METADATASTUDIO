from tkinter import ttk

COLORS = {
    "bg": "#121418",
    "panel": "#191c22",
    "card": "#20242d",
    "entry": "#252a34",
    "border": "#2e3440",
    "accent": "#7c5cff",
    "accent_hover": "#8f74ff",
    "text": "#e8eaed",
    "muted": "#9aa0a8",
    "ok": "#2ecc71",
    "err": "#ff5f56",
    "warn": "#f5b041",
}

FONT_UI = ("Segoe UI", 11)
FONT_SMALL = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI Semibold", 14)


def apply_tree_style():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "MS.Treeview",
        background=COLORS["card"],
        fieldbackground=COLORS["card"],
        foreground=COLORS["text"],
        borderwidth=0,
        rowheight=32,
        font=FONT_SMALL,
    )
    style.configure(
        "MS.Treeview.Heading",
        background=COLORS["panel"],
        foreground=COLORS["muted"],
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padding=(6, 6),
    )
    style.map(
        "MS.Treeview",
        background=[("selected", COLORS["accent"])],
        foreground=[("selected", "#ffffff")],
    )
    style.map(
        "MS.Treeview.Heading",
        background=[("active", COLORS["panel"])],
    )
