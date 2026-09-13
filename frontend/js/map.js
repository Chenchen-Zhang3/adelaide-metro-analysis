// Stores valid GTFS stop data after it is loaded
let stopData = [];

// Stores Leaflet stop markers by stop ID
const stopMarkers = {};

// Stores the currently selected Location A marker
let selectedLocationMarker = null;

// Stores coordinates of the currently selected Location A
let selectedLocation = null;


// Adelaide city centre coordinates
const ADELAIDE_LAT = -34.9285;
const ADELAIDE_LON = 138.6007;


// Create the map
const map = L.map("map").setView(
    [ADELAIDE_LAT, ADELAIDE_LON],
    14
);


// Add OpenStreetMap
L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);


// --------------------------------------------------
// INTERFACE ELEMENTS
// --------------------------------------------------

const locationButton =
    document.getElementById("locationButton");

const selectedLocationInfo =
    document.getElementById("selectedLocationInfo");

const nearestStopContainer =
    document.getElementById("nearestStop");

const nearbyStopsContainer =
    document.getElementById("nearbyStops");

const selectedStopInfo =
    document.getElementById("selectedStopInfo");

const stopCount =
    document.getElementById("stopCount");


// --------------------------------------------------
// COORDINATE VALIDATION
// --------------------------------------------------

function hasValidCoordinates(stop) {

    const latitude =
        Number(stop.stop_lat);

    const longitude =
        Number(stop.stop_lon);


    return (
        Number.isFinite(latitude) &&
        latitude >= -90 &&
        latitude <= 90 &&
        Number.isFinite(longitude) &&
        longitude >= -180 &&
        longitude <= 180
    );
}


// --------------------------------------------------
// LOAD STOPS
// --------------------------------------------------

fetch("http://127.0.0.1:5000/api/stops")

    .then(response => {

        if (!response.ok) {
            throw new Error(
                "Could not load stop data from backend."
            );
        }

        return response.json();
    })


    .then(stops => {

        const validStops =
            stops.filter(stop => {

                const valid =
                    hasValidCoordinates(stop);


                if (!valid) {

                    console.warn(
                        "Skipping stop with invalid coordinates:",
                        stop
                    );
                }


                return valid;
            });


        stopData =
            validStops.map(stop => ({

                ...stop,

                stop_lat:
                    Number(stop.stop_lat),

                stop_lon:
                    Number(stop.stop_lon)

            }));


        stopData.forEach(stop => {

            const marker =
                L.marker([
                    stop.stop_lat,
                    stop.stop_lon
                ])
                    .addTo(map);


            stopMarkers[
                stop.stop_id
            ] = marker;


            marker.bindPopup(`
                <strong>${stop.stop_name}</strong><br>
                Stop ID: ${stop.stop_id}<br>
                Latitude: ${stop.stop_lat}<br>
                Longitude: ${stop.stop_lon}
            `);


            marker.on(
                "click",
                () => {

                    selectStop(stop);
                }
            );

        });


        stopCount.textContent =
            `${stopData.length} stops loaded`;


        if (stopData.length === 0) {

            stopCount.textContent =
                "No stops available";

            nearestStopContainer.innerHTML =
                "<p>No valid stop data is currently available.</p>";

            nearbyStopsContainer.innerHTML =
                "<p>No valid stop data is currently available.</p>";
        }

    })


    .catch(error => {

        console.error(
            "Error loading stops:",
            error
        );


        stopCount.textContent =
            "Stop data unavailable";

        nearestStopContainer.innerHTML =
            "<p>Unable to load stop data.</p>";

        nearbyStopsContainer.innerHTML =
            "<p>Unable to load stop data.</p>";
    });


// --------------------------------------------------
// DISTANCE
// --------------------------------------------------

