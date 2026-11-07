
const API_BASE_URL = "http://127.0.0.1:5001";
const ADELAIDE_LAT = -34.9285;
const ADELAIDE_LON = 138.6007;

const map = L.map("map").setView([ADELAIDE_LAT, ADELAIDE_LON], 13);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

const element = id => document.getElementById(id);

const routeSelect = element("routeSelect");
const routePerformance = element("routePerformance");
const locationButton = element("locationButton");
const selectedLocationInfo = element("selectedLocationInfo");
const selectedStopInfo = element("selectedStopInfo");
const stopCount = element("stopCount");
const routeCount = element("routeCount");
const mapMessage = element("mapMessage");

const playbackStart = element("playbackStart");
const playbackEnd = element("playbackEnd");
const loadPlaybackButton = element("loadPlaybackButton");
const playbackTime = element("playbackTime");
const playbackSlider = element("playbackSlider");
const playbackStatus = element("playbackStatus");
const playButton = element("playButton");
const pauseButton = element("pauseButton");
const resetButton = element("resetButton");

const hotspotToggle = element("hotspotToggle");
const hotspotMinServices = element("hotspotMinServices");
const hotspotStatus = element("hotspotStatus");
const hotspotResults = element("hotspotResults");

let stopData = [];
let routeData = [];

const stopMarkers = new Map();

let selectedLocation = null;
let selectedLocationMarker = null;
let nearestStopMarker = null;
let selectedStopId = null;

let routeGeometryLayer = null;
let routeStopLayer = null;
let routeMapRequest = 0;
let routePerformanceRequest = 0;

const vehicleLayer = L.layerGroup().addTo(map);

let recordedPositions = [];
let playbackStartTime = null;
let playbackEndTime = null;
let currentPlaybackTime = null;
let playbackRouteId = null;
let playbackTimer = null;
let playbackRequestId = 0;

const PLAYBACK_STEP_SECONDS = 30;
const PLAYBACK_INTERVAL_MS = 500;

let hotspotData = [];
let hotspotLayer = null;
let hotspotRequest = 0;

// Basic formatting helpers
function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => {
        const replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        };

        return replacements[character];
    });
}

function formatNumber(value) {
    if (value === null || value === undefined || value === "") {
        return "Unavailable";
    }

    const number = Number(value);

    return Number.isFinite(number)
        ? number.toFixed(1)
        : "Unavailable";
}

function formatPercentage(value) {
    const number = Number(value);

    if (value === null || value === undefined || !Number.isFinite(number)) {
        return "Unavailable";
    }

    return `${number.toFixed(1)}%`;
}

function showMapMessage(message) {
    mapMessage.textContent = message;
    mapMessage.classList.remove("hidden");
}

function hideMapMessage() {
    mapMessage.classList.add("hidden");
}

function hasValidCoordinates(stop) {
    if (
        !stop ||
        stop.stop_lat === null ||
        stop.stop_lon === null ||
        stop.stop_lat === "" ||
        stop.stop_lon === ""
    ) {
        return false;
    }

    const latitude = Number(stop.stop_lat);
    const longitude = Number(stop.stop_lon);

    return (
        Number.isFinite(latitude) &&
        Number.isFinite(longitude) &&
        latitude >= -90 &&
        latitude <= 90 &&
        longitude >= -180 &&
        longitude <= 180
    );
}

function performanceMarkup(performance) {
    const metrics = [
        ["Services analysed", performance.total_services],
        ["Average delay", `${formatNumber(performance.average_delay)} min`],
        ["On time", formatPercentage(performance.on_time_percentage)],
        ["Delayed", formatPercentage(performance.delayed_percentage)],
        ["Severe delay", formatPercentage(performance.severe_delay_percentage)],
        ["Early", formatPercentage(performance.early_percentage)]
    ];

    return metrics.map(([label, value]) => `
        <div class="performance-row">
            <span class="performance-label">${escapeHtml(label)}</span>
            <span class="performance-value">${escapeHtml(value)}</span>
        </div>
    `).join("");
}

