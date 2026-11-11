import cv2
import ctypes
import pyautogui
import math
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import screen_brightness_control as sbcontrol

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

# ------------------------------
# Setup
# ------------------------------
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
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

def win_mouse_down():
    try:
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    except Exception:
        pyautogui.mouseDown()

def win_mouse_up():
    try:
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
    except Exception:
        pyautogui.mouseUp()

def win_mouse_scroll(amount):
    try:
        clicks = int(amount * 120)
        ctypes.windll.user32.mouse_event(0x0800, 0, 0, clicks, 0)
    except Exception:
        pyautogui.scroll(int(amount))

# State variables
prev_hand_pos = None
is_dragging = False
pinch_start = None
pinch_mode = None
gesture_cooldown = 0
action_msg = ""
action_timer = 0
action_color = (0, 255, 0)
prev_wrist_y = None

# Volume control
try:
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume_control = cast(interface, POINTER(IAudioEndpointVolume))
except:
    volume_control = None


# ------------------------------
# Helper Functions
# ------------------------------
def get_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def get_finger_status(landmarks):
    """
    Check which fingers are extended: (thumb, index, middle, ring, pinky)
    Robust against left vs right hand orientation.
    """
    tips = [4, 8, 12, 16, 20]
    pips = [3, 6, 10, 14, 18]
    mcps = [2, 5, 9, 13, 17]
    fingers = []

    # Thumb
    thumb_tip = landmarks[tips[0]]
    index_mcp = landmarks[mcps[1]]
    thumb_spread = math.sqrt((thumb_tip.x - index_mcp.x)**2 + (thumb_tip.y - index_mcp.y)**2)
    fingers.append(thumb_spread > 0.08)

    # 4 fingers
    for i in range(1, 5):
        if landmarks[tips[i]].y < landmarks[pips[i]].y:
            fingers.append(True)
        else:
            fingers.append(False)

    return tuple(fingers)

def get_hand_center(landmarks):
    wrist = landmarks[0]
    middle_mcp = landmarks[9]
    return ((wrist.x + middle_mcp.x) / 2, (wrist.y + middle_mcp.y) / 2)

def set_volume(level):
    if volume_control:
        try:
            level = max(0.0, min(1.0, level))
            volume_control.SetMasterVolumeLevelScalar(level, None)
        except:
            pass

def set_brightness(level):
    try:
        level = max(0, min(100, int(level)))
        sbcontrol.set_brightness(level, display=0)
    except:
        pass


def handle_gestures(landmarks, fingers, frame_w, frame_h):
    """Main gesture recognition and control logic."""
    global prev_hand_pos, is_dragging, pinch_start, pinch_mode, gesture_cooldown
    global action_msg, action_timer, action_color, prev_wrist_y

    thumb, index, middle, ring, pinky = fingers
    total_fingers = sum(fingers)

    index_tip = landmarks[8]
    thumb_tip = landmarks[4]
    middle_tip = landmarks[12]
    wrist = landmarks[0]

    pinch_left = get_distance(index_tip, thumb_tip)
    pinch_right = get_distance(middle_tip, thumb_tip)
    fingers_together = get_distance(index_tip, middle_tip)

    if gesture_cooldown > 0:
        gesture_cooldown -= 1

    # Active bounding box (15% margin for comfortable full screen reach)
    margin_x = 0.15
    margin_y = 0.15
    clamped_x = max(margin_x, min(1.0 - margin_x, index_tip.x))
    clamped_y = max(margin_y, min(1.0 - margin_y, index_tip.y))
    norm_x = (clamped_x - margin_x) / (1.0 - 2 * margin_x)
    norm_y = (clamped_y - margin_y) / (1.0 - 2 * margin_y)
    raw_x = int(norm_x * screen_w)
    raw_y = int(norm_y * screen_h)

    alpha = 0.35
    if prev_hand_pos is None:
        prev_hand_pos = (raw_x, raw_y)
    smooth_x = int(prev_hand_pos[0] * (1 - alpha) + raw_x * alpha)
    smooth_y = int(prev_hand_pos[1] * (1 - alpha) + raw_y * alpha)
    prev_hand_pos = (smooth_x, smooth_y)

    # 1. PINCH LEFT CLICK (Thumb + Index < 0.048)
    if (pinch_left < 0.048 or (index and middle and fingers_together < 0.038)) and not ring and not pinky:
        if gesture_cooldown == 0:
            win_mouse_click('left')
            gesture_cooldown = 10
            action_msg = "LEFT CLICK!"
            action_timer = 20
            action_color = (0, 255, 0)
        win_set_cursor_pos(smooth_x, smooth_y)

    # 2. PINCH RIGHT CLICK (Thumb + Middle < 0.048)
    elif pinch_right < 0.048 and index and not ring and not pinky:
        if gesture_cooldown == 0:
            win_mouse_click('right')
            gesture_cooldown = 14
            action_msg = "RIGHT CLICK!"
            action_timer = 20
            action_color = (0, 165, 255)
        win_set_cursor_pos(smooth_x, smooth_y)

    # 3. MOVE CURSOR (Index finger up)
    elif index and not ring and not pinky:
        win_set_cursor_pos(smooth_x, smooth_y)
        if is_dragging:
            win_mouse_up()
            is_dragging = False

    # 4. FIST = DRAG & DROP
    elif total_fingers == 0 or (not index and not middle and not ring and not pinky):
        if not is_dragging:
            win_mouse_down()
            is_dragging = True
            action_msg = "DRAGGING..."
            action_timer = 5
            action_color = (0, 255, 255)
        win_set_cursor_pos(smooth_x, smooth_y)

    # 5. ALL 5 FINGERS = SCROLL
    elif total_fingers == 5:
        if is_dragging:
            win_mouse_up()
            is_dragging = False
        cur_y = wrist.y * frame_h
        if prev_wrist_y is not None:
            dy = cur_y - prev_wrist_y
            if abs(dy) > 6:
                win_mouse_scroll(-int(dy * 1.5))
                action_msg = "SCROLLING"
                action_timer = 10
                action_color = (255, 191, 0)
        prev_wrist_y = cur_y
    else:
        if is_dragging:
            win_mouse_up()
            is_dragging = False
        prev_wrist_y = None

    return (smooth_x, smooth_y)


