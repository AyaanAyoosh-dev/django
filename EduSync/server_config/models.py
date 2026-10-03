from django.db import models
from django.contrib.auth.models import User

# ====================================================================
# 🗄️ MULTI-PORTAL ROLE ASSIGNMENT SCHEMA
# ====================================================================
class UserProfile(models.Model):
    USER_ROLES = [
        ('TEACHER', 'Teacher'),
        ('STUDENT_PARENT', 'Student / Parent'),
        ('ADMIN', 'System Admin'),
    ]
    # Links this profile directly to a standard Django User account
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=15, choices=USER_ROLES, default='STUDENT_PARENT')

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


# ====================================================================
# 🎙️ CORE CLASSROOM EDGE ASSET SCHEMAS
# ====================================================================
class Assignment(models.Model):
    """Stores voice-extracted tasks bound to a specific authenticated teacher account."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('VERIFIED', 'Verified & Synced'),
    ]
    
    # 🔗 LINK TO DJANGO AUTHENTICATED USER TABLE
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    subject = models.CharField(max_length=100, default="General Study")
    task_details = models.TextField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        teacher_name = self.teacher.username if self.teacher else "Unassigned"
        return f"{self.subject} ({teacher_name}) - {self.status}"


class ParentRegistry(models.Model):
    """Global contact registry for parent update blasts."""
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email