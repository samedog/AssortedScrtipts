#!/usr/bin/env python3
############################################################################################
# By Diego Cardenas "The Samedog" under the GNU GENERAL PUBLIC LICENSE Version 2, 
# June 1991 (www.gnu.org/licenses/old-licenses/gpl-2.0.html) e-mail: the.samedog[]gmail.com.
# https://github.com/samedog
############################################################################################
#
# THIS SCRIPT IS A SET OF HORRIBLE HACKS. IT MIGHT WORK, MIGHT OPEN A VORTEX AND SEND YOU 
# TO A COMPLETELY DIFFERENT UNIVERSE, OR IT MIGHT DO SHIT. WHO KNOWS?.
#
############################################################################################
# Version: 2.0
# Changelog:
#   04-05-2025: 
#        - Bitrate bound to resolution × framerate using recommended settings from 
#          YouTube/Twitch.
#        - Preset option hides when unsupported or unnecessary.
#        - Added keyboard hotkey support (Win+R) to start/stop recording.
#   05-05-2025:
#        - Code cleanup and minor optimizations.
#        - Bound CRF and QP to preset and bitrate, respectively.
################################# Code begins here #########################################

import os
import shlex
import datetime
import subprocess
from threading import Thread
from tkinter import filedialog
from ttkbootstrap import Style, Window
from ttkbootstrap.widgets import Button, Combobox, Label, Frame, Notebook
from pynput import keyboard

