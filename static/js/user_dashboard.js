(function () {
    if (window.__steveCabsUserDashboardJSLoaded) {
        return;
    }
    window.__steveCabsUserDashboardJSLoaded = true;
    console.log('user_dashboard.js loaded');

    var map;
    var pickupMarker;
    var dropMarker;
    var driverMarker;
    var pickup = null;
    var drop = null;
    var currentRideId = null;
    var watchInterval = null;
    var ws = null;

    document.addEventListener("DOMContentLoaded", function () {
        initMap();
        attachEventListeners();
    });

function attachEventListeners() {
    const requestBtn = document.getElementById("requestRide");
    if (requestBtn) requestBtn.onclick = requestRide;

    const payBtn = document.getElementById("payNow");
    if (payBtn) payBtn.onclick = handlePayment;

    const raiseBtn = document.getElementById("raiseTicket");
    if (raiseBtn) raiseBtn.onclick = raiseTicket;

    const sendBtn = document.getElementById("sendMsg");
    if (sendBtn) sendBtn.onclick = sendMessage;

    const ackBtn = document.getElementById("ackDropoff");
    if (ackBtn) {
        ackBtn.onclick = async function () {
            if (!currentRideId) return;
            const res = await fetch("/rides/customer_ack/" + currentRideId + "/", {
                method: "POST",
                headers: { "X-CSRFToken": getCookie("csrftoken") }
            });
            if (res.ok) {
                alert("Thank you — you can complete payment when it appears.");
            }
        };
    }

    const cashBtn = document.getElementById("payCash");
    if (cashBtn) {
        cashBtn.onclick = async function () {
            if (!currentRideId) return;
            const res = await fetch("/rides/pay_cash/" + currentRideId + "/", {
                method: "POST",
                headers: { "X-CSRFToken": getCookie("csrftoken") }
            });
            const j = await res.json().catch(() => ({}));
            alert(j.success ? "Marked as paid (cash)." : (j.error || "Could not record cash payment"));
        };
    }

    const fbBtn = document.getElementById("submitFeedback");
    if (fbBtn) {
        fbBtn.onclick = async function () {
            if (!currentRideId) return;
            const rating = document.getElementById("feedbackStars")?.value || "5";
            const comment = document.getElementById("feedbackComment")?.value || "";
            const res = await fetch("/rides/feedback/" + currentRideId + "/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ rating: parseInt(rating, 10), comment: comment })
            });
            const j = await res.json().catch(() => ({}));
            if (j.success) {
                alert("Thanks for your feedback!");
                const fs = document.getElementById("feedbackSection");
                if (fs) fs.style.display = "none";
            } else {
                alert(j.error || "Feedback failed");
            }
        };
    }
}

function initMap() {
    if (map) return;

    map = L.map("map").setView([12.9716, 77.5946], 13);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
    }).addTo(map);

    map.on("click", onMapClick);
}

function onMapClick(e) {
    if (!pickup) {
        pickup = { lat: e.latlng.lat, lng: e.latlng.lng };
        if (pickupMarker) map.removeLayer(pickupMarker);
        pickupMarker = L.marker([pickup.lat, pickup.lng]).addTo(map);

        fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pickup.lat}&lon=${pickup.lng}`)
            .then((res) => res.json())
            .then((data) => {
                const pickupInput = document.getElementById("pickup");
                if (pickupInput) pickupInput.value = data.display_name || "";
            });
    } else if (!drop) {
        drop = { lat: e.latlng.lat, lng: e.latlng.lng };
        if (dropMarker) map.removeLayer(dropMarker);
        dropMarker = L.marker([drop.lat, drop.lng]).addTo(map);

        fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${drop.lat}&lon=${drop.lng}`)
            .then((res) => res.json())
            .then((data) => {
                const dropoffInput = document.getElementById("dropoff");
                if (dropoffInput) dropoffInput.value = data.display_name || "";
            });
    } else {
        alert("Pickup and drop already set. Click Request Ride.");
    }
}

