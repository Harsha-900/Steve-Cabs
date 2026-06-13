/* # Driver dashboard — OTP pickup, continuous recording while ongoing, ticket TTS, location ping */

function getCookie(name) {
    let value = null;
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach(c => {
            c = c.trim();
            if (c.substring(0, name.length + 1) === (name + '=')) {
                value = decodeURIComponent(c.substring(name.length + 1));
            }
        });
    }
    return value;
}

let mediaRecorder = null;
let audioChunks = [];
let activeRecordingRideId = null;

async function startRecording(rideId, container) {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        activeRecordingRideId = rideId;
        mediaRecorder.ondataavailable = e => {
            if (e.data.size) audioChunks.push(e.data);
        };
        /* # Final upload runs in stopRecordingAndWaitUpload when driver taps Reached destination */
        mediaRecorder.onstop = () => {
            if (mediaRecorder && mediaRecorder.stream) {
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
        };
        mediaRecorder.start(1000);
        if (container) {
            const st = container.querySelector('.recording-status');
            if (st) st.innerText = 'Recording trip audio…';
        }
    } catch (err) {
        console.error('Microphone:', err);
    }
}

function stopRecordingAndWaitUpload() {
    return new Promise(resolve => {
        if (!mediaRecorder || mediaRecorder.state !== 'recording') {
            resolve();
            return;
        }
        const rid = activeRecordingRideId;
        const mr = mediaRecorder;
        mr.onstop = async () => {
            if (mr.stream) {
                mr.stream.getTracks().forEach(track => track.stop());
            }
            if (audioChunks.length > 0 && rid) {
                const blob = new Blob(audioChunks, { type: 'audio/webm' });
                const fd = new FormData();
                fd.append('audio', blob, `ride_${rid}.webm`);
                try {
                    await fetch(`/rides/upload-recording/${rid}/`, {
                        method: 'POST',
                        headers: { 'X-CSRFToken': getCookie('csrftoken') },
                        body: fd
                    });
                } catch (e) {
                    console.error(e);
                }
            }
            audioChunks = [];
            activeRecordingRideId = null;
            mediaRecorder = null;
            resolve();
        };
        mr.stop();
    });
}

function showRecorderForOngoingRide() {
    document.querySelectorAll('.ride-item').forEach(item => {
        const statusSpan = item.querySelector('.ride-status');
        const status = statusSpan ? statusSpan.innerText.trim() : '';
        const recorder = item.querySelector('.recorder-controls');
        if (recorder) {
            recorder.style.display = (status === 'ongoing') ? 'block' : 'none';
        }
    });
}

function toggleAvailabilityBanner() {
    const banner = document.getElementById('availabilityBanner');
    const upcoming = document.getElementById('upcoming');
    if (!banner || !upcoming) return;
    const hasActive = upcoming.querySelector('.ride-item');
    banner.style.display = hasActive ? 'none' : 'block';
}

function getActiveOngoingRideId() {
    const items = document.querySelectorAll('.ride-item');
    for (const item of items) {
        const st = item.querySelector('.ride-status');
        if (st && st.innerText.trim() === 'ongoing') {
            return item.getAttribute('data-ride-id');
        }
    }
    return null;
}

function loadRides() {
    return fetch('/rides/driver/')
        .then(res => res.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const u = doc.querySelector('#upcoming');
            const p = doc.querySelector('#pending');
            const c = doc.querySelector('#completed');
            const e = doc.querySelector('#earningsStrip');
            if (u) document.getElementById('upcoming').innerHTML = u.innerHTML;
            if (p) document.getElementById('pending').innerHTML = p.innerHTML;
            if (c) document.getElementById('completed').innerHTML = c.innerHTML;
            if (e) document.getElementById('earningsStrip').innerHTML = e.innerHTML;
            attachButtons();
            showRecorderForOngoingRide();
            toggleAvailabilityBanner();
        });
}

