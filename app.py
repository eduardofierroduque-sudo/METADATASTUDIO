import sys
import os
import traceback
import tkinter.messagebox


def _log_error(exc, value, tb):
    try:
        log_path = os.path.join(_app_dir(), "error.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n===== EXCEPCION =====\n")
            traceback.print_exception(exc, value, tb, file=f)
        tkinter.messagebox.showerror(
            "Error inesperado",
            "Ocurrió un error inesperado. Se guardó el detalle en:\n"
            f"{log_path}\n\n{value}",
        )
    except Exception:
        pass


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    import customtkinter as ctk
    from gui.main_window import MetadataStudioApp
    import tkinter as tk

    ctk.set_appearance_mode("dark")
    app = MetadataStudioApp()
    tk.Tk.report_callback_exception = _log_error
    paths = [a for a in sys.argv[1:] if os.path.isfile(a)]
    if paths:
        app.add_paths(paths)
    if "--selftest" in sys.argv:
        app.after(2000, lambda: (print("SELFTEST-OK"), app.destroy()))
    app.mainloop()


if __name__ == "__main__":
    main()
