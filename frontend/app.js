
const $ = id => document.getElementById(id);

let registerMode = false;
let currentPage = "Overview";
let currentUser = null;
let devices = [];

let refreshTimer = null;
let pairingTimer = null;
let refreshing = false;
let sessionVersion = 0;


async function api(path, options = {}) {

    const response = await fetch(path, {
        credentials: "same-origin",
        cache: "no-store",
        ...options,

        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const error = new Error(
            typeof data.detail === "string"
                ? data.detail
                : `Request failed (${response.status})`
        );

        error.status = response.status;
        throw error;
    }

    return data;
}


function stopTimers() {
    clearInterval(refreshTimer);
    clearInterval(pairingTimer);
    refreshTimer = null;
    pairingTimer = null;
}


function showAuth() {

    stopTimers();

    sessionVersion++;
    currentUser = null;
    devices = [];

    if ($("pairing-dialog").open) {
        $("pairing-dialog").close();
    }

    $("pairing-code").textContent = "";
    $("overview-devices").replaceChildren();
    $("device-list").replaceChildren();
    $("alert-list").replaceChildren();
    $("history-device").replaceChildren();

    $("dashboard").hidden = true;
    $("auth-screen").hidden = false;
}


function setAuthMode(register) {

    registerMode = register;

    $("name-field").hidden = !register;
    $("name").required = register;

    $("auth-title").textContent = register
        ? "Create your account"
        : "Welcome back";

    $("auth-submit").textContent = register
        ? "Create account"
        : "Sign in";

    $("auth-switch").textContent = register
        ? "Already have an account? Sign in"
        : "Don't have an account? Register";

    $("password").minLength = register ? 12 : 1;

    $("password").autocomplete = register
        ? "new-password"
        : "current-password";

    $("auth-message").textContent = "";
}


$("auth-switch").onclick = () => {
    setAuthMode(!registerMode);
};


$("auth-form").onsubmit = async event => {

    event.preventDefault();

    const button = $("auth-submit");
    button.disabled = true;

    $("auth-message").textContent = "";

    try {

        const payload = {
            email: $("email").value.trim(),
            password: $("password").value
        };

        if (registerMode) {

            payload.name = $("name").value.trim();
            payload.display_name = payload.name;

            await api("/api/auth/register", {
                method: "POST",
                body: JSON.stringify(payload)
            });

            setAuthMode(false);

            $("auth-message").textContent =
                "Account created. Please sign in.";

        } else {

            await api("/api/auth/login", {
                method: "POST",
                body: JSON.stringify(payload)
            });

            const user = await api("/api/auth/me");

            await showDashboard(user);
        }

        $("password").value = "";

    } catch (error) {

        $("auth-message").textContent = error.message;

    } finally {

        button.disabled = false;
    }
};


async function showDashboard(user) {

    stopTimers();

    sessionVersion++;
    currentUser = user.user || user;

    $("auth-screen").hidden = true;
    $("dashboard").hidden = false;

    $("account-name").textContent =
        currentUser.display_name || currentUser.name || "";

    $("account-email").textContent =
        currentUser.email || "";

    $("welcome").textContent =
        `Welcome, ${currentUser.display_name ||
                    currentUser.name || "User"}`;

    selectPage("Overview");

    await refreshDashboard();

    if (currentUser) {
        refreshTimer = setInterval(
            refreshDashboard, 5000
        );
    }
}


function selectPage(name) {

    currentPage = name;

    document.querySelectorAll(".page").forEach(page => {
        page.hidden = page.id !== `page-${name}`;
    });

    document.querySelectorAll("[data-page]").forEach(button => {
        button.classList.toggle(
            "active",
            button.dataset.page === name
        );
    });

    $("page-title").textContent = name;

    if (name === "Analytics") {
        loadHistory();
    }
}


document.querySelectorAll("[data-page]").forEach(button => {
    button.onclick = () => selectPage(button.dataset.page);
});


function createElement(tag, text, className) {

    const element = document.createElement(tag);

    if (text !== undefined) {
        element.textContent = text;
    }

    if (className) {
        element.className = className;
    }

    return element;
}


function createDeviceCard(device) {

    const card = createElement("article", undefined, "card");
    const row = createElement("div", undefined, "device-row");

    const info = createElement("div");

    info.append(
        createElement("h3", device.device_name),
        createElement("span", device.os, "muted")
    );

    const status = createElement(
        "span",
        device.status.replaceAll("_", " ").toUpperCase(),
        `status-${device.status}`
    );

    const metrics = createElement(
        "div", undefined, "device-metrics"
    );

    if (device.metrics) {

        for (const key of ["cpu", "ram", "disk"]) {

            const value = device.metrics[key]?.usage;

            metrics.append(createElement(
                "span",
                `${key.toUpperCase()}: ${value ?? "--"}%`
            ));
        }

    } else {

        metrics.textContent = "Waiting for telemetry";
    }

    row.append(info, status, metrics);
    card.append(row);
    const ips = device.metrics?.ip_addresses || {};

    const ipDetails = createElement(
        "div",
        undefined,
        "device-ip-addresses"
    );

    ipDetails.append(
        createElement(
            "span",
            "Public IP: " + (ips.public_ip || "Unavailable")
        ),
        createElement(
            "span",
            "Local IP: " + (ips.local_ip || "Unavailable")
        )
    );

    card.append(ipDetails);
    if (device.last_seen) {

        card.append(createElement(
            "small",
            "Last seen: " +
            new Date(device.last_seen * 1000).toLocaleString(),
            "muted"
        ));
    }
        if (device.status !== "revoked") {

        const revokeButton = createElement(
            "button",
            "Revoke device access",
            "revoke-button"
        );

        revokeButton.onclick = async () => {

            const confirmed = window.confirm(
                `Revoke access for ${device.device_name}?\n\n` +
                "This device will no longer be authorized " +
                "to send telemetry."
            );

            if (!confirmed) {
                return;
            }

            revokeButton.disabled = true;

            try {

                await api(
                    `/api/devices/${encodeURIComponent(device.device_id)}/revoke`,
                    {
                        method: "POST"
                    }
                );

                await refreshDashboard();

            } catch (error) {

                window.alert(error.message);

                revokeButton.disabled = false;
            }
        };

        card.append(revokeButton);



    } else {

        card.append(createElement(
            "p",
            "Device access revoked.",
            "revoked-message"
        ));

        const retryButton = createElement(
            "button",
            "Retry MQTT Revocation",
            "retry-button"
        );

        retryButton.onclick = async () => {

            retryButton.disabled = true;
            retryButton.textContent = "Processing...";

            try {

                await api(
                    `/api/devices/${encodeURIComponent(device.device_id)}/revoke`,
                    { method: "POST" }
                );

                window.alert(
                    "MQTT access successfully removed."
                );

                await refreshDashboard();

            } catch (error) {

                window.alert(error.message);

            } finally {

                retryButton.disabled = false;
                retryButton.textContent =
                    "Retry MQTT Revocation";

            }
        };

        card.append(retryButton);
    }


    return card;
}


function renderDevices() {

    for (const id of ["overview-devices", "device-list"]) {

        const container = $(id);

        container.replaceChildren();

        if (!devices.length) {

            container.append(createElement(
                "article",
                "No devices connected yet. Click Add Device.",
                "card"
            ));

        } else {

            devices.forEach(device => {
                container.append(createDeviceCard(device));
            });
        }
    }
}


function renderAlerts() {

    const container = $("alert-list");

    container.replaceChildren();

    for (const device of devices) {

        if (!device.online || !device.metrics) {
            continue;
        }

        for (const key of ["cpu", "ram", "disk"]) {

            const value = device.metrics[key]?.usage;

            if (value >= 85) {

                const card = createElement(
                    "article", undefined, "card"
                );

                card.append(
                    createElement(
                        "h2",
                        `High ${key.toUpperCase()} usage`,
                        "yellow"
                    ),

                    createElement(
                        "p",
                        `${device.device_name}: ${value}%`
                    )
                );

                container.append(card);
            }
        }
    }

    if (!container.children.length) {

        container.append(createElement(
            "article",
            "No active resource alerts.",
            "card"
        ));
    }
}


function updateHistorySelector() {

    const select = $("history-device");
    const previous = select.value;

    select.replaceChildren();

    devices.forEach(device => {

        const option = createElement(
            "option", device.device_name
        );

        option.value = device.device_id;

        select.append(option);
    });

    if (devices.some(d => d.device_id === previous)) {
        select.value = previous;
    }
}


async function refreshDashboard() {

    if (refreshing || !currentUser) {
        return;
    }

    refreshing = true;
    const version = sessionVersion;

    try {

        const data = await api("/api/dashboard/summary");

        if (version !== sessionVersion) {
            return;
        }

        devices = data.devices || [];

        $("total-devices").textContent = data.total_devices;
        $("online-devices").textContent = data.online_devices;
        $("offline-devices").textContent = data.offline_devices;
        $("pending-devices").textContent = data.pending_devices;
    $("revoked-devices").textContent = data.revoked_devices ?? 0;
        const usedSlots =
            data.total_devices - (data.revoked_devices ?? 0);

    $("device-quota").textContent =
            `Device capacity: ${usedSlots} / 5`;
    for (const key of ["cpu", "ram", "disk"]) {

            const value = Number(data[`average_${key}`]) || 0;

            $(`average-${key}`).textContent =
                `${value.toFixed(1)}%`;

            $(`${key}-bar`).value = value;
        }

        renderDevices();
        renderAlerts();
        updateHistorySelector();

        $("dashboard-message").textContent = "";

        if (currentPage === "Analytics") {
            await loadHistory();
        }

    } catch (error) {

        if (version !== sessionVersion) {
            return;
        }

        if (error.status === 401) {

            showAuth();

        } else {

            $("dashboard-message").textContent =
                "Connection problem: " + error.message;
        }

    } finally {

        refreshing = false;
    }
}


$("add-device").onclick = async () => {

    const button = $("add-device");
    button.disabled = true;

    const version = sessionVersion;

    try {

        const data = await api("/api/pairing/create", {
            method: "POST"
        });

        if (version !== sessionVersion) {
            return;
        }

        $("pairing-code").textContent = data.pairing_code;

        clearInterval(pairingTimer);

        const expires = Date.now() + data.expires_in * 1000;

        $("copy-code").disabled = false;

        function updateTimer() {

            const remaining = Math.max(
                0,
                Math.ceil((expires - Date.now()) / 1000)
            );

            const minutes = Math.floor(remaining / 60);

            const seconds = String(remaining % 60)
                .padStart(2, "0");

            $("pairing-timer").textContent =
                `Expires in ${minutes}:${seconds}`;

            if (!remaining) {

                clearInterval(pairingTimer);

                $("pairing-code").textContent = "Expired";
                $("copy-code").disabled = true;
            }
        }

        updateTimer();

        pairingTimer = setInterval(updateTimer, 1000);

        $("pairing-dialog").showModal();

    } catch (error) {

        if (version === sessionVersion) {
            $("dashboard-message").textContent = error.message;
        }

    } finally {

        button.disabled = false;
    }
};


$("copy-code").onclick = async () => {

    try {

        await navigator.clipboard.writeText(
            $("pairing-code").textContent
        );

        $("copy-code").textContent = "Copied!";

        setTimeout(() => {
            $("copy-code").textContent = "Copy code";
        }, 2000);

    } catch {

        $("pairing-timer").textContent =
            "Select and copy the code manually.";
    }
};


$("close-dialog").onclick = () => {
    $("pairing-dialog").close();
};


$("logout").onclick = async () => {

    try {

        await api("/api/auth/logout", {
            method: "POST"
        });

        showAuth();

    } catch (error) {

        $("dashboard-message").textContent = error.message;
    }
};


async function loadHistory() {

    const id = $("history-device").value;

    const canvas = $("history-chart");
    const ctx = canvas.getContext("2d");

    if (!id) {

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        $("history-message").textContent = "No devices available.";
        return;
    }

    const version = sessionVersion;

    try {

        const hours = $("history-hours").value;

        const data = await api(
            `/api/devices/${encodeURIComponent(id)}/history` +
            `?hours=${hours}&limit=1000`
        );

        if (version !== sessionVersion ||
            id !== $("history-device").value ||
            hours !== $("history-hours").value) {
            return;
        }

        drawChart(data.history || []);

    } catch (error) {

        if (version === sessionVersion) {
            $("history-message").textContent = error.message;
        }
    }
}


function drawChart(history) {

    const canvas = $("history-chart");
    const ctx = canvas.getContext("2d");

    const width = canvas.width;
    const height = canvas.height;

    const left = 55;
    const right = 15;
    const top = 20;
    const bottom = 45;

    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;

    ctx.clearRect(0, 0, width, height);

    ctx.font = "14px Segoe UI";
    ctx.fillStyle = "#94a3b8";

    for (let value = 0; value <= 100; value += 25) {

        const y = top + plotHeight * (1 - value / 100);

        ctx.strokeStyle = "#29374c";
        ctx.beginPath();
        ctx.moveTo(left, y);
        ctx.lineTo(width - right, y);
        ctx.stroke();

        ctx.fillText(`${value}%`, 5, y + 5);
    }

    if (!history.length) {

        $("history-message").textContent =
            "No telemetry recorded for this period.";

        return;
    }

    history = [...history].sort(
        (a, b) => a.timestamp - b.timestamp
    );

    const start = history[0].timestamp;
    const end = history[history.length - 1].timestamp;

    const duration = Math.max(1, end - start);

    const series = [
        ["cpu", "#38bdf8"],
        ["ram", "#a78bfa"],
        ["disk", "#fbbf24"]
    ];

    for (const [key, color] of series) {

        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.beginPath();

        history.forEach((point, index) => {

            const x = left +
                (point.timestamp - start) / duration * plotWidth;

            const value = Math.max(
                0, Math.min(100, point[key])
            );

            const y = top +
                plotHeight * (1 - value / 100);

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();
    }

    ctx.fillStyle = "#94a3b8";

    for (let index = 0; index <= 4; index++) {

        const fraction = index / 4;

        const date = new Date(
            (start + (end - start) * fraction) * 1000
        );

        const label = date.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit"
        });

        const x = left + plotWidth * fraction;

        ctx.fillText(
            label,
            Math.min(x, width - 65),
            height - 15
        );
    }

    $("history-message").textContent =
        `${history.length} telemetry records loaded.`;
}


$("history-device").onchange = loadHistory;
$("history-hours").onchange = loadHistory;


async function initialize() {

    setAuthMode(false);

    try {

        const user = await api("/api/auth/me");

        await showDashboard(user);

    } catch {

        showAuth();
    }
}

initialize();