async function requestRide() {
    if (!pickup || !drop) {
        alert("Select both pickup and drop on map");
        return;
    }

    try {
        const response = await fetch("/rides/request_ride/", {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie("csrftoken"),
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                pickup: {
                    address: document.getElementById("pickup")?.value || "",
                    lat: pickup.lat,
                    lng: pickup.lng
                },
                dropoff: {
                    address: document.getElementById("dropoff")?.value || "",
                    lat: drop.lat,
                    lng: drop.lng
                }
            })
        });

        const data = await response.json();
        if (data.ride_id) {
            currentRideId = data.ride_id;
            alert(`Ride requested! Fare: ₹${data.fare}. Waiting for driver.`);
            startTracking();
            connectWebSocket();
        } else {
            alert("Error requesting ride");
        }
    } catch (err) {
        console.error("Request ride error:", err);
        alert("Request failed");
    }
}

function stopTrackingAndSocket() {
    if (watchInterval) {
        clearInterval(watchInterval);
        watchInterval = null;
    }
    if (ws) {
        ws.close();
        ws = null;
    }
}
function startTracking() {
    if (watchInterval) clearInterval(watchInterval);

    watchInterval = setInterval(() => {
        if (!currentRideId) return;

        fetch(`/rides/ride_status/${currentRideId}/`)
            .then((res) => res.json())
            .then((data) => {
                // Update ride info
                const rideInfo = document.getElementById("rideInfo");
                if (rideInfo) {
                    var fareNum = parseFloat(data.fare);
                    var fareStr = isNaN(fareNum) ? (data.fare || "0") : fareNum.toFixed(2);
                    rideInfo.innerHTML =
                        `Status: ${data.status}<br>Driver: ${data.driver || "Not assigned"}<br>Fare: ₹${fareStr}`;
                }

                const otpSection = document.getElementById("otpSection");
                const otpDisplay = document.getElementById("otpDisplay");
                if (otpSection && otpDisplay) {
                    if (data.pickup_otp) {
                        otpSection.style.display = "block";
                        otpDisplay.innerText = data.pickup_otp;
                    } else {
                        otpSection.style.display = "none";
                        otpDisplay.innerText = "";
                    }
                }

                const ackSection = document.getElementById("ackSection");
                if (ackSection) {
                    ackSection.style.display = data.status === "awaiting_ack" ? "block" : "none";
                }

                // Update driver location on map
                if (data.driver_location) {
                    if (!driverMarker) {
                        driverMarker = L.marker([data.driver_location.lat, data.driver_location.lng]).addTo(map);
                    } else {
                        driverMarker.setLatLng([data.driver_location.lat, data.driver_location.lng]);
                    }
                    const driverLocation = document.getElementById("driverLocation");
                    if (driverLocation) {
                        driverLocation.innerHTML = `Driver at: ${data.driver_location.lat.toFixed(4)}, ${data.driver_location.lng.toFixed(4)}`;
                    }
                }

                const paymentSection = document.getElementById("paymentSection");
                if (paymentSection) {
                    paymentSection.style.display =
                        data.status === "completed" && data.payment_status !== "paid" ? "block" : "none";
                }

                const feedbackSection = document.getElementById("feedbackSection");
                if (feedbackSection) {
                    feedbackSection.style.display = data.show_feedback ? "block" : "none";
                }

                const ticketSection = document.getElementById("ticketSection");
                if (ticketSection) {
                    var showTicket =
                        currentRideId && data.driver && data.status && data.status !== "pending";
                    ticketSection.style.display = showTicket ? "block" : "none";
                }

                const chatCard = document.getElementById("chatCard");
                if (chatCard) {
                    var showChat =
                        currentRideId &&
                        (data.status === "ongoing" ||
                            data.status === "awaiting_ack" ||
                            (data.status === "completed" && data.payment_status !== "paid"));
                    chatCard.style.display = showChat ? "block" : "none";
                }

                // Ticket resolution status
                const ticketResolutionStatus = document.getElementById("ticketResolutionStatus");
                if (ticketResolutionStatus) {
                    if (data.ticket_status === "resolved_acknowledged") {
                        var msg = "Ticket resolved. Driver acknowledged.";
                        if (data.resolution_for_customer) {
                            msg += "<br><strong>Admin message:</strong> " + data.resolution_for_customer;
                        }
                        ticketResolutionStatus.innerHTML = msg;
                    } else if (data.ticket_status === "resolved_no_ack") {
                        ticketResolutionStatus.innerHTML =
                            "Admin replied. Waiting for driver acknowledgement.";
                    } else if (data.ticket_status === "open") {
                        ticketResolutionStatus.innerHTML = "Ticket open. Admin will respond.";
                    } else {
                        ticketResolutionStatus.innerHTML = "";
                    }
                }

                if (data.status === "cancelled") {
                    stopTrackingAndSocket();
                }

                loadMessages();
            })
            .catch((err) => console.error("Tracking error:", err));
    }, 3000);
}

