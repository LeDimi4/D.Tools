import argparse
import cv2
import numpy as np
import os
import csv
from datetime import timedelta
from tqdm import tqdm

# ---------- Utility functions ----------
def fmt_time(seconds_float):
    if seconds_float is None:
        return "-"
    return str(timedelta(seconds=int(seconds_float)))

def fmt_duration(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s" if m > 0 else f"{s}s"

def draw_roi_window(frame):
    print("Select the rectangular ROI around the wheel. Press ENTER or SPACE to confirm, or C to cancel.")
    clone = frame.copy()
    roi = cv2.selectROI("Select Wheel ROI", clone, fromCenter=False, showCrosshair=True)
    cv2.destroyWindow("Select Wheel ROI")
    x, y, w, h = map(int, roi)
    if w == 0 or h == 0:
        return None
    return (x, y, w, h)

# ---------- Main function ----------
def main():
    parser = argparse.ArgumentParser(description="Analyze hamster wheel time from video using motion detection.")
    parser.add_argument("--video", required=True, help="Path to input video, e.g., hamster.mp4")
    parser.add_argument("--fps_sample", type=float, default=1.0, help="Sampling rate in frames per second (default=1)")
    parser.add_argument("--motion_thresh", type=float, default=0.1, help="Motion sensitivity threshold (lower = more sensitive, default=0.1)")
    parser.add_argument("--min_blob", type=int, default=1, help="Minimum contour size in pixels to count as hamster (default=1)")
    parser.add_argument("--min_streak_sec", type=float, default=1.0, help="Minimum streak length to count as valid, in seconds (default=1.0)")
    parser.add_argument("--preview_out", default="", help="Optional: path to annotated preview video (mp4)")
    parser.add_argument("--csv_out", default="", help="Optional: path to CSV output with timeline")
    parser.add_argument("--summary_out", default="", help="Optional: path to TXT summary output")
    parser.add_argument("--roi", default="", help="Optional: predefined ROI as x,y,w,h")
    args = parser.parse_args()

    # Open video
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"ERROR: Could not open video: {args.video}")
        return

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / max(src_fps, 0.1)

    print(f"Video opened: {args.video}")
    print(f"FPS: {src_fps:.2f}, Total frames: {total_frames}, Duration: {fmt_time(duration_sec)}")

    # Read first frame
    ret, first = cap.read()
    if not ret or first is None:
        print("ERROR: Could not read the first frame of the video.")
        return

    # ROI selection
    if args.roi:
        try:
            x, y, w, h = [int(v) for v in args.roi.split(",")]
            roi_rect = (x, y, w, h)
        except:
            print("ERROR: Invalid --roi format. Use x,y,w,h")
            return
    else:
        roi_rect = draw_roi_window(first)
        if roi_rect is None:
            print("ERROR: ROI was not selected!")
            return
    x, y, w, h = roi_rect
    print(f"Using ROI: x={x}, y={y}, w={w}, h={h}")

    # Preview video writer
    writer = None
    if args.preview_out:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.preview_out, fourcc, args.fps_sample, (first.shape[1], first.shape[0]))

    # Output file paths
    csv_path = args.csv_out or os.path.splitext(args.video)[0] + "_wheel_times.csv"
    txt_path = args.summary_out or os.path.splitext(args.video)[0] + "_summary.txt"

    # Frame sampling step
    step = max(int(round(src_fps / max(args.fps_sample, 0.1))), 1)
    print(f"Processing every {step}-th frame (~{args.fps_sample} fps sampling)")

    backsub = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=8, detectShadows=False)

    prev_gray_roi = None
    timeline = []  # list of (t_sec, in_wheel, motion_score, blob_area)

    frame_idx = 0

    # Progress bar
    with tqdm(total=total_frames, desc="Processing video", unit="frame", ncols=80) as pbar:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            if frame_idx % step != 0:
                frame_idx += 1
                pbar.update(1)
                continue

            t_sec = frame_idx / max(src_fps, 0.1)

            roi = frame[y:y+h, x:x+w]
            if roi.size == 0:
                print("ERROR: ROI out of bounds!")
                break

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)

            # Motion detection
            if prev_gray_roi is None:
                motion_score = 0.0
            else:
                diff = cv2.absdiff(gray, prev_gray_roi)
                motion_score = float(np.median(diff))
            prev_gray_roi = gray

            # Foreground mask
            fgmask = backsub.apply(roi)
            fgmask = cv2.medianBlur(fgmask, 5)
            fgmask = cv2.threshold(fgmask, 127, 255, cv2.THRESH_BINARY)[1]
            fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, np.ones((3,3), np.uint8), iterations=1)
            fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8), iterations=1)

            # Contours
            contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            blob_area = max((cv2.contourArea(c) for c in contours), default=0)

            # Decision: in wheel or not
            in_wheel = bool((motion_score >= args.motion_thresh) and (blob_area >= args.min_blob))
            timeline.append((t_sec, int(in_wheel), motion_score, int(blob_area)))

            # Preview output
            if writer is not None:
                vis = frame.copy()
                cv2.rectangle(vis, (x, y), (x+w, y+h), (0, 255, 0) if in_wheel else (0, 0, 255), 2)
                label = f"t={fmt_time(t_sec)} motion={motion_score:.2f} blob={blob_area} IN_WHEEL={in_wheel}"
                cv2.putText(vis, label, (10, vis.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv2.LINE_AA)
                writer.write(vis)

            frame_idx += 1
            pbar.update(1)

    cap.release()
    if writer is not None:
        writer.release()

    # Group episodes
    episodes = []
    if timeline:
        cur_state = timeline[0][1]
        start_t = timeline[0][0]
        for i in range(1, len(timeline)):
            t, state, _, _ = timeline[i]
            if state != cur_state:
                episodes.append((start_t, t, cur_state))
                start_t = t
                cur_state = state
        episodes.append((start_t, timeline[-1][0], cur_state))

    # Clean short false streaks
    min_len = args.min_streak_sec
    cleaned = []
    for s, e, st in episodes:
        if st == 1 and (e - s) < min_len:
            cleaned.append((s, e, 0))
        else:
            cleaned.append((s, e, st))

    # Total time calculations
    total_in_wheel = sum(e - s for s, e, st in cleaned if st == 1)
    fraction = total_in_wheel / duration_sec if duration_sec > 0 else 0.0

    # Write nicer CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer_csv = csv.writer(f)
        writer_csv.writerow(["start_time", "end_time", "state", "duration"])
        for s, e, st in cleaned:
            writer_csv.writerow([
                fmt_time(s),
                fmt_time(e),
                "IN WHEEL" if st == 1 else "NOT IN WHEEL",
                fmt_duration(e - s)
            ])

    # Write summary
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Video file: {os.path.basename(args.video)}\n")
        f.write(f"Video duration: {fmt_time(duration_sec)} ({duration_sec:.1f} sec)\n")
        f.write(f"Sampling: {args.fps_sample} fps (step={step})\n")
        f.write(f"ROI: x={x}, y={y}, w={w}, h={h}\n")
        f.write(f"Parameters: motion_thresh={args.motion_thresh}, min_blob={args.min_blob}, min_streak_sec={args.min_streak_sec}\n\n")
        f.write(f"Total time in wheel: {fmt_time(total_in_wheel)} ({total_in_wheel:.1f} sec)\n")
        f.write(f"Percentage of time in wheel: {fraction*100:.2f}%\n")

    # Finish message with ASCII hamster
    print("\nProcessing complete! 🐹 Your hamster thanks you!\n")
    print(r"""
(\__/)
(•ㅅ•)   < squeak!
/ 　 づ
""")
    print(f"CSV saved to: {csv_path}")
    print(f"Summary saved to: {txt_path}")
    if args.preview_out:
        print(f"Preview video saved to: {args.preview_out}")
    print(f"Total time in wheel: {fmt_time(total_in_wheel)} ({fraction*100:.2f}%) out of {fmt_time(duration_sec)}")

if __name__ == "__main__":
    main()
