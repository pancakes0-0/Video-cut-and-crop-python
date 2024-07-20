import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import cv2
from PIL import Image, ImageTk, ImageDraw
import threading
import time

class VideoEditorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Video Editor")
        self.master.geometry("800x700")

        self.video_path = None
        self.cap = None
        self.current_frame = None
        self.total_frames = 0
        self.current_frame_number = 0
        self.is_playing = False
        self.play_thread = None
        self.split_time = None
        self.fps = 0
        self.crop_start = None
        self.crop_end = None

        self.create_widgets()

    def create_widgets(self):
        self.import_button = ctk.CTkButton(self.master, text="Import Video", command=self.import_video)
        self.import_button.pack(pady=10)

        self.video_frame = ctk.CTkFrame(self.master)
        self.video_frame.pack(pady=10)

        self.video_canvas = ctk.CTkCanvas(self.video_frame, width=640, height=480)
        self.video_canvas.pack()

        self.slider_frame = ctk.CTkFrame(self.master)
        self.slider_frame.pack(fill=tk.X, padx=20, pady=10)

        self.slider = ctk.CTkSlider(self.slider_frame, from_=0, to=100, command=self.slider_changed)
        self.slider.pack(fill=tk.X)

        # Fix: Use a CustomTkinter canvas instead of a standard Tkinter canvas
        self.split_canvas = ctk.CTkCanvas(self.slider_frame, height=20, highlightthickness=0)
        self.split_canvas.pack(fill=tk.X)
        self.split_indicator = self.split_canvas.create_rectangle(0, 0, 0, 20, fill="gray", stipple="gray50")

        self.time_label = ctk.CTkLabel(self.master, text="0:00 / 0:00")
        self.time_label.pack(pady=5)

        self.button_frame = ctk.CTkFrame(self.master)
        self.button_frame.pack(pady=10)

        self.play_pause_button = ctk.CTkButton(self.button_frame, text="Play", command=self.toggle_play)
        self.play_pause_button.pack(side=tk.LEFT, padx=5)

        self.split_button = ctk.CTkButton(self.button_frame, text="Split", command=self.split_video)
        self.split_button.pack(side=tk.LEFT, padx=5)

        self.crop_button = ctk.CTkButton(self.button_frame, text="Crop", command=self.toggle_crop_mode)
        self.crop_button.pack(side=tk.LEFT, padx=5)

        self.save_button = ctk.CTkButton(self.button_frame, text="Save", command=self.save_video)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.crop_mode = False

    def import_video(self):
        self.video_path = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4")])
        if self.video_path:
            self.load_video_thread = threading.Thread(target=self.load_video)
            self.load_video_thread.start()

    def load_video(self):
        self.cap = cv2.VideoCapture(self.video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.slider.configure(to=self.total_frames - 1)
        self.master.after(0, self.update_frame, 0)

    def slider_changed(self, value):
        frame_number = int(float(value))
        self.update_frame(frame_number)

    def update_frame(self, frame_number):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.current_frame_number = frame_number
                self.display_frame()
                self.update_time_label()

    def display_frame(self):
        if self.current_frame is not None:
            image = Image.fromarray(self.current_frame)
            image = image.resize((640, 480), Image.LANCZOS)
            if self.crop_start and self.crop_end:
                draw = ImageDraw.Draw(image)
                draw.rectangle([self.crop_start, self.crop_end], outline="red", width=2)
            photo = ImageTk.PhotoImage(image=image)
            self.video_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.video_canvas.image = photo

    def update_time_label(self):
        current_time = self.current_frame_number / self.fps
        total_time = self.total_frames / self.fps
        self.time_label.configure(text=f"{self.format_time(current_time)} / {self.format_time(total_time)}")

    def format_time(self, seconds):
        minutes, seconds = divmod(int(seconds), 60)
        return f"{minutes}:{seconds:02d}"

    def toggle_play(self):
        if self.is_playing:
            self.is_playing = False
            self.play_pause_button.configure(text="Play")
        else:
            self.is_playing = True
            self.play_pause_button.configure(text="Pause")
            if not self.play_thread or not self.play_thread.is_alive():
                self.play_thread = threading.Thread(target=self.play_video)
                self.play_thread.start()

    def play_video(self):
        while self.is_playing and self.current_frame_number < self.total_frames - 1:
            self.current_frame_number += 1
            self.master.after(0, self.slider.set, self.current_frame_number)
            self.master.after(0, self.update_frame, self.current_frame_number)
            time.sleep(1/self.fps)
        self.is_playing = False
        self.play_pause_button.configure(text="Play")

    def split_video(self):
        self.split_time = self.current_frame_number / self.fps
        print(f"Video split at {self.format_time(self.split_time)}")
        self.update_split_indicator()

    def update_split_indicator(self):
        if self.split_time:
            split_position = (self.split_time * self.fps / self.total_frames) * self.split_canvas.winfo_width()
            self.split_canvas.coords(self.split_indicator, split_position, 0, self.split_canvas.winfo_width(), 20)
        else:
            self.split_canvas.coords(self.split_indicator, 0, 0, 0, 0)

    def toggle_crop_mode(self):
        self.crop_mode = not self.crop_mode
        if self.crop_mode:
            self.crop_button.configure(text="Finish Crop")
            self.video_canvas.bind("<Button-1>", self.start_crop)
            self.video_canvas.bind("<B1-Motion>", self.update_crop)
            self.video_canvas.bind("<ButtonRelease-1>", self.end_crop)
        else:
            self.crop_button.configure(text="Crop")
            self.video_canvas.unbind("<Button-1>")
            self.video_canvas.unbind("<B1-Motion>")
            self.video_canvas.unbind("<ButtonRelease-1>")

    def start_crop(self, event):
        self.crop_start = (event.x, event.y)
        self.crop_end = None

    def update_crop(self, event):
        self.crop_end = (event.x, event.y)
        self.display_frame()

    def end_crop(self, event):
        self.crop_end = (event.x, event.y)
        self.display_frame()

    def save_video(self):
        output_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        if not output_path:
            return

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        original_width = int(self.cap.get(3))
        original_height = int(self.cap.get(4))

        if self.crop_start and self.crop_end:
            x1, y1 = self.crop_start
            x2, y2 = self.crop_end
            crop_width = abs(x2 - x1)
            crop_height = abs(y2 - y1)
            top_left_x = min(x1, x2)
            top_left_y = min(y1, y2)
            scale_x = original_width / 640
            scale_y = original_height / 480
            crop_rect = (
                int(top_left_x * scale_x),
                int(top_left_y * scale_y),
                int(crop_width * scale_x),
                int(crop_height * scale_y)
            )
            out = cv2.VideoWriter(output_path, fourcc, self.fps, (crop_rect[2], crop_rect[3]))
        else:
            out = cv2.VideoWriter(output_path, fourcc, self.fps, (original_width, original_height))

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        end_frame = self.total_frames if self.split_time is None else int(self.split_time * self.fps)

        for _ in range(end_frame):
            ret, frame = self.cap.read()
            if not ret:
                break
            if self.crop_start and self.crop_end:
                frame = frame[crop_rect[1]:crop_rect[1]+crop_rect[3], crop_rect[0]:crop_rect[0]+crop_rect[2]]
            out.write(frame)

        out.release()
        print(f"Edited video saved to {output_path}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = VideoEditorApp(root)
    root.mainloop()