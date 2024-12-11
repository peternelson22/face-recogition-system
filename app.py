import os
import cv2
from flask import Flask, render_template, request, flash, redirect, url_for, Response, jsonify
from admin import StudentRegistrationSystem
from main import AttendanceSystem

app = Flask(__name__)
app.secret_key = 'dsvvbklfbmfkbdskgnbksdhttjhryjyjyrejyrjyjyjy'

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

reg_system = StudentRegistrationSystem()
attendance_system = AttendanceSystem()

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """Stream video frames."""
    return Response(
        attendance_system.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/status')
def status():
    """Provide current system status."""
    return jsonify(attendance_system.get_status())


@app.route('/students')
def student():
    """Render the main registration page."""
    students = reg_system.list_all_students()
    return render_template('students.html', students=students)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle student registration."""
    if request.method == 'POST':
        # Check if required fields are present
        if 'name' not in request.form or 'reg_number' not in request.form or 'major' not in request.form:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('register'))

        # Check if file is uploaded
        if 'image' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(url_for('register'))

        file = request.files['image']

        # If no file is selected
        if file.filename == '':
            flash('No selected file.', 'danger')
            return redirect(url_for('register'))

        # If file is valid
        if file and allowed_file(file.filename):
            # Get file extension
            file_ext = os.path.splitext(file.filename)[1]

            # Generate filename using registration number
            reg_number = request.form['reg_number']
            filename = f"{reg_number}{file_ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Save the file
            file.save(filepath)

            # Register student
            result = reg_system.register_student(
                name=request.form['name'].capitalize(),
                reg_number=reg_number.upper(),
                major=request.form['major'],
                image_path=filepath
            )

            if result:
                flash('Student registered successfully!', 'success')
                return redirect(url_for('student'))
            else:
                # Remove the uploaded file if registration fails
                if os.path.exists(filepath):
                    os.remove(filepath)
                flash('Registration failed. Please check the details.', 'danger')
                return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/student/<reg_number>')
def student_detail(reg_number):
    """
    Display detailed information about a student with robust error handling.

    :param reg_number: Student's registration number
    :return: Rendered student detail template or error redirect
    """
    # Validate registration number (optional but recommended)
    if not reg_number or not reg_number.strip():
        flash('Invalid registration number.', 'danger')
        return redirect(url_for('student'))

    # Retrieve student information
    student = reg_system.get_student_info(reg_number)

    if student:
        # Determine image path with multiple fallback options
        image_paths = [
            f'uploads/{reg_number}.jpg',
            f'uploads/{reg_number}.jpeg',
            f'uploads/{reg_number}.png',
            'images/default.png'
        ]

        # Find the first existing image
        image_path = next((path for path in image_paths if os.path.exists(os.path.join('static', path))),
                          'images/default.png')

        return render_template('student_detail.html', student=student, image_path=image_path)
    else:
        flash('Student not found or system error.', 'danger')
        return redirect(url_for('student'))

def main():
    """Main application entry point."""
    try:
        app.run(debug=True, host='0.0.0.0', threaded=True)
    except Exception as e:
        print(f"Application startup error: {e}")
    finally:
        # Cleanup uploads
        if attendance_system.camera:
            attendance_system.camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()