// Load Adelaide Metro stops
async function loadStops() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stops`);

        if (!response.ok) {
            throw new Error("Unable to load stops");
        }

        const stops = await response.json();

        if (!Array.isArray(stops)) {
            throw new Error("Invalid stop data");
        }

        stopData = stops.filter(hasValidCoordinates).map(stop => ({
            ...stop,
            stop_lat: Number(stop.stop_lat),
            stop_lon: Number(stop.stop_lon)
        }));

        createStopMarkers();
        window.dispatchEvent(new CustomEvent("adelaide:stops-loaded", { detail: { stops: stopData } }));

        stopCount.textContent = `${stopData.length} stops`;

        if (stopData.length > 0) {
            const bounds = L.latLngBounds(
                stopData.map(stop => [stop.stop_lat, stop.stop_lon])
            );

            map.fitBounds(bounds, {
                padding: [30, 30],
                maxZoom: 15
            });
        } else {
            showMapMessage("No stop data is currently available.");
        }

        if (selectedLocation) {
            showNearestStop(
                selectedLocation.latitude,
                selectedLocation.longitude
            );
        }

        if (hotspotData.length > 0) {
            renderHotspots();
        }
    } catch (error) {
        console.error("Stop loading error:", error);
        stopCount.textContent = "Stops unavailable";
        showMapMessage("Unable to load Adelaide Metro stops.");
    }
}

// Create clickable stop markers
function createStopMarkers() {
    for (const marker of stopMarkers.values()) {
        map.removeLayer(marker);
    }

    stopMarkers.clear();

    stopData.forEach(stop => {
        const marker = L.circleMarker(
            [stop.stop_lat, stop.stop_lon],
            {
                radius: 6,
                color: "#3388ff",
                fillColor: "#3388ff",
                weight: 2,
                fillOpacity: 0.8
            }
        ).addTo(map);

        marker.bindTooltip(escapeHtml(stop.stop_name || "Stop"), {
            direction: "top",
            offset: [0, -5]
        });

        marker.bindPopup(`
            <strong>${escapeHtml(stop.stop_name || "Stop")}</strong>
            <br>Stop ID: ${escapeHtml(stop.stop_id)}
            <br>Latitude: ${stop.stop_lat.toFixed(5)}
            <br>Longitude: ${stop.stop_lon.toFixed(5)}
        `);

        marker.on("click", event => {
            L.DomEvent.stopPropagation(event);
            selectStop(stop);
        });

        stopMarkers.set(String(stop.stop_id), marker);
    });
}

// Load routes into the dropdown
async function loadRoutes() {
    routeSelect.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/api/routes`);

        if (!response.ok) {
            throw new Error("Unable to load routes");
        }

        const routes = await response.json();

        if (!Array.isArray(routes)) {
            throw new Error("Invalid route data");
        }

        routeData = routes;

        routeSelect.innerHTML = '<option value="">Select a route</option>';

        const sortedRoutes = [...routeData].sort((a, b) => {
            const first = a.route_short_name || a.route_id;
            const second = b.route_short_name || b.route_id;

            return String(first).localeCompare(String(second), undefined, {
                numeric: true
            });
        });

        sortedRoutes.forEach(route => {
            const option = document.createElement("option");

            option.value = route.route_id;

            const shortName = route.route_short_name || route.route_id;
            const longName = route.route_long_name
                ? ` — ${route.route_long_name}`
                : "";

            option.textContent = `${shortName}${longName}`;

            routeSelect.appendChild(option);
        });

        routeCount.textContent = `${routeData.length} routes`;
        routeSelect.disabled = false;
    } catch (error) {
        console.error("Route loading error:", error);

        routeCount.textContent = "Routes unavailable";
        routeSelect.innerHTML =
            '<option value="">Routes unavailable</option>';
    }
}

// Change the selected route
function chooseRoute(routeId) {
    clearPlayback();
    clearHotspots();

    if (!routeId) {
        routeMapRequest++;
        routePerformanceRequest++;

        clearRouteLayers();
        hideMapMessage();

        routePerformance.innerHTML =
            "<p>Select a route to view performance.</p>";

        routePerformance.classList.add("empty-card");
        return;
    }

    selectRoute(routeId);
    showRouteOnMap(routeId);
    loadHotspots(routeId);
}

routeSelect.addEventListener("change", () => {
    chooseRoute(routeSelect.value);
});

// Clear previous route geometry
function clearRouteLayers() {
    if (routeGeometryLayer) {
        map.removeLayer(routeGeometryLayer);
        routeGeometryLayer = null;
    }

    if (routeStopLayer) {
        map.removeLayer(routeStopLayer);
        routeStopLayer = null;
    }
}

