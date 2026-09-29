const API_BASE_URL = "http://127.0.0.1:5000";

const ADELAIDE_LAT = -34.9285;
const ADELAIDE_LON = 138.6007;

let stopData = [];
let routeData = [];

const stopMarkers = {};

let selectedLocationMarker = null;
let selectedStopId = null;


// --------------------------------------------------
// MAP
// --------------------------------------------------

const map = L.map("map").setView(
    [ADELAIDE_LAT, ADELAIDE_LON],
    13
);


L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);


// --------------------------------------------------
// INTERFACE
// --------------------------------------------------

const routeSelect =
    document.getElementById("routeSelect");

const routePerformance =
    document.getElementById("routePerformance");

const locationButton =
    document.getElementById("locationButton");

const selectedLocationInfo =
    document.getElementById("selectedLocationInfo");

const selectedStopInfo =
    document.getElementById("selectedStopInfo");

const stopCount =
    document.getElementById("stopCount");

const routeCount =
    document.getElementById("routeCount");

const mapMessage =
    document.getElementById("mapMessage");


// --------------------------------------------------
// START APPLICATION
// --------------------------------------------------

loadStops();
loadRoutes();


// --------------------------------------------------
// LOAD REAL STOP DATA FROM BACKEND
// --------------------------------------------------

async function loadStops() {

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/stops`
            );


        if (!response.ok) {

            throw new Error(
                "Unable to load stop data."
            );
        }


        const stops =
            await response.json();


        if (!Array.isArray(stops)) {

            throw new Error(
                "Invalid stop data returned by backend."
            );
        }


        stopData =
            stops
                .filter(hasValidCoordinates)
                .map(stop => ({
                    ...stop,
                    stop_lat:
                        Number(stop.stop_lat),
                    stop_lon:
                        Number(stop.stop_lon)
                }));


        createStopMarkers();


        stopCount.textContent =
            `${stopData.length} stops`;


        if (stopData.length === 0) {

            showMapMessage(
                "No stop data is currently available from the backend."
            );

            return;
        }


        fitMapToStops();

    }

    catch (error) {

        console.error(
            "Stop loading error:",
            error
        );


        stopCount.textContent =
            "Stops unavailable";


        showMapMessage(
            "Unable to load Adelaide Metro stops from the backend."
        );
    }
}


// --------------------------------------------------
// LOAD REAL ROUTE DATA FROM BACKEND
// --------------------------------------------------

async function loadRoutes() {

    routeSelect.disabled = true;


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/routes`
            );


        if (!response.ok) {

            throw new Error(
                "Unable to load route data."
            );
        }


        const routes =
            await response.json();


        if (!Array.isArray(routes)) {

            throw new Error(
                "Invalid route data returned by backend."
            );
        }


        routeData = routes;


        populateRouteSelect();


        routeCount.textContent =
            `${routeData.length} routes`;


        routeSelect.disabled =
            false;

    }

    catch (error) {

        console.error(
            "Route loading error:",
            error
        );


        routeCount.textContent =
            "Routes unavailable";


        routeSelect.innerHTML = `
            <option value="">
                Routes unavailable
            </option>
        `;
    }
}


// --------------------------------------------------
// STOP MARKERS
// --------------------------------------------------

function createStopMarkers() {

    stopData.forEach(stop => {

        const marker =
            L.circleMarker(
                [
                    stop.stop_lat,
                    stop.stop_lon
                ],
                {
                    radius: 6,
                    weight: 2,
                    fillOpacity: 0.8
                }
            )
                .addTo(map);


        stopMarkers[
            stop.stop_id
        ] = marker;


        marker.bindTooltip(
            escapeHtml(
                stop.stop_name
            ),
            {
                direction: "top",
                offset: [0, -5]
            }
        );


        marker.bindPopup(`
            <strong>
                ${escapeHtml(stop.stop_name)}
            </strong>
            <br>
            Stop ID:
            ${escapeHtml(stop.stop_id)}
            <br>
            Latitude:
            ${stop.stop_lat.toFixed(5)}
            <br>
            Longitude:
            ${stop.stop_lon.toFixed(5)}
        `);


        marker.on(
            "click",
            () => {

                selectStop(stop);
            }
        );
    });
}


// --------------------------------------------------
// ROUTE SELECT
// --------------------------------------------------

