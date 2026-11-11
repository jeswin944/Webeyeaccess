import cv2
import time
import math
import threading
import ctypes
import pyautogui
import numpy as np
from scipy.spatial import distance as dist

# Protobuf / MediaPipe compatibility bridge for protobuf 5+/7+
try:
    import google._upb._message
    if not hasattr(google._upb._message.FieldDescriptor, 'label'):
        google._upb._message.FieldDescriptor.label = property(
            lambda self: 3 if getattr(self, 'is_repeated', False) else (2 if getattr(self, 'is_required', False) else 1)
        )
except Exception:
    pass

try:
    from google.protobuf import symbol_database, message_factory
    if not hasattr(symbol_database.SymbolDatabase, 'GetPrototype'):
        symbol_database.SymbolDatabase.GetPrototype = lambda self, descriptor: message_factory.GetMessageClass(descriptor)
    if not hasattr(message_factory.MessageFactory, 'GetPrototype'):
        message_factory.MessageFactory.GetPrototype = lambda self, descriptor: message_factory.GetMessageClass(descriptor)
except Exception:
    pass

import mediapipe as mp

# Windows System Controls (Audio & Brightness)
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume_control = cast(interface, POINTER(IAudioEndpointVolume))
except Exception:
    volume_control = None

try:
    import screen_brightness_control as sbcontrol
except Exception:
    sbcontrol = None

# Configure PyAutoGUI for zero-latency execution
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False
screen_w, screen_h = pyautogui.size()


# -------------------------------------------------------------
# High-Performance Direct Windows Cursor Control (0ms delay)
# -------------------------------------------------------------
def win_set_cursor_pos(x, y):
    """Direct Windows API cursor position - instant and 0ms latency."""
    clamped_x = max(0, min(screen_w - 1, int(x)))
    clamped_y = max(0, min(screen_h - 1, int(y)))
    try:
        ctypes.windll.user32.SetCursorPos(clamped_x, clamped_y)
    except Exception:
        pyautogui.moveTo(clamped_x, clamped_y)

def win_mouse_click(button='left'):
    """Direct Windows API mouse click with zero PyAutoGUI overhead."""
    try:
        if button == 'left':
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
        elif button == 'right':
            ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
            ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
    except Exception:
        pyautogui.click(button=button)

def win_mouse_down():
    try:
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
    except Exception:
        pyautogui.mouseDown()

def win_mouse_up():
    try:
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
    except Exception:
        pyautogui.mouseUp()

def win_mouse_scroll(amount):
    try:
        # 120 is standard WHEEL_DELTA in Windows API
        clicks = int(amount * 120)
        ctypes.windll.user32.mouse_event(0x0800, 0, 0, clicks, 0)  # MOUSEEVENTF_WHEEL
    except Exception:
        pyautogui.scroll(int(amount))


