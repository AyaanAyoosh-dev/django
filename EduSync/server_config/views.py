import os
import json
import shutil
import datetime
import logging
from collections import defaultdict
from django.views.decorators.csrf import csrf_exempt
from .models import Assignment
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from .models import Assignment, ParentRegistry 
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.conf import settings




# 💻 Django Framework Core Utilities
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.cache import cache
from django.contrib.sessions.models import Session
from django.db import connection
from django.utils import timezone

# 🔐 Authentication Module Packages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

# 🧠 AI Engines
from openai import OpenAI
from dotenv import load_dotenv

# 🗄️ Relational SQLite Models

from .models import Assignment, ParentRegistry, UserProfile

logger = logging.getLogger(__name__)


# ====================================================================
# 🧠 INITIALIZE GLOBAL CLIENT & BUFFERS
# ====================================================================
ACTIVE_SESSION_TEXT_BUFFER = []

# Load environment configuration paths safely
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def clear_system_execution_cache():
    """Flushes cache, active sessions, and temporary wav audio files."""
    print("🧹 Initializing full systemic data-latch clearance...")
    cache.clear()
    
    try:
        Session.objects.all().delete()
    except Exception as session_err:
        print(f"⚠️ Session flush skipped: {session_err}")

    # Purge any remaining temporary WAV files or slices
    project_dir = os.path.dirname(os.path.abspath(__file__))
    temp_slices_dir = os.path.join(settings.MEDIA_ROOT if hasattr(settings, 'MEDIA_ROOT') else project_dir, "temp_slices")
    
    for target_dir in [project_dir, temp_slices_dir]:
        if os.path.exists(target_dir):
            try:
                for file in os.listdir(target_dir):
                    if file.endswith(".wav") or file.startswith("laptop_mic_slice"):
                        os.remove(os.path.join(target_dir, file))
            except Exception as disk_err:
                print(f"⚠️ Audio directory cleanup variance: {disk_err}")

    return True




def transcribe_incoming_chunk(audio_file_path):
    """
    Transcribes local audio files directly via Cloud OpenAI Whisper API 
    and deletes the file upon completion.
    """
    if not os.path.exists(audio_file_path):
        return ""

    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript_response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript_response.text.strip()
    except Exception as cloud_stt_err:
        logger.error(f"❌ OpenAI Cloud STT Failure: {cloud_stt_err}")
        return ""
    finally:
        # Automatic file deletion after transcription finishes
        if os.path.exists(audio_file_path):
            try:
                os.remove(audio_file_path)
                print(f"🗑️ Removed transcribed chunk: {audio_file_path}")
            except Exception as file_err:
                logger.warning(f"⚠️ Failed to delete transcribed chunk {audio_file_path}: {file_err}")


# ====================================================================
# 🔐 MAPPED TEACHER DICTIONARY MATRIX LOGISTICS
# ====================================================================
TEACHER_SUBJECT_MAP = {
    "pratheeba": {"subject": "Mathematics", "last_name": "Ms. Pratheeba"},
    "renarta": {"subject": "English", "last_name": "Ms. Renarta"},
    "bindu": {"subject": "Biology", "last_name": "Ms. Bindu"},
    "sandhya": {"subject": "Chemistry", "last_name": "Ms. Sandhya"},
    "smitha": {"subject": "Physics", "last_name": "Ms. Smitha"},
    "lucy": {"subject": "Social Studies", "last_name": "Ms. Lucy"}
}


# ====================================================================
# 🔐 AUTHENTICATION PORTAL HANDLING VIEWS
# ====================================================================
def portal_select_view(request):
    """Renders the root 3-block selection screen."""
    return render(request, 'portal_select.html')


