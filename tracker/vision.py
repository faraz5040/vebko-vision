import asyncio
import inspect
import sys
from typing import Any, Callable, Literal
import cv2
import numpy as np
import numpy.typing as npt
from typing import TypedDict
from config import config

is_interactive = __name__ == "__main__"
DEBUG = config["vision_debug"]

Vec3Col = tuple[tuple[float], tuple[float], tuple[float]]
Vec3Row = tuple[float, float, float]


class Vec3(TypedDict):
    x: float
    y: float
    z: float


class TagTracker:
    frame: npt.NDArray[np.uint8]
    video: cv2.VideoCapture
    on_location: Callable[[Vec3Row], Any] | None
    on_frame: Callable[[bytes], Any] | None

    def __init__(self, video_path=config["video_path"]):
        self.on_location = None
        self.on_frame = None
        self._stop = False
        self._loop_thread = None
        self.video_path = video_path
        self.video = None
        self.frame = None
        self.frame_text_count = 0
        self.text_opts = {
            "error": (cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2),
            "success": (cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2),
            "info": (cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 0, 0), 2),
        }
        # Define id and position of real 3D points of fixed ArUco markers used for solving PnP problem
        self.fixed_marker_3d_top_lefts: dict[int, Vec3Row] = {
            1: (0, 0, 0),
            2: (70, 0, 0),
            3: (0, 50, 0),
            4: (70, 50, 0),
        }

        self.moving_tag_id = 5

    def open_video(self):
        video = cv2.VideoCapture(self.video_path)
        if not video.isOpened():
            self.message(f"Could not open video: '{self.video_path}'", exit=True)

        # Read first frame.
        ok, _ = video.read()

        if not ok:
            self.message("Cannot read video file", exit=True)

        self.video = video

    async def start(
        self,
        on_location: Callable[[Vec3Row], Any] | None = None,
        on_frame: Callable[[bytes], Any] | None = None,
    ):
        if self.video is None:
            self.open_video()
        print("cam start")
        self.on_location = on_location
        self.on_frame = on_frame
        self._stop = False
        while not self._stop:
            await self._loop()

    async def _loop(self):
        # Start timer to measure processing time
        start_time = cv2.getTickCount()
        self.frame_text_count = 0

        # Read a new frame
        ok, self.frame = self.video.read()

        # Break the loop when we reach the end of the video
        if not ok:
            self._stop = True
            return

        location = await self.process_frame()

        if callable(self.on_frame):
            ok, jpg = cv2.imencode(".jpg", self.frame)
            if ok:
                ret = self.on_frame({"frame": jpg.tobytes(), "location": location})
                if inspect.isawaitable(ret):
                    await ret
            else:
                self.message("Failed to encode frame as JPEG")

        if is_interactive:
            # Exit if ESC pressed
            k = cv2.waitKey(1) & 0xFF
            if k == 27:
                self._stop = True
                return

        # Calculate Frames per second (FPS)
        end_time = cv2.getTickCount()
        ticks_past = end_time - start_time
        fps = cv2.getTickFrequency() / ticks_past
        self.message(f"FPS : {int(fps)}", type="success")
        if is_interactive:
            cv2.imshow("Tracking", self.frame)

    def stop(self):
        self._stop = True
        if self.video is not None:
            self.video.release()

    async def process_frame(self) -> Vec3 | None:
        # Get Marker Points bounding box
        ok, marker_corners = self.aruco()

        if not ok:
            return self.message("No ArUco markers detected")

        await asyncio.sleep(0)

        moving_tag_image_point = next(
            (
                image_point
                for id, image_point in marker_corners.items()
                if id == self.moving_tag_id
            ),
            None,
        )

        # Pair up image and object points of same markers using id
        fixed_image_object_point_pairs = tuple(
            (image_point, self.fixed_marker_3d_top_lefts[id])
            for id, image_point in marker_corners.items()
            if id in self.fixed_marker_3d_top_lefts
        )

        if len(fixed_image_object_point_pairs) < 4 or moving_tag_image_point is None:
            self.message("Cant detect required markers")
            return

        ok, rotation_vector, translation_vector = self.solve_3d_to_2d_transform(
            object_points=np.array(
                [object_point for _, object_point in fixed_image_object_point_pairs],
                dtype=np.float32,
            ),
            image_points=np.array(
                [image_point for image_point, _ in fixed_image_object_point_pairs],
                dtype=np.float32,
            ),
        )

        if not ok:
            return self.message("Failed to Converge")

        await asyncio.sleep(0)

        ok, moving_tag_object_point = self.calc_3d_point_from_image(
            rotation_vector, translation_vector, moving_tag_image_point, z=0
        )

        if not ok:
            return self.message("Error calculating moving tag object point")

        await asyncio.sleep(0)

        self.message(f"Location of moving tag {moving_tag_object_point}", type="info")

        x, y, z = moving_tag_object_point
        return Vec3(x=x, y=y, z=z)

    def aruco(self):
        # Create the ArUco dictionary
        # (in this part yoy should name all ot the markers that you have used)
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)

        # Creating the ArUco parameters
        aruco_params = cv2.aruco.DetectorParameters()

        # Detecting ArUco markers in the image
        corners, idMat, _ = cv2.aruco.detectMarkers(
            self.frame, aruco_dict, parameters=aruco_params
        )

        if idMat is None:
            return False, None

        # Draw the detected markers on the frame
        cv2.aruco.drawDetectedMarkers(self.frame, corners, idMat)

        ids = idMat.flatten()
        # Image points of detected marker top left corners
        marker_image_top_lefts: dict[int, tuple[float, float]] = {
            id: corner.reshape((4, 2))[0] for id, corner in zip(ids, corners)
        }

        return True, marker_image_top_lefts

    def solve_3d_to_2d_transform(
        self,
        object_points: npt.NDArray[np.float64],
        image_points: npt.NDArray[np.float64],
    ) -> tuple[Literal[True], Vec3Col, Vec3Col] | tuple[Literal[False], None, None]:
        camera_matrix = self.calc_camera_matrix()

        # pnp_solve_method = cv2.SOLVEPNP_IPPE_SQUARE
        pnp_solve_method = cv2.SOLVEPNP_ITERATIVE
        dist_coeffs = np.zeros((4, 1))  # Assuming no lens distortion

        try:
            return cv2.solvePnP(
                object_points,
                image_points,
                camera_matrix,
                dist_coeffs,
                # useExtrinsicGuess=True,
                flags=pnp_solve_method,
            )
        except cv2.error:
            return False, None, None

    def calc_camera_matrix(self):
        # Define camera parameters (focal length, center, camera matrix, and distortion coefficients)
        # Modify these parameters according to your camera setup
        size = self.frame.shape
        focal_length = size[1]
        center = (size[1] / 2, size[0] / 2)
        return np.array(
            [
                [focal_length, 0, center[0]],
                [0, focal_length, center[1]],
                [0, 0, 1],
            ],
            dtype="double",
        )

    def calc_3d_point_from_image(
        self, rotation_vector, translation_vector, image_point: tuple[float, float], z=0
    ):
        # ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
        #     objpoints,
        #     imgpoints,
        #     gray.shape[::-1],
        #     None,
        #     np.zeros(5, "float32"),
        #     flags=cv2.CALIB_USE_INTRINSIC_GUESS,
        # )
        # Calculate the camera transformation matrix
        camera_matrix = self.calc_camera_matrix()
        lcam = camera_matrix.dot(
            np.hstack((cv2.Rodrigues(rotation_vector)[0], translation_vector))
        )
        try:
            px, py = image_point
            # Calculate the tag's location in 3D space
            tag_loc: Vec3Row = np.linalg.inv(
                np.hstack((lcam[:, 0:2], np.array([[-1 * px], [-1 * py], [-1]])))
            ).dot((-z * lcam[:, 2] - lcam[:, 3]))
            return True, tag_loc
        except:
            return False, None

    def message(self, text: str, type="error", exit=False):
        if DEBUG:
            print(text)
        if self.frame is not None:
            self.frame_text_count += 1
            position = (100, 80 * self.frame_text_count)
            cv2.putText(self.frame, text, position, *self.text_opts[type])
        if exit:
            if is_interactive:
                sys.exit(1)
            else:
                raise Exception(text)


if is_interactive:
    tag_tracker = TagTracker()
    asyncio.run(tag_tracker.start())