function connectWebSocket() {
    if (!currentRideId) return;
    if (ws) ws.close();

    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${scheme}://${window.location.host}/ws/ride/${currentRideId}/`);

    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === "location") {
            if (!driverMarker) {
                driverMarker = L.marker([data.lat, data.lng]).addTo(map);
            } else {
                driverMarker.setLatLng([data.lat, data.lng]);
            }

            const driverLocation = document.getElementById("driverLocation");
            if (driverLocation) {
                driverLocation.innerHTML = `Driver at: ${data.lat.toFixed(4)}, ${data.lng.toFixed(4)}`;
            }
        }
    };

    ws.onerror = (err) => {
        console.error("WebSocket error:", err);
    };
}

async function handlePayment() {
    if (!currentRideId) return;

    try {
        const res = await fetch(`/payments/create_order/${currentRideId}/`, {
            method: "POST",
            headers: { "X-CSRFToken": getCookie("csrftoken") }
        });
        const order = await res.json();
        if (!order.order_id) throw new Error("No order");

        const options = {
            key: order.key,
            amount: order.amount,
            currency: "INR",
            name: "Steve Cabs",
            description: order.description,
            order_id: order.order_id,
            handler: async function (response) {
                const resp = await fetch("/payments/payment_success/", {
                    method: "POST",
                    headers: { "X-CSRFToken": getCookie("csrftoken") },
                    body: new URLSearchParams({
                        razorpay_order_id: response.razorpay_order_id,
                        razorpay_payment_id: response.razorpay_payment_id,
                        razorpay_signature: response.razorpay_signature
                    })
                });

                const data = await resp.json();
                alert(data.success ? "Payment successful! You can leave feedback below." : "Payment failed");
            }
        };

        const rzp = new Razorpay(options);
        rzp.open();
    } catch (e) {
        console.error(e);
        alert("Payment initiation failed");
    }
}

async function raiseTicket() {
    if (!currentRideId) {
        alert("No active ride");
        return;
    }

    const reason = document.getElementById("ticketReason")?.value || "";
    const description = document.getElementById("ticketDesc")?.value || "";

    if (!description) {
        alert("Please describe the issue");
        return;
    }

    const formData = new FormData();
    formData.append("ride_id", currentRideId);
    formData.append("reason", reason);
    formData.append("description", description);

    try {
        const res = await fetch("/tickets/create/", {
            method: "POST",
            headers: { "X-CSRFToken": getCookie("csrftoken") },
            body: formData
        });

        const data = await res.json();
        if (data.ticket_id) {
            const ticketResult = document.getElementById("ticketResult");
            if (ticketResult) ticketResult.innerText = `Ticket ID: ${data.ticket_id}`;
            alert("Ticket raised successfully! ID: " + data.ticket_id);
        } else {
            alert("Error: " + (data.error || "Unknown error"));
        }
    } catch (e) {
        console.error(e);
        alert("Failed to raise ticket");
    }
}

function loadMessages() {
    if (!currentRideId) return;

    fetch(`/rides/get_messages/${currentRideId}/`)
        .then((res) => res.json())
        .then((messages) => {
            const container = document.getElementById("chatMessages");
            if (container) {
                container.innerHTML = messages
                    .map((m) => `<div class="message"><b>${m.sender__username}:</b> ${m.text}</div>`)
                    .join("");
            }
        })
        .catch((err) => console.error("Load messages error:", err));
}

function sendMessage() {
    const chatInput = document.getElementById("chatInput");
    const text = chatInput?.value?.trim();

    if (!text || !currentRideId) return;

    fetch("/rides/send_message/", {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ ride_id: currentRideId, text: text })
    })
        .then(() => {
            if (chatInput) chatInput.value = "";
            loadMessages();
        })
        .catch((err) => console.error("Send message error:", err));
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
})();