def teacher_login_view(request):
    """Handles credential checks and guarantees roles match gateway card."""
    target_role = request.GET.get('role', 'STUDENT_PARENT')
    
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        current_session_role = 'ADMIN' if (request.user.is_superuser or request.user.username == 'admin') else profile.role
        
        if current_session_role == target_role:
            return route_user_by_role(request.user)
        else:
            request.session.flush()
            logout(request)

    role_labels = {
        'TEACHER': 'Instructor Terminal',
        'ADMIN': 'System Admin Control',
        'STUDENT_PARENT': 'Student / Parent Portal'
    }
    current_label = role_labels.get(target_role, 'Authentication Gateway')

    error_msg = None
    if request.method == 'POST':
        user_raw = request.POST.get('username', '').strip().lower()
        pass_raw = request.POST.get('password', '').strip()
        
        user = authenticate(request, username=user_raw, password=pass_raw)
        
        if user is not None:
            profile, created = UserProfile.objects.get_or_create(user=user)
            actual_user_role = 'ADMIN' if (user.is_superuser or user.username == 'admin') else profile.role
            
            if actual_user_role != target_role:
                error_msg = f"Access Denied: This account is not registered under the {current_label} directory."
                logout(request) 
            else:
                login(request, user)
                profile.role = target_role
                profile.save()
                return route_user_by_role(user)
        else:
            error_msg = f"Invalid credentials for the {current_label} registry."
            
    return render(request, 'login.html', {
        'error': error_msg,
        'role_title': current_label
    })
        


def route_user_by_role(user):
    """Helper function to route users after authentication."""
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if profile.role in ['ADMIN', 'TEACHER'] or user.is_superuser:
        return redirect('teacher_dashboard')
    elif profile.role == 'STUDENT_PARENT':
        return redirect('student_parent_portal')

    return redirect('teacher_login')


def teacher_logout_view(request):
    """Terminates active user session and redirects to login."""
    request.session.flush()
    logout(request)
    return redirect('portal_select')




