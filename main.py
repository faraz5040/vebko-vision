import typing
import sys
import cv2
import numpy as np

def main():
    # Read the video from the specified path
    video = cv2.VideoCapture(1)

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
            aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)

            # Creating the ArUco parameters
            aruco_params = cv2.aruco.DetectorParameters()

            # Detect ArUco markers in the image and return their corners and IDs
            corners, ids, _ = cv2.aruco.detectMarkers(frame, aruco_dict, parameters=aruco_params)

            if ids is not None:
                # Draw the detected markers on the frame
                cv2.aruco.drawDetectedMarkers(frame, corners, ids)

                # Define image points and object points for camera calibration
                """
                this is dynamic image points which will be detected in the video with AruCo Markers
                we have 4 points in the image, also its respective points in the room (real-world) that is called 
                object points

                """
                image_points = np.zeros(shape=(4, 2))
                object_points = np.array([[0, 0, 0], [70, 0, 0], [70, 50, 0], [0, 50, 0]], dtype=np.float64)

                tag = None
                for id, corner in zip(ids, corners):
                    # Check if the ID is the Tag (ID 5)
                    if id == [5]:
                        tag = list(corner[0][0])
                    else:
                        try:
                            # Store image points for non-tag markers
                            image_points[id - 1] = list(corner[0][0])
                        except:
                            print(f'aruco tag {id} not found')

                # Setup the Camera Matrix
                size = frame.shape
                focal_length = size[1]
                center = (size[1] / 2, size[0] / 2)
                camera_matrix = np.array(
                    [[focal_length, 0, center[0]],
                     [0, focal_length, center[1]],
                     [0, 0, 1]], dtype="double"
                )

                image_points = np.array(image_points)
                dist_coeffs = np.zeros((4, 1))  # Assuming no lens distortion

                # Solve for rotation and translation vectors using PnP
                (success, rotation_vector, translation_vector) = cv2.solvePnP(object_points, image_points,
                                                                              camera_matrix, dist_coeffs,
                                                                              flags=cv2.SOLVEPNP_ITERATIVE)

                # Calculate the camera transformation matrix
                Lcam = camera_matrix.dot(np.hstack((cv2.Rodrigues(rotation_vector)[0], translation_vector)))

                try:
                    px, py = tag[0], tag[1]
                    Z = 0
                    # Calculate the tag's location in 3D space
                    tag_loc = np.linalg.inv(np.hstack((Lcam[:, 0:2], np.array([[-1 * px], [-1 * py], [-1]])))).dot(
                        (-Z * Lcam[:, 2] - Lcam[:, 3]))
                    print("location of tag", tag_loc)
                except:
                    print("Tag not Found..")

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

        # Display the resulting frame with the bounding box and head pose estimation
        cv2.imshow("Tracking", frame)

        # Exit if ESC key is pressed
        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            break

if __name__ == "__main__":
    main()