# ------------------------------
# Main Function
# ------------------------------
def start_hand_gesture(is_active_callback=None, cam_index=0):
    global prev_hand_pos, is_dragging, pinch_start, pinch_mode, gesture_cooldown
    global action_msg, action_timer, action_color, prev_wrist_y

    prev_hand_pos = None
    is_dragging = False
    pinch_start = None
    pinch_mode = None
    gesture_cooldown = 0
    action_msg = ""
    action_timer = 0
    prev_wrist_y = None

    try:
        cam_idx = int(cam_index)
    except (ValueError, TypeError):
        cam_idx = 0

    print(f"[WEB EYE] Opening camera index for gesture control: {cam_idx}")
    cam = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    if not cam.isOpened():
        cam.release()
        cam = cv2.VideoCapture(cam_idx)
    if not cam.isOpened():
        print(f"[WEB EYE] Camera {cam_idx} not found! Falling back to camera 0...")
        cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cam.isOpened():
            cam.release()
            cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            print("[WEB EYE] No camera could be opened!")
            return

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    try:
        with mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        ) as hands:

            while True:
                if is_active_callback is not None and not is_active_callback():
                    print("[WEB EYE] Hand gesture control stopped by user")
                    break

                ret, frame = cam.read()
                if not ret:
                    continue

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)
                h, w, _ = frame.shape

                # Active margin box
                cv2.rectangle(frame, (int(0.15*w), int(0.15*h)), (int(0.85*w), int(0.85*h)), (80, 100, 120), 1)

                current_cx, current_cy = screen_w // 2, screen_h // 2

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS
                        )

                        fingers = get_finger_status(hand_landmarks.landmark)
                        current_cx, current_cy = handle_gestures(hand_landmarks.landmark, fingers, w, h)

                        # High-visibility cursor reticle on index finger tip
                        itip = hand_landmarks.landmark[8]
                        ix, iy = int(itip.x * w), int(itip.y * h)
                        cv2.circle(frame, (ix, iy), 6, (0, 255, 255), -1)
                        cv2.circle(frame, (ix, iy), 18, (0, 255, 255), 2)
                        cv2.line(frame, (ix - 24, iy), (ix + 24, iy), (0, 255, 255), 1)
                        cv2.line(frame, (ix, iy - 24), (ix, iy + 24), (0, 255, 255), 1)
                else:
                    if is_dragging:
                        win_mouse_up()
                        is_dragging = False
                    prev_hand_pos = None
                    prev_wrist_y = None

                # Mini Desktop Monitor Preview in corner
                mon_w, mon_h = 130, 75
                mon_x, mon_y = w - mon_w - 15, h - mon_h - 15
                cv2.rectangle(frame, (mon_x, mon_y), (mon_x + mon_w, mon_y + mon_h), (20, 24, 34), -1)
                cv2.rectangle(frame, (mon_x, mon_y), (mon_x + mon_w, mon_y + mon_h), (0, 255, 128), 2)
                cv2.putText(frame, "DESKTOP", (mon_x + 5, mon_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 128), 1)

                cur_norm_x = min(1.0, max(0.0, current_cx / max(1, screen_w)))
                cur_norm_y = min(1.0, max(0.0, current_cy / max(1, screen_h)))
                cur_mx = int(mon_x + 8 + cur_norm_x * (mon_w - 16))
                cur_my = int(mon_y + 20 + cur_norm_y * (mon_h - 26))
                cv2.circle(frame, (cur_mx, cur_my), 4, (0, 255, 255), -1)
                cv2.line(frame, (cur_mx - 6, cur_my), (cur_mx + 6, cur_my), (0, 255, 255), 1)
                cv2.line(frame, (cur_mx, cur_my - 6), (cur_mx, cur_my + 6), (0, 255, 255), 1)
                cv2.putText(frame, f"X:{current_cx} Y:{current_cy}", (mon_x, mon_y - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 220, 255), 1)

                if action_timer > 0:
                    action_timer -= 1
                    cv2.rectangle(frame, (w // 2 - 100, h // 2 - 25), (w // 2 + 100, h // 2 + 25), (15, 20, 30), -1)
                    cv2.putText(frame, action_msg, (w // 2 - 85, h // 2 + 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.85, action_color, 2)

                # Status info
                status_text = f"Hand Gesture Control [Cam {cam_idx}] - ESC to quit"
                cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

                cv2.imshow("WEB EYE - Hand Gesture Control", frame)

                if cv2.waitKey(1) & 0xFF == 27:
                    print("[WEB EYE] Hand gesture control stopped by ESC key")
                    break

    except Exception as e:
        print(f"[WEB EYE] Error in hand gesture control: {e}")
    finally:
        if is_dragging:
            win_mouse_up()
        try:
            cam.release()
        except Exception:
            pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        print("[WEB EYE] Hand gesture control resources released")


def start(is_active_callback=None, cam_index=0):
    start_hand_gesture(is_active_callback, cam_index=cam_index)


if __name__ == "__main__":
    start_hand_gesture()