# ====================================================================
# 📡 WIRELESS AUDIO INGESTION ROUTER
# ====================================================================
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.files.storage import default_storage
import os
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def route_wireless_audio_payload(request):
    """
    Transcribes audio slices, auto-deletes the source files,
    and saves the transcript into Django Cache mapped to the logged-in user.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "POST method required"}, status=400)

    if 'audio' not in request.FILES:
        return JsonResponse({
            "status": "Warning", 
            "text": "", 
            "message": "No audio payload attached."
        }, status=200)

    audio_file = request.FILES['audio']
    temp_file_path = None

    try:
        # 1. Save temporary audio slice
        temp_file_path = default_storage.save(f"temp_slices/{audio_file.name}", audio_file)
        full_disk_path = default_storage.path(temp_file_path)

        # 2. Transcribe via Whisper
        with open(full_disk_path, "rb") as f:
            transcript_response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        
        text_result = transcript_response.text.strip()

        # 3. Save transcript to Cache using request User ID (or session key fallback)
        if text_result:
            cache_key = f"transcript_buffer_{request.user.id}" if request.user.is_authenticated else "transcript_buffer_anonymous"
            existing_transcript = cache.get(cache_key, "")
            
            # Append new text chunk to existing transcript buffer
            updated_transcript = f"{existing_transcript} {text_result}".strip()
            
            # Persist in cache for 2 hours (7200 seconds)
            cache.set(cache_key, updated_transcript, timeout=7200)

        return JsonResponse({
            "status": "Success", 
            "text": text_result,
            "full_buffer": cache.get(f"transcript_buffer_{request.user.id}", "")
        })

    except Exception as e:
        logger.error(f"❌ Error during audio processing: {e}")
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        # 4. Immediate Auto-Cleanup of audio file
        if temp_file_path and default_storage.exists(temp_file_path):
            try:
                default_storage.delete(temp_file_path)
            except Exception as cleanup_err:
                logger.warning(f"⚠️ Could not delete temp audio file {temp_file_path}: {cleanup_err}")



@csrf_exempt
def compile_and_send_summary_text(request):
    """
    Processes voice transcript and dynamically routes the task:
    - EMAIL -> Sends email directly and marks status as 'SENT'
    - DASHBOARD -> Saves task as 'PENDING' for teacher review on dashboard
    """
    cache_key = f"transcript_buffer_{request.user.id}" if request.user.is_authenticated else "transcript_buffer_anonymous"
    full_lecture_transcript = cache.get(cache_key, "")

    global ACTIVE_SESSION_TEXT_BUFFER
    if not full_lecture_transcript and ACTIVE_SESSION_TEXT_BUFFER:
        full_lecture_transcript = " ".join(ACTIVE_SESSION_TEXT_BUFFER)

    if not full_lecture_transcript or len(full_lecture_transcript.strip()) < 10:
        return JsonResponse({
            "summary_text": "No classroom audio recorded.",
            "delivery_action": "STANDBY"
        })

    try:
        prompt = f"""
        Review this classroom audio transcript: "{full_lecture_transcript}"
        
        Instructions:
        1. Classify the subject: Mathematics, English, Biology, Chemistry, Physics, Social Studies. (Default: 'General Study')
        2. Summarize class recap and homework details.
        3. Identify user intent:
           - If the teacher wants to email parents immediately -> "delivery_action": "EMAIL"
           - If the teacher wants to review/push to web -> "delivery_action": "DASHBOARD"
        
        Format strictly as raw JSON:
        {{
            "subject": "Subject Name",
            "class_recap": "Factual recap sentence.",
            "homework_task": "Details of homework assigned.",
            "spoken_readout": "Brief verbal response to state back to the teacher.",
            "delivery_action": "EMAIL" or "DASHBOARD"
        }}
        """

        ai_completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        parsed_payload = json.loads(ai_completion.choices[0].message.content.strip())
        detected_subject = parsed_payload.get("subject", "General Study").strip()
        delivery_action = parsed_payload.get("delivery_action", "DASHBOARD").upper()
        task_text = f"Today in Class: {parsed_payload.get('class_recap')}\n\nAt Home Task: {parsed_payload.get('homework_task')}"

        # Clear buffer immediately to avoid duplicates
        cache.delete(cache_key)
        ACTIVE_SESSION_TEXT_BUFFER = []

        # Determine status based on teacher intent
        if delivery_action == "EMAIL":
            # 1. Direct Email Branch
            initial_status = 'SENT'
            
            # Fetch parents for this subject/class
            parent_emails = list(ParentRegistry.objects.values_list('email', flat=True))
            if parent_emails:
                try:
                    send_mail(
                        subject=f"[{detected_subject}] Classroom Update & Homework",
                        message=task_text,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=parent_emails,
                        fail_silently=True
                    )
                except Exception as email_err:
                    logger.error(f"Email delivery failed: {email_err}")

        else:
            # 2. Dashboard Review Branch
            initial_status = 'PENDING'

        # Create Assignment record with calculated status
        new_task = Assignment.objects.create(
            teacher=request.user if request.user.is_authenticated else None,
            subject=detected_subject,
            task_details=task_text,
            status=initial_status,
            due_date=datetime.date.today() + datetime.timedelta(days=1)
        )

        return JsonResponse({
            "summary_text": parsed_payload.get("spoken_readout"),
            "delivery_action": delivery_action,
            "status": initial_status,
            "assignment_id": new_task.id
        })

    except Exception as e:
        logger.error(f"❌ Processing fault: {e}")
        return JsonResponse({"summary_text": f"Error: {str(e)}"}, status=500)
# ====================================================================
# 🏫 VISUAL CONTROL TERMINAL INTERFACE PANEL
# ====================================================================
@login_required(login_url='teacher_login')
def teacher_dashboard_view(request):
    """
    Teacher dashboard view showing assigned subject tasks + pending voice tasks.
    """
    current_username = request.user.username.lower()
    
    # Map teacher username to subject
    assigned_subject = None
    for key, data in TEACHER_SUBJECT_MAP.items():
        if key in current_username or current_username in key:
            assigned_subject = data.get("subject")
            break

    if request.user.is_superuser or current_username == 'admin':
        pending_assignments = Assignment.objects.filter(status="PENDING").order_by("-created_at")
        verified_assignments = Assignment.objects.filter(status__in=["VERIFIED", "SENT"]).order_by("-created_at")
    elif assigned_subject:
        # Show pending tasks for this teacher's subject OR pending tasks with 'General Study'
        pending_assignments = Assignment.objects.filter(
            status="PENDING"
        ).filter(
            subject__iexact=assigned_subject
        ) | Assignment.objects.filter(
            status="PENDING", subject="General Study"
        )
        pending_assignments = pending_assignments.order_by("-created_at")

        verified_assignments = Assignment.objects.filter(
            subject__iexact=assigned_subject, 
            status__in=["VERIFIED", "SENT"]
        ).order_by("-created_at")
    else:
        pending_assignments = Assignment.objects.filter(status="PENDING").order_by("-created_at")
        verified_assignments = Assignment.objects.filter(status__in=["VERIFIED", "SENT"]).order_by("-created_at")

    registered_parents = ParentRegistry.objects.all().order_by("email")
    transaction_logs = Assignment.objects.all().order_by("-created_at")[:20]

    context = {
        "pending_assignments": pending_assignments,
        "verified_assignments": verified_assignments,
        "registered_parents": registered_parents,
        "transaction_logs": transaction_logs,
        "assigned_subject": assigned_subject or "All Subjects",
    }

    return render(request, "dashboard.html", context)
# ====================================================================
# 🔘 TEACHER VERIFICATION ACTION ROUTER
# ====================================================================


@login_required(login_url='teacher_login')
def student_parent_portal(request):
    """Unified chronological feed layout for parent monitoring dashboards."""
    if hasattr(request.user, 'profile') and request.user.profile.role != 'STUDENT_PARENT':
        return HttpResponse("Access Denied.", status=403)
        
    all_verified_tasks = Assignment.objects.filter(status__in=['VERIFIED', 'SENT']).order_by('-created_at')
    
    daily_matrix = defaultdict(list)
    for task in all_verified_tasks:
        date_key = task.created_at.strftime("%A, %B %d, %Y")
        daily_matrix[date_key].append(task)
        
    classly_matrix = defaultdict(list)
    for task in all_verified_tasks:
        classly_matrix[task.subject].append(task)
        
    return render(request, 'student_parent_portal.html', {
        'daily_summaries': dict(daily_matrix),
        'classly_summaries': dict(classly_matrix),
        'display_name': request.user.username
    })


import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.utils.html import strip_tags

# Import your models and client here (e.g., Assignment, ParentRegistry, client)
# from .models import Assignment, ParentRegistry

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.conf import settings

# Import your models here (adjust import paths to match your app structure)
from .models import Assignment, ParentRegistry

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.conf import settings

from .models import Assignment, ParentRegistry

@csrf_exempt
def parse_voice_routing_intent(request):
    """
    Handles voice decisions sent from the terminal sensor.
    Renders parents_digest.html with 'homework_list' context key for direct email blasts.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests allowed."}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        spoken_text = data.get("spoken_text", "")
        assignment_id = data.get("assignment_id")

        if not assignment_id:
            return JsonResponse({"error": "Missing assignment_id in payload."}, status=400)

        # Retrieve target assignment
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return JsonResponse({"error": f"Assignment #{assignment_id} not found."}, status=404)

        # Fallback keyword intent determination
        spoken_lower = spoken_text.lower()
        if any(keyword in spoken_lower for keyword in ["blast", "send", "email", "mail"]):
            intent = "BLAST"
        elif any(keyword in spoken_lower for keyword in ["save", "hold", "queue", "dashboard"]):
            intent = "DASHBOARD"
        else:
            intent = "DISCARD"

        # ROUTE 1: EMAIL BLAST
        if intent == "BLAST":
            print(f"🚀 Processing Direct Email Blast for Assignment #{assignment.id}...")

            # 1. Fetch active parent recipients
            recipient_list = list(
                ParentRegistry.objects.filter(is_active=True).values_list('email', flat=True)
            )
            recipient_list = [email for email in recipient_list if email]

            if not recipient_list:
                recipient_list = ['ayushkp8@gmail.com']

            # 2. Update status first
            assignment.status = 'SENT'
            assignment.save()

            # 3. Pass assignment inside 'homework_list' list to match template {% for task in homework_list %}
            context = {
                'homework_list': [assignment]
            }


            

            # 4. Render template and extract plain text
            html_content = render_to_string('parents_digest.html', context)
            plain_message = strip_tags(html_content)

            subject_title = f"📝 New Classroom Update: {assignment.subject} Task"

            # 5. Dispatch Email Blast
            send_mail(
                subject=subject_title,
                message=plain_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@edusync.com'),
                recipient_list=recipient_list,
                html_message=html_content,
                fail_silently=False,
            )

            return JsonResponse({
                "intent": "BLAST",
                "status": "SENT",
                "assignment_id": assignment.id,
                "message": "Email blast dispatched using parents_digest.html template."
            })

        # ROUTE 2: SAVE TO DASHBOARD HOLD QUEUE
        elif intent == "DASHBOARD":
            assignment.status = 'PENDING'
            assignment.save()

            return JsonResponse({
                "intent": "DASHBOARD",
                "status": "PENDING",
                "assignment_id": assignment.id,
                "message": "Assignment saved to dashboard queue."
            })

        # ROUTE 3: DISCARD ASSIGNMENT
        else:
            assignment.delete()
            return JsonResponse({
                "intent": "DISCARD",
                "status": "DELETED",
                "message": "Assignment discarded and deleted."
            })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    except Exception as e:
        print(f"❌ Error in parse_voice_routing_intent: {e}")
        return JsonResponse({"error": str(e)}, status=500)

    
