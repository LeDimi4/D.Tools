import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import subprocess
import os
import threading
import re

def run_pipeline():
    folder = filedialog.askdirectory(title="Select Folder with Videos")
    if not folder:
        return

    # Параметри зі слайдерів
    motion = motion_slider.get()
    blob = blob_slider.get()
    fps = fps_slider.get()
    folder_name = os.path.basename(folder.rstrip("\\/"))
    merged_path = os.path.join(folder, f"{folder_name}.mp4")

    # Створюємо mylist.txt
    list_path = os.path.join(folder, "mylist.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for root_dir, _, files in os.walk(folder):
            for file in sorted(files):
                if file.endswith(".mp4"):
                    full = os.path.join(root_dir, file)
                    f.write(f"file '{full}'\n")

    # Запускаємо в окремому потоці
    thread = threading.Thread(
        target=process_pipeline,
        args=(folder, folder_name, merged_path, motion, blob, fps)
    )
    thread.start()


def process_pipeline(folder, folder_name, merged_path, motion, blob, fps):
    progress_label.config(text="Merging video files...")
    progress_bar["value"] = 0
    progress_bar["maximum"] = 100

    # 1️⃣ Отримуємо тривалість відео (через ffprobe)
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         "-safe", "0", "-f", "concat", "-i", os.path.join(folder, "mylist.txt")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        total_duration = float(result.stdout.strip())
    except:
        total_duration = 0

    # 2️⃣ Реальне злиття з прогресом
    ffmpeg_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", "mylist.txt",
        "-c:v", "copy", "-an", "-progress", "pipe:1", merged_path
    ]

    process = subprocess.Popen(ffmpeg_cmd, cwd=folder,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, universal_newlines=True)

    for line in process.stdout:
        line = line.strip()
        if "out_time_ms=" in line:
            ms = int(re.findall(r"\d+", line)[0])
            current_time = ms / 1_000_000
            if total_duration > 0:
                percent = min((current_time / total_duration) * 100, 100)
                progress_bar["value"] = percent
                progress_label.config(text=f"Merging video files... {percent:.1f}%")
                root.update_idletasks()

    process.wait()

    progress_label.config(text="Analyzing hamster activity...")
    progress_bar["value"] = 0
    root.update_idletasks()

    # 3️⃣ Запуск аналізатора
    py_cmd = [
        "python", "..\\hamster_wheel_analyzer.py",
        "--video", merged_path,
        "--motion_thresh", str(motion),
        "--min_blob", str(blob),
        "--fps_sample", str(fps),
        "--preview_out", f"{folder_name}_preview.mp4"
    ]
    subprocess.run(py_cmd, cwd=folder)

    progress_bar["value"] = 100
    progress_label.config(text="✅ Completed")
    messagebox.showinfo("Done", f"Processing finished:\n{merged_path}")

# --- GUI window ---
root = tk.Tk()
root.title("Hamster Analyzer UI 🐹")
root.geometry("500x400")
root.resizable(False, False)
root.configure(bg="#2b2b2b")

tk.Label(root, text="Motion Threshold", fg="white", bg="#2b2b2b").pack(pady=(10,0))
motion_slider = tk.Scale(root, from_=0.0, to=3.0, resolution=0.1, orient="horizontal", length=380)
motion_slider.set(0.1)
motion_slider.pack()

tk.Label(root, text="Minimum Blob Size", fg="white", bg="#2b2b2b").pack(pady=(10,0))
blob_slider = tk.Scale(root, from_=1, to=500, resolution=1, orient="horizontal", length=380)
blob_slider.set(1)
blob_slider.pack()

tk.Label(root, text="FPS Sampling Rate", fg="white", bg="#2b2b2b").pack(pady=(10,0))
fps_slider = tk.Scale(root, from_=0.5, to=5.0, resolution=0.5, orient="horizontal", length=380)
fps_slider.set(1.0)
fps_slider.pack()

tk.Button(root, text="Run Full Pipeline 🐹", command=run_pipeline, bg="#4caf50", fg="white", width=25).pack(pady=20)
progress_label = tk.Label(root, text="Idle", fg="#cccccc", bg="#2b2b2b")
progress_label.pack()
progress_bar = ttk.Progressbar(root, orient="horizontal", length=380, mode="determinate")
progress_bar.pack(pady=5)

root.mainloop()
