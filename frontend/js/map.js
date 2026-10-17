
const API_BASE_URL = "http://127.0.0.1:5000";
const ADELAIDE_LAT = -34.9285;
const ADELAIDE_LON = 138.6007;

let stopData = [];
let routeData = [];
const stopMarkers = {};

let selectedLocation = null;
let selectedLocationMarker = null;
let nearestStopMarker = null;
let selectedStopId = null;

let routeGeometryLayer = null;
let routeStopLayer = null;
let routeMapRequest = 0;
let routePerformanceRequest = 0;

let recordedPositions = [];
let playbackStartTime = null;
let playbackEndTime = null;
let currentPlaybackTime = null;
let playbackRouteId = null;
let playbackTimer = null;
let playbackRequestId = 0;

const PLAYBACK_STEP_SECONDS = 30;
const PLAYBACK_INTERVAL_MS = 500;

const map = L.map("map").setView([ADELAIDE_LAT, ADELAIDE_LON], 13);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

const routeSelect = document.getElementById("routeSelect");
const routePerformance = document.getElementById("routePerformance");
const locationButton = document.getElementById("locationButton");
const selectedLocationInfo = document.getElementById("selectedLocationInfo");
const selectedStopInfo = document.getElementById("selectedStopInfo");
const stopCount = document.getElementById("stopCount");
const routeCount = document.getElementById("routeCount");
const mapMessage = document.getElementById("mapMessage");

const playbackStart = document.getElementById("playbackStart");
const playbackEnd = document.getElementById("playbackEnd");
const loadPlaybackButton = document.getElementById("loadPlaybackButton");
const playbackTime = document.getElementById("playbackTime");
const playbackSlider = document.getElementById("playbackSlider");
const playbackStatus = document.getElementById("playbackStatus");
const playButton = document.getElementById("playButton");
const pauseButton = document.getElementById("pauseButton");
const resetButton = document.getElementById("resetButton");

const vehicleLayer = L.layerGroup().addTo(map);

loadStops();
loadRoutes();

// Load stops from the backend
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

        stopData = stops
            .filter(hasValidCoordinates)
            .map(stop => ({
                ...stop,
                stop_lat: Number(stop.stop_lat),
                stop_lon: Number(stop.stop_lon)
            }));

        createStopMarkers();
        stopCount.textContent = `${stopData.length} stops`;

        if (stopData.length === 0) {
            showMapMessage("No stop data is currently available.");
        } else {
            fitMapToStops();
        }

        if (selectedLocation) {
            showNearestStop(
                selectedLocation.latitude,
                selectedLocation.longitude
            );
        }
    } catch (error) {
        console.error("Stop loading error:", error);
        stopCount.textContent = "Stops unavailable";
        showMapMessage("Unable to load Adelaide Metro stops.");
    }
}

// Load routes from the backend
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
        populateRouteSelect();

        routeCount.textContent = `${routeData.length} routes`;
        routeSelect.disabled = false;
    } catch (error) {
        console.error("Route loading error:", error);
        routeCount.textContent = "Routes unavailable";
        routeSelect.innerHTML =
            '<option value="">Routes unavailable</option>';
    }
}

// Add stop markers to the map
function createStopMarkers() {
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

        stopMarkers[stop.stop_id] = marker;

        marker.bindTooltip(escapeHtml(stop.stop_name), {
            direction: "top",
            offset: [0, -5]
        });

        marker.bindPopup(`
            <strong>${escapeHtml(stop.stop_name)}</strong>
            <br>Stop ID: ${escapeHtml(stop.stop_id)}
            <br>Latitude: ${stop.stop_lat.toFixed(5)}
            <br>Longitude: ${stop.stop_lon.toFixed(5)}
        `);

        marker.on("click", event => {
            L.DomEvent.stopPropagation(event);
            selectStop(stop);
        });
    });
}

