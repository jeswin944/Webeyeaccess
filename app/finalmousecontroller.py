import cv2
import ctypes
import pyautogui
import math
from scipy.spatial import distance as dist

# -------------------------------------------------------------
# Protobuf / MediaPipe compatibility bridge for protobuf 5+/7+
# -------------------------------------------------------------
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

# ------------------------------
# Setup
# ------------------------------
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False
screen_w, screen_h = pyautogui.size()

# Direct Windows API mouse control for zero-latency execution
def win_set_cursor_pos(x, y):
    clamped_x = max(0, min(screen_w - 1, int(x)))
    clamped_y = max(0, min(screen_h - 1, int(y)))
    try:
        ctypes.windll.user32.SetCursorPos(clamped_x, clamped_y)
    except Exception:
        pyautogui.moveTo(clamped_x, clamped_y)

def win_mouse_click(button='left'):
    try:
        if button == 'left':
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        elif button == 'right':
            ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)
    except Exception:
        pyautogui.click(button=button)

# Face Mesh Model
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# Neutral head / nose position
neutral_x = None
neutral_y = None

# Cursor Smoothing
prev_x, prev_y = None, None
alpha = 0.28  # Smoothing factor (0 = full previous, 1 = raw new)

# Blink Detection Counters & Thresholds
left_blink_counter = 0
right_blink_counter = 0
click_cooldown = 0
EAR_THRESHOLD = 0.21  # Eye Aspect Ratio threshold for blink detection
BLINK_CONSEC_FRAMES = 2  # Consecutive frames eye must be closed

# Landmark Indices for Eyes & Nose
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
NOSE_TIP = 1


# ------------------------------
# Helper Functions
# ------------------------------
def eye_aspect_ratio(eye_landmarks):
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


