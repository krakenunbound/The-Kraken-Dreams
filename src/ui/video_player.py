
import tkinter as tk
import sys

class VideoPlayerWindow:
    """
    A separate window for video playback, designed to host a VLC player instance.
    """
    def __init__(self, parent, title="📺 Video Viewer"):
        self.parent = parent
        self.is_closed = False
        
        # Create Toplevel window
        self.window = tk.Toplevel(parent)
        self.window.title(f"{title} - The Kraken Dreams")
        self.window.configure(bg='black')
        self.window.geometry("640x360")
        
        # Create a frame for VLC to render into
        self.video_frame = tk.Frame(self.window, bg='black')
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        
        # Center the window relative to parent
        try:
            x = parent.winfo_x() + parent.winfo_width() + 10
            y = parent.winfo_y()
            self.window.geometry(f"+{x}+{y}")
        except:
            pass
        
        # Bind close event
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def get_handle(self):
        """Get the window handle (HWND) for VLC."""
        return self.video_frame.winfo_id()

    def on_close(self):
        """Handle window closing."""
        self.is_closed = True
        self.window.destroy()
        # Callback to parent to let it know we closed (optional, handled by parent polling)

    def cleanup(self):
        if not self.is_closed:
            self.on_close()

    def sync(self, timestamp):
        # No-op for VLC (it handles sync internally)
        pass