function attachButtons() {
    document.querySelectorAll('.accept-btn').forEach(btn => {
        btn.onclick = () => {
            const rideId = btn.dataset.rideid;
            fetch(`/rides/accept_ride/${rideId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            }).then(() => loadRides());
        };
    });

    document.querySelectorAll('.reach-pickup-btn').forEach(btn => {
        btn.onclick = () => {
            const rideId = btn.dataset.rideid;
            fetch(`/rides/reach_pickup/${rideId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            }).then(() => loadRides());
        };
    });

    document.querySelectorAll('.verify-otp-btn').forEach(btn => {
        btn.onclick = () => {
            const rideId = btn.dataset.rideid;
            const input = document.querySelector(`.otp-input[data-rideid="${rideId}"]`);
            const otp = (input && input.value) ? input.value.trim() : '';
            fetch(`/rides/verify_pickup_otp/${rideId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ otp })
            }).then(r => {
                if (!r.ok) alert('OTP did not match');
                return loadRides();
            });
        };
    });

    document.querySelectorAll('.start-btn').forEach(btn => {
        btn.onclick = async () => {
            const rideId = btn.dataset.rideid;
            const res = await fetch(`/rides/start_ride/${rideId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            });
            if (!res.ok) {
                alert('Start ride failed — verify OTP first.');
                return;
            }
            await loadRides();
            setTimeout(() => {
                const rideItem = document.querySelector(`.ride-item[data-ride-id="${rideId}"]`);
                const recorderDiv = rideItem && rideItem.querySelector('.recorder-controls');
                if (recorderDiv) {
                    recorderDiv.style.display = 'block';
                    startRecording(rideId, recorderDiv);
                }
            }, 400);
        };
    });

    document.querySelectorAll('.destination-btn').forEach(btn => {
        btn.onclick = async () => {
            const rideId = btn.dataset.rideid;
            await stopRecordingAndWaitUpload();
            await fetch(`/rides/reach_destination/${rideId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            });
            loadRides();
        };
    });
}

let locationInterval = null;
function initLocation() {
    const btn = document.getElementById('startLocation');
    if (!btn) return;
    btn.onclick = () => {
        if (locationInterval) clearInterval(locationInterval);
        locationInterval = setInterval(() => {
            const rideId = getActiveOngoingRideId();
            if (!rideId) return;
            navigator.geolocation.getCurrentPosition(pos => {
                fetch('/rides/update_location/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        ride_id: rideId,
                        lat: pos.coords.latitude,
                        lng: pos.coords.longitude
                    })
                });
            });
        }, 4000);
        const st = document.getElementById('locationStatus');
        if (st) st.innerText = 'Location active (ongoing ride)';
    };
}

async function loadDriverTickets() {
    try {
        const res = await fetch('/rides/driver-tickets/');
        const tickets = await res.json();
        const container = document.getElementById('driverTicketList');
        if (!container) return;
        container.innerHTML = '';

        for (const t of tickets) {
            for (const r of t.replies) {
                const wrap = document.createElement('div');
                wrap.style.cssText = 'background:#1e1e1e;margin:12px 0;padding:14px;border-radius:12px;border-left:3px solid #dc143c;';

                const p = document.createElement('p');
                const strong = document.createElement('strong');
                strong.textContent = 'Admin message (your language):';
                p.appendChild(strong);
                p.appendChild(document.createElement('br'));
                p.appendChild(document.createTextNode(r.translated_for_driver || ''));
                wrap.appendChild(p);

                if (r.audio_url) {
                    const audio = document.createElement('audio');
                    audio.controls = true;
                    audio.preload = 'metadata';
                    audio.style.width = '100%';
                    audio.style.marginTop = '10px';
                    const src = document.createElement('source');
                    src.src = r.audio_url;
                    src.type = 'audio/mpeg';
                    audio.appendChild(src);
                    wrap.appendChild(audio);
                    const link = document.createElement('a');
                    link.href = r.audio_url;
                    link.target = '_blank';
                    link.rel = 'noopener';
                    link.textContent = 'Open audio in new tab';
                    link.style.cssText = 'display:block;color:#dc143c;font-size:.85rem;margin-top:6px;';
                    wrap.appendChild(link);
                } else {
                    const np = document.createElement('p');
                    np.style.color = '#888';
                    np.textContent = 'Voice clip not generated — ask admin to resend reply.';
                    wrap.appendChild(np);
                }

                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'acknowledge-btn btn-red';
                btn.dataset.id = t.ticket_id;
                btn.textContent = 'Acknowledge';
                btn.style.marginTop = '10px';
                wrap.appendChild(btn);
                container.appendChild(wrap);
            }
        }

        document.querySelectorAll('.acknowledge-btn').forEach(b => {
            b.onclick = async () => {
                await fetch(`/rides/acknowledge-ticket/${b.dataset.id}/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') }
                });
                loadDriverTickets();
            };
        });
    } catch (err) {
        console.error(err);
    }
}

function initChat() {
    const sendBtn = document.getElementById('sendMsg');
    if (!sendBtn) return;
    sendBtn.onclick = () => {
        const rideId = getActiveOngoingRideId();
        const input = document.getElementById('chatInput');
        const text = input && input.value.trim();
        if (!rideId || !text) return;
        fetch('/rides/send_message/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ride_id: rideId, text })
        }).then(() => {
            if (input) input.value = '';
            loadChat(rideId);
        });
    };
}

function loadChat(rideId) {
    if (!rideId) return;
    fetch(`/rides/get_messages/${rideId}/`)
        .then(r => r.json())
        .then(messages => {
            const box = document.getElementById('chatMessages');
            if (!box) return;
            box.innerHTML = messages.map(m => `<div><b>${m.sender__username}:</b> ${m.text}</div>`).join('');
        });
}

document.addEventListener('DOMContentLoaded', () => {
    attachButtons();
    showRecorderForOngoingRide();
    toggleAvailabilityBanner();
    initLocation();
    initChat();
    loadDriverTickets();
    loadRides();

    setInterval(() => {
        const rid = getActiveOngoingRideId();
        if (rid) loadChat(rid);
    }, 8000);

    setInterval(loadRides, 6000);
    setInterval(loadDriverTickets, 8000);
});
