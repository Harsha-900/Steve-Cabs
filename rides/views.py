import json
import math
import subprocess
import os
import uuid
import random
import shutil

from django.db.models import Sum
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt

from .models import Ride, Message, RideRecording
from tickets.models import Ticket
from .transcribe_helper import transcribe_audio, translate_with_qwen, generate_audio


# # ---------------------------------------------------------------------------
# # FFmpeg: use FFMPEG_BINARY in settings, PATH, or common Windows dev path
# # ---------------------------------------------------------------------------
def _ffmpeg_executable():
    configured = getattr(settings, "FFMPEG_BINARY", "") or os.environ.get("FFMPEG_BINARY", "")
    if configured and os.path.isfile(configured):
        return configured
    which = shutil.which("ffmpeg")
    if which:
        return which
    fallback = r"C:\Users\steph\OneDrive\Desktop\ffmpeg\bin\ffmpeg.exe"
    if os.path.isfile(fallback):
        return fallback
    return "ffmpeg"


# ---------------- BASIC ----------------
def landing(request):
    return render(request, 'rides/landing.html')


@login_required
def dashboard(request):
    if request.user.role == 'driver':
        return redirect('/rides/driver/')
    # # Past trips for “ride history” panel on customer dashboard
    past_rides = (
        Ride.objects.filter(customer=request.user)
        .select_related("driver")
        .order_by("-created_at")[:40]
    )
    return render(request, "rides/user_dashboard.html", {"past_rides": past_rides})


