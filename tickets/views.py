from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import Ticket, AdminReply
from rides.models import Ride
from accounts.models import User

# ✅ CORRECT IMPORTS
from rides.llm_ai_helper import get_natural_translation
from rides.voice_helper import generate_voice_note as generate_voice


# =========================
# CREATE TICKET (USER)
# =========================
@login_required
def create_ticket(request):
    if request.method == 'POST':
        ride_id = request.POST.get('ride_id')

        if not ride_id:
            return JsonResponse({'error': 'Missing ride_id'}, status=400)

        ride = get_object_or_404(Ride, id=ride_id, customer=request.user)

        reason = request.POST.get('reason')
        description = request.POST.get('description')

        if not reason or not description:
            return JsonResponse({'error': 'Missing reason or description'}, status=400)

        ticket = Ticket.objects.create(
            user=request.user,
            ride=ride,
            reason=reason,
            description=description
        )

        return JsonResponse({'ticket_id': ticket.ticket_id})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


# =========================
# ADMIN TICKETS (AI + VOICE)
# =========================
@staff_member_required
def admin_tickets(request):
    tickets = Ticket.objects.all().order_by('-created_at')

    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id')
        message = request.POST.get('message')

        ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
        driver = ticket.ride.driver

        # ✅ Step 1: AI human-style message
        if driver and driver.language:
            translated = get_natural_translation(
                message,
                driver.language
            )

            # ✅ Step 2: generate voice (param name is lang_code, not lang)
            voice_file = generate_voice(translated, driver.language)
        else:
            translated = message
            voice_file = None

        # ✅ Step 3: save reply (driver dashboard reads audio_url; FileField expects a file path, not a URL string)
        AdminReply.objects.create(
            ticket=ticket,
            message=message,
            translated_for_driver=translated,
            audio_url=voice_file,
        )

        # # Step 4: customer-visible English summary (after driver acknowledges ticket audio)
        ticket.resolution_for_customer = (message or "").strip()
        ticket.status = 'resolved'
        ticket.save()

        print("ADMIN TEXT:", message)
        print("DRIVER TEXT:", translated)
        print("VOICE:", voice_file)

        return redirect('/tickets/admin/')

    return render(request, 'tickets/admin_tickets.html', {
        'tickets': tickets
    })
@login_required
def driver_tickets(request):
    tickets = Ticket.objects.filter(
        ride__driver=request.user,
        status='resolved',
        acknowledged_by_driver=False
    ).prefetch_related('replies')
    data = []
    for t in tickets:
        replies = t.replies.all().order_by('-created_at')
        data.append({
            'ticket_id': t.ticket_id,
            'replies': [{
                'message': r.message,
                'translated_for_driver': r.translated_for_driver,
                'audio_url': r.audio_url or (
                    r.voice_note.url if r.voice_note and r.voice_note.name else None
                ),
            } for r in replies]
        })
    return JsonResponse(data, safe=False)