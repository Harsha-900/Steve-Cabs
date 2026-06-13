How to use this file in Microsoft Word: Open Word → File → Open → choose this HTML file → then File → Save As → Word Document (*.docx).

Steve Cabs — From beginning to end
This guide walks a new developer from installing Python through running the app, understanding packages (pip), and following the main product flow (customer → driver → payment).

Part 1 — What you need on your computer
Python 3.10 or newer (3.11 or 3.12 is fine). Download from the official site: https://www.python.org/downloads/
During Windows setup, enable "Add python.exe to PATH" so you can run python and pip from any folder.
A code editor (e.g. Visual Studio Code) is optional but helpful.
Part 2 — What is pip, and where do you install packages?
pip is Python's package installer. It downloads libraries (Django, Razorpay, etc.) from the internet into your Python environment.

Where to run pip: Always run it in a terminal (PowerShell or Command Prompt), after you have:

Navigated to your project folder (the folder that contains manage.py and requirements.txt).
Activated a virtual environment (recommended) so packages stay inside this project and do not clash with other Python projects.
Typical Windows commands (project folder = steve_cabs):

cd path\to\steve_cabs
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
The line pip install -r requirements.txt reads the list in requirements.txt and installs every package with the versions your team chose.

If PyTorch install fails or is very slow: On Windows, install the CPU build first, then run pip install -r requirements.txt again:
pip install torch --index-url https://download.pytorch.org/whl/cpu
Part 3 — What each main pip package is for
, daphne
Package	Role in Steve Cabs
Django	Web framework: URLs, views, templates, database (ORM).
channels	WebSockets / async support (e.g. chat-style features).
channels-redis	Optional scaling layer for Channels (Redis); project may use in-memory layer in dev.
razorpay	Server-side SDK: create orders and verify payment signatures.
Pillow	Image handling if uploads use images.
google-generativeai	Optional Gemini-related helpers if configured.
ollama	Talks to a local Ollama API (e.g. Qwen) for translations/summaries when running.
httpx, httpcore, requests	HTTP clients for APIs and helpers.
deep-translator	Fallback translation (e.g. admin message to driver language).
gTTS, edge-tts, pyttsx3	Text-to-speech paths for tickets or audio features.
faster-whisper, soundfile, numpy	Local speech-to-text for trip recordings (downloads a model on first use).
torch, transformers	Used by optional/heavy utilities (e.g. voice generation scripts); not every page load needs them.
Part 4 — Environment file (.env) and secrets
Copy .env.example to .env in the same folder as manage.py.
Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET from the Razorpay dashboard (Test mode for development).
Never commit .env to Git; it is in .gitignore.
Optional: DJANGO_SECRET_KEY, GEMINI_API_KEY, FFMPEG_BINARY (path to ffmpeg.exe on Windows).
Part 5 — Database and first run
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
Open the URL shown (usually http://127.0.0.1:8000/). The superuser account is for Django admin and staff-only pages.

Part 6 — Project layout (where to look in code)
Path	Purpose
steve_cabs/settings.py	Loads .env, database, static files, Razorpay settings.
rides/	Core rides: models, views, booking and driver flow, recordings.
payments/	Razorpay order creation and payment verification.
tickets/	Support tickets and admin replies.
admin_dashboard/	Staff dashboards, charts, ride history.
accounts/	Users, registration, driver vs customer flags.
static/css/style.css	Main theme and dashboard layout.
static/js/*.js	Browser logic (maps, Razorpay checkout, driver/rider UI).
Part 7 — End-to-end product flow (conceptual)
Customer registers/logs in, books a ride (pickup/dropoff).
Driver sees requests, accepts, drives to pickup; pickup may use an OTP check.
Trip moves to destination; customer may acknowledge completion.
Payment: Cash (recorded in app) or Razorpay (test cards in test mode).
Razorpay path: browser asks server to create_order → Razorpay Checkout opens → on success, browser sends payment id + signature to payment_success → server verifies with the secret key → ride marked paid.
Optional: ratings, tickets, recordings (Whisper/Ollama) depending on configuration.
Part 8 — Troubleshooting
ModuleNotFoundError: Activate venv and run pip install -r requirements.txt again.
Payment errors: Confirm .env keys, restart server after editing .env.
Ollama / Qwen errors: Install and run Ollama locally if you use that translation path; otherwise fallback translation may still run.
Whisper first run: May download a model; needs disk space and time.
End of document. For a shorter developer-only outline, see JUNIOR_GUIDE.md in the same project folder.
