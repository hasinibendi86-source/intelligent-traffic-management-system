"""
vehicle_detection.py
---------------------
A beginner-friendly OpenCV vehicle detection & counting module.

How it works (simple approach, no GPU / deep learning needed):
1. Read the video frame by frame.
2. Use background subtraction (MOG2) to find moving objects.
3. Find contours of the moving blobs and filter by size to
   approximate "vehicles".
4. Count a vehicle each time a blob's center crosses a virtual
   counting line.

This is intentionally simple so it's easy to read and demo. It is
NOT a production-grade detector (it can't tell a car from a bike),
but it demonstrates the full "camera -> detection -> count" pipeline
requested by the project.

If no real video is available, use `simulate_vehicle_count()` from
this module instead — this keeps the OpenCV path clearly separate
from the simulation path, as required.
"""

import random

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:  # pragma: no cover
    OPENCV_AVAILABLE = False


MIN_CONTOUR_AREA = 800  # tune this based on video resolution


def count_vehicles_in_video(video_path, counting_line_y_ratio=0.6, max_frames=None):
    """
    Reads a video file and counts vehicles crossing a horizontal
    counting line using simple background subtraction.

    Returns: {"total_count": int, "frames_processed": int}
    """
    if not OPENCV_AVAILABLE:
        raise RuntimeError(
            "OpenCV (cv2) is not installed. Run: pip install opencv-python-headless"
        )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    back_sub = cv2.createBackgroundSubtractorMOG2(
        history=500, varThreshold=40, detectShadows=True
    )

    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    counting_line_y = int(frame_height * counting_line_y_ratio)

    counted_ids = 0
    tracked_centers = []  # simple list of last-seen y positions
    frames_processed = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frames_processed += 1
        if max_frames and frames_processed > max_frames:
            break

        fg_mask = back_sub.apply(frame)
        _, thresh = cv2.threshold(fg_mask, 244, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:
            if cv2.contourArea(contour) < MIN_CONTOUR_AREA:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            center_y = y + h // 2

            # Very simple crossing check: if the blob center is near
            # the counting line in this frame, count it once.
            near_line = abs(center_y - counting_line_y) < 5
            already_counted = any(abs(center_y - c) < 15 for c in tracked_centers)

            if near_line and not already_counted:
                counted_ids += 1
                tracked_centers.append(center_y)

        # keep the tracked list small
        tracked_centers = tracked_centers[-30:]

    cap.release()
    return {"total_count": counted_ids, "frames_processed": frames_processed}


def simulate_vehicle_count():
    """
    Fallback simulation mode used when no real camera/video is
    available. Clearly separated from the real OpenCV path above.
    """
    cars = random.randint(20, 70)
    bikes = random.randint(10, 45)
    buses = random.randint(1, 8)
    trucks = random.randint(0, 6)
    return {
        "cars": cars,
        "bikes": bikes,
        "buses": buses,
        "trucks": trucks,
        "total_vehicles": cars + bikes + buses + trucks,
        "mode": "simulation",
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python vehicle_detection.py <path_to_video>")
        print("No video path given — running simulated count instead:\n")
        print(simulate_vehicle_count())
    else:
        result = count_vehicles_in_video(sys.argv[1])
        print("Vehicle count result:", result)