// Show official recorded route geometry
async function showRouteOnMap(routeId) {
    const requestId = ++routeMapRequest;

    clearRouteLayers();
    showMapMessage("Loading route map...");

    try {
        const response = await fetch(
            `${API_BASE_URL}/api/routes/${encodeURIComponent(routeId)}/map-data?source=static`
        );

        if (
            requestId !== routeMapRequest ||
            routeSelect.value !== String(routeId)
        ) {
            return;
        }

        if (!response.ok) {
            if (response.status === 404) {
                throw new Error(
                    "Static route geometry is not available for this route."
                );
            }

            if (response.status === 503) {
                throw new Error(
                    "Static GTFS route catalogue is not configured on the backend."
                );
            }

            throw new Error("Unable to load this route on the map.");
        }

        const data = await response.json();

        if (
            requestId !== routeMapRequest ||
            routeSelect.value !== String(routeId)
        ) {
            return;
        }

        if (
            !data.geometry ||
            !Array.isArray(data.geometry.features) ||
            data.geometry.features.length === 0
        ) {
            showMapMessage(
                "No static route geometry is available for this route."
            );
            return;
        }

        routeGeometryLayer = L.geoJSON(data.geometry, {
            style: {
                color: "#d97706",
                weight: 5,
                opacity: 0.85
            }
        }).addTo(map);

        if (data.stops && Array.isArray(data.stops.features)) {
            routeStopLayer = L.geoJSON(data.stops, {
                pointToLayer: (_feature, latlng) => {
                    return L.circleMarker(latlng, {
                        radius: 4,
                        color: "#92400e",
                        fillColor: "#fbbf24",
                        fillOpacity: 0.9,
                        weight: 2
                    });
                },

                onEachFeature: (feature, layer) => {
                    const name =
                        feature.properties?.stop_name || "Route stop";

                    const stopId =
                        feature.properties?.stop_id || "";

                    layer.bindPopup(`
                        <strong>${escapeHtml(name)}</strong>
                        <br>Stop ID: ${escapeHtml(stopId)}
                    `);
                }
            }).addTo(map);
        }

        const bounds = routeGeometryLayer.getBounds();

        if (bounds.isValid()) {
            map.fitBounds(bounds, {
                padding: [30, 30],
                maxZoom: 15
            });
        }

        hideMapMessage();
    } catch (error) {
        if (requestId !== routeMapRequest) {
            return;
        }

        console.error("Route map error:", error);
        clearRouteLayers();
        showMapMessage(error.message);
    }
}

// Load performance for the selected route
async function selectRoute(routeId) {
    const requestId = ++routePerformanceRequest;

    const route = routeData.find(
        item => String(item.route_id) === String(routeId)
    );

    routePerformance.classList.remove("empty-card");
    routePerformance.innerHTML =
        "<p>Loading route performance...</p>";

    try {
        const response = await fetch(
            `${API_BASE_URL}/api/routes/${encodeURIComponent(routeId)}/performance`
        );

        if (
            requestId !== routePerformanceRequest ||
            routeSelect.value !== String(routeId)
        ) {
            return;
        }

        if (response.status === 404) {
            displayRoutePerformance(route, null);
            return;
        }

        if (!response.ok) {
            throw new Error("Unable to load route performance");
        }

        const performance = await response.json();

        if (requestId === routePerformanceRequest) {
            displayRoutePerformance(route, performance);
        }
    } catch (error) {
        if (requestId !== routePerformanceRequest) {
            return;
        }

        console.error("Route performance error:", error);
        routePerformance.innerHTML =
            "<p>Unable to load route performance.</p>";
    }
}

function displayRoutePerformance(route, performance) {
    const routeName = route
        ? route.route_short_name || route.route_id
        : "Selected route";

    if (!performance || performance.total_services === 0) {
        routePerformance.innerHTML = `
            <strong class="selected-stop-name">
                Route ${escapeHtml(routeName)}
            </strong>
            <p class="detail-message">
                No performance data is currently available for this route.
            </p>
        `;
        return;
    }

    routePerformance.innerHTML = `
        <strong class="selected-stop-name">
            Route ${escapeHtml(routeName)}
        </strong>
        ${performanceMarkup(performance)}
    `;
}

