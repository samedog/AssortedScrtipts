##########################################################################################
# By Diego Cardenas "The Samedog" under GNU GENERAL PUBLIC LICENSE Version 2, June 1991
# (www.gnu.org/licenses/old-licenses/gpl-2.0.html) e-mail: the.samedog[]gmail.com.
# https://github.com/samedog
##########################################################################################
#
# THIS SCRIPT IS A SET OF HORRIBLE HACKS, IT MIGHT WORK, MIGHT OPEN A VORTEX 
# AND SEND YOU TO A COMPLETELY DIFFERENT UNIVERSE, OR MIGHT DO SHIT, WHO KNOWS?.
#
##########################################################################################
# Version: 1.0
#
################################# Code begins here #######################################

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from ttkbootstrap import Style
from ttkbootstrap.widgets import Button, Combobox, Label
import os
import subprocess
import datetime
import shlex
import glob

class ScreenRecorderUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("390x550")
        self.style = Style("darkly")
        self.title("FFMPEG Screen Recorder")
        self.screens = self.get_screens()
        self.output_folder = os.path.expanduser("~")
        self.label_fg = "#ED1C24"
        self.recording_process = None
        self.recording = False
        self.recording_start_time = None

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.record_frame = tk.Frame(self.notebook)
        self.notebook.add(self.record_frame, text="Record")

        self.stream_frame = tk.Frame(self.notebook)
        self.notebook.add(self.stream_frame, text="Stream")

        self.build_record_ui(self.record_frame)
        self.build_stream_ui(self.stream_frame)
        self.display = os.environ.get("DISPLAY", ":0")
        if not self.display:
            print("Warning: DISPLAY not found, defaulting to :0")
            self.display = ":0"
            
    def get_pulseaudio_sources(self):
        try:
            output = subprocess.check_output(["pactl", "list", "short", "sources"]).decode()
            lines = output.strip().splitlines()
            sources = {}

            for line in lines:
                parts = line.split()
                if len(parts) < 2:
                    continue
                name = parts[1]

                if name.endswith(".monitor"):
                    if "hdmi" in name:
                        label = "Desktop (HDMI)"
                    elif "analog" in name:
                        label = "Desktop (Analog)"
                    else:
                        label = f"Desktop ({name})"
                else:
                    if "analog" in name:
                        label = "Microphone (Analog)"
                    elif "hdmi" in name:
                        label = "Microphone (HDMI)"
                    else:
                        label = f"Microphone ({name})"

                # Prevent duplicate labels (e.g., two HDMI monitors)
                base_label = label
                i = 2
                while label in sources:
                    label = f"{base_label} #{i}"
                    i += 1

                sources[label] = name
            return sources
        except Exception as e:
            print("Failed to get PulseAudio sources:", e)
            return {}


    def build_record_ui(self, parent):
        padding = {"padx": 10, "pady": 5}
        row = 0

        def add_row(label_text, widget):
            nonlocal row
            label = Label(parent, text=label_text, foreground=self.label_fg)
            label.grid(row=row, column=0, sticky="e", **padding)
            widget.grid(row=row, column=1, sticky="w", **padding)
            row += 1
        
        COMMON_WIDTH = 25

        self.encoder_menu = Combobox(parent, values=["hevc_vaapi", "h264_vaapi", "libx264", "mpeg1video"], state="readonly", width=COMMON_WIDTH)
        self.encoder_menu.set("hevc_vaapi")
        add_row("Encoder:", self.encoder_menu)

        self.filetype_menu = Combobox(parent, values=["mp4", "mkv", "webm"], state="readonly", width=COMMON_WIDTH)
        self.filetype_menu.set("mp4")
        add_row("File Type:", self.filetype_menu)

        self.fps_menu = Combobox(parent, values=["30", "60"], state="readonly", width=COMMON_WIDTH)
        self.fps_menu.set("60")
        add_row("FPS:", self.fps_menu)

        screen_names = [f"{name} ({res})" for name, res, _ in self.screens]
        self.screen_menu = Combobox(parent, values=screen_names, state="readonly", width=COMMON_WIDTH)
        if screen_names:
            self.screen_menu.set(screen_names[0])
        add_row("Screen:", self.screen_menu)

        self.resolution_menu = Combobox(parent, values=["3840x2160", "2560x1440", "1920x1080", "1280x720"], state="readonly", width=COMMON_WIDTH)
        self.resolution_menu.set("1920x1080")
        add_row("Resolution:", self.resolution_menu)

        self.audio_sources = {"None": None}
        self.audio_sources.update(self.get_pulseaudio_sources())
        self.audio_menu = Combobox(parent, values=list(self.audio_sources.keys()), state="readonly", width=COMMON_WIDTH)
        self.audio_menu.set("None" if "Desktop (Analog)" not in self.audio_sources else next(k for k in self.audio_sources if "Desktop (Analog)" in k))
        add_row("Audio:", self.audio_menu)

        self.preset_menu = Combobox(parent, values=["ultrafast", "veryfast", "fast", "medium", "slow"], state="readonly", width=COMMON_WIDTH)
        self.preset_menu.set("ultrafast")
        add_row("Preset:", self.preset_menu)
        
        Label(parent, text="Output Folder:", foreground=self.label_fg).grid(row=row, column=0, sticky="e", **padding)
        browse_button = Button(parent, text="Browse", bootstyle="secondary", command=self.select_folder)
        browse_button.grid(row=row, column=1, sticky="w", **padding)
        row += 1
        self.folder_label = Label(parent, text=self.output_folder, wraplength=400, anchor="center", justify="center")
        self.folder_label.grid(row=row, column=0, columnspan=2, sticky="w", **padding)
        row += 1

        self.timer_label = Label(parent, text="00:00", font=("Arial", 18, "bold"), foreground=self.label_fg, anchor="center")
        self.timer_label.grid(row=row, column=0, columnspan=2, sticky="ew", **padding)

        row += 1

        button_frame = tk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        self.start_button = Button(button_frame, text="Start Recording", bootstyle="danger", command=self.start_recording)
        self.start_button.pack(side="left", padx=10)
        self.stop_button = Button(button_frame, text="Stop Recording", bootstyle="secondary", command=self.stop_recording)
        self.stop_button.pack(side="right", padx=10)
        self.stop_button["state"] = "disabled"


    def build_stream_ui(self, parent):
        padding = {"padx": 10, "pady": 5}
        Label(parent, text="Streaming Placeholder UI", font=("Arial", 14, "bold"), foreground=self.label_fg).pack(pady=20)
        Label(parent, text="This tab will contain stream settings.", foreground=self.label_fg).pack(**padding)
        Button(parent, text="Coming Soon", bootstyle="info").pack(pady=10)

    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_folder, title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.folder_label.config(text=folder)

    def get_screens(self):
        try:
            output = subprocess.check_output(["xrandr", "--query"]).decode()
            screens = []
            for line in output.splitlines():
                if " connected" in line:
                    parts = line.split()
                    name = parts[0]
                    resolution = next((p for p in parts if "+" in p and "x" in p), None)
                    if resolution:
                        res_part = resolution.split("+")[0]
                        offset_x = resolution.split("+")[1]
                        offset_y = resolution.split("+")[2]
                        if "primary" in line: 
                            screens.append((name + " primary", res_part, f"+{offset_x},{offset_y}"))
                        else:
                            screens.append((name, res_part, f"+{offset_x},{offset_y}"))
            return screens
        except Exception as e:
            print("Error fetching screens:", e)
            return []

    def start_recording(self):
        if self.recording:
            return

        if not self.output_folder:
            print("Error: No output folder selected!")
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_extension = self.filetype_menu.get()
        output_file = f"{self.output_folder}/recording_{timestamp}.{file_extension}"
        encoder = self.encoder_menu.get()
        fps = self.fps_menu.get()
        resolution = self.resolution_menu.get()
        preset = self.preset_menu.get()
        audio_choice = self.audio_menu.get()

        screen_index = self.screen_menu.current()
        offset = self.screens[screen_index][2] if screen_index != -1 else "+0,0"
        command = [
            "ffmpeg",
            "-f", "x11grab",
            "-thread_queue_size", "512",
            "-framerate", fps,
            "-threads", "4",
            "-video_size", self.screens[screen_index][1],
            "-i", f"{self.display}{offset}",
        ]

        selected_audio = self.audio_sources.get(audio_choice)
        if selected_audio:
            command += ["-f", "pulse", "-thread_queue_size", "512", "-i", selected_audio, "-c:a", "aac", "-b:a", "128k"]


        if encoder == "h264_vaapi":
            hwupload_chain = f"scale={resolution},format=nv12,hwupload"
            command += ["-vaapi_device", "/dev/dri/renderD128", "-vf", hwupload_chain, "-c:v", encoder, "-qp", "24", "-preset", preset, "-bsf:v", "dump_extra"]
        elif encoder == "hevc_vaapi":
            command += ["-vaapi_device", "/dev/dri/renderD128", "-vf", "format=nv12,hwupload", "-c:v", encoder, "-qp", "24", "-preset", preset, "-bsf:v", "dump_extra"]
        else:
            command += ["-vf", f"scale={resolution}", "-c:v", encoder, "-crf", "23", "-preset", preset]

        command += [output_file]

        print("Running command:", " ".join(shlex.quote(arg) for arg in command))
        self.recording_process = subprocess.Popen(command)
        self.recording = True
        self.recording_start_time = datetime.datetime.now()
        self.update_timer()

        self.start_button["state"] = "disabled"
        self.stop_button.config(state="normal", bootstyle="danger")


    def update_timer(self):
        if self.recording and self.recording_start_time:
            elapsed = datetime.datetime.now() - self.recording_start_time
            minutes, seconds = divmod(elapsed.seconds, 60)
            self.timer_label.config(text=f"{minutes:02}:{seconds:02}")
            self.after(1000, self.update_timer)

    def stop_recording(self):
        if self.recording and self.recording_process:
            self.recording_process.terminate()
            self.recording_process.wait()
            self.recording_process = None
            self.recording = False
            self.start_button["state"] = "normal"
            self.stop_button.config(state="disabled", bootstyle="secondary")
            self.timer_label.config(text="00:00")

if __name__ == "__main__":
    app = ScreenRecorderUI()
    app.mainloop()