def start_eye_mouse(is_active_callback=None, cam_index=0):
    """
    Main function to run head movement cursor control with left/right eye blink clicking.
    """
    global neutral_x, neutral_y, prev_x, prev_y
    global left_blink_counter, right_blink_counter, click_cooldown

    # Reset tracking variables
    neutral_x = None
    neutral_y = None
    prev_x, prev_y = None, None
    left_blink_counter = 0
    right_blink_counter = 0
    click_cooldown = 0

    try:
        cam_idx = int(cam_index)
    except (ValueError, TypeError):
        cam_idx = 0

    print(f"[WEB EYE] Launching Eye & Head Tracking on Camera Index: {cam_idx}")
    cam = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    if not cam.isOpened():
        cam.release()
        cam = cv2.VideoCapture(cam_idx)
    if not cam.isOpened():
        print(f"[WEB EYE] Camera {cam_idx} unavailable, falling back to default Camera 0...")
        cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cam.isOpened():
            cam.release()
            cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            print("[WEB EYE] ERROR: No camera device accessible.")
            return

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    try:
        while True:
            # Check external stop condition from Django thread wrapper
            if is_active_callback is not None and not is_active_callback():
                print("[WEB EYE] Eye & Head Tracking stopped by user.")
                break

            ret, frame = cam.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)  # Mirror frame for natural interaction
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)

            if click_cooldown > 0:
                click_cooldown -= 1

            action_msg = ""
            current_cursor_x = screen_w // 2
            current_cursor_y = screen_h // 2

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark

                # -------------------------------------------------------------
                # 1. Head Movement for Cursor Control (using nose tip landmark 1)
                # -------------------------------------------------------------
                nose = landmarks[NOSE_TIP]
                nose_x, nose_y = nose.x, nose.y

                # Initialize neutral resting center
                if neutral_x is None:
                    neutral_x = nose_x
                    neutral_y = nose_y

                # Displacement from neutral center
                dx = nose_x - neutral_x
                dy = nose_y - neutral_y

                # Small deadband
                if abs(dx) < 0.004:
                    dx = 0.0
                if abs(dy) < 0.004:
                    dy = 0.0

                # Sensitivity multiplier
                sensitivity = 3.6
                target_x = int(screen_w / 2 + dx * screen_w * sensitivity)
                target_y = int(screen_h / 2 + dy * screen_h * sensitivity)

                # Clamp to screen dimensions
                target_x = max(0, min(screen_w - 1, target_x))
                target_y = max(0, min(screen_h - 1, target_y))

                # Smooth cursor movement
                if prev_x is None:
                    prev_x, prev_y = target_x, target_y
                smoothed_x = int(prev_x * (1 - alpha) + target_x * alpha)
                smoothed_y = int(prev_y * (1 - alpha) + target_y * alpha)
                prev_x, prev_y = smoothed_x, smoothed_y
                current_cursor_x = smoothed_x
                current_cursor_y = smoothed_y

                # Move OS mouse cursor with zero latency
                win_set_cursor_pos(smoothed_x, smoothed_y)

                # -------------------------------------------------------------
                # 2. Eye Blink Detection (Left-eye = Left Click, Right-eye = Right Click)
                # -------------------------------------------------------------
                left_eye_points = [landmarks[i] for i in LEFT_EYE]
                right_eye_points = [landmarks[i] for i in RIGHT_EYE]

                left_ear = eye_aspect_ratio(left_eye_points)
                right_ear = eye_aspect_ratio(right_eye_points)

                # Visualization on landmarks
                for lm in left_eye_points:
                    cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 2, (0, 255, 255), -1)
                for lm in right_eye_points:
                    cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 2, (255, 0, 255), -1)

                nx, ny = int(nose_x * w), int(nose_y * h)
                cv2.circle(frame, (nx, ny), 6, (0, 255, 0), -1)
                cv2.circle(frame, (nx, ny), 14, (0, 255, 0), 1)

                # Neutral center guide reticle
                if neutral_x is not None:
                    nc_x, nc_y = int(neutral_x * w), int(neutral_y * h)
                    cv2.circle(frame, (nc_x, nc_y), 16, (255, 255, 255), 1)
                    cv2.line(frame, (nc_x - 10, nc_y), (nc_x + 10, nc_y), (255, 255, 255), 1)
                    cv2.line(frame, (nc_x, nc_y - 10), (nc_x, nc_y + 10), (255, 255, 255), 1)

                # Differential blink detection
                ear_diff = 0.035
                if click_cooldown == 0:
                    if left_ear < EAR_THRESHOLD and right_ear < EAR_THRESHOLD:
                        left_blink_counter = 0
                        right_blink_counter = 0
                    elif left_ear < EAR_THRESHOLD and (right_ear - left_ear) >= ear_diff:
                        left_blink_counter += 1
                        if left_blink_counter >= BLINK_CONSEC_FRAMES:
                            win_mouse_click('left')
                            action_msg = "LEFT CLICK!"
                            left_blink_counter = 0
                            click_cooldown = 12
                    elif right_ear < EAR_THRESHOLD and (left_ear - right_ear) >= ear_diff:
                        right_blink_counter += 1
                        if right_blink_counter >= BLINK_CONSEC_FRAMES:
                            win_mouse_click('right')
                            action_msg = "RIGHT CLICK!"
                            right_blink_counter = 0
                            click_cooldown = 12
                    else:
                        left_blink_counter = 0
                        right_blink_counter = 0

                # On-screen HUD info
                hud_text = f"EAR: L={left_ear:.2f} R={right_ear:.2f}"
                cv2.putText(frame, hud_text, (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Draw Mini Desktop Monitor Preview in corner
            mon_w, mon_h = 130, 75
            mon_x, mon_y = w - mon_w - 15, h - mon_h - 15
            cv2.rectangle(frame, (mon_x, mon_y), (mon_x + mon_w, mon_y + mon_h), (20, 24, 34), -1)
            cv2.rectangle(frame, (mon_x, mon_y), (mon_x + mon_w, mon_y + mon_h), (0, 255, 128), 2)
            cv2.putText(frame, "DESKTOP", (mon_x + 5, mon_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 128), 1)
            
            cur_norm_x = min(1.0, max(0.0, current_cursor_x / max(1, screen_w)))
            cur_norm_y = min(1.0, max(0.0, current_cursor_y / max(1, screen_h)))
            cur_mx = int(mon_x + 8 + cur_norm_x * (mon_w - 16))
            cur_my = int(mon_y + 20 + cur_norm_y * (mon_h - 26))
            cv2.circle(frame, (cur_mx, cur_my), 4, (0, 255, 255), -1)
            cv2.line(frame, (cur_mx - 6, cur_my), (cur_mx + 6, cur_my), (0, 255, 255), 1)
            cv2.line(frame, (cur_mx, cur_my - 6), (cur_mx, cur_my + 6), (0, 255, 255), 1)
            cv2.putText(frame, f"X:{current_cursor_x} Y:{current_cursor_y}", (mon_x, mon_y - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 220, 255), 1)

            if action_msg:
                color = (0, 255, 0) if "LEFT" in action_msg else (0, 165, 255)
                cv2.rectangle(frame, (w // 2 - 100, h // 2 - 25), (w // 2 + 100, h // 2 + 25), (15, 20, 30), -1)
                cv2.putText(frame, action_msg, (w // 2 - 80, h // 2 + 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3)

            # Display Status Bar
            status_text = f"Head Control [Cam {cam_idx}] - 'C' Recalibrate, ESC exit"
            cv2.putText(frame, status_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

            cv2.putText(frame, "Left Blink = Left Click | Right Blink = Right Click", (10, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

            cv2.imshow("WEB EYE - Head & Eye Tracking", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                print("[WEB EYE] Eye tracking terminated via ESC key.")
                break
            elif key == ord('c') or key == ord('C'):
                neutral_x = None
                neutral_y = None
                print("[WEB EYE] Neutral center reset via 'C' key.")

    except Exception as e:
        print(f"[WEB EYE] Error in eye control: {e}")
    finally:
        try:
            cam.release()
        except Exception:
            pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        print("[WEB EYE] Eye & Head Tracking camera resources freed.")