from urllib import request
from django.shortcuts import render,redirect
from django.contrib.auth.models import User,Group
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import User_profile, complaints, feedback
import cv2
import mediapipe as mp
import threading
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.contrib import messages


import subprocess
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache, cache_control



# Global flags
face_scan_active = False
face_capture = None

mp_face_mesh = mp.solutions.face_mesh

# Create your views here.
def home(request):
    return render(request, 'home.html')



@csrf_exempt
@never_cache
def logout_view(request):
    auth_logout(request)
    request.session.flush()

    response = redirect('/login/')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )
        request.session['user_id']=user.id

        if user is not None:
            login(request, user)

            if user.is_superuser:
                return redirect('admindashboard')
            else:
                return redirect('dashboard')

        return redirect('login_view')

    return render(request, 'login.html')



def register_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('First_name')
        last_name = request.POST.get('Last_name')
        email = request.POST.get('Email')
        phone_number = request.POST.get('Phone_number')
        place = request.POST.get('place')
        gender = request.POST.get('Gender')
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(first_name, last_name, email, phone_number, place, gender, username, password)
        user = User.objects.create_user( first_name=first_name, last_name=last_name, username=username, email=email, password=password)
        user.save()
        User_profile.objects.create(user=user, First_name=first_name, Last_name=last_name, Phone_number =phone_number, place=place, Gender=gender,Email=email)
        return redirect('login_view')

    return render(request, 'register.html')


@login_required
@never_cache
@csrf_exempt
def permission_view(request):
    return render(request, 'permission.html')


@login_required
@never_cache
@csrf_exempt
def dashboard_view(request):
    return render(request, 'dashboard.html') 


@login_required
@never_cache
@csrf_exempt   
def callibration_view(request):
    return render(request, 'callibration.html')


@login_required
@never_cache
@csrf_exempt
def camera_view(request):
    return render(request, 'camera.html')


@login_required
@never_cache
@csrf_exempt
def tracking_view(request):
    return render(request, 'livetracking_interface.html')


@login_required
@never_cache
@csrf_exempt
def profile_view(request):
    u=request.session.get('user_id')
    a=User.objects.get(id=u)
    c=User_profile.objects.filter(user=a)

    return render(request, 'profile.html',{"profile":c})


@login_required
@never_cache
@csrf_exempt
def complaint(request):
    if request.method == 'POST':
        Title = request.POST.get('Title')
        Description = request.POST.get('Description')  
        u=request.session.get('user_id')
       
        print(Title,Description)
        complaints.objects.create(Title=Title,Description=Description,user=User.objects.get(id=u))
        return redirect('MyComplaints')

    return render(request, 'complaint.html')


@login_required
@never_cache
@csrf_exempt
def my_complaints_view(request):
    u=request.session.get('user_id')
    a=User.objects.get(id=u)
    c=complaints.objects.filter(user=a)
    
    return render(request, 'my_complaints.html',{'c':c})


@login_required
@never_cache
@csrf_exempt
def feedback_view(request):
    print("Feedback view called")
    if request.method == 'POST':
        Feedback = request.POST.get('feedback')
        print(Feedback)
        u=request.session.get('user_id')
        print(u)
        a=User.objects.get(id=u)
        print(a)
      
        feedback.objects.create(user=a, Feedback=Feedback)
        return redirect('my_feedback')
    return render(request, 'feedback.html')


@login_required
@never_cache
@csrf_exempt
def adminlogin_view(request):
    return render(request, 'adminlogin.html')


@login_required
@never_cache
@csrf_exempt
def admindashboard_view(request):
    total_users = User.objects.count()
    total_complaints = complaints.objects.count()
    pending_complaints = complaints.objects.filter(reply__isnull=True).count()
    empty_reply = complaints.objects.filter(reply="").count()
    pending_complaints += empty_reply
    resolved_complaints = total_complaints - pending_complaints
    total_feedback = feedback.objects.count()
    recent_complaints = complaints.objects.all().order_by('-Date')[:4]
    recent_feedback = feedback.objects.all().order_by('-date')[:2]
    today = timezone.now().date()

    activity = []

    for days_ago in range(6, -1, -1):

        current_date = today - timedelta(days=days_ago)

        count = complaints.objects.filter(
            Date__date=current_date
        ).count()

        activity.append({
            'day': current_date.strftime('%a'),
            'count': count
        })
        context = {

        'total_users': total_users,

        'pending_complaints': pending_complaints,

        'resolved_complaints': resolved_complaints,

        'total_feedback': total_feedback,

        'recent_complaints': recent_complaints,

        'recent_feedback': recent_feedback,

        'activity': activity,
    }


    return render(request,'admindashboard.html',context)