class ScreenRecorderUI(Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.setup_hotkeys()
        self.geometry("390x550")
        self.title("FFMPEG Screen Recorder")
        self.screens = self.get_screens()
        self.output_folder = os.path.expanduser("~")
        self.label_fg = "#ED1C24"
        self.recording_process = None
        self.recording = False
        self.recording_start_time = None
        self.notebook = Notebook(self)
        self.record_frame = Frame(self.notebook)
        self.record_frame = Frame(self.notebook)
        self.notebook.add(self.record_frame, text="Record")
        self.stream_frame = Frame(self.notebook)
        self.notebook.add(self.stream_frame, text="Stream")
        self.build_record_ui(self.record_frame)
        self.build_stream_ui(self.stream_frame)
        self.notebook.pack(fill="both", expand=True)
        self.display = os.environ.get("DISPLAY", ":0")
        if not self.display:
            print("Warning: DISPLAY not found, defaulting to :0")
            self.display = ":0"
                
    def add_labeled_combobox(self, parent, label_text, values, default, row):
        label = Label(parent, text=label_text, foreground=self.label_fg)
        label.grid(row=row, column=0, sticky="e", padx=10, pady=5)
        combo = Combobox(parent, values=values, state="readonly", width=25)
        combo.set(default)
        combo.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        return combo

    def setup_hotkeys(self):
        def on_press(key):
            self.pressed_keys.add(key)
            if keyboard.Key.cmd in self.pressed_keys and getattr(key, 'char', '').lower() == 'r':
                if self.recording:
                    self.stop_recording()
                else:
                    self.start_recording()

        def on_release(key):
            self.pressed_keys.discard(key)

        def listener_thread():
            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
                
        self.pressed_keys = set()
        Thread(target=listener_thread, daemon=True).start()
           
    def get_bitrate(self, resolution, fps):
        table = {
            ("1280x720", "30"): "2.5M",
            ("1280x720", "60"): "4M",
            ("1920x1080", "30"): "5M",
            ("1920x1080", "60"): "8M",
            ("2560x1440", "60"): "12M",
            ("3840x2160", "30"): "20M",
            ("3840x2160", "60"): "35M",
        }
        return table.get((resolution, fps), "8M")
            
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

        self.encoder_menu = self.add_labeled_combobox(parent, "Encoder:", ["hevc_vaapi", "h264_vaapi", "libx264", "mpeg1video"], "hevc_vaapi", row)
        row += 1
        self.filetype_menu = self.add_labeled_combobox(parent, "File Type:", ["mp4", "mkv", "webm"], "mp4", row)
        row += 1
        self.fps_menu = self.add_labeled_combobox(parent, "FPS:", ["30", "60"], "60", row)
        row += 1

        screen_names = [f"{name} ({res})" for name, res, _ in self.screens]
        if not screen_names:
            screen_names = "None"
        
        self.screen_menu = self.add_labeled_combobox(parent, "Screen:", screen_names, screen_names[0], row)
        row += 1
        self.resolution_menu = self.add_labeled_combobox(parent, "Screen:", ["3840x2160", "2560x1440", "1920x1080", "1280x720"], "1920x1080", row)
        row += 1
        self.audio_sources = {"None": None}
        self.audio_sources.update(self.get_pulseaudio_sources())
        
        default_audio = "None"
        for label in self.audio_sources:
            if "Desktop (Analog)" in label:
                default_audio = label
                break

        self.audio_menu = self.add_labeled_combobox(parent, "Audio:", list(self.audio_sources.keys()), default_audio, row)
        row += 1
        self.preset_label, self.preset_menu = self.add_toggleable_combobox(parent, "Preset:", ["ultrafast", "veryfast", "fast", "medium", "slow"], "ultrafast", row)
        row += 1
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
        button_frame = Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        self.start_button = Button(button_frame, text="Start Recording", bootstyle="danger", command=self.start_recording)
        self.start_button.pack(side="left", padx=10)
        self.stop_button = Button(button_frame, text="Stop Recording", bootstyle="secondary", command=self.stop_recording)
        self.stop_button.pack(side="right", padx=10)
        self.stop_button["state"] = "disabled"
        self.encoder_menu.bind("<<ComboboxSelected>>", self.toggle_preset_visibility)
        self.toggle_preset_visibility()
        
    def add_toggleable_combobox(self, parent, label_text, values, default, row):
        padding = {"padx": 10, "pady": 5}
        label = Label(parent, text=label_text, foreground=self.label_fg)
        combo = Combobox(parent, values=values, state="readonly", width=25)
        combo.set(default)
        label.grid(row=row, column=0, sticky="e", **padding)
        combo.grid(row=row, column=1, sticky="w", **padding)
        return label, combo

    def toggle_preset_visibility(self, *_):
        encoder = self.encoder_menu.get()
        if encoder in ["libx264", "libx265", "mpeg1video"]:
            self.preset_label.grid()
            self.preset_menu.grid()
        else:
            self.preset_label.grid_remove()
            self.preset_menu.grid_remove()

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
    def get_vaapi_device(self):
        # Look for files that match /dev/dri/renderD* (render devices)
        render_devices = [f for f in os.listdir('/dev/dri/') if f.startswith('renderD')]
        if render_devices:
            # Return the first available render device (e.g., renderD128)
            return f"/dev/dri/{render_devices[0]}"
        else:
            return None  # No VAAPI device found

    def get_crf_for_preset(self, preset):
        crf_values = {
            "ultrafast": 28,
            "veryfast": 26,
            "fast": 24,
            "medium": 23,
            "slow": 22,
        }
        return crf_values.get(preset, 23)  # Default fallback
                    
    def get_qp_for_bitrate(self, bitrate):
        try:
            mbps = int(bitrate.rstrip("M"))
            # Lower bitrate = higher QP (lower quality), higher = lower QP
            if mbps <= 4:
                return 28
            elif mbps <= 8:
                return 26
            elif mbps <= 12:
                return 24
            elif mbps <= 20:
                return 23
            else:
                return 21
        except:
            return 24

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
        bitrate = self.get_bitrate(resolution, fps)
        is_vaapi = encoder in ("h264_vaapi", "hevc_vaapi")
        
        # Dynamically get the VAAPI device
        vaapi_device = self.get_vaapi_device()
        if vaapi_device:
            print(f"Using VAAPI device: {vaapi_device}")
        else:
            print("No VAAPI device found, using software encoding.")
        
        if is_vaapi:
            qp = self.get_qp_for_bitrate(bitrate)
            command += [
                "-vaapi_device", vaapi_device,
                "-vf", f"scale={resolution},format=nv12,hwupload",
                "-c:v", encoder,
                "-b:v", bitrate,
                "-maxrate", bitrate,
                "-bufsize", str(int(bitrate.rstrip('M')) * 2) + "M",
                "-qp", str(qp),
                "-bsf:v", "dump_extra"
            ]
        elif encoder == "mpeg1video":
            command += ["-vf", f"scale={resolution}", "-c:v", encoder, "-b:v", bitrate]
        else:  # libx264
            crf = self.get_crf_for_preset(preset)
            command += ["-vf", f"scale={resolution}", "-c:v", encoder, "-crf", str(crf), "-preset", preset]

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

