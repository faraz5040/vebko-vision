import typing
import sys
import cv2

TRACKER_TYPE = typing.Literal[
    "BOOSTING",
    "MIL",
    "KCF",
    "TLD",
    "MEDIANFLOW",
    "GOTURN",
    "MOSSE",
    "CSRT",
]


def create_tracker(tracker_type: TRACKER_TYPE) -> cv2.Tracker:
    if tracker_type == "BOOSTING":
        return cv2.TrackerBoosting_create()
    if tracker_type == "MIL":
        return cv2.TrackerMIL_create()
    if tracker_type == "KCF":
        return cv2.TrackerKCF_create()
    if tracker_type == "TLD":
        return cv2.TrackerTLD_create()
    if tracker_type == "MEDIANFLOW":
        return cv2.TrackerMedianFlow_create()
    if tracker_type == "GOTURN":
        return cv2.TrackerGOTURN_create()
    if tracker_type == "MOSSE":
        return cv2.TrackerMOSSE_create()
    if tracker_type == "CSRT":
        return cv2.TrackerCSRT_create()
    raise Exception(f'Unknown tracker type: "{tracker_type}"')


def main():
    tracker_type: TRACKER_TYPE = "KCF"
    tracker = create_tracker(tracker_type)

    # Read video
    video = cv2.VideoCapture("videos/sticker1.mp4")

    # Exit if video not opened.
    if not video.isOpened():
        print("Could not open video")
        sys.exit()

    # Read first frame.
    ok, frame = video.read()
    if not ok:
        print("Cannot read video file")
        sys.exit()

    # Define an initial bounding box
    bbox = (0, 0, 1000, 1000)

    # Uncomment the line below to select a different bounding box
    bbox = cv2.selectROI(frame, False)

    # Initialize tracker with first frame and bounding box
    ok = tracker.init(frame, bbox)

    while True:
        # Read a new frame
        ok, frame = video.read()
        if not ok:
            break

        # Start timer
        timer = cv2.getTickCount()

        # Update tracker
        ok, bbox = tracker.update(frame)

        # Calculate Frames per second (FPS)
        fps = cv2.getTickFrequency() / (cv2.getTickCount() - timer)

        # Draw bounding box
        if ok:
            # Tracking success
            p1 = (int(bbox[0]), int(bbox[1]))
            p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
        else:
            # Tracking failure
            cv2.putText(
                frame,
                "Tracking failure detected",
                (100, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 0, 255),
                2,
            )

        # Display tracker type on frame
        cv2.putText(
            frame,
            tracker_type + " Tracker",
            (100, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (50, 170, 50),
            2,
        )

        # Display FPS on frame
        cv2.putText(
            frame,
            "FPS : " + str(int(fps)),
            (100, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (50, 170, 50),
            2,
        )

        # Display result
        cv2.imshow("Tracking", frame)

        # Exit if ESC pressed
        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            break


if __name__ == "__main__":
    main()
