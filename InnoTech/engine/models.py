from django.db import models

from django.contrib.auth.models import User
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('worker', 'Factory Floor Worker'),
        ('safety_officer', 'Safety Officer'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    factory_name = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.factory_name} ({self.role})"


class BatchRun(models.Model):
    """Stores industrial XRF telemetry, final recipe, and audit status for each batch."""
    serial_number = models.CharField(max_length=100, unique=True)
    factory_name = models.CharField(max_length=255)
    worker_username = models.CharField(max_length=150)
    xrf_data = models.TextField()
    final_recipe = models.TextField(blank=True, null=True)
    final_score = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default="PENDING_REVIEW")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Batch {self.serial_number} - Score: {self.final_score}/100"


class AgentDebateTurn(models.Model):
    """Stores the step-by-step multi-agent chat history for a specific batch run."""
    batch = models.ForeignKey(BatchRun, related_name='debate_turns', on_delete=models.CASCADE)
    turn_number = models.IntegerField()
    chemist_proposal = models.TextField()
    peer_critique = models.TextField()
    auditor_critique = models.TextField()
    safety_score = models.IntegerField()
    hazards = models.TextField()

    def __str__(self):
        return f"Batch {self.batch.serial_number} - Turn {self.turn_number}"