class CameraStreamManager:
    """
    Singleton Manager for camera access, MediaPipe processing,
    virtual mouse control, and real-time MJPEG in-browser streaming.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CameraStreamManager, cls).__new__(cls)
                cls._instance._init_manager()
            return cls._instance

    def _init_manager(self):
        self.active_stream_id = 0
        self.stream_lock = threading.Lock()
        self.is_streaming = False
        self.current_mode = "preview"
        self.current_cam_index = 0
        self.mouse_enabled = True
        self.recalibrate_flag = False

        # Telemetry
        self.telemetry = {
            "fps": 0,
            "face_detected": False,
            "hand_detected": False,
            "left_ear": 0.0,
            "right_ear": 0.0,
            "active_gesture": "None",
            "finger_count": 0,
            "last_action": "Ready",
            "cam_index": 0,
            "mode": "preview",
            "mouse_enabled": True,
            "cursor_x": screen_w // 2,
            "cursor_y": screen_h // 2,
            "click_event": None,
            "screen_w": screen_w,
            "screen_h": screen_h
        }


        # MediaPipe Solutions
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # Landmark Indices for Eyes & Nose
        self.LEFT_EYE = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE = [362, 385, 387, 263, 373, 380]
        self.NOSE_TIP = 1
        self.EAR_THRESHOLD = 0.21
        self.BLINK_CONSEC_FRAMES = 2

    def set_mouse_enabled(self, enabled: bool):
        """Allows enabling/disabling system mouse control instantly on the fly."""
        self.mouse_enabled = bool(enabled)
        self.telemetry["mouse_enabled"] = self.mouse_enabled
        if not self.mouse_enabled:
            win_mouse_up()
        print(f"[CameraStream] System mouse control set to: {self.mouse_enabled}")

    def recalibrate_neutral(self):
        """Triggers recalibration of neutral center point for eye/head tracking."""
        self.recalibrate_flag = True
        print("[CameraStream] Neutral center recalibration requested.")

    def open_camera(self, cam_index=0):
        """Opens camera using DSHOW on Windows for fast non-blocking startup."""
        cam_idx = int(cam_index)
        cap = None
        # Try DirectShow first on Windows
        try:
            cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                cap = None
        except Exception:
            cap = None

        # Fallback to standard capture
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(cam_idx)

        # Fallback to camera 0 if chosen index failed
        if not cap.isOpened() and cam_idx != 0:
            print(f"[CameraStream] Camera {cam_idx} failed, falling back to 0")
            try:
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap.release()
                    cap = cv2.VideoCapture(0)
            except Exception:
                cap = cv2.VideoCapture(0)

        if cap is not None and cap.isOpened():
            # Optimize capture resolution and buffer
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        return cap

    def eye_aspect_ratio(self, eye_landmarks):
        """Compute Eye Aspect Ratio (EAR) for blink detection."""
        p1 = (eye_landmarks[1].x, eye_landmarks[1].y)
        p5 = (eye_landmarks[5].x, eye_landmarks[5].y)
        p2 = (eye_landmarks[2].x, eye_landmarks[2].y)
        p4 = (eye_landmarks[4].x, eye_landmarks[4].y)
        p0 = (eye_landmarks[0].x, eye_landmarks[0].y)
        p3 = (eye_landmarks[3].x, eye_landmarks[3].y)

        A = dist.euclidean(p1, p5)
        B = dist.euclidean(p2, p4)
        C = dist.euclidean(p0, p3)

        if C == 0:
            return 0.3
        return (A + B) / (2.0 * C)

    def get_finger_status(self, landmarks):
        """
        Check which fingers are extended: (thumb, index, middle, ring, pinky).
        Robust against left vs right hand orientation.
        """
        tips = [4, 8, 12, 16, 20]
        pips = [3, 6, 10, 14, 18]
        mcps = [2, 5, 9, 13, 17]
        fingers = []

        # Thumb: check distance between thumb tip (4) and index MCP (5)
        thumb_tip = landmarks[tips[0]]
        index_mcp = landmarks[mcps[1]]
        thumb_spread = math.sqrt((thumb_tip.x - index_mcp.x)**2 + (thumb_tip.y - index_mcp.y)**2)
        # If thumb tip is extended away from palm
        fingers.append(thumb_spread > 0.08)

        # Other 4 fingers (vertical extension relative to PIP joint in upright hand)
        for i in range(1, 5):
            if landmarks[tips[i]].y < landmarks[pips[i]].y:
                fingers.append(True)
            else:
                fingers.append(False)

        return tuple(fingers)

    def get_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def set_system_volume(self, level):
        if volume_control:
            try:
                level = max(0.0, min(1.0, level))
                volume_control.SetMasterVolumeLevelScalar(level, None)
            except Exception:
                pass

    def set_system_brightness(self, level):
        if sbcontrol:
            try:
                level = max(0, min(100, int(level)))
                sbcontrol.set_brightness(level)
            except Exception:
                pass

    def stop_stream(self):
        """Signals active stream generator to stop and release camera."""
        with self.stream_lock:
            self.active_stream_id += 1
            self.is_streaming = False
            self.telemetry["last_action"] = "Stopped"
            if hasattr(self, 'active_cap') and self.active_cap is not None:
                try:
                    self.active_cap.release()
                except Exception:
                    pass
                self.active_cap = None

    def get_telemetry(self):
        return self.telemetry

    def draw_virtual_cursor_hud(self, frame, cursor_x, cursor_y, is_clicking=False, click_type="none"):
        """
        Draws clear status of real laptop mouse position on camera frame.
        """
        h, w, _ = frame.shape
        status_text = f"REAL LAPTOP CURSOR: X={int(cursor_x)} Y={int(cursor_y)}"
        bg_color = (0, 160, 60) if self.mouse_enabled else (50, 50, 60)
        cv2.rectangle(frame, (w - 310, h - 35), (w - 15, h - 10), bg_color, -1)
        cv2.putText(frame, status_text, (w - 300, h - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1)

    def generate_frames(self, mode="preview", cam_index=0, enable_mouse=True):
        """
        Main generator that reads frames, runs AI detection, renders overlays,
        handles virtual mouse actions, and yields MJPEG HTTP byte chunks.
        """
        with self.stream_lock:
            if hasattr(self, 'active_cap') and self.active_cap is not None:
                try:
                    self.active_cap.release()
                except Exception:
                    pass
                self.active_cap = None
                time.sleep(0.1)

            self.active_stream_id += 1
            current_id = self.active_stream_id
            self.is_streaming = True
            self.current_mode = mode
            self.current_cam_index = cam_index
            self.mouse_enabled = enable_mouse
            self.recalibrate_flag = False


        self.telemetry.update({
            "mode": mode,
            "cam_index": cam_index,
            "mouse_enabled": enable_mouse,
            "last_action": f"Started {mode.upper()}"
        })

        cap = self.open_camera(cam_index)
        self.active_cap = cap
        if cap is None or not cap.isOpened():
            print(f"[CameraStream] Could not open camera {cam_index}")
            err_img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(err_img, f"Camera {cam_index} not accessible", (70, 230),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            cv2.putText(err_img, "Please check permissions or select another camera.", (40, 270),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            _, buffer = cv2.imencode('.jpg', err_img)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            self.is_streaming = False
            return

        # State tracking variables
        neutral_x, neutral_y = None, None
        prev_x, prev_y = screen_w // 2, screen_h // 2
        alpha_eye = 0.28   # Smoothing for head tracking
        alpha_hand = 0.35  # Smoothing for hand tracking
        left_blink_counter = 0
        right_blink_counter = 0
        click_cooldown = 0
        gesture_cooldown = 0

        # Hand tracking state
        prev_hand_pos = None
        is_dragging = False
        prev_wrist_y = None

        # Visual action display variables
        action_msg = ""
        action_timer = 0
        action_color = (0, 255, 0)
        current_cursor_x = screen_w // 2
        current_cursor_y = screen_h // 2
        frame_is_clicking = False
        frame_click_type = "none"

        # Frame rate calculation
        fps_timer = time.time()
        frame_counter = 0
        current_fps = 0

        # MediaPipe models
        face_mesh = None
        hands = None

        if mode == "eye":
            face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6
            )
        elif mode == "hand":
            hands = self.mp_hands.Hands(
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7
            )

        try:
            while True:
                # Check if stream was cancelled
                if current_id != self.active_stream_id or not self.is_streaming:
                    break

                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                # Mirror frame for natural intuitive self-view
                frame = cv2.flip(frame, 1)
                h, w, _ = frame.shape

                # Calculate FPS
                frame_counter += 1
                now = time.time()
                if now - fps_timer >= 1.0:
                    current_fps = int(frame_counter / (now - fps_timer))
                    frame_counter = 0
                    fps_timer = now
                    self.telemetry["fps"] = current_fps

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_is_clicking = False
                frame_click_type = "none"

                # Decrement action visual timer
                if action_timer > 0:
                    action_timer -= 1
                else:
                    action_msg = ""

                # Check manual center recalibration request
                if self.recalibrate_flag:
                    neutral_x = None
                    neutral_y = None
                    self.recalibrate_flag = False
                    action_msg = "CENTER RECALIBRATED"
                    action_timer = 20
                    action_color = (0, 255, 255)
                    self.telemetry["last_action"] = "Center Recalibrated"

                # =========================================================
                # MODE: EYE & HEAD TRACKING
                # =========================================================
                if mode == "eye" and face_mesh is not None:
                    results = face_mesh.process(rgb)
                    self.telemetry["face_detected"] = bool(results.multi_face_landmarks)

                    if click_cooldown > 0:
                        click_cooldown -= 1

                    if results.multi_face_landmarks:
                        landmarks = results.multi_face_landmarks[0].landmark

                        # 1. Head displacement via Nose Tip
                        nose = landmarks[self.NOSE_TIP]
                        nose_x, nose_y = nose.x, nose.y

                        if neutral_x is None:
                            neutral_x = nose_x
                            neutral_y = nose_y

                        dx = nose_x - neutral_x
                        dy = nose_y - neutral_y

                        # Micro-deadband to prevent tremor drift
                        if abs(dx) < 0.004:
                            dx = 0.0
                        if abs(dy) < 0.004:
                            dy = 0.0

                        # Visual neutral center guide reticle
                        nc_x, nc_y = int(neutral_x * w), int(neutral_y * h)
                        cv2.circle(frame, (nc_x, nc_y), 18, (255, 255, 255), 1)
                        cv2.line(frame, (nc_x - 12, nc_y), (nc_x + 12, nc_y), (255, 255, 255), 1)
                        cv2.line(frame, (nc_x, nc_y - 12), (nc_x, nc_y + 12), (255, 255, 255), 1)

                        # Virtual cursor target calculation
                        sensitivity = 3.6
                        raw_x = screen_w / 2 + (dx * screen_w * sensitivity)
                        raw_y = screen_h / 2 + (dy * screen_h * sensitivity)
                        target_x = max(0, min(screen_w - 1, int(raw_x)))
                        target_y = max(0, min(screen_h - 1, int(raw_y)))

                        # Smooth interpolation
                        smoothed_x = int(prev_x * (1 - alpha_eye) + target_x * alpha_eye)
                        smoothed_y = int(prev_y * (1 - alpha_eye) + target_y * alpha_eye)
                        prev_x, prev_y = smoothed_x, smoothed_y
                        current_cursor_x = smoothed_x
                        current_cursor_y = smoothed_y

                        # Execute system mouse move
                        if self.mouse_enabled:
                            win_set_cursor_pos(smoothed_x, smoothed_y)

                        # 2. Eye Aspect Ratio & Blink Clicks
                        left_eye_pts = [landmarks[i] for i in self.LEFT_EYE]
                        right_eye_pts = [landmarks[i] for i in self.RIGHT_EYE]

                        left_ear = self.eye_aspect_ratio(left_eye_pts)
                        right_ear = self.eye_aspect_ratio(right_eye_pts)
                        self.telemetry["left_ear"] = round(left_ear, 2)
                        self.telemetry["right_ear"] = round(right_ear, 2)

                        # Draw eye contour points
                        for pt in left_eye_pts:
                            cv2.circle(frame, (int(pt.x * w), int(pt.y * h)), 2, (0, 255, 255), -1)
                        for pt in right_eye_pts:
                            cv2.circle(frame, (int(pt.x * w), int(pt.y * h)), 2, (255, 0, 255), -1)

                        # Highlight tracked nose point with high-visibility target
                        nx, ny = int(nose_x * w), int(nose_y * h)
                        cv2.circle(frame, (nx, ny), 7, (0, 255, 0), -1)
                        cv2.circle(frame, (nx, ny), 14, (0, 255, 0), 1)

                        # Differential Blink Detection (robust against natural double blinks and squinting)
                        ear_threshold = self.EAR_THRESHOLD
                        differential = 0.035

                        if click_cooldown == 0:
                            # Both closed -> natural resting blink (ignore)
                            if left_ear < ear_threshold and right_ear < ear_threshold:
                                left_blink_counter = 0
                                right_blink_counter = 0

                            # Left eye closed exclusively -> LEFT CLICK
                            elif left_ear < ear_threshold and (right_ear - left_ear) >= differential:
                                left_blink_counter += 1
                                if left_blink_counter >= self.BLINK_CONSEC_FRAMES:
                                    if self.mouse_enabled:
                                        win_mouse_click('left')
                                    action_msg = "LEFT CLICK!"
                                    action_timer = 20
                                    action_color = (0, 255, 0)
                                    frame_is_clicking = True
                                    frame_click_type = "left"
                                    self.telemetry["last_action"] = "Left Click (Blink)"
                                    self.telemetry["click_event"] = "left"
                                    left_blink_counter = 0
                                    click_cooldown = 12

                            # Right eye closed exclusively -> RIGHT CLICK
                            elif right_ear < ear_threshold and (left_ear - right_ear) >= differential:
                                right_blink_counter += 1
                                if right_blink_counter >= self.BLINK_CONSEC_FRAMES:
                                    if self.mouse_enabled:
                                        win_mouse_click('right')
                                    action_msg = "RIGHT CLICK!"
                                    action_timer = 20
                                    action_color = (0, 165, 255)
                                    frame_is_clicking = True
                                    frame_click_type = "right"
                                    self.telemetry["last_action"] = "Right Click (Blink)"
                                    self.telemetry["click_event"] = "right"
                                    right_blink_counter = 0
                                    click_cooldown = 12
                            else:
                                left_blink_counter = 0
                                right_blink_counter = 0

                        # HUD on frame
                        cv2.putText(frame, f"EAR L: {left_ear:.2f} | R: {right_ear:.2f}", (15, 60),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    else:
                        cv2.putText(frame, "Align your face in view...", (15, 60),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 165, 255), 2)

                # =========================================================
                # MODE: HAND GESTURE CONTROL
                # =========================================================
                elif mode == "hand" and hands is not None:
                    results = hands.process(rgb)
                    self.telemetry["hand_detected"] = bool(results.multi_hand_landmarks)

                    if gesture_cooldown > 0:
                        gesture_cooldown -= 1

                    if results.multi_hand_landmarks:
                        for hand_landmarks in results.multi_hand_landmarks:
                            # Draw skeleton
                            self.mp_drawing.draw_landmarks(
                                frame,
                                hand_landmarks,
                                self.mp_hands.HAND_CONNECTIONS,
                                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                                self.mp_drawing_styles.get_default_hand_connections_style()
                            )

                            lm = hand_landmarks.landmark
                            fingers = self.get_finger_status(lm)
                            total_fingers = sum(fingers)
                            self.telemetry["finger_count"] = total_fingers

                            # Key landmarks
                            thumb_tip = lm[4]
                            index_tip = lm[8]
                            middle_tip = lm[12]
                            ring_tip = lm[16]
                            pinky_tip = lm[20]
                            wrist = lm[0]

                            # Distance calculations for clicks
                            pinch_left = self.get_distance(thumb_tip, index_tip)
                            pinch_right = self.get_distance(thumb_tip, middle_tip)
                            fingers_together = self.get_distance(index_tip, middle_tip)

                            # ---------------------------------------------------------
                            # Active Interaction Bounding Box (15% margin for full reach)
                            # ---------------------------------------------------------
                            margin_x = 0.15
                            margin_y = 0.15

                            # Draw bounding boundary guide box on camera frame
                            box_x1 = int(margin_x * w)
                            box_y1 = int(margin_y * h)
                            box_x2 = int((1.0 - margin_x) * w)
                            box_y2 = int((1.0 - margin_y) * h)
                            cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), (80, 100, 120), 1)
                            cv2.putText(frame, "Active Track Area", (box_x1 + 6, box_y1 + 16),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 140, 160), 1)

                            # Map index tip inside active margin to full screen desktop
                            clamped_ix = max(margin_x, min(1.0 - margin_x, index_tip.x))
                            clamped_iy = max(margin_y, min(1.0 - margin_y, index_tip.y))
                            norm_x = (clamped_ix - margin_x) / (1.0 - 2 * margin_x)
                            norm_y = (clamped_iy - margin_y) / (1.0 - 2 * margin_y)
                            raw_target_x = int(norm_x * screen_w)
                            raw_target_y = int(norm_y * screen_h)

                            # Smooth cursor tracking
                            if prev_hand_pos is None:
                                prev_hand_pos = (raw_target_x, raw_target_y)
                            smooth_x = int(prev_hand_pos[0] * (1 - alpha_hand) + raw_target_x * alpha_hand)
                            smooth_y = int(prev_hand_pos[1] * (1 - alpha_hand) + raw_target_y * alpha_hand)
                            prev_hand_pos = (smooth_x, smooth_y)
                            current_cursor_x = smooth_x
                            current_cursor_y = smooth_y

                            # Cursor target dot on index tip
                            tip_px = int(index_tip.x * w)
                            tip_py = int(index_tip.y * h)

                            # ---------------------------------------------------------
                            # GESTURE 1: PINCH LEFT CLICK (Thumb + Index pinch < 0.048)
                            # or Index & Middle touching (< 0.038)
                            # ---------------------------------------------------------
                            if (pinch_left < 0.048 or (fingers[1] and fingers[2] and fingers_together < 0.038)) and not fingers[3] and not fingers[4]:
                                self.telemetry["active_gesture"] = "Left Click (Pinch)"
                                if gesture_cooldown == 0:
                                    if self.mouse_enabled:
                                        win_mouse_click('left')
                                    gesture_cooldown = 10
                                    action_msg = "LEFT CLICK!"
                                    action_timer = 20
                                    action_color = (0, 255, 0)
                                    frame_is_clicking = True
                                    frame_click_type = "left"
                                    self.telemetry["last_action"] = "Hand Left Click"
                                    self.telemetry["click_event"] = "left"

                                # Draw pinch connection line
                                cv2.line(frame, (int(thumb_tip.x * w), int(thumb_tip.y * h)),
                                         (tip_px, tip_py), (0, 255, 0), 3)
                                cv2.circle(frame, (tip_px, tip_py), 16, (0, 255, 0), 2)

                            # ---------------------------------------------------------
                            # GESTURE 2: PINCH RIGHT CLICK (Thumb + Middle pinch < 0.048)
                            # ---------------------------------------------------------
                            elif pinch_right < 0.048 and fingers[1] and not fingers[3] and not fingers[4]:
                                self.telemetry["active_gesture"] = "Right Click (Pinch)"
                                if gesture_cooldown == 0:
                                    if self.mouse_enabled:
                                        win_mouse_click('right')
                                    gesture_cooldown = 14
                                    action_msg = "RIGHT CLICK!"
                                    action_timer = 20
                                    action_color = (0, 165, 255)
                                    frame_is_clicking = True
                                    frame_click_type = "right"
                                    self.telemetry["last_action"] = "Hand Right Click"
                                    self.telemetry["click_event"] = "right"

                                cv2.line(frame, (int(thumb_tip.x * w), int(thumb_tip.y * h)),
                                         (int(middle_tip.x * w), int(middle_tip.y * h)), (0, 165, 255), 3)

                            # ---------------------------------------------------------
                            # GESTURE 3: FIST (DRAG & DROP)
                            # ---------------------------------------------------------
                            elif total_fingers == 0 or (not fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]):
                                self.telemetry["active_gesture"] = "Fist / Drag Active"
                                if not is_dragging:
                                    if self.mouse_enabled:
                                        win_mouse_down()
                                    is_dragging = True
                                    self.telemetry["last_action"] = "Drag Started"

                                # Track drag via hand position
                                if self.mouse_enabled:
                                    win_set_cursor_pos(smooth_x, smooth_y)

                                action_msg = "DRAGGING..."
                                action_timer = 5
                                action_color = (0, 255, 255)
                                cv2.putText(frame, "DRAG ACTIVE", (15, 120),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                            # ---------------------------------------------------------
                            # GESTURE 4: MOVE REAL LAPTOP CURSOR (Default for open hand, pointing, etc.)
                            # ---------------------------------------------------------
                            else:
                                if is_dragging:
                                    if self.mouse_enabled:
                                        win_mouse_up()
                                    is_dragging = False

                                # Check rapid scroll swipe if 5 fingers moving vertically
                                is_scrolling = False
                                if total_fingers == 5:
                                    cur_wrist_y = wrist.y * h
                                    if prev_wrist_y is not None:
                                        dy = cur_wrist_y - prev_wrist_y
                                        if abs(dy) > 18:
                                            if self.mouse_enabled:
                                                win_mouse_scroll(-int(dy * 1.5))
                                            action_msg = "SCROLLING"
                                            action_timer = 8
                                            action_color = (255, 191, 0)
                                            is_scrolling = True
                                    prev_wrist_y = cur_wrist_y
                                else:
                                    prev_wrist_y = None

                                if not is_scrolling:
                                    self.telemetry["active_gesture"] = "Move Laptop Cursor"
                                    # Move the REAL laptop cursor across the screen!
                                    if self.mouse_enabled:
                                        win_set_cursor_pos(smooth_x, smooth_y)

                                # High-visibility cursor reticle on tracked hand
                                cv2.circle(frame, (tip_px, tip_py), 6, (0, 255, 255), -1)
                                cv2.circle(frame, (tip_px, tip_py), 18, (0, 255, 255), 2)
                                cv2.line(frame, (tip_px - 24, tip_py), (tip_px + 24, tip_py), (0, 255, 255), 1)
                                cv2.line(frame, (tip_px, tip_py - 24), (tip_px, tip_py + 24), (0, 255, 255), 1)

                            cv2.putText(frame, f"Fingers: {total_fingers} | {self.telemetry['active_gesture']}",
                                        (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

                    else:
                        if is_dragging:
                            if self.mouse_enabled:
                                win_mouse_up()
                            is_dragging = False
                        prev_hand_pos = None
                        prev_wrist_y = None
                        self.telemetry["active_gesture"] = "None"
                        cv2.putText(frame, "Show hand inside active box...", (15, 60),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 165, 255), 2)

                # =========================================================
                # MODE: PREVIEW / TEST
                # =========================================================
                else:
                    self.telemetry["active_gesture"] = "Preview Only"
                    cx, cy = w // 2, h // 2
                    cv2.line(frame, (cx - 30, cy), (cx + 30, cy), (0, 255, 128), 1)
                    cv2.line(frame, (cx, cy - 30), (cx, cy + 30), (0, 255, 128), 1)
                    cv2.rectangle(frame, (w//4, h//6), (3*w//4, 5*h//6), (0, 255, 128), 1)
                    cv2.putText(frame, "Position Face / Hand in Box", (w//4 + 10, h//6 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 128), 1)

                # Update live telemetry coordinates
                self.telemetry["cursor_x"] = current_cursor_x
                self.telemetry["cursor_y"] = current_cursor_y

                # Draw Mini Desktop Screen and Target Reticle HUD on frame
                self.draw_virtual_cursor_hud(
                    frame,
                    current_cursor_x,
                    current_cursor_y,
                    is_clicking=frame_is_clicking,
                    click_type=frame_click_type
                )

                # Action flash banner on frame
                if action_msg:
                    tw = len(action_msg) * 16
                    cv2.rectangle(frame, (w//2 - tw//2 - 15, h//2 - 30), (w//2 + tw//2 + 15, h//2 + 30), (10, 15, 25), -1)
                    cv2.rectangle(frame, (w//2 - tw//2 - 15, h//2 - 30), (w//2 + tw//2 + 15, h//2 + 30), action_color, 2)
                    cv2.putText(frame, action_msg, (w//2 - tw//2, h//2 + 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.85, action_color, 2)

                # Universal Top HUD Banner
                mode_label = mode.upper()
                mouse_status = "MOUSE: LIVE" if self.mouse_enabled else "PREVIEW ONLY"
                status_color = (0, 255, 0) if self.mouse_enabled else (200, 200, 200)

                cv2.rectangle(frame, (0, 0), (w, 32), (15, 20, 28), -1)
                cv2.putText(frame, f"WEB EYE | {mode_label} | Cam {cam_index} | {mouse_status}",
                            (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, status_color, 1)
                cv2.putText(frame, f"{current_fps} FPS", (w - 75, 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 200), 1)

                # Encode to JPEG
                ret_enc, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if not ret_enc:
                    continue

                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        except Exception as e:
            print(f"[CameraStream] Error in video generation: {e}")
        finally:
            if is_dragging:
                win_mouse_up()
            if face_mesh:
                try:
                    face_mesh.close()
                except Exception:
                    pass
            if hands:
                try:
                    hands.close()
                except Exception:
                    pass
            if cap:
                try:
                    cap.release()
                except Exception:
                    pass
            if getattr(self, 'active_cap', None) is cap:
                self.active_cap = None
            self.is_streaming = False
            print("[CameraStream] Camera capture cleanly released.")


# Global singleton instance
stream_manager = CameraStreamManager()
