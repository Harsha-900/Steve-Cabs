# Steve Cabs — junior developer guide

This document explains how the project is put together so you can run it locally, follow a ride from booking to payment, and know where to change things.

## What this app is

Steve Cabs is a Django web app for a simple ride-hailing flow: customers book rides, drivers accept and complete trips, staff can use an admin-style dashboard. It uses **SQLite** by default, **Razorpay (test mode)** for card/UPI-style checkout, and optional extras (maps, tickets, recordings) depending on configuration.

There are three “hats” you should know:

| Role | Typical account | What they do |
|------|-----------------|--------------|
| **Customer (rider)** | Normal user | Books rides, pays (Razorpay or cash), rates trip |
| **Driver** | User flagged as driver in the system | Sees requests, navigates flow (pickup OTP, destination, etc.) |
| **Staff / admin** | Superuser or staff URLs | Tickets, ride history, charts (varies by URL) |

Exact flags and URLs live in `accounts`, `rides`, and `admin_dashboard` — search for `is_driver` or staff checks in views if you need details.

## One-time setup

1. **Python 3** with a virtual environment (the repo may include `venv/`; if not, create one).

   ```text
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment variables** — copy the example file and edit **only on your machine**:

   ```text
   copy .env.example .env
   ```

   Open `.env` and set at least:

   - `RAZORPAY_KEY_ID` — from [Razorpay Dashboard](https://dashboard.razorpay.com/app/keys) in **Test mode**
   - `RAZORPAY_KEY_SECRET` — same place, **never** paste this into chat, screenshots, or git

   **Security rule:** `.env` is listed in `.gitignore`. If keys ever leak, **rotate them** in the Razorpay dashboard and update your local `.env` only.

3. **Database**

   ```text
   python manage.py migrate
   ```

4. **Create a superuser** (for admin / staff pages)

   ```text
   python manage.py createsuperuser
   ```

5. **Run the server**

   ```text
   python manage.py runserver
   ```

   Open the URL Django prints (usually `http://127.0.0.1:8000/`).

## Where the code lives (mental map)

| Area | Path | Purpose |
|------|------|---------|
| Project settings | `steve_cabs/settings.py` | DB, static files, media, `RAZORPAY_*` from environment |
| Rides (core domain) | `rides/` | Models, views, URLs for booking and driver flow |
| Payments | `payments/` | Create Razorpay order, verify signature, mark ride paid |
| Tickets | `tickets/` | Support tickets and admin reply UI |
| Admin dashboard | `admin_dashboard/` | Staff views (history, charts, etc.) |
| Templates | `*/templates/` | HTML; rider/driver dashboards extend `rides/base.html` |
| CSS / JS | `static/css/style.css`, `static/js/*.js` | Theme, dashboard subnav, map, Razorpay checkout on rider side |

When you change behavior, start from the **view** that handles the URL, then the **template** and **JS** that call it.

## Rider dashboard layout (blocks + nav)

The rider and driver pages use a **sticky horizontal subnav** (pill buttons) that scrolls to **sections** on the same page. Each section is a “block” (`.dash-section.dashboard-card` inside `.dash-shell`). Styling is in `static/css/style.css` (look for `.dash-subnav`, `.dash-shell`, `.dashboard-card`).

If nav links look wrong, check that section elements have stable `id` attributes and that `static/js/dash_subnav.js` is loaded — it marks the active pill while scrolling.

## Payments — how Razorpay fits in (for juniors)

**Important:** The **secret key** is only used on the **server**. The browser only receives the **Key ID** (public) when opening the Razorpay Checkout popup.

High-level sequence:

1. Customer finishes a ride and chooses online pay.
2. **Frontend** (`static/js/user_dashboard.js`) sends `POST` to  
   `/payments/create_order/<ride_id>/` (with CSRF cookie/header as for other Django POSTs).
3. **Backend** (`payments/views.py`, `create_order`) uses the Razorpay Python SDK with `RAZORPAY_KEY_ID` + `RAZORPAY_KEY_SECRET` to create an **order** (amount in **paise**, i.e. rupees × 100).
4. The JSON response includes `order_id`, `amount`, and `key` (Key ID) for Checkout.js.
5. The script opens **Razorpay Checkout**; after success, Razorpay returns `razorpay_payment_id` and `razorpay_signature`.
6. **Frontend** posts those to `payment_success` (verify path in `payments/urls.py`) so the server can **verify the signature** with the secret. Only if verification succeeds does the app set the ride to paid and store `payment_method='razorpay'`.

**Cash** is a separate path (e.g. `pay_cash` in rides) — no Razorpay involved.

If you see `Payment service unavailable` or 500 on create order, check:

- `.env` exists next to `manage.py` and contains both Razorpay variables (no quotes needed unless your value has spaces).
- Server was **restarted** after editing `.env`.
- Django logs for the warning: keys missing vs API error.

## Typical ride flow (conceptual)

Exact names may vary — read `rides/models.py` (`Ride` statuses) and `rides/views.py`:

1. Customer creates / requests a ride.
2. Driver accepts; pickup may use **OTP** verification (`pickup_otp`, `verify_pickup_otp`, etc.).
3. Trip progresses to destination; customer may **acknowledge** completion.
4. **Payment**: Razorpay or cash; feedback/rating may follow.

Use the browser **Network** tab and Django **runserver** logs when debugging step-by-step.

## Media and recordings

Uploaded files (e.g. audio) go under `MEDIA_ROOT` (see `settings.py`). For production you would use real storage (S3, etc.); locally, files sit in `media/`.

## Optional integrations

- **FFmpeg** — path can be set in `.env` as `FFMPEG_BINARY` on Windows if not on `PATH`.
- **AI / TTS** — ticket copy and driver voice features depend on optional services and keys; if something is “optional”, failures should not always block core ride flow — check the view code.

## How to explain this to a new junior (short script)

You can say:

1. “Clone or copy the project, create a venv, `pip install -r requirements.txt`, `migrate`, add `.env` from `.env.example` with **test** Razorpay keys.”
2. “Django serves HTML; our business logic is mostly in `rides` and `payments`. Templates in `rides/templates`, behavior in `static/js`.”
3. “Razorpay: server creates the order with the **secret**; browser only gets the **Key ID**; after pay, server **verifies the signature** — that’s what makes it safe.”
4. “Never commit `.env` or secrets; use test keys until you deploy, then use live keys only on the server environment.”

If they get stuck, have them trace **one button click**: which JS function runs → which URL → which view → which template updates.

---

*Last aligned with the repo layout and Razorpay env-based config. Update this file if you add new apps or change payment URLs.*
