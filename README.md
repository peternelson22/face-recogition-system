# Student Attendance System

A Python-based student attendance system that leverages facial recognition technology to streamline attendance-taking. This project utilizes **OpenCV**, **face_recognition**, and **Flask** for the web interface, with **Redis** as the in-memory database.

---

## Table of Contents
- [Features](#features)
- [Technologies Used](#technologies-used)
- [System Requirements](#system-requirements)
- [Installation](#installation)
  - [Cloning the Repository](#cloning-the-repository)
  - [Installing Redis](#installing-redis)
  - [Starting the Application](#starting-the-application)
- [Running with Docker](#running-with-docker)
- [Manual Redis Installation](#manual-redis-installation)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features
- Facial recognition for identifying and marking student attendance.
- Web interface for easy management using Flask.
- Fast performance with Redis as an in-memory database.
- Flexible setup: supports Docker or manual Redis installation.

## Technologies Used
- **Python**
- **OpenCV** (Computer Vision library)
- **face_recognition** (Python library for face recognition)
- **NumPy** (Numerical operations)
- **Flask** (Web interface)
- **Jinja2** (Wec template engine)
- **Redis** (In-memory database)
- **Docker** (Optional for Redis)

## System Requirements
- **Operating System**: Windows, macOS, or Linux
- **Python**: Version 3.8+
- **Redis**: In-memory database
- **CMake**: Ensure **Desktop development with C++** is installed

> [How to install Desktop development with C++](https://learn.microsoft.com/en-us/cpp/ide/using-the-visual-studio-ide-for-cpp-desktop-development?view=msvc-170) 

---

## Installation
Follow the steps below to set up and run the Student Attendance System:

### Cloning the Repository
First, clone the repository:
```bash
# Clone the repository
git clone https://github.com/peternelson22/face-recogition-system.git
cd face-recogition-system
```

### Installing Dependencies
Install the necessary Python libraries:
```bash
# Install dependencies
pip install -r requirements.txt
```

### Installing Redis
You can either run Redis using Docker (recommended) or install it manually.

---

## Running with Docker
If Docker is installed, you can start Redis using the following steps:
```bash
# Start Redis using Docker Compose
docker-compose up
```

The Docker setup will automatically configure Redis for you.

---

## Manual Redis Installation
If Docker is not available, you can manually install and start Redis:

1. **Download Redis**:
   - Visit the [Redis download page](https://redis.io/download).

2. **Start Redis Server**:
   - On Linux/Mac:
     ```bash
     redis-server
     ```
   - On Windows:
     Use a compatible Redis version for Windows.

Ensure Redis is running before starting the app.

---

## Starting the Application
Once Redis is running, start the application:
```bash
# Start the Flask app
python app.py
```
The application will be accessible at:
```
http://127.0.0.1:5000
```

---

## Usage
1. Open the web interface at `http://127.0.0.1:5000`.
2. Upload student data with images.
3. The system will recognize student faces and mark attendance automatically.

---

## Troubleshooting
- **Redis not running**: Ensure Redis is started either manually or using Docker Compose.
- **CMake Error**: Install **Desktop development with C++**.
- **Port Conflicts**: If port `5000` is in use, change the port in `app.py`.

---

## License
This project is licensed under the MIT License.

---

## Contributions
Contributions are welcome! Feel free to fork the repository and create pull requests.

---


Happy coding!