function calculateDistance(
    lat1,
    lon1,
    lat2,
    lon2
) {

    const earthRadius = 6371;

    const latitude1 = Number(lat1);
    const longitude1 = Number(lon1);
    const latitude2 = Number(lat2);
    const longitude2 = Number(lon2);


    if (
        !Number.isFinite(latitude1) ||
        !Number.isFinite(longitude1) ||
        !Number.isFinite(latitude2) ||
        !Number.isFinite(longitude2)
    ) {

        return null;
    }


    const latDifference =
        (latitude2 - latitude1) *
        Math.PI / 180;


    const lonDifference =
        (longitude2 - longitude1) *
        Math.PI / 180;


    const a =
        Math.sin(latDifference / 2) ** 2 +

        Math.cos(
            latitude1 * Math.PI / 180
        ) *

        Math.cos(
            latitude2 * Math.PI / 180
        ) *

        Math.sin(lonDifference / 2) ** 2;


    const c =
        2 * Math.atan2(
            Math.sqrt(a),
            Math.sqrt(1 - a)
        );


    return earthRadius * c;
}


// --------------------------------------------------
// SELECT LOCATION
// --------------------------------------------------

function setSelectedLocation(
    latitude,
    longitude,
    sourceText
) {

    const lat = Number(latitude);
    const lon = Number(longitude);


    if (
        !Number.isFinite(lat) ||
        !Number.isFinite(lon)
    ) {

        selectedLocationInfo.innerHTML =
            "<p>Invalid location coordinates.</p>";

        return;
    }


    selectedLocation = {
        lat: lat,
        lon: lon
    };


    if (selectedLocationMarker) {

        map.removeLayer(
            selectedLocationMarker
        );
    }


    selectedLocationMarker =
        L.marker([
            lat,
            lon
        ])
            .addTo(map)
            .bindPopup(`
                <strong>Location A</strong><br>
                ${sourceText}<br>
                Latitude: ${lat.toFixed(5)}<br>
                Longitude: ${lon.toFixed(5)}
            `)
            .openPopup();


    selectedLocationInfo.classList.remove(
        "empty-card"
    );


    selectedLocationInfo.innerHTML = `
        <span class="location-label">
            ${sourceText}
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


    findNearbyStops(
        lat,
        lon
    );
}


// Click map
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


// --------------------------------------------------
// BROWSER LOCATION
// --------------------------------------------------

locationButton.addEventListener(
    "click",
    () => {

        if (!navigator.geolocation) {

            selectedLocationInfo.innerHTML =
                "<p>Location services are not supported by this browser.</p>";

            return;
        }


        locationButton.disabled = true;

        locationButton.textContent =
            "Finding Location...";


        navigator.geolocation.getCurrentPosition(

            position => {

                const userLat =
                    position.coords.latitude;

                const userLon =
                    position.coords.longitude;


                setSelectedLocation(
                    userLat,
                    userLon,
                    "Your current location"
                );


                map.setView(
                    [
                        userLat,
                        userLon
                    ],
                    15
                );


                locationButton.disabled =
                    false;

                locationButton.textContent =
                    "Use My Location";
            },


            error => {

                console.error(
                    "Location error:",
                    error
                );


                selectedLocationInfo.innerHTML =
                    "<p>Unable to access your location.</p>";


                locationButton.disabled =
                    false;

                locationButton.textContent =
                    "Use My Location";
            }
        );
    }
);


// --------------------------------------------------
// NEAREST STOPS
// --------------------------------------------------

function findNearbyStops(
    userLat,
    userLon
) {

    if (stopData.length === 0) {

        nearestStopContainer.innerHTML =
            "<p>Stop data is still loading. Please try again.</p>";

        nearbyStopsContainer.innerHTML =
            "<p>Stop data is still loading. Please try again.</p>";

        return;
    }


    const stopsWithDistance =
        stopData

            .map(stop => {

                const distance =
                    calculateDistance(
                        userLat,
                        userLon,
                        stop.stop_lat,
                        stop.stop_lon
                    );


                if (distance === null) {
                    return null;
                }


                return {
                    ...stop,
                    distance: distance
                };
            })

            .filter(
                stop =>
                    stop !== null
            );


    stopsWithDistance.sort(
        (a, b) =>
            a.distance - b.distance
    );


    if (stopsWithDistance.length === 0) {

        nearestStopContainer.innerHTML =
            "<p>No nearby stop could be calculated.</p>";

        nearbyStopsContainer.innerHTML =
            "<p>No nearby stops could be calculated.</p>";

        return;
    }


    const nearestStop =
        stopsWithDistance[0];


    nearestStopContainer.classList.remove(
        "empty-card"
    );


    nearestStopContainer.innerHTML = `
        <strong class="nearest-stop-name">
            ${nearestStop.stop_name}
        </strong>

        <div class="nearest-stop-id">
            Stop ID: ${nearestStop.stop_id}
        </div>

        <span class="nearest-distance">
            ${formatDistance(nearestStop.distance)}
        </span>
    `;


    nearestStopContainer.style.cursor =
        "pointer";


    nearestStopContainer.onclick =
        () => {

            focusStop(
                nearestStop
            );
        };


    const otherNearbyStops =
        stopsWithDistance.slice(1, 3);


    nearbyStopsContainer.innerHTML = "";


    if (otherNearbyStops.length === 0) {

        nearbyStopsContainer.innerHTML =
            "<p>No additional nearby stops available.</p>";

        return;
    }


    otherNearbyStops.forEach(stop => {

        const stopElement =
            document.createElement(
                "div"
            );


        stopElement.classList.add(
            "nearby-stop"
        );


        stopElement.innerHTML = `
            <strong>
                ${stop.stop_name}
            </strong>

            <span>
                ${formatDistance(stop.distance)}
            </span>
        `;


        stopElement.addEventListener(
            "click",
            () => {

                focusStop(stop);
            }
        );


        nearbyStopsContainer.appendChild(
            stopElement
        );
    });
}


// --------------------------------------------------
// SELECT STOP
// --------------------------------------------------

async function selectStop(stop) {

    selectedStopInfo.classList.remove(
        "empty-card"
    );


    selectedStopInfo.innerHTML = `
        <strong class="selected-stop-name">
            ${stop.stop_name}
        </strong>

        <div class="selected-stop-id">
            Stop ID: ${stop.stop_id}
        </div>

        <p class="detail-message">
            Loading transport information...
        </p>
    `;


    try {

        const routeRequest =
            fetch(
                `http://127.0.0.1:5000/api/stops/${encodeURIComponent(stop.stop_id)}/routes`
            );


        const performanceRequest =
            fetch(
                `http://127.0.0.1:5000/api/stops/${encodeURIComponent(stop.stop_id)}/performance`
            );


        const [
            routeResponse,
            performanceResponse
        ] = await Promise.all([
            routeRequest,
            performanceRequest
        ]);


        if (!routeResponse.ok) {

            throw new Error(
                "Could not load route information."
            );
        }


        if (!performanceResponse.ok) {

            throw new Error(
                "Could not load performance information."
            );
        }


        const routes =
            await routeResponse.json();


        const performance =
            await performanceResponse.json();


        displayStopInformation(
            stop,
            routes,
            performance
        );

    }

    catch (error) {

        console.error(
            "Error loading selected stop information:",
            error
        );


        selectedStopInfo.innerHTML = `
            <strong class="selected-stop-name">
                ${stop.stop_name}
            </strong>

            <div class="selected-stop-id">
                Stop ID: ${stop.stop_id}
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

    let routeContent = "";


    if (
        !Array.isArray(routes) ||
        routes.length === 0
    ) {

        routeContent = `
            <p class="detail-message">
                No route information available for this stop.
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
                "Route name unavailable";


            routeContent += `
                <div class="route-item">

                    <span class="route-short-name">
                        ${shortName}
                    </span>

                    <div class="route-long-name">
                        ${longName}
                    </div>

                </div>
            `;
        });
    }


    let performanceContent = "";


    if (
        !Array.isArray(performance) ||
        performance.length === 0
    ) {

        performanceContent = `
            <p class="detail-message">
                No performance data available for this stop.
            </p>
        `;
    }

    else {

        performance.forEach(record => {

            performanceContent += `
                <div class="performance-item">

                    <div class="performance-row">

                        <span class="performance-label">
                            Route
                        </span>

                        <span class="performance-value">
                            ${record.route_id || "Unavailable"}
                        </span>

                    </div>


                    <div class="performance-row">

                        <span class="performance-label">
                            Trip
                        </span>

                        <span class="performance-value">
                            ${record.trip_id || "Unavailable"}
                        </span>

                    </div>


                    <div class="performance-row">

                        <span class="performance-label">
                            Scheduled
                        </span>

                        <span class="performance-value">
                            ${formatArrivalTime(record.scheduled_arrival)}
                        </span>

                    </div>


                    <div class="performance-row">

                        <span class="performance-label">
                            Actual
                        </span>

                        <span class="performance-value">
                            ${formatArrivalTime(record.actual_arrival)}
                        </span>

                    </div>


                    <span class="delay-status">
                        ${formatDelay(record.delay_seconds)}
                    </span>

                </div>
            `;
        });
    }


    selectedStopInfo.innerHTML = `
        <strong class="selected-stop-name">
            ${stop.stop_name}
        </strong>

        <div class="selected-stop-id">
            Stop ID: ${stop.stop_id}
        </div>


        <div class="detail-heading">
            Routes serving this stop
        </div>

        ${routeContent}


        <div class="detail-heading">
            Performance
        </div>

        ${performanceContent}
    `;
}


