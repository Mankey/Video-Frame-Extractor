"""
Video Frame Extractor
--------------------
Extracts EVERY frame from a video into its own image file so an AI skill can
inspect the video frame-by-frame.

Install once:
    pip install opencv-python

Run:
    python video_frame_extractor.py

The script opens file/folder pickers. Frames are saved as:
    output_folder/
        frame_000001.jpg
        frame_000002.jpg
        ...
        frames.csv

The CSV records each frame's number and timestamp.
"""

import csv
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

import cv2


class FrameExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Frame Extractor")
        self.root.geometry("520x245")
        self.root.resizable(False, False)

        self.video_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.status = tk.StringVar(value="Choose a video and an output folder.")
        self.progress_value = tk.DoubleVar(value=0)

        frame = ttk.Frame(root, padding=18)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Video file").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.video_path, width=48).grid(
            row=1, column=0, sticky="ew", pady=(4, 8)
        )
        ttk.Button(frame, text="Browse", command=self.choose_video).grid(
            row=1, column=1, padx=(8, 0), pady=(4, 8)
        )

        ttk.Label(frame, text="Output folder").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.output_path, width=48).grid(
            row=3, column=0, sticky="ew", pady=(4, 8)
        )
        ttk.Button(frame, text="Browse", command=self.choose_output).grid(
            row=3, column=1, padx=(8, 0), pady=(4, 8)
        )

        self.progress = ttk.Progressbar(
            frame, variable=self.progress_value, maximum=100, mode="determinate"
        )
        self.progress.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 5))

        ttk.Label(frame, textvariable=self.status).grid(
            row=5, column=0, columnspan=2, sticky="w"
        )

        self.start_button = ttk.Button(
            frame, text="Extract every frame", command=self.start_extraction
        )
        self.start_button.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        frame.columnconfigure(0, weight=1)

    def choose_video(self):
        path = filedialog.askopenfilename(
            title="Select a video",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.video_path.set(path)
            if not self.output_path.get():
                video = Path(path)
                self.output_path.set(str(video.parent / f"{video.stem}_frames"))

    def choose_output(self):
        path = filedialog.askdirectory(title="Choose where frames should be saved")
        if path:
            self.output_path.set(path)

    def start_extraction(self):
        video = self.video_path.get().strip()
        output = self.output_path.get().strip()

        if not video or not Path(video).is_file():
            messagebox.showerror("Missing video", "Please select a valid video file.")
            return
        if not output:
            messagebox.showerror("Missing folder", "Please choose an output folder.")
            return

        self.start_button.config(state="disabled")
        self.progress_value.set(0)
        self.status.set("Opening video...")
        threading.Thread(
            target=self.extract_frames, args=(video, output), daemon=True
        ).start()

    def extract_frames(self, video_path, output_path):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            self.root.after(0, lambda: self.finish_error("Could not open this video."))
            return

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 0

        csv_path = output_dir / "frames.csv"
        extracted = 0
        failed = False

        try:
            with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["frame_number", "timestamp_seconds", "filename"])

                while True:
                    success, frame = cap.read()
                    if not success:
                        break

                    extracted += 1
                    filename = f"frame_{extracted:06d}.jpg"
                    image_path = output_dir / filename

                    # High-quality JPEG; every decoded source frame is saved.
                    saved = cv2.imwrite(
                        str(image_path),
                        frame,
                        [cv2.IMWRITE_JPEG_QUALITY, 95],
                    )
                    if not saved:
                        failed = True
                        break

                    timestamp = (extracted - 1) / fps if fps else ""
                    writer.writerow([extracted, timestamp, filename])

                    if total_frames > 0 and extracted % 5 == 0:
                        percent = min(100, extracted / total_frames * 100)
                        self.root.after(
                            0, self.update_progress, percent, extracted, total_frames
                        )
                    elif extracted % 100 == 0:
                        self.root.after(
                            0,
                            lambda n=extracted: self.status.set(
                                f"Extracted {n:,} frames..."
                            ),
                        )
        except Exception as exc:
            cap.release()
            self.root.after(0, lambda: self.finish_error(str(exc)))
            return
        finally:
            cap.release()

        if failed:
            self.root.after(
                0,
                lambda: self.finish_error(
                    f"Could not save frame {extracted:,}. Check disk space and folder permissions."
                ),
            )
            return

        self.root.after(
            0, self.finish_success, extracted, str(output_dir), total_frames
        )

    def update_progress(self, percent, current, total):
        self.progress_value.set(percent)
        self.status.set(f"Extracting frame {current:,} of {total:,}...")

    def finish_error(self, error):
        self.start_button.config(state="normal")
        self.status.set("Extraction failed.")
        messagebox.showerror("Extraction failed", error)

    def finish_success(self, count, folder, expected):
        self.progress_value.set(100)
        self.start_button.config(state="normal")
        self.status.set(f"Finished. Saved {count:,} frames.")
        extra = ""
        if expected and count != expected:
            extra = (
                f"\n\nThe video reported {expected:,} frames, but {count:,} "
                "frames were successfully decoded."
            )
        messagebox.showinfo(
            "Extraction complete",
            f"Saved {count:,} frames to:\n{folder}\n\n"
            "A frames.csv index was also created." + extra,
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = FrameExtractorApp(root)
    root.mainloop()
