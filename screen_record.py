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
from tkinter import filedialog
from ttkbootstrap import Style
from ttkbootstrap.widgets import Button, Combobox, Label
import os
import subprocess
import datetime
import shlex

class ScreenRecorderUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("600x560")
        self.style = Style("darkly")
        self.title("FFMPEG Screen Recorder")
        self.update()
        self.output_folder = os.path.expanduser("~")
        self.label_fg = "#ED1C24"
        self.recording_process = None
        self.recording = False
        self.recording_start_time = None
        self.build_ui()      
            
    def build_ui(self):
        padding = {"padx": 10, "pady": 5}

        ###  PARAMS  ###
        Label(self, text="Encoder:", foreground=self.label_fg).pack(anchor="w", **padding)
        self.encoder_menu = Combobox(self, values=["hevc_vaapi", "h264_vaapi", "libx264", "mpeg1video"], state="readonly")
        self.encoder_menu.set("hevc_vaapi")
        self.encoder_menu.pack(fill="x", **padding)
        Label(self, text="FPS:", foreground=self.label_fg).pack(anchor="w", **padding)
        self.fps_menu = Combobox(self, values=["30", "60"], state="readonly")
        self.fps_menu.set("60")
        self.fps_menu.pack(fill="x", **padding)
        Label(self, text="Resolution:", foreground=self.label_fg).pack(anchor="w", **padding)
        self.resolution_menu = Combobox(self, values=["3840x2160", "2560x1440", "1920x1080", "1280x720"], state="readonly")
        self.resolution_menu.set("1920x1080")
        self.resolution_menu.pack(fill="x", **padding)
        Label(self, text="Audio:", foreground=self.label_fg).pack(anchor="w", **padding)
        self.audio_menu = Combobox(self, values=["None", "Desktop", "Microphone"], state="readonly")
        self.audio_menu.set("Desktop")
        self.audio_menu.pack(fill="x", **padding)
        Label(self, text="Preset:", foreground=self.label_fg).pack(anchor="w", **padding)
        self.preset_menu = Combobox(self, values=["ultrafast", "veryfast", "fast", "medium", "slow"], state="readonly")
        self.preset_menu.set("ultrafast")
        self.preset_menu.pack(fill="x", **padding)
        
        ### TIMER
        self.timer_label = Label(self, text="00:00", font=("Arial", 18, "bold"), foreground=self.label_fg, anchor="center")
        self.timer_label.pack(pady=10)
        
        ### FOLDER PICKER ###   
        Label(self, text="Output Folder:", foreground=self.label_fg).pack(anchor="w", **padding)        
        folder_frame = tk.Frame(self)
        folder_frame.pack(fill="x", **padding)
        self.folder_label = Label(folder_frame, text=self.output_folder, wraplength=400)
        self.folder_label.pack(side="left", fill="x", expand=True)
        Button(folder_frame, text="Browse", bootstyle="secondary", command=self.select_folder).pack(side="right")

        ### BUTTONS ###
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        self.start_button = Button(button_frame, text="Start Recording", bootstyle="danger", command=self.start_recording)
        self.start_button.pack(side="left", padx=10)
        self.stop_button = Button(button_frame, text="Stop Recording", bootstyle="secondary", command=self.stop_recording)
        self.stop_button.pack(side="right", padx=10)
        self.stop_button["state"] = "disabled"

    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_folder, title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.folder_label.config(text=folder)

    def start_recording(self):
        if self.recording:
            return

        if not self.output_folder:
            print("Error: No output folder selected!")
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_file = f"{self.output_folder}/recording_{timestamp}.mp4"
        encoder = self.encoder_menu.get()
        fps = self.fps_menu.get()
        resolution = self.resolution_menu.get()
        preset = self.preset_menu.get()
        audio_choice = self.audio_menu.get()

        offset = "+1920,0"
        command = [
            "ffmpeg",
            "-f", "x11grab",
            "-thread_queue_size", "512",
            "-framerate", fps,
            "-threads", "4",
            "-video_size", resolution,
            "-i", f":1.0{offset}",
        ]

        if audio_choice == "Desktop":
            command += ["-f", "pulse", "-thread_queue_size", "512", "-i", "alsa_output.pci-0000_0c_00.4.analog-stereo.monitor", "-c:a", "aac", "-b:a", "128k"]
        elif audio_choice == "Microphone":
            command += ["-f", "pulse", "-thread_queue_size", "512", "-i", "alsa_input.pci-0000_0c_00.4.analog-stereo.3", "-c:a", "aac", "-b:a", "128k"]

        if encoder == "h264_vaapi":
            command += ["-vaapi_device", "/dev/dri/renderD128", "-vf", "format=nv12,hwupload", "-c:v", encoder, "-qp", "24", "-preset", preset, "-bsf:v", "dump_extra"]
        elif encoder == "hevc_vaapi":
            command += ["-vaapi_device", "/dev/dri/renderD128", "-vf", "format=nv12,hwupload", "-c:v", encoder, "-qp", "24", "-preset", preset, "-bsf:v", "dump_extra"]
        else:
            command += ["-c:v", encoder, "-crf", "23", "-preset", preset]

        command += [output_file]

        print("Running command:", " ".join(shlex.quote(arg) for arg in command))
        self.recording_process = subprocess.Popen(command)
        self.recording = True
        self.recording_start_time = datetime.datetime.now()
        self.update_timer()

        self.recording_start_time = datetime.datetime.now()

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