// Fill the route dropdown
function populateRouteSelect() {
    routeSelect.innerHTML =
        '<option value="">Select a route</option>';

    const sortedRoutes = [...routeData].sort((a, b) => {
        const nameA = a.route_short_name || a.route_id;
        const nameB = b.route_short_name || b.route_id;

        return String(nameA).localeCompare(
            String(nameB),
            undefined,
            { numeric: true }
        );
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
}

// Update route details, geometry and playback together
function chooseRoute(routeId) {
    clearPlayback();

    if (!routeId) {
        routePerformanceRequest++;
        routeMapRequest++;

        routePerformance.classList.add("empty-card");
        routePerformance.innerHTML =
            "<p>Select a route to view performance.</p>";

        clearRouteLayers();
        hideMapMessage();
        return;
    }

    selectRoute(routeId);
    showRouteOnMap(routeId);
}

routeSelect.addEventListener("change", () => {
    chooseRoute(routeSelect.value);
});

// Remove the previous route layers
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

// Show the selected route using official geometry
async function showRouteOnMap(routeId) {
    const requestId = ++routeMapRequest;

    clearRouteLayers();
    showMapMessage("Loading route map...");

    try {
        const response = await fetch(
            `${API_BASE_URL}/api/routes/${encodeURIComponent(routeId)}/map-data`
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
                    "Recorded map data is not available for this route."
                );
            }

            if (response.status === 503) {
                throw new Error(
                    "Recorded route map data is not configured on the backend."
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
                "No recorded route geometry is available for this route."
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
        console.error("Route performance error:", error);

        if (requestId === routePerformanceRequest) {
            routePerformance.innerHTML =
                "<p>Unable to load route performance.</p>";
        }
    }
}

function displayRoutePerformance(route, performance) {
    const routeName = route
        ? route.route_short_name || route.route_id
        : "Selected route";

    if (!performance || performance.total_services === 0) {
        routePerformance.innerHTML = `
            <strong class="selected-stop-name">
                ${escapeHtml(routeName)}
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

// Load information when a stop is selected
async function selectStop(stop) {
    selectedStopId = stop.stop_id;
    selectedStopInfo.classList.remove("empty-card");

    selectedStopInfo.innerHTML = `
        <strong class="selected-stop-name">
            ${escapeHtml(stop.stop_name)}
        </strong>
        <div class="selected-stop-id">
            Stop ID: ${escapeHtml(stop.stop_id)}
        </div>
        <div class="selected-stop-location">
            ${stop.stop_lat.toFixed(5)}, ${stop.stop_lon.toFixed(5)}
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
        } else if (performanceResponse.status !== 404) {
            throw new Error("Unable to load stop performance");
        }

        if (selectedStopId !== stop.stop_id) {
            return;
        }

        displayStopInformation(stop, routes, performance);
    } catch (error) {
        console.error("Stop information error:", error);

        if (selectedStopId !== stop.stop_id) {
            return;
        }

        selectedStopInfo.innerHTML = `
            <strong class="selected-stop-name">
                ${escapeHtml(stop.stop_name)}
            </strong>
            <div class="selected-stop-id">
                Stop ID: ${escapeHtml(stop.stop_id)}
            </div>
            <p class="detail-message">
                Unable to load transport information.
            </p>
        `;
    }
}

// Show routes and performance for the selected stop
function displayStopInformation(stop, routes, performance) {
    let routeMarkup = "";

    if (!Array.isArray(routes) || routes.length === 0) {
        routeMarkup = `
            <p class="detail-message">
                No route information is available for this stop.
            </p>
        `;
    } else {
        routes.forEach(route => {
            const shortName = route.route_short_name || route.route_id;
            const longName =
                route.route_long_name || "Route description unavailable";

            routeMarkup += `
                <div class="route-item"
                     data-route-id="${escapeHtml(route.route_id)}">
                    <span class="route-short-name">
                        ${escapeHtml(shortName)}
                    </span>
                    <div class="route-long-name">
                        ${escapeHtml(longName)}
                    </div>
                </div>
            `;
        });
    }

    const performanceContent =
        !performance || performance.total_services === 0
            ? `<p class="detail-message">
                   No performance data is currently available for this stop.
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
        .forEach(element => {
            element.style.cursor = "pointer";

            element.addEventListener("click", () => {
                const routeId = element.dataset.routeId;

                const routeExists = [...routeSelect.options].some(
                    option => option.value === routeId
                );

                if (!routeExists) {
                    return;
                }

                routeSelect.value = routeId;
                chooseRoute(routeId);
            });
        });
}

function performanceMarkup(performance) {
    const metrics = [
        ["Services analysed", escapeHtml(performance.total_services)],
        ["Average delay", `${formatNumber(performance.average_delay)} min`],
        ["On time", formatPercentage(performance.on_time_percentage)],
        ["Delayed", formatPercentage(performance.delayed_percentage)],
        ["Severe delay", formatPercentage(performance.severe_delay_percentage)],
        ["Early", formatPercentage(performance.early_percentage)]
    ];

    return `
        <div class="performance-card">
            ${metrics.map(([label, value]) => `
                <div class="performance-row">
                    <span class="performance-label">${label}</span>
                    <span class="performance-value">${value}</span>
                </div>
            `).join("")}
        </div>
    `;
}

// Select a location by clicking the map
map.on("click", event => {
    setSelectedLocation(
        event.latlng.lat,
        event.latlng.lng,
        "Selected on map"
    );
});

// Use the browser's location when permission is given
locationButton.addEventListener("click", () => {
    if (!navigator.geolocation) {
        if (!selectedLocation) {
            selectedLocationInfo.innerHTML =
                "<p>Location services are not supported by this browser.</p>";
        }
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

            if (!selectedLocation) {
                selectedLocationInfo.innerHTML = `
                    <p>
                        Unable to access your location.
                        You can still select a location by clicking the map.
                    </p>
                `;
            }

            resetLocationButton();
        },
        {
            enableHighAccuracy: true,
            timeout: 10000
        }
    );
});

// Update the selected location and its nearest stop
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

    selectedLocationMarker = L.marker(
        [lat, lon],
        { title: "Selected Location" }
    ).addTo(map);

    selectedLocationMarker.bindPopup(`
        <strong>Selected Location</strong>
        <br>${escapeHtml(source)}
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

// Calculate straight-line distance between two locations
function calculateStraightLineDistance(lat1, lon1, lat2, lon2) {
    const earthRadiusMetres = 6371000;
    const toRadians = degrees => degrees * Math.PI / 180;

    const latitudeDifference = toRadians(lat2 - lat1);
    const longitudeDifference = toRadians(lon2 - lon1);

    const a =
        Math.sin(latitudeDifference / 2) ** 2 +
        Math.cos(toRadians(lat1)) *
        Math.cos(toRadians(lat2)) *
        Math.sin(longitudeDifference / 2) ** 2;

    return 2 * earthRadiusMetres *
        Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Find the closest stop in the loaded data
function findNearestStop(latitude, longitude) {
    let nearestStop = null;
    let shortestDistance = Infinity;

    for (const stop of stopData) {
        const distance = calculateStraightLineDistance(
            latitude,
            longitude,
            stop.stop_lat,
            stop.stop_lon
        );

        if (distance < shortestDistance) {
            nearestStop = stop;
            shortestDistance = distance;
        }
    }

    if (!nearestStop) {
        return null;
    }

    return {
        stop: nearestStop,
        distance: shortestDistance
    };
}

// Show and highlight the nearest stop
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

    const resultElement = document.getElementById("nearestStopResult");

    if (!resultElement) {
        return;
    }

    if (stopData.length === 0) {
        resultElement.innerHTML = `
            <p class="detail-message">
                No stop data is available to calculate the nearest stop.
            </p>
        `;
        return;
    }

    const result = findNearestStop(latitude, longitude);

    if (!result) {
        resultElement.innerHTML =
            "<p>Unable to find a nearby stop.</p>";
        return;
    }

    const { stop, distance } = result;

    const distanceLabel = distance < 1000
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
            <span class="coordinate-value">${distanceLabel}</span>
        </div>

        <p class="detail-message">
            Distance is measured in a straight line,
            not along roads or walking paths.
        </p>
    `;

    nearestStopMarker = stopMarkers[stop.stop_id] || null;

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

function resetLocationButton() {
    locationButton.disabled = false;
    locationButton.textContent = "Use My Location";
}

// Fit the map around the available stops
function fitMapToStops() {
    if (stopData.length === 0) {
        return;
    }

    const bounds = L.latLngBounds(
        stopData.map(stop => [stop.stop_lat, stop.stop_lon])
    );

    if (bounds.isValid()) {
        map.fitBounds(bounds, {
            padding: [30, 30],
            maxZoom: 15
        });
    }
}

function showMapMessage(message) {
    mapMessage.textContent = message;
    mapMessage.classList.remove("hidden");
}

function hideMapMessage() {
    mapMessage.classList.add("hidden");
}

function hasValidCoordinates(stop) {
    if (!stop || typeof stop !== "object") {
        return false;
    }

    if (
        stop.stop_lat === null ||
        stop.stop_lon === null ||
        stop.stop_lat === "" ||
        stop.stop_lon === ""
    ) {
        return false;
    }

    const lat = Number(stop.stop_lat);
    const lon = Number(stop.stop_lon);

    return (
        Number.isFinite(lat) &&
        Number.isFinite(lon) &&
        lat >= -90 &&
        lat <= 90 &&
        lon >= -180 &&
        lon <= 180
    );
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
    if (value === null || value === undefined || value === "") {
        return "Unavailable";
    }

    const number = Number(value);

    return Number.isFinite(number)
        ? `${number.toFixed(1)}%`
        : "Unavailable";
}

// Keep backend text safe when displaying it as HTML
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

// Convert Adelaide local time to an offset-aware timestamp
function getPlaybackDate(value) {
    if (!value) {
        return null;
    }

    const match = value.match(
        /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/
    );

    if (!match) {
        return null;
    }

    const [, year, month, day, hour, minute] = match;

    // Adelaide uses daylight saving from October to early April.
    // September 2026 recorded data uses +09:30.
    const offset = "+09:30";
    const date = new Date(
        `${year}-${month}-${day}T${hour}:${minute}:00${offset}`
    );

    return Number.isNaN(date.getTime()) ? null : date;
}

// Format the playback clock in Adelaide time
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

// Remove old playback data when the route changes
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

// Load recorded positions from every API page
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
                let message = `Unable to load vehicle history (${response.status}).`;

                try {
                    const errorData = await response.json();
                    if (errorData.error) {
                        message = errorData.error;
                    }
                } catch (_error) {
                    // Keep the HTTP error message.
                }

                throw new Error(message);
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

        if (
            requestId !== playbackRequestId ||
            routeSelect.value !== routeId
        ) {
            return;
        }

        recordedPositions = allPositions
            .filter(position => {
                const latitude = Number(position.latitude);
                const longitude = Number(position.longitude);
                const time = new Date(position.timestamp);

                return (
                    position.latitude !== null &&
                    position.longitude !== null &&
                    Number.isFinite(latitude) &&
                    Number.isFinite(longitude) &&
                    latitude >= -90 &&
                    latitude <= 90 &&
                    longitude >= -180 &&
                    longitude <= 180 &&
                    !Number.isNaN(time.getTime())
                );
            })
            .sort((a, b) => {
                const difference =
                    new Date(a.timestamp) - new Date(b.timestamp);

                return difference ||
                    Number(a.id || 0) - Number(b.id || 0);
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

// Show each vehicle at its last recorded position
function updateVehicleMarkers() {
    vehicleLayer.clearLayers();

    if (!currentPlaybackTime || recordedPositions.length === 0) {
        return {
            vehicles: 0,
            observations: 0
        };
    }

    const latestPositions = new Map();
    let observationCount = 0;

    for (const position of recordedPositions) {
        const observationTime = new Date(position.timestamp);

        if (observationTime > currentPlaybackTime) {
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
            [
                Number(position.latitude),
                Number(position.longitude)
            ],
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
            <br>GPS recorded: ${escapeHtml(
                formatPlaybackTime(new Date(position.timestamp))
            )}
            <br>
            <small>Last known position, not a live location.</small>
        `);

        marker.addTo(vehicleLayer);
    }

    return {
        vehicles: latestPositions.size,
        observations: observationCount
    };
}

// Refresh the clock, slider and vehicle markers
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

    if (result.observations === 0) {
        playbackStatus.textContent =
            "No observations recorded yet in this playback window.";
    } else {
        playbackStatus.textContent =
            `${result.vehicles} vehicles shown from ` +
            `${result.observations} recorded observations.`;
    }
}

// Advance the playback clock by 30 seconds
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
