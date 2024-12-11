import os
import time
import threading
import numpy as np
import cv2
import face_recognition
import json
from datetime import datetime, timedelta
from redis_connection import RedisConnectionManager

redis = RedisConnectionManager()

class AttendanceSystem:
    def __init__(self, resize_scale=0.5, tolerance=0.5, detection_cooldown=3, attendance_cooldown_hours=24):
        """
        Advanced attendance system with Redis as database.

        :param resize_scale: Scale factor for image resizing (lower = faster processing)
        :param tolerance: Face matching tolerance (lower = stricter matching)
        :param detection_cooldown: Minimum time between user detections
        """
        self.redis_client = redis.get_redis_client() if redis else None

        if not redis.is_connected():
            print("Failed to connect to Redis")

        self.stored_images_path = redis.images_path
        self.resize_scale = resize_scale
        self.tolerance = tolerance
        self.detection_cooldown = detection_cooldown
        self.attendance_cooldown_hours = attendance_cooldown_hours

        # Thread-safe status and user tracking
        self.status_lock = threading.Lock()
        self.current_status = "Initializing"
        self.current_user = {
            "name": "N/A",
            "id": "N/A",
            "status": "Inactive",
            "details_shown_time": 0
        }
        self.last_detection_time = 0

        # Camera and face recognition setup
        self.camera = None
        self.known_faces = {}

        self._load_known_faces()
        self._init_camera()

    def _init_camera(self):
        """
        Initialize the camera with comprehensive error handling.
        Attempts multiple camera indices and sets optimal resolution.
        """
        camera_indices = [0, 1, 2]  # Try different camera indices
        for index in camera_indices:
            try:
                self.camera = cv2.VideoCapture(index)

                # Set camera properties for optimal performance
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

                if not self.camera.isOpened():
                    raise IOError(f"Cannot open camera at index {index}")

                self._update_status(f"Camera initialized at index {index}")
                return
            except Exception as e:
                print(f"Camera initialization error at index {index}: {e}")

        self._update_status("Camera Initialization Failed")
        self.camera = None

    def generate_frames(self):
        """
        Generate video frames with optimized face recognition.
        """
        if not self.camera:
            return

        while True:
            try:
                success, frame = self.camera.read()
                if not success:
                    break

                # Resize frame for faster processing
                small_frame = cv2.resize(frame, (0, 0),
                                         fx=self.resize_scale,
                                         fy=self.resize_scale)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                # Process each detected face
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    # Scale face locations back to original frame size
                    top = int(top / self.resize_scale)
                    right = int(right / self.resize_scale)
                    bottom = int(bottom / self.resize_scale)
                    left = int(left / self.resize_scale)

                    # Compare with known faces
                    matches = face_recognition.compare_faces(
                        list(self.known_faces.values()),
                        face_encoding,
                        tolerance=self.tolerance
                    )

                    name = "Unknown"
                    if True in matches:
                        matched_index = matches.index(True)
                        name = list(self.known_faces.keys())[matched_index]
                        self._update_current_user(name)

                    # Draw face rectangle and name
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                    cv2.putText(frame, name, (left, top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

                # Encode frame
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    continue

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

            except Exception as e:
                print(f"Frame generation error: {e}")
                break


    def _update_status(self, new_status):
        """
        Thread-safe method to update system status.

        :param new_status: New status string
        """
        with self.status_lock:
            self.current_status = new_status

    def _can_mark_attendance(self, reg_number):
        """
        Check if student can mark attendance based on 24-hour cooldown.

        :param reg_number: Student's registration number
        :return: Tuple (can_mark, message)
        """
        if not self.redis_client:
            return False, "System error"

        try:
            student_key = f"student:{reg_number}"
            last_attendance = self.redis_client.hget(student_key, "last_attendance")

            if not last_attendance or last_attendance == "Never":
                return True, "First time attendance"

            # Parse last attendance time
            last_attendance_time = datetime.fromisoformat(last_attendance)
            current_time = datetime.now()
            time_since_last_attendance = current_time - last_attendance_time

            # Check if 24 hours have passed
            if time_since_last_attendance >= timedelta(hours=self.attendance_cooldown_hours):
                return True, "Ready to mark"
            else:
                hours_remaining = self.attendance_cooldown_hours - time_since_last_attendance.total_seconds() / 3600
                return False, f"Already marked. Wait {hours_remaining:.1f} hours"

        except Exception as e:
            print(f"Error checking attendance eligibility: {e}")
            return False, "Check failed"

    def _load_known_faces(self):
        """
        Load known faces from the stored images path and retrieve student info from Redis.
        """
        # Ensure images directory exists
        os.makedirs(self.stored_images_path, exist_ok=True)

        supported_extensions = ['.jpg', '.jpeg', '.png', '.bmp']

        try:
            for filename in os.listdir(self.stored_images_path):
                # Check file extension
                if any(filename.lower().endswith(ext) for ext in supported_extensions):
                    filepath = os.path.join(self.stored_images_path, filename)

                    try:
                        # Extract registration number from filename
                        reg_number = os.path.splitext(filename)[0]

                        image = face_recognition.load_image_file(filepath)

                        # Resize for faster processing
                        small_image = cv2.resize(image, (0, 0),
                                                 fx=self.resize_scale,
                                                 fy=self.resize_scale)

                        # Encode faces
                        encodings = face_recognition.face_encodings(small_image)

                        if encodings:
                            student_info = self._get_student_info(reg_number)
                            if student_info:
                                # Use first face encoding if multiple found
                                name = f"{student_info.get('name', reg_number)} ({reg_number})"
                                face_encoding = np.array(json.loads(student_info.get('face_encoding')))
                                self.known_faces[name] = face_encoding
                            else:
                                print(f"No student found for {reg_number}")

                        else:
                            print(f"No face found in {filename}")

                    except Exception as img_error:
                        print(f"Error processing {filename}: {img_error}")

            self._update_status(f"Loaded {len(self.known_faces)} known faces")

        except Exception as e:
            print(f"Error loading known faces: {e}")
            self._update_status("Face Loading Error")

    def _get_student_info(self, reg_number):
        """
        Retrieve student information from Redis.

        :param reg_number: Student's registration number
        :return: Dictionary of student information or None
        """
        if not self.redis_client:
            return None

        try:
            student_key = f"student:{reg_number}"
            student_data = self.redis_client.hgetall(student_key)

            return student_data if student_data else None

        except Exception as e:
            print(f"Error retrieving student info: {e}")
            return None

    def _update_attendance(self, reg_number):
        """
        Update student attendance in Redis.

        :param reg_number: Student's registration number
        :return: Boolean indicating successful update
        """
        if not self.redis_client:
            return False

        try:
            student_key = f"student:{reg_number}"

            # Update last attendance timestamp
            last_attendance = time.strftime("%Y-%m-%d %H:%M:%S")

            # Use hincrby to atomically increment the total_attendance
            total_attendance = self.redis_client.hincrby(student_key, "total_attendance", 1)

            # Set last attendance timestamp
            self.redis_client.hset(student_key, "last_attendance", last_attendance)

            print(f"Updated last attendance and total attendance for student {reg_number}")
            print(f"Total attendance for {reg_number}: {total_attendance}")

            return True

        except Exception as e:
            print(f"Error updating last attendance: {e}")
            return False

    def _update_current_user(self, name):
        """
        Update current user with enhanced attendance tracking.

        :param name: Detected user name
        """
        current_time = time.time()

        # Implement detection cooldown
        if current_time - self.last_detection_time > self.detection_cooldown:
            with self.status_lock:
                # Extract registration number from name
                reg_number = name.split('(')[-1].strip(')')

                student_info = self._get_student_info(reg_number)

                if student_info:
                    # Check attendance eligibility
                    can_mark, message = self._can_mark_attendance(reg_number)

                    if can_mark:
                        # Update attendance
                        self._update_attendance(reg_number)

                        # Set current user status with details display time
                        self.current_user = {
                            "name": student_info.get('name', 'Unknown'),
                            "id": reg_number,
                            "status": "Active",
                            "major": student_info.get('major', 'N/A'),
                            "details_shown_time": current_time,
                            "attendance_message": "Attendance Marked"
                        }
                    else:
                        # Cannot mark attendance
                        self.current_user = {
                            "name": student_info.get('name', 'Unknown'),
                            "id": reg_number,
                            "status": "Restricted",
                            "major": student_info.get('major', 'N/A'),
                            "details_shown_time": current_time,
                            "attendance_message": message
                        }

                    self.last_detection_time = current_time
                    self.current_status = f"Active: {self.current_user['name']}"
                else:
                    # Fallback if no student info found
                    self.current_user = {
                        "name": name,
                        "id": "Unknown",
                        "status": "Unregistered",
                        "details_shown_time": current_time
                    }
                    self.current_status = "Unregistered User Detected"

    def get_status(self):
        """
        Retrieve current status and user information.

        :return: Dictionary with status and user details
        """
        with self.status_lock:
            current_time = time.time()

            # Check if details display time has expired
            if (self.current_user.get('details_shown_time', 0) > 0 and
                    current_time - self.current_user['details_shown_time'] > 3):
                # Reset to initial state after 3 seconds
                self.current_user = {
                    "name": "N/A",
                    "id": "N/A",
                    "status": "Inactive",
                    "details_shown_time": 0
                }
                self.current_status = "Ready for Next Student"

            attendance_info = self._get_last_attendance(self.current_user.get('id', 'N/A'))

            return {
                "status": self.current_status,
                "user": {
                    "name": self.current_user.get('name', 'Unknown'),
                    "id": self.current_user.get('id', 'N/A'),
                    "status": self.current_user.get('status', 'Inactive'),
                    "major": self.current_user.get('major', 'N/A'),
                    "last_attendance": attendance_info['last_attendance'],
                    "total_attendance": attendance_info['total_attendance'],
                    "attendance_message": self.current_user.get('attendance_message', '')
                }
            }
    def _get_last_attendance(self, reg_number):
        """
        Retrieve last attendance date and total attendance for a student.

        :param reg_number: Student's registration number
        :return: Dictionary with last attendance and total attendance
        """
        if not self.redis_client:
            return {'last_attendance': 'Unable to retrieve', 'total_attendance': 0}

        try:
            student_key = f"student:{reg_number}"
            last_attendance = self.redis_client.hget(student_key, "last_attendance") or 'Never'
            total_attendance = int(self.redis_client.hget(student_key, "total_attendance") or 0)

            return {
                'last_attendance': last_attendance,
                'total_attendance': total_attendance
            }
        except Exception as e:
            print(f"Error retrieving attendance info: {e}")
            return {'last_attendance': 'Unable to retrieve', 'total_attendance': 0}
