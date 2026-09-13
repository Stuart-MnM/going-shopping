/* ============================================================
   GOING SHOPPING - OFFLINE TRIP HANDLING
   ============================================================

   Only ONE part of this app needs to work with no signal:
   the shopping trip itself (checking things off, removing
   things) once you've tapped "Start Trip".

   Everything else - My Usual Shop, Add / Change List,
   Previous Lists - is a normal server page. It needs a
   connection, and it always shows exactly what is saved on
   the server, because nothing is duplicated here.

   The trip lives entirely in localStorage while it's running,
   and is sent back to the server as one JSON message when you
   tap "Shopping Completed". If that message can't be sent
   right away (no signal), it is queued and retried
   automatically the moment the phone is back online.
   ============================================================ */

const GS_TRIP_KEY = "goingShoppingTrip";
const GS_PENDING_KEY = "goingShoppingPendingCompletion";
const GS_LOCAL_HISTORY_KEY = "goingShoppingLocalHistory";


function gsGet(key, fallback) {
    try {
        const value = localStorage.getItem(key);
        return value === null ? fallback : JSON.parse(value);
    } catch (error) {
        return fallback;
    }
}


function gsSet(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
}


function gsRemove(key) {
    localStorage.removeItem(key);
}


/* ============================================================
   THE ACTIVE TRIP
   ============================================================ */

function gsGetTrip() {
    return gsGet(GS_TRIP_KEY, null);
}


function gsSaveTrip(trip) {
    gsSet(GS_TRIP_KEY, trip);
}


function gsStartTrip(items) {
    const trip = {
        items: items.slice(),
        checked: [],
        startedAt: new Date().toISOString(),
        stoppedAt: null
    };

    gsSaveTrip(trip);
    return trip;
}


/* ============================================================
   SYNCING A COMPLETED TRIP BACK TO THE SERVER
   ============================================================ */

function gsQueuePendingCompletion(payload) {
    gsSet(GS_PENDING_KEY, payload);

    const history = gsGet(GS_LOCAL_HISTORY_KEY, []);

    history.unshift({
        date: new Date().toLocaleDateString("en-GB", {
            day: "2-digit",
            month: "long",
            year: "numeric"
        }),
        items: payload.items,
        started_at: payload.started_at,
        stopped_at: payload.stopped_at,
        overall_time: ""
    });

    gsSet(GS_LOCAL_HISTORY_KEY, history);
}