# ---------------- DISTANCE ----------------
def calculate_distance(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


# ---------------- REQUEST RIDE ----------------
@login_required
def request_ride(request):
    data = json.loads(request.body)

    distance = calculate_distance(
        data['pickup']['lat'], data['pickup']['lng'],
        data['dropoff']['lat'], data['dropoff']['lng']
    )

    fare = round(distance * 2, 2)

    ride = Ride.objects.create(
        customer=request.user,
        pickup_location=data['pickup'],
        dropoff_location=data['dropoff'],
        fare=fare
    )

    return JsonResponse({'ride_id': ride.id, 'fare': fare})


# ---------------- DRIVER DASHBOARD ----------------
@login_required
def driver_dashboard(request):
    # # Active work: accepted (pickup OTP), ongoing (recording), awaiting customer ack
    upcoming = (
        Ride.objects.filter(
            driver=request.user,
            status__in=["accepted", "ongoing", "awaiting_ack"],
        )
        .select_related("customer", "recording")
        .order_by("created_at")
    )
    pending = Ride.objects.filter(status="pending").select_related("customer").order_by("-created_at")
    completed = (
        Ride.objects.filter(driver=request.user, status="completed")
        .select_related("recording")
        .order_by("-updated_at")[:25]
    )

    # # Sum fares for rides completed today (local date) — "amount received for the day"
    today = timezone.localdate()
    # # All completed trips today (fare totals) — payment settlement can be separate
    today_earnings = (
        Ride.objects.filter(
            driver=request.user,
            status="completed",
            updated_at__date=today,
        ).aggregate(total=Sum("fare"))["total"]
        or 0
    )

    return render(
        request,
        "rides/driver_dashboard.html",
        {
            "upcoming": upcoming,
            "pending": pending,
            "completed": completed,
            "today_earnings": today_earnings,
        },
    )


# ---------------- RIDE FLOW ----------------
@login_required
def accept_ride(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, status="pending")
    ride.driver = request.user
    ride.status = "accepted"
    ride.pickup_otp = None
    ride.otp_verified = False
    ride.save()
    return JsonResponse({"success": True})


# # Driver arrived at pickup — creates OTP for customer to read aloud
@login_required
def reach_pickup(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, driver=request.user, status="accepted")
    ride.pickup_otp = "".join(str(random.randint(0, 9)) for _ in range(6))
    ride.otp_verified = False
    ride.save()
    return JsonResponse({"success": True, "message": "OTP sent to customer app."})


# # Driver types the OTP the customer told them
@login_required
def verify_pickup_otp(request, ride_id):
    data = json.loads(request.body or "{}")
    otp = (data.get("otp") or "").strip()
    ride = get_object_or_404(Ride, id=ride_id, driver=request.user, status="accepted")
    if ride.pickup_otp and otp == ride.pickup_otp:
        ride.otp_verified = True
        ride.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Invalid OTP"}, status=400)


@login_required
def start_ride(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, driver=request.user, status="accepted")
    # # Trip only starts after pickup OTP is verified (customer confirms verbally)
    if not ride.otp_verified:
        return JsonResponse({"success": False, "error": "Verify pickup OTP first"}, status=400)
    ride.status = "ongoing"
    ride.save()
    return JsonResponse({"success": True})


# # Driver finished trip — recording upload should run before/around this call from the browser
@login_required
def reach_destination(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, driver=request.user, status="ongoing")
    ride.status = "awaiting_ack"
    ride.save()
    return JsonResponse({"success": True})


# # Legacy endpoint kept for older clients; payment stays pending until Razorpay succeeds
@login_required
def complete_ride(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, driver=request.user)
    ride.status = "completed"
    ride.customer_acknowledged_completion = True
    ride.payment_status = "pending"
    ride.save()
    return JsonResponse({"success": True})


# # Customer confirms they are dropped off — unlocks payment screen
@login_required
def customer_acknowledge_ride(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, customer=request.user, status="awaiting_ack")
    ride.customer_acknowledged_completion = True
    ride.status = "completed"
    ride.payment_status = "pending"
    ride.save()
    return JsonResponse({"success": True})


# # Mark ride paid offline — cash (no Razorpay signature)
@login_required
def pay_cash(request, ride_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    ride = get_object_or_404(Ride, id=ride_id, customer=request.user)
    if ride.status != "completed" or ride.payment_status == "paid":
        return JsonResponse({"error": "Invalid ride state"}, status=400)
    ride.payment_status = "paid"
    ride.payment_method = "cash"
    ride.save()
    return JsonResponse({"success": True})


# # Star rating + comment after payment
@login_required
def submit_ride_feedback(request, ride_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    data = json.loads(request.body or "{}")
    ride = get_object_or_404(Ride, id=ride_id, customer=request.user)
    if ride.payment_status != "paid":
        return JsonResponse({"error": "Pay for the ride first"}, status=400)
    if ride.customer_rating is not None:
        return JsonResponse({"error": "Feedback already saved"}, status=400)
    rating = int(data.get("rating") or 0)
    if rating < 1 or rating > 5:
        return JsonResponse({"error": "Pick 1–5 stars"}, status=400)
    ride.customer_rating = rating
    ride.customer_feedback = (data.get("comment") or "")[:4000]
    ride.save()
    return JsonResponse({"success": True})


# ---------------- RIDE STATUS ----------------
@login_required
def get_ride_status(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id)
    ticket = Ticket.objects.filter(ride=ride).first()
    ticket_status = None
    ticket_id = ticket.ticket_id if ticket else None
    resolution_for_customer = ""

    # # Ticket UX for customer: open → admin resolved → driver acknowledged → show English resolution
    if ride.customer == request.user and ticket:
        if ticket.status == "open":
            ticket_status = "open"
        elif ticket.status == "resolved":
            if ticket.acknowledged_by_driver and ticket.resolution_for_customer:
                ticket_status = "resolved_acknowledged"
                resolution_for_customer = ticket.resolution_for_customer
            elif ticket.acknowledged_by_driver:
                ticket_status = "resolved_acknowledged"
            else:
                ticket_status = "resolved_no_ack"

    pickup_otp = None
    if ride.customer == request.user and ride.pickup_otp and not ride.otp_verified:
        pickup_otp = ride.pickup_otp

    payload = {
        "status": ride.status,
        "driver": ride.driver.username if ride.driver else None,
        "fare": str(ride.fare) if ride.fare else None,
        "payment_status": ride.payment_status,
        "ticket_status": ticket_status,
        "ticket_id": ticket_id,
        "pickup_otp": pickup_otp,
        "otp_verified": ride.otp_verified,
        "driver_location": ride.current_location,
    }
    # # Customer-only fields for ticket closure messaging
    if ride.customer == request.user:
        payload["resolution_for_customer"] = resolution_for_customer
        payload["show_feedback"] = (
            ride.status == "completed"
            and ride.payment_status == "paid"
            and ride.customer_rating is None
        )
        payload["feedback_done"] = ride.customer_rating is not None
    return JsonResponse(payload)


# ---------------- CHAT ----------------
@login_required
def send_message(request):
    data = json.loads(request.body)
    ride = get_object_or_404(Ride, id=data['ride_id'])

    Message.objects.create(
        ride=ride,
        sender=request.user,
        text=data['text']
    )
    return JsonResponse({'success': True})


@login_required
def get_messages(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id)
    msgs = Message.objects.filter(ride=ride).values('sender__username', 'text', 'created_at')
    return JsonResponse(list(msgs), safe=False)


# ---------------- RECORDING + TRANSCRIBE ----------------
@csrf_exempt
@login_required
def upload_recording(request, ride_id):
    # # Trip audio: always store WebM first; FFmpeg/AI optional so admin can still play raw clip
    ride = get_object_or_404(Ride, id=ride_id)
    if ride.driver_id != request.user.id:
        return JsonResponse({"error": "Only the assigned driver can upload"}, status=403)

    audio = request.FILES.get("audio")
    if not audio:
        return JsonResponse({"error": "No audio"}, status=400)

    rec, _ = RideRecording.objects.get_or_create(ride=ride)
    rec.audio_file.save(f"ride_{ride_id}.webm", audio)
    rec.save()

    src = rec.audio_file.path
    wav_path = src.replace(".webm", ".wav")
    ffmpeg_ok = False
    try:
        subprocess.run(
            [
                _ffmpeg_executable(),
                "-y",
                "-i",
                src,
                "-ar",
                "16000",
                "-ac",
                "1",
                wav_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            check=False,
        )
        ffmpeg_ok = os.path.isfile(wav_path) and os.path.getsize(wav_path) > 0
    except Exception as e:
        print("FFmpeg (non-fatal):", e)

    transcribe_path = wav_path if ffmpeg_ok else src
    try:
        text, lang = transcribe_audio(transcribe_path)
        print("TRANSCRIBED:", text, "LANG:", lang)
        rec.original_transcript = text if text else "NO SPEECH DETECTED"
        translated = translate_with_qwen(text)
        rec.english_transcript = translated if translated else text
        audio_path = os.path.join(settings.MEDIA_ROOT, f"audio/ride_{ride_id}.mp3")
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        generate_audio(translated, audio_path)
        rec.audio_output.name = f"audio/ride_{ride_id}.mp3"
    except Exception as e:
        print("AI pipeline (recording still saved):", e)
        rec.original_transcript = rec.original_transcript or "PROCESSING_PENDING"
        rec.english_transcript = rec.english_transcript or ""

    rec.save()

    return JsonResponse(
        {
            "success": True,
            "recording_url": rec.audio_file.url if rec.audio_file else None,
            "text": rec.original_transcript,
            "translated": rec.english_transcript,
            "audio": rec.audio_output.url if rec.audio_output else None,
        }
    )


def _admin_reply_audio_url(reply):
    """URL exposed to driver dashboard: prefer explicit audio_url, else uploaded voice_note file."""
    if reply.audio_url:
        return reply.audio_url
    f = reply.voice_note
    if not f or not getattr(f, "name", None):
        return None
    try:
        return f.url
    except ValueError:
        return None


# ---------------- DRIVER TICKETS ----------------
@login_required
def driver_tickets(request):
    # # Absolute URLs so <audio src> always resolves (localhost / LAN / HTTPS)
    def abs_media(path):
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return request.build_absolute_uri(path)

    tickets = Ticket.objects.filter(
        ride__driver=request.user,
        status="resolved",
        acknowledged_by_driver=False,
    ).prefetch_related("replies")

    data = []
    for t in tickets:
        replies = t.replies.all().order_by("-created_at")
        data.append(
            {
                "ticket_id": t.ticket_id,
                "replies": [
                    {
                        "translated_for_driver": r.translated_for_driver,
                        "audio_url": abs_media(_admin_reply_audio_url(r)),
                    }
                    for r in replies
                ],
            }
        )
    return JsonResponse(data, safe=False)

# ---------------- LOCATION UPDATE ----------------
@csrf_exempt
@login_required
def update_location(request):
    data = json.loads(request.body)

    ride = get_object_or_404(Ride, id=data.get("ride_id"))

    ride.current_location = {
        "lat": data.get("lat"),
        "lng": data.get("lng")
    }
    ride.save()

    return JsonResponse({"success": True})


# ---------------- ACKNOWLEDGE TICKET ----------------
@login_required
def acknowledge_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
    ticket.acknowledged_by_driver = True
    ticket.save()
    return JsonResponse({"success": True})
# # JSON list of processed trip recordings — staff only (admin analytics panel)
@staff_member_required
def admin_recordings(request):
    recs = RideRecording.objects.all().order_by("-id")

    def absu(u):
        if not u:
            return None
        return u if u.startswith("http") else request.build_absolute_uri(u)

    data = []
    for r in recs:
        data.append(
            {
                "ride_id": r.ride.id,
                "audio": absu(r.audio_file.url if r.audio_file else None),
                "text": r.original_transcript,
                "translated": r.english_transcript,
                "tts": absu(r.audio_output.url if r.audio_output else None),
            }
        )

    return JsonResponse({"recordings": data})