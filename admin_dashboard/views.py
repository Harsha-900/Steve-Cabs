# # admin_dashboard/views.py — staff-only operations centre (charts, users, rides, tickets)
from datetime import date, timedelta

from django.db.models import Count, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils import timezone
from accounts.models import User
from accounts.forms import RegisterForm
from rides.models import Ride
from tickets.models import Ticket, AdminReply
from rides.llm_ai_helper import get_natural_translation
from rides.voice_helper import generate_voice_note


@staff_member_required
def dashboard(request):
    users = User.objects.all().order_by("-date_joined")
    rides = Ride.objects.all().order_by("-created_at").select_related(
        "customer", "driver", "recording"
    )
    tickets = Ticket.objects.filter(status="open").order_by("-created_at")
    return render(
        request,
        "admin_dashboard/dashboard.html",
        {
            "users": users,
            "rides": rides,
            "tickets": tickets,
            "ride_status_choices": Ride.STATUS_CHOICES,
        },
    )


# # JSON for Chart.js — ride counts by status + last 7 days fare totals
@staff_member_required
def stats_api(request):
    status_counts = list(Ride.objects.values("status").annotate(c=Count("id")))
    today = timezone.localdate()
    daily = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        total = (
            Ride.objects.filter(status="completed", updated_at__date=d).aggregate(
                s=Sum("fare")
            )["s"]
            or 0
        )
        daily.append({"date": d.isoformat(), "fare": float(total)})
    return JsonResponse({"status_counts": status_counts, "daily_fares": daily})


# # Staff creates customer/driver accounts without switching login session
@staff_member_required
def create_user(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("/admin-dashboard/")
    else:
        form = RegisterForm()
    return render(request, "admin_dashboard/create_user.html", {"form": form})


# # Filterable ride history table (defaults to today)
@staff_member_required
def ride_history(request):
    q = request.GET.get("date") or timezone.localdate().isoformat()
    try:
        day = date.fromisoformat(q)
    except ValueError:
        day = timezone.localdate()
    rides = (
        Ride.objects.filter(created_at__date=day)
        .select_related("customer", "driver", "recording")
        .prefetch_related("ticket_set")
        .order_by("-created_at")
    )
    return render(
        request,
        "admin_dashboard/ride_history.html",
        {"rides": rides, "filter_date": day.isoformat()},
    )

@staff_member_required
def resolve_ticket(request, ticket_id):
    if request.method == 'POST':
        ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
        admin_msg = request.POST.get('message')
        driver = ticket.ride.driver

        print(f"DEBUG: Admin message = {admin_msg}")
        print(f"DEBUG: Driver exists? {driver is not None}")
        if driver:
            print(f"DEBUG: Driver language = {driver.language}")

        translated = admin_msg
        audio_url = None
        if driver and driver.language:
            translated = get_natural_translation(admin_msg, driver.language)
            print(f"DEBUG: Translated text = {translated}")
            audio_url = generate_voice_note(translated, driver.language)
            print(f"DEBUG: Generated audio URL = {audio_url}")
        else:
            print("DEBUG: No driver or no language set – skipping audio generation")

        reply = AdminReply.objects.create(
            ticket=ticket,
            message=admin_msg,
            translated_for_driver=translated,
            audio_url=audio_url,
        )
        print(f"DEBUG: Saved AdminReply id={reply.id}, audio_url={reply.audio_url}")

        # # Customer sees this English text after the driver taps Acknowledge on the ticket audio
        ticket.resolution_for_customer = (admin_msg or "").strip()
        ticket.status = "resolved"
        ticket.save()
        return redirect('/admin-dashboard/')
    return JsonResponse({'error': 'Invalid method'}, status=400)

# keep assign_driver and update_ride_status as before
@staff_member_required
def assign_driver(request, ride_id):
    if request.method == 'POST':
        ride = get_object_or_404(Ride, id=ride_id)
        driver_id = request.POST.get('driver_id')
        if driver_id:
            driver = get_object_or_404(User, id=driver_id, role='driver')
            ride.driver = driver
            ride.status = 'accepted'
            ride.save()
        return redirect('/admin-dashboard/')
    return JsonResponse({'error': 'Invalid method'}, status=400)

@staff_member_required
def update_ride_status(request, ride_id):
    if request.method == 'POST':
        ride = get_object_or_404(Ride, id=ride_id)
        new_status = request.POST.get('status')
        if new_status in [
            "pending",
            "accepted",
            "ongoing",
            "awaiting_ack",
            "completed",
            "cancelled",
        ]:
            ride.status = new_status
            ride.save()
        return redirect('/admin-dashboard/')
    return JsonResponse({'error': 'Invalid method'}, status=400)