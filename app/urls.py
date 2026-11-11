from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login_view'),
    path('register/', views.register_view, name='register'),
    path('permission/', views.permission_view, name='permission'),
    path('dashboard/', views.dashboard_view, name='dashboard'), 
    path('callibration/', views.callibration_view, name='callibration'),
    path('camera/', views.camera_view, name='camera'),
    path('livetracking_interface/', views.tracking_view, name='LiveTracking'),
    path('profile/', views.profile_view, name='Profile'),
    path('complaint/', views.complaint, name='complaint'),
    path('my_complaints/', views.my_complaints_view, name='MyComplaints'),
    path('feedback/', views.feedback_view, name='Feedback'),
    path('adminlogin/',views.adminlogin_view, name='adminlogin'),
    path('admindashboard/',views.admindashboard_view, name='admindashboard'),
    path('complaintmanagement/',views.complaint_management_view, name='complaintmanagement'),
    path('reply_complaint/<int:complaint_id>/', views.reply_complaint_view, name='reply_complaint'),
    path('usermanagement/',views.user_management_view, name='usermanagement'),
    path('feedbackmanagement/',views.feedback_management_view, name='feedbackmanagement'),
    path('logout/', views.logout_view, name='logout'),
    path('face_scan/', views.face_scan_page, name='face_scan_page'),
    path('start_face_scan/', views.start_face_scan, name='start_face_scan'),
    path('stop_face_scan/', views.stop_face_scan, name='stop_face_scan'),
    path('my_feedback/', views.my_feedback_view, name='my_feedback'),
    path('gesture/',views.gesture_view, name='gesture'),
    path("virtual-keyboard/",views.virtual_keyboard,name="virtual_keyboard"),





    path('mouse_control_eye/',views.mouse_control_eye,name='mouse_control_eye'),
    path('mouse_control_hand/',views.mouse_control_hand,name='mouse_control_hand'),
    path('mouse_control/', views.mouse_control_page, name='mouse_control_page'),
    path('stop_mouse_control/', views.stop_mouse_control, name='stop_mouse_control'),
    path('api/get_available_cameras/', views.get_available_cameras, name='get_available_cameras'),
    path('video_feed/', views.video_feed, name='video_feed'),
    path('api/stop_stream/', views.stop_stream_api, name='stop_stream_api'),
    path('api/stream_status/', views.stream_status_api, name='stream_status_api'),
    path('api/set_mouse_control/', views.set_mouse_control_api, name='set_mouse_control_api'),
    path('api/recalibrate_center/', views.recalibrate_center_api, name='recalibrate_center_api'),
]
