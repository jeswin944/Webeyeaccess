# 👁️ WebEye Access — Hands-Free Web Accessibility Platform

A Django-based web accessibility platform enabling hands-free computer interaction through **eye tracking**, **gesture control**, and **facial recognition** — designed for users with physical disabilities.

---

## ✨ Features

- **Eye/Head Tracking Mouse Control** — Head movement controls cursor via nose-tip tracking; eye blinks trigger left/right clicks
- **Hand Gesture Recognition** — Index finger cursor control, pinch gestures for clicks, fist for drag-and-drop, open hand for scrolling
- **In-Browser Camera Streaming** — Real-time MJPEG streaming with AI detection overlays
- **System Controls via Gestures** — Volume and brightness adjustment through hand gestures
- **Face Scan Authentication** — Facial recognition-based login
- **Virtual Keyboard** — On-screen keyboard accessible via eye/gesture control
- **Calibration System** — Real-time calibration and tracking visualization
- **Multi-Camera Support** — Auto-detection and selection of multiple cameras
- **Real-Time Telemetry** — FPS, EAR values, active gesture, and cursor position
- **Admin Dashboard** — User management, complaint handling, activity statistics
- **Complaint & Feedback System** — User complaints with admin reply workflow
- **WebEye-Keyboard Chrome Extension** — Browser extension for virtual keyboard integration

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, Django 4.2+ |
| Database | MySQL (`webeye`) |
| Computer Vision | OpenCV, MediaPipe (Face Mesh + Hands) |
| Mouse Automation | PyAutoGUI, Windows API (ctypes) |
| Audio Control | pycaw |
| Display Control | screen-brightness-control |
| Math/Science | SciPy (distance calculations) |
| Streaming | MJPEG via Django StreamingHttpResponse |

---

## 📂 Project Structure

```
Webeyeaccess/
├── manage.py                   # Django management script
├── requirements.txt            # Python dependencies
├── db.sqlite3                  # SQLite database
├── app/
│   ├── views.py                # View controllers
│   ├── models.py               # Database models
│   ├── urls.py                 # URL routing
│   ├── camera_stream.py        # Webcam streaming service
│   ├── finalmousecontroller.py # Eye-tracking mouse controller
│   ├── Gesture_Controller.py   # Hand gesture recognition
│   ├── virtual_keyboard.py     # Virtual keyboard module
│   ├── admin.py                # Admin configuration
│   └── migrations/             # Database migrations
├── templates/                  # Django HTML templates
│   ├── home.html
│   ├── dashboard.html
│   ├── mouse_control.html
│   ├── gesture.html
│   ├── camera.html
│   ├── face_scan.html
│   ├── callibration.html
│   └── ... (20+ templates)
├── Webeyeaccess/               # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── WebEye-Keyboard/            # Chrome Extension
    ├── manifest.json
    ├── content.js
    └── keyboard.css
```

---

## 🚀 Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up the database:**
   ```bash
   python manage.py migrate
   ```

3. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```

4. **Run the server:**
   ```bash
   python manage.py runserver
   ```

5. **Chrome Extension** — Load `WebEye-Keyboard/` as an unpacked extension in Chrome.