// --------------------------------------------------
// FORMAT ARRIVAL TIME
// --------------------------------------------------

function formatArrivalTime(timestamp) {

    if (!timestamp) {
        return "Unavailable";
    }


    const date =
        new Date(timestamp);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return timestamp;
    }


    return date.toLocaleTimeString(
        [],
        {
            hour: "2-digit",
            minute: "2-digit"
        }
    );
}


// --------------------------------------------------
// FORMAT DELAY
// --------------------------------------------------

function formatDelay(delaySeconds) {

    const seconds =
        Number(delaySeconds);


    if (!Number.isFinite(seconds)) {

        return "Delay unavailable";
    }


    if (seconds === 0) {

        return "On time";
    }


    if (seconds > 0) {

        if (seconds < 60) {

            return `${seconds} sec late`;
        }


        const minutes =
            Math.round(
                seconds / 60
            );


        return `${minutes} min late`;
    }


    const earlySeconds =
        Math.abs(seconds);


    if (earlySeconds < 60) {

        return `${earlySeconds} sec early`;
    }


    const earlyMinutes =
        Math.round(
            earlySeconds / 60
        );


    return `${earlyMinutes} min early`;
}


// --------------------------------------------------
// FOCUS STOP
// --------------------------------------------------

function focusStop(stop) {

    map.setView(
        [
            stop.stop_lat,
            stop.stop_lon
        ],
        17
    );


    const marker =
        stopMarkers[
            stop.stop_id
        ];


    if (marker) {

        marker.openPopup();
    }


    selectStop(stop);
}


// --------------------------------------------------
// FORMAT DISTANCE
// --------------------------------------------------

function formatDistance(
    distanceKm
) {

    if (
        distanceKm === null ||
        !Number.isFinite(distanceKm)
    ) {

        return "Distance unavailable";
    }


    if (distanceKm < 1) {

        return `${
            Math.round(
                distanceKm * 1000
            )
        } m away`;
    }


    return `${
        distanceKm.toFixed(2)
    } km away`;
}