function populateRouteSelect() {

    routeSelect.innerHTML = `
        <option value="">
            Select a route
        </option>
    `;


    const sortedRoutes =
        [...routeData].sort(
            (a, b) => {

                const nameA =
                    a.route_short_name ||
                    a.route_id;

                const nameB =
                    b.route_short_name ||
                    b.route_id;


                return String(nameA)
                    .localeCompare(
                        String(nameB),
                        undefined,
                        {
                            numeric: true
                        }
                    );
            }
        );


    sortedRoutes.forEach(route => {

        const option =
            document.createElement(
                "option"
            );


        option.value =
            route.route_id;


        const shortName =
            route.route_short_name ||
            route.route_id;


        const longName =
            route.route_long_name
                ? ` — ${route.route_long_name}`
                : "";


        option.textContent =
            `${shortName}${longName}`;


        routeSelect.appendChild(
            option
        );
    });
}


routeSelect.addEventListener(
    "change",
    () => {

        const routeId =
            routeSelect.value;


        if (!routeId) {

            routePerformance.classList.add(
                "empty-card"
            );


            routePerformance.innerHTML = `
                <p>
                    Select a route to view performance.
                </p>
            `;


            resetStopMarkerEmphasis();

            return;
        }


        selectRoute(routeId);
    }
);


// --------------------------------------------------
// SELECT ROUTE
// --------------------------------------------------

async function selectRoute(routeId) {

    const route =
        routeData.find(
            item =>
                String(item.route_id) ===
                String(routeId)
        );


    routePerformance.classList.remove(
        "empty-card"
    );


    routePerformance.innerHTML = `
        <p>
            Loading route performance...
        </p>
    `;


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/routes/${encodeURIComponent(routeId)}/performance`
            );


        if (response.status === 404) {

            displayRoutePerformance(
                route,
                null
            );

            return;
        }


        if (!response.ok) {

            throw new Error(
                "Unable to load route performance."
            );
        }


        const performance =
            await response.json();


        displayRoutePerformance(
            route,
            performance
        );

    }

    catch (error) {

        console.error(
            "Route performance error:",
            error
        );


        routePerformance.innerHTML = `
            <p>
                Unable to load route performance.
            </p>
        `;
    }
}


// --------------------------------------------------
// DISPLAY ROUTE PERFORMANCE
// --------------------------------------------------

function displayRoutePerformance(
    route,
    performance
) {

    const routeName =
        route
            ? (
                route.route_short_name ||
                route.route_id
            )
            : "Selected route";


    if (
        !performance ||
        performance.total_services === 0
    ) {

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


// --------------------------------------------------
// SELECT STOP
// --------------------------------------------------

async function selectStop(stop) {

    selectedStopId =
        stop.stop_id;


    selectedStopInfo.classList.remove(
        "empty-card"
    );


    selectedStopInfo.innerHTML = `
        <strong class="selected-stop-name">
            ${escapeHtml(stop.stop_name)}
        </strong>

        <div class="selected-stop-id">
            Stop ID:
            ${escapeHtml(stop.stop_id)}
        </div>

        <div class="selected-stop-location">
            ${stop.stop_lat.toFixed(5)},
            ${stop.stop_lon.toFixed(5)}
        </div>

        <p class="detail-message">
            Loading transport information...
        </p>
    `;


    try {

        const [
            routeResponse,
            performanceResponse
        ] =
            await Promise.all([
                fetch(
                    `${API_BASE_URL}/api/stops/${encodeURIComponent(stop.stop_id)}/routes`
                ),

                fetch(
                    `${API_BASE_URL}/api/stops/${encodeURIComponent(stop.stop_id)}/performance`
                )
            ]);


        if (!routeResponse.ok) {

            throw new Error(
                "Unable to load stop routes."
            );
        }


        const routes =
            await routeResponse.json();


        let performance = null;


        if (performanceResponse.ok) {

            performance =
                await performanceResponse.json();
        }

        else if (
            performanceResponse.status !== 404
        ) {

            throw new Error(
                "Unable to load stop performance."
            );
        }


        if (
            selectedStopId !==
            stop.stop_id
        ) {

            return;
        }


        displayStopInformation(
            stop,
            routes,
            performance
        );

    }

    catch (error) {

        console.error(
            "Stop information error:",
            error
        );


        if (
            selectedStopId !==
            stop.stop_id
        ) {

            return;
        }


        selectedStopInfo.innerHTML = `
            <strong class="selected-stop-name">
                ${escapeHtml(stop.stop_name)}
            </strong>

            <div class="selected-stop-id">
                Stop ID:
                ${escapeHtml(stop.stop_id)}
            </div>

            <p class="detail-message">
                Unable to load transport information.
            </p>
        `;
    }
}


// --------------------------------------------------
// DISPLAY STOP INFORMATION
// --------------------------------------------------

function displayStopInformation(
    stop,
    routes,
    performance
) {

    let routeMarkup = "";


    if (
        !Array.isArray(routes) ||
        routes.length === 0
    ) {

        routeMarkup = `
            <p class="detail-message">
                No route information is available for this stop.
            </p>
        `;
    }

    else {

        routes.forEach(route => {

            const shortName =
                route.route_short_name ||
                route.route_id;


            const longName =
                route.route_long_name ||
                "Route description unavailable";


            routeMarkup += `
                <div
                    class="route-item"
                    data-route-id="${escapeHtml(route.route_id)}"
                >

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


    let performanceMarkupContent;


    if (
        !performance ||
        performance.total_services === 0
    ) {

        performanceMarkupContent = `
            <p class="detail-message">
                No performance data is currently available for this stop.
            </p>
        `;
    }

    else {

        performanceMarkupContent =
            performanceMarkup(
                performance
            );
    }


    selectedStopInfo.innerHTML = `
        <strong class="selected-stop-name">
            ${escapeHtml(stop.stop_name)}
        </strong>

        <div class="selected-stop-id">
            Stop ID:
            ${escapeHtml(stop.stop_id)}
        </div>

        <div class="selected-stop-location">
            Location:
            ${stop.stop_lat.toFixed(5)},
            ${stop.stop_lon.toFixed(5)}
        </div>


        <div class="detail-heading">
            Routes serving this stop
        </div>

        ${routeMarkup}


        <div class="detail-heading">
            Stop performance
        </div>

        ${performanceMarkupContent}
    `;


    selectedStopInfo
        .querySelectorAll(
            ".route-item[data-route-id]"
        )
        .forEach(element => {

            element.style.cursor =
                "pointer";


            element.addEventListener(
                "click",
                () => {

                    const routeId =
                        element.dataset.routeId;


                    routeSelect.value =
                        routeId;


                    selectRoute(
                        routeId
                    );
                }
            );
        });
}


