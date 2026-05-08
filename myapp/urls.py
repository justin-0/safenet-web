from django.urls import path

from myapp import views

urlpatterns = [
    path('',views.home,name='home'),
    path('login_view/',views.login,name='login'),
    path('logout_view/',views.logout_view,name='logout_view'),

    # =================== admin ================================================
    path('admin_home', views.admin_home, name='admin_home'),

    path('admin_add_authority/', views.admin_add_authority, name='admin_add_authority'),
    path('admin_view_authority/', views.admin_view_authority, name='admin_view_authority'),
    path('admin_delete_authority/<int:id>/', views.admin_delete_authority, name='admin_delete_authority'),

    path('admin_detect_unauthorized_entries/',views.admin_detect_unauthorized_entries,name='admin_detect_unauthorized_entries'),

    path('admin_category/', views.admin_category, name='admin_category'),
    path('admin_delete_category/<int:id>/', views.admin_delete_category, name='admin_delete_category'),
    path('admin_edit_category/<int:id>/', views.admin_edit_category, name='admin_edit_category'),

    path('admin_view_residents/', views.admin_view_residents, name='admin_view_residents'),
    path('admin_view_resident_complaints/<int:rid>/', views.admin_view_resident_complaints,
         name='admin_view_resident_complaints'),
    path('admin_view_workers/', views.admin_view_workers, name='admin_view_workers'),
    path('admin_view_worker_request_history/<int:wid>/', views.admin_view_worker_request_history,
         name='admin_view_worker_request_history'),

    path('admin_add_camera/', views.admin_add_camera, name='admin_add_camera'),
    path('admin_edit_camera/<int:cid>/', views.admin_edit_camera, name='admin_edit_camera'),
    path('admin_delete_camera/<int:cid>/', views.admin_delete_camera, name='admin_delete_camera'),

    path('admin_view_stray_dog_alerts/', views.admin_view_stray_dog_alerts, name='admin_view_stray_dog_alerts'),
    path('admin_view_unauthorized_entries', views.admin_view_unauthorized_entries,
         name="admin_view_unauthorized_entries"),
    path('admin_view_emergency_alerts/', views.admin_view_emergency_alerts, name='admin_view_emergency_alerts'),

    # ==================== authority =========================================
    path('authority_home', views.authority_home, name='authority_home'),
    path('authority_profile', views.authority_profile, name='authority_profile'),
    path('authority_edit_profile', views.authority_edit_profile, name='authority_edit_profile'),

    path('authority_view_resident/', views.authority_view_resident, name='authority_view_resident'),
    path('authority_approve_resident/<int:rid>/', views.authority_approve_resident, name='authority_approve_resident'),
    path('authority_reject_resident/<int:rid>/', views.authority_reject_resident, name='authority_reject_resident'),

    path('authority_view_worker/', views.authority_view_worker, name='authority_view_worker'),
    path('authority_approve_worker/<int:wid>/', views.authority_approve_worker, name='authority_approve_worker'),
    path('authority_reject_worker/<int:wid>/', views.authority_reject_worker, name='authority_reject_worker'),
    path('authority_view_cameras/', views.authority_view_cameras, name='authority_view_cameras'),

    path('authority_view_resident_complaints/', views.authority_view_resident_complaints,
         name='authority_view_resident_complaints'),
    path('authority_send_reply/<int:cid>/', views.authority_send_reply, name='authority_send_reply'),

    path('authority_view_stray_dog_alerts/', views.authority_view_stray_dog_alerts,
         name='authority_view_stray_dog_alerts'),
    path('authority_view_unauthorized_entries/<int:cam_id>', views.authority_view_unauthorized_entries,
         name='authority_view_unauthorized_entries'),
    path('authority_change_password', views.authority_change_password, name='authority_change_password'),
    path('authority_view_worker_request_history/<int:wid>', views.authority_view_worker_request_history,
         name='authority_view_worker_request_history'),
    path('authority_view_emergency_alerts/', views.authority_view_emergency_alerts,
         name='authority_view_emergency_alerts'),

    # ================== app =======================================================
    path('login_app/',views.login_app,name='login_app'),

    # ================================ resident ===================================

    path('resident_register/', views.resident_register, name='resident_register'),
    path('resident_profile/', views.resident_profile, name='resident_profile'),
    path('resident_editprofile/', views.resident_editprofile, name='resident_editprofile'),

    path('resident_add_familymember/', views.resident_add_familymember, name='resident_add_familymember'),
    path('resident_view_familymembers/', views.resident_view_familymembers, name='resident_view_familymembers'),
    path('resident_edit_familymember/', views.resident_edit_familymember, name='resident_edit_familymember'),
    path('resident_delete_familymember/', views.resident_delete_familymember, name='resident_delete_familymember'),

    path('resident_send_complaint/', views.resident_send_complaint, name='resident_send_complaint'),
    path('resident_view_complaints/', views.resident_view_complaints, name='resident_view_complaints'),

    path('resident_view_workers/', views.resident_view_workers,name='resident_view_workers'),
    path('resident_send_worker_request/', views.resident_send_worker_request,name='resident_view_workers'),

    path('emergency_alert/', views.emergency_alert,name='emergency_alert'),
    path('send_stray_dog_alert/', views.send_stray_dog_alert,name='send_stray_dog_alert'),
    path('view_stray_dog_alerts/', views.view_stray_dog_alerts,name='view_stray_dog_alerts'),
    path('delete_stray_dog_alert/', views.delete_stray_dog_alert,name='delete_stray_dog_alert'),

    # ================================ worker ===================================

    path('worker_register/', views.worker_register, name='worker_register'),
    path('worker_get_categories/', views.worker_get_categories, name='worker_get_categories'),
    path('worker_profile/', views.worker_profile, name='worker_profile'),
    path('worker_editprofile/', views.worker_editprofile, name='worker_editprofile'),

    path('worker_view_requests/', views.worker_view_requests,name='worker_view_requests'),
    path('worker_accept_request/', views.worker_accept_request,name='worker_accept_request'),
    path('worker_reject_request/', views.worker_reject_request,name='worker_reject_request'),

    #===================== chat ====================================================

    path('resident_view_authorities/', views.resident_view_authorities, name='resident_view_authorities'),
    path('resident_send_chat/', views.resident_send_chat, name='resident_send_chat'),
    path('resident_view_chat/', views.resident_view_chat, name='resident_view_chat'),

    path('authority_view_approved_residents/', views.authority_view_approved_residents,name='authority_view_approved_residents'),
    path('authority_send_chat/', views.authority_send_chat, name='authority_send_chat'),
    path('authority_view_chat/', views.authority_view_chat, name='authority_view_chat'),




]