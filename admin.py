import os
import face_recognition
import json
import humanize
from datetime import datetime
from redis_connection import RedisConnectionManager

redis = RedisConnectionManager()

class StudentRegistrationSystem:
    def __init__(self):
        """
        Initialize Redis connection and student registration system.

        """
        self.redis_client = redis.get_redis_client() if redis else None

        if not redis.is_connected():
            print("Failed to connect to Redis")

    def register_student(self, name, reg_number, major, image_path):
        """
        Register a new student with face encoding and metadata.

        :param name: Student's full name
        :param reg_number: Student's registration number
        :param major: Student's academic major
        :param image_path: Path to student's image file
        :return: Boolean indicating successful registration
        """
        if not self.redis_client:
            print("Redis connection not established.")
            return False

        try:
            # Load and encode image
            image = face_recognition.load_image_file(image_path)
            face_encodings = face_recognition.face_encodings(image)

            if not face_encodings:
                print(f"No face found in image for {name}")
                return False

            # Take first face encoding
            face_encoding = face_encodings[0]

            # Prepare student data
            student_data = {
                "name": name,
                "reg_number": reg_number,
                "major": major,
                "last_attendance": "Never",
                "total_attendance": "0",
                "registration_date": datetime.now().isoformat(),
                "face_encoding": json.dumps(face_encoding.tolist())
            }

            # Store student metadata
            student_key = f"student:{reg_number}"
            self.redis_client.hmset(student_key, student_data)

            # Store image in a specific directory with reg_number as filename
            filename = os.path.join(redis.images_path, f"{reg_number}{os.path.splitext(image_path)[1]}")
            os.rename(image_path, filename)

            self.redis_client.publish("data_update", "refresh")

            print(f"Student {name} registered successfully.")
            return True

        except Exception as e:
            print(f"Error registering student: {e}")
            return False

    def get_student_info(self, reg_number):
        """
        Retrieve comprehensive student information from Redis with enhanced error handling.

        :param reg_number: Student's registration number
        :return: Comprehensive dictionary of student information or None
        """
        if not self.redis_client:
            print("Redis connection is not available")
            return None

        try:
            student_key = f"student:{reg_number}"

            # Retrieve all hash fields for the student
            student_data = self.redis_client.hgetall(student_key)

            # If no data found, return None
            if not student_data:
                print(f"No data found for student: {reg_number}")
                return None

            # Parse registration date
            registration_date_str = student_data.get('registration_date')
            try:
                registration_date = datetime.fromisoformat(registration_date_str)
                formatted_registration_date = registration_date.strftime('%d/%m/%Y')
            except (ValueError, TypeError):
                formatted_registration_date = 'N/A'

            # Standardize the student data
            processed_data = {}

            # Map common fields with default values and type conversion
            mapping = {
                'name': lambda x: x.title() if x else 'Unknown Name',
                'major': lambda x: x.title() if x else 'Undeclared',
                'year': lambda x: str(x) if x else 'N/A',
                'last_attendance': lambda x: x if x else 'Never',
                'registration_date': lambda x: x if x else 'N/A',
                'total_attendance': lambda x: int(x) if x and x.isdigit() else 0,
                'face_encoding': lambda x: x
            }

            # Process each field
            for key, processor in mapping.items():
                value = student_data.get(key)
                if value is not None:
                    try:
                        processed_data[key] = processor(value)
                    except Exception as e:
                        print(f"Error processing {key}: {e}")
                        processed_data[key] = 'N/A'

            processed_data['reg_number'] = reg_number
            processed_data['registration_date'] = formatted_registration_date

            # Optional: Add any additional fields from raw data
            for key, value in student_data.items():
                if key not in processed_data:
                    processed_data[key] = value

            return processed_data

        except Exception as e:
            print(f"Comprehensive error retrieving student info for {reg_number}: {e}")
            return None

    def list_all_students(self):
        """
        List registered students with detailed information and pagination support.

        :return: Dictionary containing student details, total count, and pagination info
        """
        if not self.redis_client:
            return {
                "students": [],
            }

        try:
            # Find all student keys
            student_keys = self.redis_client.keys("student:*")

            # Retrieve and process student details for the current page
            students = []
            for key in student_keys:
                # Retrieve full student details
                reg_number = key.split(':')[1]
                student_data = self.redis_client.hgetall(key)

                last_attendance_str = student_data.get('last_attendance')
                try:
                    last_attendance_time = datetime.fromisoformat(last_attendance_str)
                    relative_attendance_time = humanize.naturaltime(last_attendance_time)
                except (ValueError, TypeError):
                    relative_attendance_time = 'Never'

                # Convert byte strings to regular strings
                student = {
                    "reg_number": reg_number,
                    "name": student_data.get('name'),
                    "last_attendance_date": relative_attendance_time
                }

                students.append(student)
            return students

        except Exception as e:
            print(f"Error listing students: {e}")
            return {
                "students": [],
            }

    def update_last_attendance(self, reg_number):
        """
        Update the last attendance timestamp for a student.

        :param reg_number: Student's registration number
        :return: Boolean indicating successful update
        """
        if not self.redis_client:
            return False

        try:
            student_key = f"student:{reg_number}"

            # Update last attendance timestamp
            last_attendance = datetime.now().isoformat()
            current_attendance = int(self.redis_client.hget(student_key, "total_attendance") or 0)
            new_total_attendance = current_attendance + 1

            # Update both last attendance and total attendance
            self.redis_client.hmset(student_key, {
                "last_attendance": last_attendance,
                "total_attendance": str(new_total_attendance)
            })

            print(f"Updated last attendance for student {reg_number}")
            return True

        except Exception as e:
            print(f"Error updating last attendance: {e}")
            return False

    # This is just an additional method in the event multiple students are to be registered at once
    def bulk_register_students(self, json_file_path):
        """
        Bulk register students from a JSON file.

        :param json_file_path: Path to JSON file containing student registration data
        :return: Dictionary with registration results
        """
        if not self.redis_client:
            print("Redis connection not established.")
            return {"success": [], "failed": []}

        try:
            # Read JSON file
            with open(json_file_path, 'r') as file:
                students_data = json.load(file)

            # Results tracking
            registration_results = {
                "success": [],
                "failed": []
            }

            # Process each student
            for student in students_data:
                try:
                    # Validate required fields
                    required_fields = ['name', 'reg_number', 'major', 'image_path']
                    if not all(field in student for field in required_fields):
                        print(f"Missing required fields for student: {student}")
                        registration_results["failed"].append({
                            "student": student,
                            "reason": "Missing required fields"
                        })
                        continue

                    # Attempt registration
                    if self.register_student(
                            name=student['name'],
                            reg_number=student['reg_number'],
                            major=student['major'],
                            image_path=student['image_path']
                    ):
                        registration_results["success"].append(student['reg_number'])
                    else:
                        registration_results["failed"].append({
                            "student": student,
                            "reason": "Registration failed"
                        })

                except Exception as student_error:
                    print(f"Error processing student {student.get('name', 'Unknown')}: {student_error}")
                    registration_results["failed"].append({
                        "student": student,
                        "reason": str(student_error)
                    })

            return registration_results

        except Exception as e:
            print(f"Error in bulk registration: {e}")
            return {"success": [], "failed": []}