// --------------------------------------------------
// PERFORMANCE MARKUP
// --------------------------------------------------

function performanceMarkup(
    performance
) {

    const averageDelay =
        formatNumber(
            performance.average_delay
        );


    const onTime =
        formatPercentage(
            performance.on_time_percentage
        );


    const delayed =
        formatPercentage(
            performance.delayed_percentage
        );


    const severe =
        formatPercentage(
            performance.severe_delay_percentage
        );


    const early =
        formatPercentage(
            performance.early_percentage
        );


    return `
        <div class="performance-card">

            <div class="performance-row">

                <span class="performance-label">
                    Services analysed
                </span>

                <span class="performance-value">
                    ${escapeHtml(performance.total_services)}
                </span>

            </div>


            <div class="performance-row">

                <span class="performance-label">
                    Average delay
                </span>

                <span class="performance-value">
                    ${averageDelay} min
                </span>

            </div>


            <div class="performance-row">

                <span class="performance-label">
                    On time
                </span>

                <span class="performance-value">
                    ${onTime}
                </span>

            </div>


            <div class="performance-row">

                <span class="performance-label">
                    Delayed
                </span>

                <span class="performance-value">
                    ${delayed}
                </span>

            </div>


            <div class="performance-row">

                <span class="performance-label">
                    Severe delay
                </span>

                <span class="performance-value">
                    ${severe}
                </span>

            </div>


            <div class="performance-row">

                <span class="performance-label">
                    Early
                </span>

                <span class="performance-value">
                    ${early}
                </span>

            </div>

        </div>
    `;
}


// --------------------------------------------------
// LOCATION SELECTION
// --------------------------------------------------

map.on(
    "click",
    event => {

        setSelectedLocation(
            event.latlng.lat,
            event.latlng.lng,
            "Selected on map"
        );
    }
);


