import typing
import sys
import cv2
import numpy as np


def main():
    # Read the video from the specified path
    video = cv2.VideoCapture("videos/aruco_image.mp4")

    # Exit if video not opened.
    if not video.isOpened():
        print("Could not open video")
        sys.exit()

    # Read first frame.
    ok, frame = video.read()

    if not ok:
        print("Cannot read video file")
        sys.exit()

    while True:
        # Read a new frame
        ok, frame = video.read()

        # Break the loop when we reach the end of the video
        if not ok:
            break

        # Start timer to measure processing time
        timer = cv2.getTickCount()

        # Calculate Frames per second (FPS)
        fps = cv2.getTickFrequency() / (cv2.getTickCount() - timer)

        # Draw bounding box
        if ok:
            # Create the ArUco dictionary
            # (in this part yoy should name all ot the markers that you have used)
            aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)

            # Creating the ArUco parameters
            aruco_params = cv2.aruco.DetectorParameters()

            # Detecting ArUco markers in the image
            corners, ids, _ = cv2.aruco.detectMarkers(frame, aruco_dict, parameters=aruco_params)

            if ids is not None:
                # Draw the detected markers on the frame
                cv2.aruco.drawDetectedMarkers(frame, corners, ids)

                # Print the detected marker IDs and their corresponding corners
                image_points = np.zeros(shape=(4, 2))
                # Print the detected marker IDs and their corresponding corners
                for id, corner in zip(ids, corners):
                    try:
                        image_points[id - 1] = list(corner[0][id - 1][0])
                    except:
                        print('aruco tag not found')

                # Define the 2D and 3D points for the solvePnP function
                # Modify image_points and object_points accordingly
                image_points = np.array(image_points)
                object_points = np.array([[0, 0, 0], [70, 0, 0], [0, 50, 0], [70, 50, 0]], dtype=np.float64)

                # Define camera parameters (focal length, center, camera matrix, and distortion coefficients)
                # Modify these parameters according to your camera setup
                size = frame.shape
                focal_length = size[1]
                center = (size[1] / 2, size[0] / 2)
                camera_matrix = np.array(
                    [[focal_length, 0, center[0]],
                     [0, focal_length, center[1]],
                     [0, 0, 1]], dtype="double"
                )

                dist_coeffs = np.zeros((4, 1))  # Assuming no lens distortion
                (success, rotation_vector, translation_vector) = cv2.solvePnP(object_points, image_points,
                                                                              camera_matrix, dist_coeffs,
                                                                              flags=cv2.SOLVEPNP_ITERATIVE)
                if success:
                    pass
                    # TODO

                    # Project the 3D point (x, y, z) onto the image plane for visualization

                    # (box_2d, jacobian) = cv2.projectPoints(box_3d, rotation_vector,
                    #                                        translation_vector, camera_matrix, dist_coeffs)
                    # print(box_2d)
                else:
                    print('Failed to Converge')

                # Show the frame with detected markers
                cv2.imshow("Detected Markers", frame)
            else:
                print("No ArUco markers detected.")
        else:
            # If the tracking failed, display a message on the frame
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

        # # Display the resulting frame with the bounding box and head pose estimation
        cv2.imshow("Tracking", frame)

        # Exit if ESC pressed
        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            break


if __name__ == "__main__":
    main()