async function gsSendCompletion(payload) {
    try {
        const response = await fetch("/api/complete-trip", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        return response.ok;
    } catch (error) {
        return false;
    }
}


async function gsCompleteTrip(payload) {
    const sent = await gsSendCompletion(payload);

    if (sent) {
        gsRemove(GS_PENDING_KEY);
    } else {
        gsQueuePendingCompletion(payload);
    }

    gsRemove(GS_TRIP_KEY);

    return sent;
}


async function gsRetryPendingCompletion() {
    const pending = gsGet(GS_PENDING_KEY, null);

    if (!pending) {
        return;
    }

    if (!navigator.onLine) {
        return;
    }

    const sent = await gsSendCompletion(pending);

    if (sent) {
        gsRemove(GS_PENDING_KEY);

        // The server now has this trip in its own history,
        // so drop our temporary local copy of it.
        const history = gsGet(GS_LOCAL_HISTORY_KEY, []);

        const remaining = history.filter(function (trip) {
            return (
                trip.started_at !== pending.started_at ||
                trip.stopped_at !== pending.stopped_at
            );
        });

        gsSet(GS_LOCAL_HISTORY_KEY, remaining);

        // Refresh the page so the now-cleared list (and, on
        // Previous Lists, the newly-synced trip) actually shows
        // up, rather than silently updating somewhere the person
        // isn't currently looking at.
        window.location.reload();
    }
}


/* ============================================================
   RENDERING THE SHOPPING-MODE LIST
   ============================================================ */

function gsRenderShoppingMode(trip) {
    const page = document.querySelector(".page");
    const listCard = document.querySelector(".list-card");

    if (!page || !listCard) {
        return;
    }

    // Hide the normal "setup" buttons/cards while a trip is active.
    page.querySelectorAll(".main-button.button-link, .card").forEach(function (element) {
        element.style.display = "none";
    });

    const startTripForm = document.getElementById("startTripForm");

    if (startTripForm) {
        startTripForm.style.display = "none";
    }

    // Banner above the list.
    let banner = document.getElementById("gsTripBanner");

    if (!banner) {
        banner = document.createElement("div");
        banner.id = "gsTripBanner";
        banner.className = "mode-title";
        page.insertBefore(banner, listCard);
    }

    banner.textContent = trip.stoppedAt
        ? "Trip stopped \u2014 review your list"
        : "Shopping trip in progress";

    // The list itself.
    listCard.innerHTML = "";

    const heading = document.createElement("div");
    heading.className = "list-heading";

    const h2 = document.createElement("h2");
    h2.textContent = "Today's List";
    heading.appendChild(h2);

    const count = document.createElement("div");
    count.className = "list-count";
    count.textContent = trip.items.length
        ? trip.items.length + " item" + (trip.items.length === 1 ? "" : "s")
        : "";
    heading.appendChild(count);

    listCard.appendChild(heading);

    if (!trip.items.length) {
        const empty = document.createElement("div");
        empty.className = "empty-message";
        empty.textContent = "Your shopping list is empty.";
        listCard.appendChild(empty);
    }

    trip.items.forEach(function (item) {
        const row = document.createElement("div");
        row.className = "item";

        const label = document.createElement("label");

        if (trip.checked.includes(item)) {
            label.classList.add("checked-item");
        }

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "item-checkbox";
        checkbox.checked = trip.checked.includes(item);

        checkbox.addEventListener("change", function () {
            const current = gsGetTrip();

            if (!current) {
                return;
            }

            if (checkbox.checked) {
                if (!current.checked.includes(item)) {
                    current.checked.push(item);
                }
                label.classList.add("checked-item");
            } else {
                current.checked = current.checked.filter(function (savedItem) {
                    return savedItem !== item;
                });
                label.classList.remove("checked-item");
            }

            gsSaveTrip(current);
        });

        const span = document.createElement("span");
        span.textContent = item;

        label.appendChild(checkbox);
        label.appendChild(span);

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "remove-button";
        removeButton.textContent = "REMOVE";

        removeButton.addEventListener("click", function () {
            const current = gsGetTrip();

            if (!current) {
                return;
            }

            current.items = current.items.filter(function (savedItem) {
                return savedItem !== item;
            });

            current.checked = current.checked.filter(function (savedItem) {
                return savedItem !== item;
            });

            gsSaveTrip(current);
            gsRenderShoppingMode(current);
        });

        row.appendChild(label);
        row.appendChild(removeButton);
        listCard.appendChild(row);
    });

    // Stop / Completed controls live below the list.
    let controls = document.getElementById("gsTripControls");

    if (!controls) {
        controls = document.createElement("div");
        controls.id = "gsTripControls";
        listCard.insertAdjacentElement("afterend", controls);
    }

    controls.innerHTML = "";

    if (!trip.stoppedAt) {

        const timing = document.createElement("div");
        timing.className = "timing-card";

        const label = document.createElement("div");
        label.className = "timing-label";
        label.textContent = "Trip started";

        const value = document.createElement("div");
        value.className = "timing-value";
        value.textContent = new Date(trip.startedAt).toLocaleTimeString("en-GB", {
            hour: "2-digit",
            minute: "2-digit"
        });

        timing.appendChild(label);
        timing.appendChild(value);
        controls.appendChild(timing);

        const stopButton = document.createElement("button");
        stopButton.type = "button";
        stopButton.className = "main-button stop";
        stopButton.textContent = "\uD83D\uDED1 STOP TRIP";

        stopButton.addEventListener("click", function () {
            const current = gsGetTrip();

            if (!current) {
                return;
            }

            current.stoppedAt = new Date().toISOString();
            gsSaveTrip(current);
            gsRenderShoppingMode(current);
        });

        controls.appendChild(stopButton);

    } else {

        const completedButton = document.createElement("button");
        completedButton.type = "button";
        completedButton.className = "main-button primary completed-button";
        completedButton.textContent = "\u2705 SHOPPING COMPLETED";

        completedButton.addEventListener("click", async function () {
            const current = gsGetTrip();

            if (!current) {
                return;
            }

            const uncheckedCount = current.items.length - current.checked.length;

            if (uncheckedCount > 0) {
                const proceed = window.confirm(
                    "You still have " + uncheckedCount +
                    " unchecked item" + (uncheckedCount === 1 ? "" : "s") +
                    ".\n\nDo you want to finish shopping without them?"
                );

                if (!proceed) {
                    return;
                }
            }

            completedButton.disabled = true;
            completedButton.textContent = "Finishing up\u2026";

            const sent = await gsCompleteTrip({
                items: current.checked,
                started_at: current.startedAt,
                stopped_at: current.stoppedAt
            });

            if (sent) {
                // We're online and it's already saved - a normal
                // fresh reload is safe and gives a clean new page.
                window.location.reload();
                return;
            }

            // No connection right now - reloading would just show
            // a broken page. Finish up right here instead: the
            // trip is safely queued and will send itself the
            // moment this page is reopened with a connection.
            banner.textContent = "Shopping complete \uD83C\uDF89";

            listCard.innerHTML = "";

            const doneMessage = document.createElement("div");
            doneMessage.className = "empty-message";
            doneMessage.style.padding = "20px 4px";
            doneMessage.textContent =
                "Nice work! This trip will finish saving to your " +
                "shopping history the next time this page is open " +
                "with a connection - you don't need to do anything.";
            listCard.appendChild(doneMessage);

            controls.innerHTML = "";
        });

        controls.appendChild(completedButton);
    }
}


/* ============================================================
   HOME PAGE STARTUP
   ============================================================ */

function gsSetUpStartTripForm() {
    const startTripForm = document.getElementById("startTripForm");

    if (!startTripForm) {
        return;
    }

    startTripForm.addEventListener("submit", function (event) {
        event.preventDefault();

        const serverItems = (window.GS_SERVER_STATE && window.GS_SERVER_STATE.todayList) || [];
        const trip = gsStartTrip(serverItems);

        gsRenderShoppingMode(trip);
    });
}


function gsInitHomePage() {
    gsRetryPendingCompletion();

    const trip = gsGetTrip();

    if (trip) {
        gsRenderShoppingMode(trip);
    } else {
        gsSetUpStartTripForm();
    }

    window.addEventListener("online", gsRetryPendingCompletion);

    // On a phone, coming back to this page after a while often
    // resumes it rather than fully reloading it, so "online"
    // may never fire. Checking again whenever the page becomes
    // visible catches that case too.
    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") {
            gsRetryPendingCompletion();
        }
    });
}


document.addEventListener("DOMContentLoaded", function () {

    if (document.getElementById("startTripForm") || document.querySelector(".list-card")) {
        gsInitHomePage();
    } else {
        // Other pages (Previous Lists) may still have a pending
        // completion waiting to go out - give it a chance here too.
        gsRetryPendingCompletion();
        window.addEventListener("online", gsRetryPendingCompletion);

        document.addEventListener("visibilitychange", function () {
            if (document.visibilityState === "visible") {
                gsRetryPendingCompletion();
            }
        });
    }
});