locationButton.addEventListener(
    "click",
    () => {

        if (!navigator.geolocation) {

            selectedLocationInfo.innerHTML = `
                <p>
                    Location services are not supported by this browser.
                </p>
            `;

            return;
        }


        locationButton.disabled =
            true;


        locationButton.textContent =
            "Finding Location...";


        navigator.geolocation.getCurrentPosition(

            position => {

                setSelectedLocation(
                    position.coords.latitude,
                    position.coords.longitude,
                    "Current location"
                );


                map.setView(
                    [
                        position.coords.latitude,
                        position.coords.longitude
                    ],
                    15
                );


                resetLocationButton();
            },


            error => {

                console.error(
                    "Geolocation error:",
                    error
                );


                selectedLocationInfo.innerHTML = `
                    <p>
                        Unable to access your location.
                    </p>
                `;


                resetLocationButton();
            }
        );
    }
);


function setSelectedLocation(
    latitude,
    longitude,
    source
) {

    const lat =
        Number(latitude);

    const lon =
        Number(longitude);


    if (
        !Number.isFinite(lat) ||
        !Number.isFinite(lon)
    ) {

        return;
    }


    if (selectedLocationMarker) {

        map.removeLayer(
            selectedLocationMarker
        );
    }


    selectedLocationMarker =
        L.marker(
            [lat, lon],
            {
                title: "Selected Location"
            }
        )
            .addTo(map)
            .bindPopup(`
                <strong>Selected Location</strong>
                <br>
                ${escapeHtml(source)}
                <br>
                ${lat.toFixed(5)},
                ${lon.toFixed(5)}
            `)
            .openPopup();


    selectedLocationInfo.classList.remove(
        "empty-card"
    );


    selectedLocationInfo.innerHTML = `
        <span class="location-label">
            ${escapeHtml(source)}
        </span>

        <div class="coordinate-row">

            <span class="coordinate-label">
                Latitude
            </span>

            <span class="coordinate-value">
                ${lat.toFixed(5)}
            </span>

        </div>

        <div class="coordinate-row">

            <span class="coordinate-label">
                Longitude
            </span>

            <span class="coordinate-value">
                ${lon.toFixed(5)}
            </span>

        </div>
    `;
}


function resetLocationButton() {

    locationButton.disabled =
        false;


    locationButton.textContent =
        "Use My Location";
}


// --------------------------------------------------
// MAP HELPERS
// --------------------------------------------------

function fitMapToStops() {

    if (stopData.length === 0) {

        return;
    }


    const bounds =
        L.latLngBounds(
            stopData.map(
                stop => [
                    stop.stop_lat,
                    stop.stop_lon
                ]
            )
        );


    if (bounds.isValid()) {

        map.fitBounds(
            bounds,
            {
                padding: [30, 30],
                maxZoom: 15
            }
        );
    }
}


function resetStopMarkerEmphasis() {

    Object.values(
        stopMarkers
    ).forEach(marker => {

        marker.setStyle({
            radius: 6,
            weight: 2,
            fillOpacity: 0.8
        });
    });
}


function showMapMessage(message) {

    mapMessage.textContent =
        message;


    mapMessage.classList.remove(
        "hidden"
    );
}


// --------------------------------------------------
// VALIDATION
// --------------------------------------------------

function hasValidCoordinates(stop) {

    const lat =
        Number(stop.stop_lat);

    const lon =
        Number(stop.stop_lon);


    const valid =
        Number.isFinite(lat) &&
        Number.isFinite(lon) &&
        lat >= -90 &&
        lat <= 90 &&
        lon >= -180 &&
        lon <= 180;


    if (!valid) {

        console.warn(
            "Skipping stop with invalid coordinates:",
            stop
        );
    }


    return valid;
}


// --------------------------------------------------
// FORMATTERS
// --------------------------------------------------

function formatNumber(value) {

    const number =
        Number(value);


    if (!Number.isFinite(number)) {

        return "Unavailable";
    }


    return number.toFixed(1);
}


function formatPercentage(value) {

    const number =
        Number(value);


    if (!Number.isFinite(number)) {

        return "Unavailable";
    }


    return `${number.toFixed(1)}%`;
}


function escapeHtml(value) {

    return String(
        value ?? ""
    ).replace(
        /[&<>"']/g,
        character => {

            const replacements = {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                "\"": "&quot;",
                "'": "&#039;"
            };


            return replacements[
                character
            ];
        }
    );
}