def get_latest_summary_api(request):
    """
    Returns the task details and assignment ID of the most recent pending assignment.
    """
    if request.method == 'GET':
        try:
            latest_assignment = Assignment.objects.filter(status='PENDING').latest('created_at')
            
            return JsonResponse({
                'status': 'success',
                'assignment_id': latest_assignment.id,
                'summary_text': latest_assignment.task_details
            }, status=200)

        except Assignment.DoesNotExist:
            return JsonResponse({
                'status': 'empty',
                'assignment_id': None,
                'summary_text': 'No active assignment queued.'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'error': 'GET method required'}, status=400)
@csrf_exempt
def api_direct_create_assignment(request):
    """Directly inserts structured assignment JSON into SQLite database."""
    if request.method != 'POST':
        return JsonResponse({"error": "POST method required"}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
        subject = data.get('subject', 'General Study')
        task_details = data.get('task_details', '')

        # Fallback for due date string parsing
        raw_due_date = data.get('due_date')
        try:
            due_date = datetime.datetime.strptime(raw_due_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            due_date = datetime.date.today() + datetime.timedelta(days=1)

        # Force database insertion
        new_assignment = Assignment.objects.create(
            subject=subject,
            task_details=task_details,
            due_date=due_date,
            status='PENDING'
        )

        print(f"✅ DB Insert Success: Assignment #{new_assignment.id} saved.")
        return JsonResponse({
            "status": "success",
            "assignment_id": new_assignment.id
        }, status=201)

    except Exception as e:
        logger.error(f"❌ DB Direct Write Failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)







def send_instant_parent_notification(assignment_id, teacher_user=None):
    """Dispatches HTML email containing the single assignment."""
    try:
        single_assignment = Assignment.objects.get(id=int(assignment_id))
        subject_line = f"📝 New Classroom Update: {single_assignment.subject} Task"
        homework_list = [single_assignment]

        parent_emails = list(ParentRegistry.objects.filter(is_active=True).values_list('email', flat=True))
        if not parent_emails:
            parent_emails = ["ayushkp8@gmail.com"]

        html_content = render_to_string('parents_digest.html', {'homework_list': homework_list})
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject_line, 
            text_content, 
            getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER), 
            parent_emails
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        return True
    except Exception as e:
        print(f"❌ Email Gateway failed: {e}")
        return False


@csrf_exempt
@login_required(login_url='teacher_login')
def verify_and_sync_assignment(request, assignment_id):
    """
    Handles both 'verify' and 'approve' routes.
    Updates DB status to VERIFIED, assigns teacher, and sends HTML email blast.
    """
    if request.method == 'POST':
        try:
            task = get_object_or_404(Assignment, id=int(assignment_id))
            
            # Department / User check
            if task.teacher and task.teacher != request.user:
                return JsonResponse({
                    "status": "error", 
                    "message": "This assignment belongs to another department queue."
                }, status=403)
            
            # Assign teacher and verify
            task.teacher = request.user
            task.status = 'VERIFIED'
            task.save()
            
            # Send HTML Email Notification using existing helper
            send_instant_parent_notification(task.id, request.user)

            return JsonResponse({"status": "success", "message": "Task verified and emailed!"})
            
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "POST required"}, status=400)
@csrf_exempt
def reject_assignment_view(request, assignment_id):
    """
    Handles rejecting an assignment card.
    Deletes the task from the database so it disappears upon page refresh.
    """
    if request.method == "POST":
        try:
            assignment = get_object_or_404(Assignment, id=assignment_id)
            assignment.delete()  # Permanently removes from db.sqlite3
            
            return JsonResponse({
                "status": "success", 
                "message": f"Assignment #{assignment_id} rejected and removed."
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "POST request required."}, status=400)


# --- ALIASES (In case your urls.py uses 'approve' instead of 'verify') ---
approve_assignment_view = verify_and_sync_assignment