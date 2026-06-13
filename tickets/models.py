from django.db import models
from accounts.models import User
from rides.models import Ride

class Ticket(models.Model):
    REASON_CHOICES = [
        ('extra_money','Driver asking extra money'),
        ('delay','Excessive delay'),
        ('other','Other')
    ]

    STATUS_CHOICES = [
        ('open','Open'),
        ('resolved','Resolved')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    ticket_id = models.CharField(max_length=10, unique=True, blank=True)
    acknowledged_by_driver = models.BooleanField(default=False)
    audio_url = models.URLField(max_length=500, blank=True, null=True)

    # # English summary from admin shown to customer after driver acknowledges the ticket reply
    resolution_for_customer = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            import random, string
            self.ticket_id = ''.join(random.choices(string.digits, k=8))
        super().save(*args, **kwargs)


class AdminReply(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='replies')
    message = models.TextField()
    translated_for_driver = models.TextField(blank=True)
    audio_url = models.URLField(max_length=500, blank=True, null=True)
    voice_note = models.FileField(upload_to='voice_notes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)