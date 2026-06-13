from django.db import models
from accounts.models import User

class Ride(models.Model):
    # # Ride lifecycle: pending → accepted (OTP at pickup) → ongoing → awaiting_ack → completed
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('ongoing', 'Ongoing'),
        ('awaiting_ack', 'Awaiting customer acknowledgment'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rides_as_customer')
    driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides_as_driver')

    pickup_location = models.JSONField()
    dropoff_location = models.JSONField()

    # # Last known vehicle position for this ride (driver app posts here for customer map)
    current_location = models.JSONField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    fare = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=20, default='pending')
    # # razorpay | cash — set when customer pays
    payment_method = models.CharField(max_length=20, blank=True, default='')
    # # Post-ride feedback (after payment)
    customer_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    customer_feedback = models.TextField(blank=True)

    # # Pickup OTP: generated when driver taps "Reach location"; customer reads it to the driver
    pickup_otp = models.CharField(max_length=6, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)

    # # Customer confirms end of trip after driver taps "Reached destination"
    customer_acknowledged_completion = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Message(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class RideRecording(models.Model):
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name='recording')

    audio_file = models.FileField(upload_to='recordings/', blank=True, null=True)

    original_transcript = models.TextField(blank=True)
    english_transcript = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    audio_output = models.FileField(upload_to='audio/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recording for Ride {self.ride.id}"