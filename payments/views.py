import razorpay  # type: ignore[reportMissingImports]
import logging
from decimal import Decimal

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from rides.models import Ride
from .models import Payment

logger = logging.getLogger(__name__)

_razorpay_client = None

def _get_razorpay_client():
    global _razorpay_client
    if _razorpay_client is not None:
        return _razorpay_client
    key_id = (settings.RAZORPAY_KEY_ID or "").strip()
    key_secret = (settings.RAZORPAY_KEY_SECRET or "").strip()
    if not key_id or not key_secret:
        logger.warning(
            "Razorpay not configured: set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env (see .env.example)"
        )
        return None
    try:
        _razorpay_client = razorpay.Client(auth=(key_id, key_secret))
    except Exception as e:
        logger.error(f"Failed to initialize Razorpay client: {e}")
        _razorpay_client = None
    return _razorpay_client


@login_required
def create_order(request, ride_id):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid method'}, status=405)

    ride = get_object_or_404(Ride, id=ride_id, customer=request.user)

    if ride.payment_status == 'paid':
        return JsonResponse({'error': 'Already paid'}, status=400)

    amount = int(Decimal(ride.fare) * 100)

    razorpay_client = _get_razorpay_client()
    if razorpay_client is None:
        logger.error("Razorpay client unavailable when creating order")
        return JsonResponse({'error': 'Payment service unavailable'}, status=500)

    try:
        order = razorpay_client.order.create({
            'amount': amount,
            'currency': 'INR',
            'receipt': f'ride_{ride.id}',
            'payment_capture': 1
        })
    except Exception as e:
        logger.error(f"Order creation failed: {str(e)}")
        return JsonResponse({'error': 'Order creation failed', 'details': str(e)}, status=500)

    payment, created = Payment.objects.get_or_create(
        ride=ride,
        defaults={
            'user': request.user,
            'razorpay_order_id': order['id'],
            'amount': ride.fare,
        }
    )

    if not created:
        payment.razorpay_order_id = order['id']
        payment.status = 'created'
        payment.razorpay_payment_id = None
        payment.razorpay_signature = None
        payment.save()

    pickup_address = (
        ride.pickup_location.get('address', 'Unknown')
        if isinstance(ride.pickup_location, dict) else 'Unknown'
    )
    dropoff_address = (
        ride.dropoff_location.get('address', 'Unknown')
        if isinstance(ride.dropoff_location, dict) else 'Unknown'
    )

    return JsonResponse({
        'order_id': order['id'],
        'amount': amount,
        'key': settings.RAZORPAY_KEY_ID,
        'name': 'Steve Cabs',
        'description': f'Ride from {pickup_address} to {dropoff_address}',
    })


@login_required
def payment_success(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid method'}, status=405)

    data = request.POST
    order_id = data.get('razorpay_order_id')
    payment_id = data.get('razorpay_payment_id')
    signature = data.get('razorpay_signature')

    if not order_id or not payment_id or not signature:
        return JsonResponse({'success': False, 'error': 'Missing Razorpay payment parameters'}, status=400)

    try:
        payment = get_object_or_404(
            Payment,
            razorpay_order_id=order_id,
            user=request.user
        )

        params = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }

        razorpay_client = _get_razorpay_client()
        if razorpay_client is None:
            return JsonResponse({'success': False, 'error': 'Payment service unavailable'}, status=500)

        razorpay_client.utility.verify_payment_signature(params)

        payment.razorpay_payment_id = params['razorpay_payment_id']
        payment.razorpay_signature = params['razorpay_signature']
        payment.status = 'paid'
        payment.save()

        ride = payment.ride
        ride.payment_status = 'paid'
        ride.payment_method = 'razorpay'
        ride.save()

        return JsonResponse({'success': True})

    except Exception as e:
        logger.error(f"Payment verification failed: {str(e)}")

        if 'payment' in locals():
            payment.status = 'failed'
            payment.save()

        return JsonResponse({'success': False, 'error': str(e)}, status=400)