@login_required
@never_cache
@csrf_exempt
def complaint_management_view(request):
    c=complaints.objects.all()
    return render(request, 'complaintmanagement.html',{'c':c})


@login_required
@never_cache
@csrf_exempt
def reply_complaint_view(request, complaint_id):
    if request.method == 'POST':
        reply_text = request.POST.get('reply')
        complaint_instance = complaints.objects.get(id=complaint_id)
        complaint_instance.reply = reply_text
        complaint_instance.save()
        return redirect('complaintmanagement')
    return render(request, 'reply_complaint_view.html')


@login_required
@never_cache
@csrf_exempt
def user_management_view(request):

    users = User.objects.all().order_by('-date_joined')
    total_users = User.objects.count()

    return render(
        request,
        'usermanagement.html',
        {
            'u': users,
            'total_users': total_users
        }
    )  
@login_required
@never_cache
@csrf_exempt


def feedback_management_view(request):
    f=feedback.objects.all()
    return render(request, 'feedbackmanagement.html',{'f':f})
@login_required
@never_cache
@csrf_exempt

def face_scan_worker():
    """Opens webcam, detects face landmarks, draws points until stopped"""
    global face_scan_active, face_capture

    face_capture = cv2.VideoCapture(0)

    with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:

        while face_scan_active:
            ret, frame = face_capture.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)

            if results.multi_face_landmarks:
                h, w, _ = frame.shape
                for face_landmarks in results.multi_face_landmarks:
                    points = []
                    for lm in face_landmarks.landmark:
                        x, y = int(lm.x * w), int(lm.y * h)
                        points.append((x, y))
                        cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)

                    # 'points' now holds all facial landmark (x, y) coordinates
                    # save/process/send them here if needed

            cv2.imshow('Face Scan - Press Q to close', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    face_scan_active = False
    if face_capture:
        face_capture.release()
        face_capture = None
    cv2.destroyAllWindows()


@login_required(login_url='login')
@never_cache
@csrf_exempt
def face_scan_page(request):
    """Renders the face scan page"""
    context = {'face_scan_active': face_scan_active}
    return render(request, 'face_scan.html', context)


@login_required(login_url='login')
@never_cache
@csrf_exempt
def start_face_scan(request):
    """Starts face scan in a background thread"""
    global face_scan_active

    if face_scan_active:
        messages.warning(request, 'Face scan is already running!')
        return redirect('face_scan_page')

    face_scan_active = True
    t = threading.Thread(target=face_scan_worker, daemon=True)
    t.start()

    messages.success(request, 'Face scan started! Check your camera window.')
    return redirect('face_scan_page')


@login_required(login_url='login')
@never_cache
@csrf_exempt
def stop_face_scan(request):
    """Stops the face scan"""
    global face_scan_active, face_capture

    was_active = face_scan_active
    face_scan_active = False

    if face_capture:
        face_capture.release()
        face_capture = None
    cv2.destroyAllWindows()

    if was_active:
        messages.success(request, 'Face scan stopped successfully!')
    else:
        messages.info(request, 'No active face scan to stop.')

    return redirect('face_scan_page')


@login_required
@never_cache
@csrf_exempt
def my_feedback_view(request):
    u=request.session.get('user_id')
    a=User.objects.get(id=u)
    f=feedback.objects.filter(user=a)
    return render(request, 'my_feedback.html',{'f':f})


@login_required
@never_cache
@csrf_exempt
def gesture_view(request):      
    return render(request, 'gesture.html')





#####################################   VIRTUAL MOUSE IMPLEMENTATION   ####################################################


from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
import threading
import cv2

# Global flags to control the threads
eye_control_active = False
hand_control_active = False

# Global references to video captures (to release them when stopping)
# Global references to video captures (to release them when stopping)
eye_capture = None
hand_capture = None

def eye_mouse_wrapper(cam_index=0):
    """Wrapper that checks the flag and releases resources"""
    global eye_control_active, eye_capture
    from .finalmousecontroller import start_eye_mouse
    
    try:
        # Pass the control flag and camera index to the function
        start_eye_mouse(lambda: eye_control_active, cam_index=cam_index)
    finally:
        eye_control_active = False
        if eye_capture:
            try:
                eye_capture.release()
            except Exception:
                pass
            eye_capture = None
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

def hand_gesture_wrapper(cam_index=0):
    """Wrapper that checks the flag and releases resources"""
    global hand_control_active, hand_capture
    from .Gesture_Controller import start
    
    try:
        # Pass the control flag and camera index to the function
        start(lambda: hand_control_active, cam_index=cam_index)
    finally:
        hand_control_active = False
        if hand_capture:
            try:
                hand_capture.release()
            except Exception:
                pass
            hand_capture = None
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

def check_available_cameras(probe_hardware=False, max_tested=4):
    """
    Detects available camera devices.
    If probe_hardware=False, uses fast Windows PnP / defaults without turning on physical camera.
    If probe_hardware=True, physically probes video capture devices.
    """
    if hasattr(cv2, 'setLogLevel'):
        try:
            cv2.setLogLevel(0)
        except Exception:
            pass

    # Try to obtain friendly device names from Windows PnP
    friendly_names = []
    try:
        cmd = ['powershell', '-NoProfile', '-Command', 'Get-PnpDevice -Class Camera, Image -Status OK | Select-Object -ExpandProperty FriendlyName']
        creation_flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        out = subprocess.check_output(cmd, timeout=3, creationflags=creation_flags).decode()
        friendly_names = [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        pass

    if not probe_hardware:
        available = []
        if friendly_names:
            for idx, name in enumerate(friendly_names[:max_tested]):
                available.append({'index': idx, 'name': f"Camera {idx} ({name})"})
        if not available:
            available.append({'index': 0, 'name': 'Camera 0 (Default / Built-in)'})
        return available

    available = []
    for i in range(max_tested):
        try:
            # Probe with CAP_DSHOW on Windows for instant response without freezing
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(i)
            if cap is not None and cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    if i < len(friendly_names) and friendly_names[i]:
                        label = f"Camera {i} ({friendly_names[i]})"
                    elif i == 0:
                        label = "Camera 0 (Default / Built-in)"
                    else:
                        label = f"Camera {i} (External USB {i})"
                    available.append({'index': i, 'name': label})
                cap.release()
        except Exception:
            pass

    # Ensure at least Camera 0 is represented if none opened (e.g. camera temporarily busy)
    if not available:
        label = f"Camera 0 ({friendly_names[0]})" if friendly_names else "Camera 0 (Default / Built-in)"
        available.append({'index': 0, 'name': label})

    return available

@login_required(login_url='login')
@never_cache
def mouse_control_page(request):
    """
    Renders the mouse control selection page with verified connected cameras
    """
    available_cams = check_available_cameras(probe_hardware=False)
    request.session['available_cameras'] = available_cams
    
    selected_cam = request.session.get('selected_cam_index', 0)
    avail_indices = [c['index'] for c in available_cams]
    if selected_cam not in avail_indices and avail_indices:
        selected_cam = avail_indices[0]
        request.session['selected_cam_index'] = selected_cam

    context = {
        'eye_active': eye_control_active,
        'hand_active': hand_control_active,
        'selected_cam': selected_cam,
        'available_cameras': available_cams,
    }
    return render(request, 'mouse_control.html', context)

@login_required(login_url='login')
@never_cache
def mouse_control_eye(request):
    """
    Starts the eye-controlled mouse in a background thread
    """
    global eye_control_active
    
    if eye_control_active:
        messages.warning(request, 'Eye control is already running!')
        return redirect('mouse_control_page')
    
    # Extract chosen camera index
    try:
        cam_index = int(request.GET.get('cam_index', request.POST.get('cam_index', 0)))
    except (ValueError, TypeError):
        cam_index = 0
    request.session['selected_cam_index'] = cam_index

    eye_control_active = True
    
    # Start the eye mouse thread (daemon so it closes with Django)
    t = threading.Thread(target=eye_mouse_wrapper, args=(cam_index,), daemon=True)
    t.start()
    
    messages.success(request, f'Eye-controlled mouse started on Camera {cam_index}!')
    return redirect('mouse_control_page')

@login_required(login_url='login')
@never_cache
def mouse_control_hand(request):
    """
    Starts the hand gesture-controlled mouse
    """
    global hand_control_active
    
    if hand_control_active:
        messages.warning(request, 'Hand control is already running!')
        return redirect('mouse_control_page')
    
    # Extract chosen camera index
    try:
        cam_index = int(request.GET.get('cam_index', request.POST.get('cam_index', 0)))
    except (ValueError, TypeError):
        cam_index = 0
    request.session['selected_cam_index'] = cam_index

    hand_control_active = True
    
    # Start in a thread to avoid blocking
    t = threading.Thread(target=hand_gesture_wrapper, args=(cam_index,), daemon=True)
    t.start()
    
    messages.success(request, f'Hand gesture control started on Camera {cam_index}!')
    return redirect('mouse_control_page')

@login_required(login_url='login')
@never_cache
def stop_mouse_control(request):
    """
    Stops all mouse control threads safely
    """
    global eye_control_active, hand_control_active, eye_capture, hand_capture
    from .camera_stream import stream_manager
    
    was_active = eye_control_active or hand_control_active or stream_manager.is_streaming
    
    eye_control_active = False
    hand_control_active = False
    stream_manager.stop_stream()
    
    # Release camera resources safely
    if eye_capture:
        try:
            eye_capture.release()
        except Exception:
            pass
        eye_capture = None
    if hand_capture:
        try:
            hand_capture.release()
        except Exception:
            pass
        hand_capture = None
    
    # Safely destroy any OpenCV windows without throwing error on headless/missing backends
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
    
    if was_active:
        messages.success(request, 'All camera & mouse control sessions stopped successfully!')
    else:
        messages.info(request, 'No active mouse control to stop.')
    
    return redirect('mouse_control_page')

@csrf_exempt
@login_required(login_url='login')
@never_cache
def get_available_cameras(request):
    """
    API endpoint that dynamically probes available cameras on host machine and returns JSON
    """
    cameras = check_available_cameras(max_tested=4)
    request.session['available_cameras'] = cameras
    return JsonResponse({
        'status': 'success',
        'cameras': cameras,
        'count': len(cameras)
    })

@login_required(login_url='login')
@never_cache
def video_feed(request):
    """
    In-browser MJPEG streaming endpoint for camera preview & virtual mouse detection.
    """
    from .camera_stream import stream_manager
    mode = request.GET.get('mode', 'preview').strip().lower()
    try:
        cam_index = int(request.GET.get('cam_index', 0))
    except (ValueError, TypeError):
        cam_index = 0
    enable_mouse = request.GET.get('enable_mouse', '1') in ['1', 'true', 'True', True]

    return StreamingHttpResponse(
        stream_manager.generate_frames(mode=mode, cam_index=cam_index, enable_mouse=enable_mouse),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


@csrf_exempt
@login_required(login_url='login')
@never_cache
def stop_stream_api(request):
    """
    AJAX endpoint to safely stop the in-browser camera stream and free resources.
    """
    from .camera_stream import stream_manager
    stream_manager.stop_stream()
    return JsonResponse({'status': 'success', 'message': 'Camera stream stopped.'})

@csrf_exempt
@login_required(login_url='login')
@never_cache
def stream_status_api(request):
    """
    AJAX telemetry endpoint to display real-time FPS, detected landmarks, and gestures in the HTML page.
    """
    from .camera_stream import stream_manager
    return JsonResponse({
        'status': 'success',
        'is_streaming': stream_manager.is_streaming,
        'telemetry': stream_manager.get_telemetry()
    })

@csrf_exempt
@login_required(login_url='login')
@never_cache
def set_mouse_control_api(request):
    """
    AJAX endpoint to dynamically toggle system mouse control on/off without restarting the stream.
    """
    from .camera_stream import stream_manager
    enabled_val = request.GET.get('enabled', request.POST.get('enabled', '0'))
    enabled = enabled_val in ['1', 'true', 'True', True]
    stream_manager.set_mouse_enabled(enabled)
    return JsonResponse({
        'status': 'success',
        'mouse_enabled': stream_manager.mouse_enabled
    })

@csrf_exempt
@login_required(login_url='login')
@never_cache
def recalibrate_center_api(request):
    """
    AJAX endpoint to recalibrate the neutral head resting position for eye/head tracking.
    """
    from .camera_stream import stream_manager
    stream_manager.recalibrate_neutral()
    return JsonResponse({
        'status': 'success',
        'message': 'Neutral head center recalibrated.'
    })

def virtual_keyboard(request):
    return render(
        request,
        "virtual_keyboard_test.html"
    )


