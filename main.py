import sys
import cv2
import numpy as np
import numpy.typing as npt


class TagTracker:
    frame: npt.NDArray[np.uint8]

    def __init__(self, video_path: str):
        self.text_opts = ((100, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
        self.object_points = np.array(
            [[0, 0, 0], [70, 0, 0], [0, 50, 0], [70, 50, 0]], dtype=np.float64
        )

    def open_video(self, video_path: str):
        video = cv2.VideoCapture(video_path)
        if not video.isOpened():
            self.message("Could not open video")
            sys.exit(1)

        # Read first frame.
        ok, frame = video.read()

        if not ok:
            self.message("Cannot read video file")
            sys.exit(1)

        return frame

    def run(self):
        while True:
            # Start timer to measure processing time
            timer = cv2.getTickCount()

            # Read a new frame
            ok, self.frame = self.video.read()

            # Break the loop when we reach the end of the video
            if not ok:
                break

            self.process_frame()

            # Exit if ESC pressed
            k = cv2.waitKey(1) & 0xFF
            if k == 27:
                break

            # Calculate Frames per second (FPS)
            fps = cv2.getTickFrequency() / (cv2.getTickCount() - timer)
            self.message(f"FPS : {int(fps)}")
            cv2.imshow("Tracking", self.frame)

    def process_frame(self) -> None:
        # Get Marker Points bounding box
        ok, image_points = self.aruco()

        if not ok:
            return self.message("No ArUco markers detected")

        ok, rotation_vector, translation_vector = self.solve_3d_to_2d_transform(
            image_points
        )

        if not ok:
            return self.message("Failed to Converge")

    def aruco(self):
        # Create the ArUco dictionary
        # (in this part yoy should name all ot the markers that you have used)
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)

        # Creating the ArUco parameters
        aruco_params = cv2.aruco.DetectorParameters()

        # Detecting ArUco markers in the image
        corners, ids, _ = cv2.aruco.detectMarkers(
            self.frame, aruco_dict, parameters=aruco_params
        )

        if ids is None:
            return False, None

        # Draw the detected markers on the frame
        cv2.aruco.drawDetectedMarkers(self.frame, corners, ids)

        # Print the detected marker IDs and their corresponding corners
        image_points = np.zeros(shape=(4, 2))
        # Print the detected marker IDs and their corresponding corners
        for id, corner in zip(ids, corners):
            try:
                image_points[id - 1] = list(corner[0][id - 1][0])
            except:
                print("aruco tag not found")

            # Define the 2D and 3D points for the solvePnP function
            # Modify image_points and object_points accordingly
        return True, np.array(image_points)

    def solve_3d_to_2d_transform(self, image_points: npt.NDArray[np.float64]):
        # Define camera parameters (focal length, center, camera matrix, and distortion coefficients)
        # Modify these parameters according to your camera setup
        size = self.frame.shape
        focal_length = size[1]
        center = (size[1] / 2, size[0] / 2)
        camera_matrix = np.array(
            [
                [focal_length, 0, center[0]],
                [0, focal_length, center[1]],
                [0, 0, 1],
            ],
            dtype="double",
        )

        pnp_solve_method = cv2.SOLVEPNP_IPPE_SQUARE
        dist_coeffs = np.zeros((4, 1))  # Assuming no lens distortion
        return cv2.solvePnP(
            self.object_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        # Project the 3D point (x, y, z) onto the image plane for visualization

        # (box_2d, jacobian) = cv2.projectPoints(box_3d, rotation_vector,
        #                                        translation_vector, camera_matrix, dist_coeffs)
        # print(box_2d)

    def message(self, text: str):
        print(text)
        cv2.putText(self.frame, text, *self.text_opts)


def main():
    tag_tracker = TagTracker(video_path="videos/aruco_vid.mp4")
    tag_tracker.run()


if __name__ == "__main__":
    main()
