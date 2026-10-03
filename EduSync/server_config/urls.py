from django.urls import path
from . import views

urlpatterns = [
    # 🔐 Authentication Gates
    path('login/', views.teacher_login_view, name='teacher_login'),
    path('logout/', views.teacher_logout_view, name='teacher_logout'),
    
    # 🏫 Terminal Dashboard Panel Layouts
    path('', views.portal_select_view, name='portal_select'), 
    path('dashboard/', views.teacher_dashboard_view, name='teacher_dashboard'),
    path('portal/hub/', views.student_parent_portal, name='student_parent_portal'), 
    
    # 📡 Hardware Sensor JSON Data Ingestion
    path('api/create-assignment/', views.api_direct_create_assignment, name='create_assignment'),
    path('api/blast-assignment/', views.parse_voice_routing_intent, name='blast_assignment'),
    
    # 🎤 Streaming Audio / File Upload Ingestion
    path('api/receive-audio/', views.route_wireless_audio_payload, name='receive_audio'),
    
    # 🔄 Action & Query Endpoints
    path('api/approve-assignment/<int:assignment_id>/', views.verify_and_sync_assignment, name='approve_assignment'),
    path('api/verify-assignment/<int:assignment_id>/', views.verify_and_sync_assignment, name='verify_assignment'),
    path('api/reject-assignment/<int:assignment_id>/', views.reject_assignment_view, name='reject_assignment'),
    
    path('api/get-summary/', views.compile_and_send_summary_text, name='get_summary'),
    path('api/get-latest-summary/', views.get_latest_summary_api, name='get_latest_summary_api'),
    path('api/parse-intent/', views.parse_voice_routing_intent, name='parse_voice_routing_intent'),
]