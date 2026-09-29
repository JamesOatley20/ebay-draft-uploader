"""Native, memory-only authentication and results. Never create a results file."""

import queue
import threading
import webbrowser

from . import AppError
from .auth import Auth
from .ebay import Ebay
from .network import make_client
from .workflow import SessionResult, STATUS_TEXT, submit_batch


def run_session(items) -> list[SessionResult]:
    import tkinter as tk
    from tkinter import simpledialog
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.withdraw()
    root.title("eBay Drafts — this session only")
    stop = threading.Event()
    events = queue.Queue()
    results = []
    done = False
    worker = None
    auth = None

    def callback_error(*_):
        # Tk's default handler prints tracebacks, which may contain request data.
        stop.set()
        root.quit()

    root.report_callback_exception = callback_error
    try:
        token = simpledialog.askstring(
            "Connect for this run",
            "Enter a Production OAuth User access token for your seller account.\n"
            "Get it from the eBay Developer Portal (see README for scopes).\n"
            "It stays in memory and must be entered again next run.\n"
            "No refresh token, password, App ID or Cert ID is needed here.",
            parent=root, show="*",
        )
        if token is None:
            return []
        if len(token) > 20000:
            raise AppError("The supplied token is too long.")
        auth = Auth(token.strip())
        token = None
        root.geometry("850x570")
        status = tk.Label(root, text="Session results are not saved. Review Seller Hub before retrying any item.", wraplength=800)
        status.pack(padx=12, pady=12)
        output = ScrolledText(root, wrap="word", state="disabled")
        output.pack(fill="both", expand=True, padx=12, pady=8)
        controls = tk.Frame(root)
        controls.pack(pady=12)

        def close_or_stop():
            if done:
                root.destroy()
            else:
                stop.set()
                status.config(text="Stopping after the current request (up to its timeout). Remote work may continue; check Seller Hub.")
                stop_button.config(state="disabled")

        stop_button = tk.Button(controls, text="Stop this session", command=close_or_stop)
        stop_button.pack(side="left", padx=8)
        tk.Button(controls, text="Open Seller Hub drafts",
                  command=lambda: webbrowser.open("https://www.ebay.co.uk/sh/lst/drafts")).pack(side="left", padx=8)
        root.protocol("WM_DELETE_WINDOW", close_or_stop)

        def work():
            try:
                with make_client() as client:
                    api = Ebay(client, auth, sleeper=stop.wait, cancelled=stop.is_set)
                    results.extend(submit_batch(api, items, events.put))
            except BaseException:
                # No thread traceback, response dump, exception repr or disk report.
                failure = SessionResult("Session", "error", ["Unexpected failure. Check Seller Hub before any new attempt."])
                results.append(failure)
                events.put(failure)
            finally:
                auth.close()
                events.put(None)

        def pump():
            nonlocal done
            try:
                while True:
                    event = events.get_nowait()
                    if event is None:
                        done = True
                        status.config(text="Session ended. Results exist only in this window. Check Seller Hub; closing does not undo uploads.")
                        stop_button.config(text="Close", state="normal")
                        break
                    output.config(state="normal")
                    output.insert("end", event.name + ": " + STATUS_TEXT[event.status] + "\n")
                    for message in event.messages:
                        clean = "".join(c for c in message[:2000] if c in "\n\t" or ord(c) >= 32)
                        output.insert("end", clean + "\n")
                    output.insert("end", "\n")
                    output.see("end")
                    output.config(state="disabled")
            except queue.Empty:
                pass
            if not done:
                root.after(100, pump)

        root.deiconify()
        worker = threading.Thread(target=work, name="ebay-session")
        worker.start()
        root.after(100, pump)
        root.mainloop()
        return results
    finally:
        stop.set()
        if worker:
            worker.join()
        if auth:
            auth.close()
        try:
            root.destroy()
        except tk.TclError:
            pass