// Load routes and performance for a selected stop
async function selectStop(stop) {
    selectedStopId = String(stop.stop_id);

    selectedStopInfo.classList.remove("empty-card");
    selectedStopInfo.innerHTML = `
        <strong class="selected-stop-name">
            ${escapeHtml(stop.stop_name)}
        </strong>
        <div class="selected-stop-id">
            Stop ID: ${escapeHtml(stop.stop_id)}
        </div>
        <p class="detail-message">Loading transport information...</p>
    `;

    try {
        const stopId = encodeURIComponent(stop.stop_id);

        const [routeResponse, performanceResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/api/stops/${stopId}/routes`),
            fetch(`${API_BASE_URL}/api/stops/${stopId}/performance`)
        ]);

        if (!routeResponse.ok) {
            throw new Error("Unable to load stop routes");
        }

        const routes = await routeResponse.json();

        let performance = null;

        if (performanceResponse.ok) {
            performance = await performanceResponse.json();
        }

        if (selectedStopId !== String(stop.stop_id)) {
            return;
        }

        displayStopInformation(stop, routes, performance);
    } catch (error) {
        if (selectedStopId !== String(stop.stop_id)) {
            return;
        }

        console.error("Stop information error:", error);

        selectedStopInfo.innerHTML = `
            <strong>${escapeHtml(stop.stop_name)}</strong>
            <p class="detail-message">
                Unable to load transport information.
            </p>
        `;
    }
}

// Display stop details and clickable routes
function displayStopInformation(stop, routes, performance) {
    const routeList = Array.isArray(routes) ? routes : [];

    const routeMarkup = routeList.length === 0
        ? `<p class="detail-message">
               No route information is available for this stop.
           </p>`
        : routeList.map(route => `
            <div class="route-item"
                 data-route-id="${escapeHtml(route.route_id)}">
                <span class="route-short-name">
                    ${escapeHtml(route.route_short_name || route.route_id)}
                </span>
                <span class="route-long-name">
                    ${escapeHtml(route.route_long_name || "Route")}
                </span>
            </div>
        `).join("");

    const performanceContent =
        !performance || performance.total_services === 0
            ? `<p class="detail-message">
                   No performance data is currently available.
               </p>`
            : performanceMarkup(performance);

    selectedStopInfo.innerHTML = `
        <strong class="selected-stop-name">
            ${escapeHtml(stop.stop_name)}
        </strong>

        <div class="selected-stop-id">
            Stop ID: ${escapeHtml(stop.stop_id)}
        </div>

        <div class="selected-stop-location">
            Location: ${stop.stop_lat.toFixed(5)},
            ${stop.stop_lon.toFixed(5)}
        </div>

        <div class="detail-heading">Routes serving this stop</div>
        ${routeMarkup}

        <div class="detail-heading">Stop performance</div>
        ${performanceContent}
    `;

    selectedStopInfo
        .querySelectorAll(".route-item[data-route-id]")
        .forEach(item => {
            item.addEventListener("click", () => {
                const routeId = item.dataset.routeId;

                const exists = [...routeSelect.options].some(
                    option => option.value === routeId
                );

                if (exists) {
                    routeSelect.value = routeId;
                    chooseRoute(routeId);
                }
            });
        });
}

// Select a location on the map
map.on("click", event => {
    setSelectedLocation(
        event.latlng.lat,
        event.latlng.lng,
        "Selected on map"
    );
});

// Use the browser's current location
locationButton.addEventListener("click", () => {
    if (!navigator.geolocation) {
        selectedLocationInfo.textContent =
            "Location services are not supported by this browser.";
        return;
    }

    locationButton.disabled = true;
    locationButton.textContent = "Finding Location...";

    navigator.geolocation.getCurrentPosition(
        position => {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            setSelectedLocation(
                latitude,
                longitude,
                "Current location"
            );

            map.setView([latitude, longitude], 15);
            resetLocationButton();
        },
        error => {
            console.error("Geolocation error:", error);

            selectedLocationInfo.textContent =
                "Unable to access your location. Click the map instead.";

            resetLocationButton();
        },
        {
            enableHighAccuracy: true,
            timeout: 10000
        }
    );
});

function resetLocationButton() {
    locationButton.disabled = false;
    locationButton.textContent = "Use My Location";
}

// Calculate straight-line distance in metres
function calculateStraightLineDistance(lat1, lon1, lat2, lon2) {
    const radius = 6371000;
    const radians = degrees => degrees * Math.PI / 180;

    const latitudeDifference = radians(lat2 - lat1);
    const longitudeDifference = radians(lon2 - lon1);

    const a =
        Math.sin(latitudeDifference / 2) ** 2 +
        Math.cos(radians(lat1)) *
        Math.cos(radians(lat2)) *
        Math.sin(longitudeDifference / 2) ** 2;

    return 2 * radius * Math.atan2(
        Math.sqrt(a),
        Math.sqrt(1 - a)
    );
}

// Find the closest stop
function findNearestStop(latitude, longitude) {
    let nearest = null;
    let shortestDistance = Infinity;

    for (const stop of stopData) {
        const distance = calculateStraightLineDistance(
            latitude,
            longitude,
            stop.stop_lat,
            stop.stop_lon
        );

        if (distance < shortestDistance) {
            nearest = stop;
            shortestDistance = distance;
        }
    }

    return nearest
        ? { stop: nearest, distance: shortestDistance }
        : null;
}

// Show the selected location
function setSelectedLocation(latitude, longitude, source) {
    const lat = Number(latitude);
    const lon = Number(longitude);

    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        return;
    }

    selectedLocation = {
        latitude: lat,
        longitude: lon,
        source
    };

    if (selectedLocationMarker) {
        map.removeLayer(selectedLocationMarker);
    }

    selectedLocationMarker = L.marker([lat, lon]).addTo(map);

    selectedLocationMarker.bindPopup(`
        <strong>${escapeHtml(source)}</strong>
        <br>${lat.toFixed(5)}, ${lon.toFixed(5)}
    `);

    selectedLocationInfo.classList.remove("empty-card");

    selectedLocationInfo.innerHTML = `
        <span class="location-label">${escapeHtml(source)}</span>

        <div class="coordinate-row">
            <span class="coordinate-label">Latitude</span>
            <span class="coordinate-value">${lat.toFixed(5)}</span>
        </div>

        <div class="coordinate-row">
            <span class="coordinate-label">Longitude</span>
            <span class="coordinate-value">${lon.toFixed(5)}</span>
        </div>

        <div id="nearestStopResult"></div>
    `;

    showNearestStop(lat, lon);
}

// Highlight the nearest stop
function showNearestStop(latitude, longitude) {
    if (nearestStopMarker) {
        nearestStopMarker.setStyle({
            color: "#3388ff",
            fillColor: "#3388ff",
            radius: 6,
            weight: 2
        });

        nearestStopMarker = null;
    }

    const resultElement = element("nearestStopResult");

    if (!resultElement) {
        return;
    }

    const result = findNearestStop(latitude, longitude);

    if (!result) {
        resultElement.innerHTML = `
            <p class="detail-message">
                No stop data is available to find the nearest stop.
            </p>
        `;
        return;
    }

    const { stop, distance } = result;

    const distanceText = distance < 1000
        ? `${Math.round(distance)} m`
        : `${(distance / 1000).toFixed(2)} km`;

    resultElement.innerHTML = `
        <div class="detail-heading">Nearest Adelaide Metro Stop</div>

        <div class="coordinate-row">
            <span class="coordinate-label">Stop name</span>
            <span class="coordinate-value">
                ${escapeHtml(stop.stop_name)}
            </span>
        </div>

        <div class="coordinate-row">
            <span class="coordinate-label">Stop ID</span>
            <span class="coordinate-value">
                ${escapeHtml(stop.stop_id)}
            </span>
        </div>

        <div class="coordinate-row">
            <span class="coordinate-label">Straight-line distance</span>
            <span class="coordinate-value">${distanceText}</span>
        </div>

        <p class="detail-message">
            This is straight-line distance, not walking distance.
        </p>
    `;

    nearestStopMarker = stopMarkers.get(String(stop.stop_id)) || null;

    if (nearestStopMarker) {
        nearestStopMarker.setStyle({
            color: "#d97706",
            fillColor: "#f59e0b",
            radius: 11,
            weight: 4
        });

        nearestStopMarker.bringToFront();
    }
}

// Convert the selected demo date to Adelaide time

function getPlaybackDate(value) {
    if (!value) {
        return null;
    }

    // Interpret the selected date and time in Australia/Adelaide.
    const local = new Date(`${value}:00Z`);
    if (Number.isNaN(local.getTime())) {
        return null;
    }

    const formatter = new Intl.DateTimeFormat("en-US", {
        timeZone: "Australia/Adelaide",
        timeZoneName: "longOffset"
    });

    function offsetMinutes(date) {
        const part = formatter.formatToParts(date)
            .find(item => item.type === "timeZoneName");

        const match = part?.value.match(
            /^GMT([+-])(\d{1,2})(?::(\d{2}))?$/
        );

        if (!match) {
            return null;
        }

        const sign = match[1] === "+" ? 1 : -1;
        return sign * (
            Number(match[2]) * 60 + Number(match[3] || 0)
        );
    }

    let offset = offsetMinutes(local);
    if (offset === null) {
        return null;
    }

    let result = new Date(local.getTime() - offset * 60000);

    // Recheck the offset at the actual instant for daylight saving.
    const correctedOffset = offsetMinutes(result);
    if (correctedOffset === null) {
        return null;
    }

    if (correctedOffset !== offset) {
        result = new Date(
            local.getTime() - correctedOffset * 60000
        );
    }

    return Number.isNaN(result.getTime()) ? null : result;
}


// Display Adelaide local time
function formatPlaybackTime(date) {
    if (!date || Number.isNaN(date.getTime())) {
        return "--:--:--";
    }

    return new Intl.DateTimeFormat("en-AU", {
        timeZone: "Australia/Adelaide",
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false
    }).format(date);
}

// Clear historical playback
function clearPlayback() {
    playbackRequestId++;
    pausePlayback();

    recordedPositions = [];
    playbackStartTime = null;
    playbackEndTime = null;
    currentPlaybackTime = null;
    playbackRouteId = null;

    vehicleLayer.clearLayers();

    playbackSlider.value = 0;
    playbackSlider.max = 100;
    playbackSlider.disabled = true;

    playbackTime.textContent = "--:--:--";

    playButton.disabled = true;
    pauseButton.disabled = true;
    resetButton.disabled = true;

    loadPlaybackButton.disabled = false;
    loadPlaybackButton.textContent = "Load Vehicle History";

    playbackStatus.textContent =
        "Select a route and load its recorded vehicle history.";
}

// Load recorded GPS observations
async function loadVehicleHistory() {
    const routeId = routeSelect.value;

    if (!routeId) {
        playbackStatus.textContent = "Please select a route first.";
        return;
    }

    const start = getPlaybackDate(playbackStart.value);
    const end = getPlaybackDate(playbackEnd.value);

    if (!start || !end || start >= end) {
        playbackStatus.textContent =
            "Please enter a valid start and end time.";
        return;
    }

    clearPlayback();

    const requestId = ++playbackRequestId;

    loadPlaybackButton.disabled = true;
    loadPlaybackButton.textContent = "Loading...";
    playbackStatus.textContent = "Loading recorded vehicle positions...";

    try {
        const allPositions = [];
        let offset = 0;

        while (true) {
            const params = new URLSearchParams({
                start_time: start.toISOString(),
                end_time: end.toISOString(),
                limit: "1000",
                offset: String(offset)
            });

            const response = await fetch(
                `${API_BASE_URL}/api/routes/${encodeURIComponent(routeId)}/vehicle-positions?${params}`
            );

            if (
                requestId !== playbackRequestId ||
                routeSelect.value !== routeId
            ) {
                return;
            }

            if (!response.ok) {
                throw new Error(
                    `Unable to load vehicle history (${response.status}).`
                );
            }

            const data = await response.json();

            if (
                requestId !== playbackRequestId ||
                routeSelect.value !== routeId
            ) {
                return;
            }

            if (!Array.isArray(data.positions)) {
                throw new Error("Invalid vehicle history response.");
            }

            allPositions.push(...data.positions);

            playbackStatus.textContent =
                `Loaded ${allPositions.length} observations...`;

            if (data.next_offset == null) {
                break;
            }

            if (
                !Number.isInteger(data.next_offset) ||
                data.next_offset <= offset
            ) {
                throw new Error("Invalid vehicle history pagination.");
            }

            offset = data.next_offset;
        }

        recordedPositions = allPositions.filter(position => {
            const latitude = Number(position.latitude);
            const longitude = Number(position.longitude);
            const timestamp = new Date(position.timestamp);

            return (
                position.latitude != null &&
                position.longitude != null &&
                Number.isFinite(latitude) &&
                Number.isFinite(longitude) &&
                latitude >= -90 &&
                latitude <= 90 &&
                longitude >= -180 &&
                longitude <= 180 &&
                !Number.isNaN(timestamp.getTime())
            );
        }).sort((a, b) => {
            return new Date(a.timestamp) - new Date(b.timestamp);
        });

        playbackStartTime = start;
        playbackEndTime = end;
        currentPlaybackTime = new Date(start);
        playbackRouteId = routeId;

        playbackSlider.max = Math.ceil(
            (end.getTime() - start.getTime()) / 1000
        );

        playbackSlider.value = 0;
        playbackTime.textContent = formatPlaybackTime(start);

        if (recordedPositions.length === 0) {
            playbackStatus.textContent =
                "No recorded vehicle positions are available in this period.";
            return;
        }

        playbackSlider.disabled = false;
        playButton.disabled = false;
        resetButton.disabled = false;

        updatePlaybackDisplay();
    } catch (error) {
        if (requestId !== playbackRequestId) {
            return;
        }

        console.error("Playback loading error:", error);
        playbackStatus.textContent = error.message;
    } finally {
        if (requestId === playbackRequestId) {
            loadPlaybackButton.disabled = false;
            loadPlaybackButton.textContent = "Load Vehicle History";
        }
    }
}

// Show the last recorded position for each vehicle
function updateVehicleMarkers() {
    vehicleLayer.clearLayers();

    if (!currentPlaybackTime) {
        return { vehicles: 0, observations: 0 };
    }

    const latestPositions = new Map();
    let observationCount = 0;

    for (const position of recordedPositions) {
        if (new Date(position.timestamp) > currentPlaybackTime) {
            break;
        }

        observationCount++;

        const vehicleId = String(
            position.vehicle_id || `observation-${position.id}`
        );

        latestPositions.set(vehicleId, position);
    }

    for (const position of latestPositions.values()) {
        const marker = L.circleMarker(
            [Number(position.latitude), Number(position.longitude)],
            {
                radius: 8,
                color: "#166534",
                fillColor: "#22c55e",
                fillOpacity: 0.95,
                weight: 2
            }
        );

        marker.bindPopup(`
            <strong>Recorded vehicle</strong>
            <br>Vehicle: ${escapeHtml(position.vehicle_id || "Unknown")}
            <br>Route: ${escapeHtml(position.route_id || playbackRouteId)}
            <br>Trip: ${escapeHtml(position.trip_id || "Unknown")}
            <br>GPS recorded:
            ${escapeHtml(formatPlaybackTime(new Date(position.timestamp)))}
            <br><small>Last recorded position, not live tracking.</small>
        `);

        marker.addTo(vehicleLayer);
    }

    return {
        vehicles: latestPositions.size,
        observations: observationCount
    };
}

// Update the playback clock and map
function updatePlaybackDisplay() {
    if (!currentPlaybackTime || !playbackStartTime) {
        return;
    }

    playbackTime.textContent =
        formatPlaybackTime(currentPlaybackTime);

    playbackSlider.value = Math.round(
        (currentPlaybackTime.getTime() -
            playbackStartTime.getTime()) / 1000
    );

    const result = updateVehicleMarkers();

    playbackStatus.textContent = result.observations === 0
        ? "No observations recorded yet in this playback window."
        : `${result.vehicles} vehicles shown from ` +
          `${result.observations} recorded observations.`;
}

function advancePlayback() {
    if (!currentPlaybackTime || !playbackEndTime) {
        return;
    }

    const nextTime = new Date(
        currentPlaybackTime.getTime() +
        PLAYBACK_STEP_SECONDS * 1000
    );

    if (nextTime >= playbackEndTime) {
        currentPlaybackTime = new Date(playbackEndTime);
        updatePlaybackDisplay();
        pausePlayback();
        return;
    }

    currentPlaybackTime = nextTime;
    updatePlaybackDisplay();
}

function playPlayback() {
    if (
        playbackTimer ||
        !currentPlaybackTime ||
        recordedPositions.length === 0
    ) {
        return;
    }

    if (currentPlaybackTime >= playbackEndTime) {
        currentPlaybackTime = new Date(playbackStartTime);
        updatePlaybackDisplay();
    }

    playbackTimer = setInterval(
        advancePlayback,
        PLAYBACK_INTERVAL_MS
    );

    playButton.disabled = true;
    pauseButton.disabled = false;
}

function pausePlayback() {
    if (playbackTimer) {
        clearInterval(playbackTimer);
        playbackTimer = null;
    }

    pauseButton.disabled = true;

    playButton.disabled =
        recordedPositions.length === 0 ||
        !currentPlaybackTime;
}

function resetPlayback() {
    pausePlayback();

    if (!playbackStartTime) {
        return;
    }

    currentPlaybackTime = new Date(playbackStartTime);
    updatePlaybackDisplay();
}

loadPlaybackButton.addEventListener("click", loadVehicleHistory);
playButton.addEventListener("click", playPlayback);
pauseButton.addEventListener("click", pausePlayback);
resetButton.addEventListener("click", resetPlayback);

playbackSlider.addEventListener("input", () => {
    if (!playbackStartTime) {
        return;
    }

    pausePlayback();

    currentPlaybackTime = new Date(
        playbackStartTime.getTime() +
        Number(playbackSlider.value) * 1000
    );

    updatePlaybackDisplay();
});

// Clear hotspots when changing routes
function clearHotspots() {
    hotspotRequest++;
    hotspotData = [];

    if (hotspotLayer) {
        map.removeLayer(hotspotLayer);
        hotspotLayer = null;
    }

    hotspotResults.innerHTML = "";
    hotspotStatus.textContent = "Select a route to view hotspots.";
}

// Load ranked delay hotspots from the backend
async function loadHotspots(routeId) {
    const requestId = ++hotspotRequest;

    hotspotData = [];

    if (hotspotLayer) {
        map.removeLayer(hotspotLayer);
        hotspotLayer = null;
    }

    hotspotResults.innerHTML = "";
    hotspotStatus.textContent = "Loading historical delay hotspots...";

    try {
        const params = new URLSearchParams({
            route_id: routeId,
            min_services: hotspotMinServices.value
        });

        const response = await fetch(
            `${API_BASE_URL}/api/analysis/hotspots?${params}`
        );

        if (
            requestId !== hotspotRequest ||
            routeSelect.value !== routeId
        ) {
            return;
        }

        if (!response.ok) {
            throw new Error(
                `Unable to load hotspots (${response.status}).`
            );
        }

        const data = await response.json();

        if (!Array.isArray(data.hotspots)) {
            throw new Error("Invalid hotspot response.");
        }

        hotspotData = data.hotspots;
        renderHotspots();
    } catch (error) {
        if (requestId !== hotspotRequest) {
            return;
        }

        console.error("Hotspot loading error:", error);
        hotspotStatus.textContent = error.message;
    }
}

// Display hotspot markers and the ranked list
function renderHotspots() {
    if (hotspotLayer) {
        map.removeLayer(hotspotLayer);
        hotspotLayer = null;
    }

    hotspotResults.innerHTML = "";

    if (hotspotData.length === 0) {
        hotspotStatus.textContent =
            "No stops meet the minimum service threshold for this route.";
        return;
    }

    const stopLookup = new Map(
        stopData.map(stop => [String(stop.stop_id), stop])
    );

    const markers = [];
    let mappedCount = 0;

    for (const hotspot of hotspotData) {
        const stop = stopLookup.get(String(hotspot.stop_id));

        if (!stop) {
            continue;
        }

        mappedCount++;

        const rank = Number(hotspot.rank) || mappedCount;
        const severe = Number(hotspot.severe_delay_percentage);
        const late = Number(hotspot.total_late_percentage);
        const services = Number(hotspot.total_services);

        const severeText = Number.isFinite(severe)
            ? `${severe.toFixed(1)}%`
            : "Unavailable";

        const lateText = Number.isFinite(late)
            ? `${late.toFixed(1)}%`
            : "Unavailable";

        const servicesText = Number.isFinite(services)
            ? String(services)
            : "Unavailable";

        const marker = L.circleMarker(
            [stop.stop_lat, stop.stop_lon],
            {
                radius: rank <= 3 ? 12 : 9,
                color: "#991b1b",
                fillColor: rank <= 3 ? "#dc2626" : "#f97316",
                fillOpacity: 0.9,
                weight: 2
            }
        );

        marker.bindPopup(`
            <strong>#${rank} Delay hotspot</strong>
            <br>${escapeHtml(stop.stop_name)}
            <br>Stop ID: ${escapeHtml(stop.stop_id)}
            <br>Severe delays: ${severeText}
            <br>Late services: ${lateText}
            <br>Services analysed: ${servicesText}
            <br>
            <small>Historical analysis, not live delay information.</small>
        `);

        markers.push(marker);

        if (mappedCount <= 10) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "hotspot-item";

            const title = document.createElement("strong");
            title.textContent = `#${rank} ${stop.stop_name}`;

            const details = document.createElement("small");
            details.textContent =
                `Severe delays: ${severeText} · ` +
                `Late: ${lateText} · ${servicesText} services`;

            button.append(title, details);

            button.addEventListener("click", () => {
                map.setView(
                    [stop.stop_lat, stop.stop_lon],
                    Math.max(map.getZoom(), 15)
                );

                if (hotspotToggle.checked && hotspotLayer) {
                    marker.openPopup();
                } else {
                    selectStop(stop);
                }
            });

            hotspotResults.appendChild(button);
        }
    }

    if (mappedCount === 0) {
        hotspotStatus.textContent =
            `${hotspotData.length} hotspots returned, ` +
            "but no matching stop coordinates were loaded.";
        return;
    }

    hotspotLayer = L.layerGroup(markers);

    if (hotspotToggle.checked) {
        hotspotLayer.addTo(map);
    }

    hotspotStatus.textContent =
        `${mappedCount} of ${hotspotData.length} ranked hotspots mapped. ` +
        "Showing the top 10 below.";
}

// Show or hide the hotspot layer
hotspotToggle.addEventListener("change", () => {
    if (!hotspotLayer) {
        return;
    }

    if (hotspotToggle.checked) {
        hotspotLayer.addTo(map);
    } else {
        map.removeLayer(hotspotLayer);
    }
});

// Refresh hotspots when the minimum service count changes
hotspotMinServices.addEventListener("change", () => {
    if (routeSelect.value) {
        loadHotspots(routeSelect.value);
    }
});

// Start loading the network
loadStops();
loadRoutes();
