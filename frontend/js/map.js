// Stores the GTFS stop data after it is loaded
let stopData = [];

// Stores map markers so they can be accessed from the sidebar
const stopMarkers = {};

// Adelaide city centre coordinates
const ADELAIDE_LAT = -34.9285;
const ADELAIDE_LON = 138.6007;

// Create the map and centre it on Adelaide
const map = L.map("map").setView(
    [ADELAIDE_LAT, ADELAIDE_LON],
    14
);

// Add the OpenStreetMap base layer
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);


// Load sample GTFS stop data provided by the shared test fixtures
fetch("../tests/fixtures/sample_stops.json")
    .then(response => {
        if (!response.ok) {
            throw new Error("Could not load stop data.");
        }

        return response.json();
    })
    .then(stops => {

        stopData = stops;

        stops.forEach(stop => {

            const marker = L.marker([
                stop.stop_lat,
                stop.stop_lon
            ]).addTo(map);

            // Store marker using stop ID so the sidebar can open it later
            stopMarkers[stop.stop_id] = marker;

            marker.bindPopup(`
                <strong>${stop.stop_name}</strong><br>
                Stop ID: ${stop.stop_id}<br>
                Latitude: ${stop.stop_lat}<br>
                Longitude: ${stop.stop_lon}
            `);
        });
    })
    .catch(error => {
        console.error("Error loading bus stops:", error);
    });


// Calculate distance between two coordinates using the Haversine formula
function calculateDistance(lat1, lon1, lat2, lon2) {
    const earthRadius = 6371;

    const latDifference = (lat2 - lat1) * Math.PI / 180;
    const lonDifference = (lon2 - lon1) * Math.PI / 180;

    const a =
        Math.sin(latDifference / 2) * Math.sin(latDifference / 2) +
        Math.cos(lat1 * Math.PI / 180) *
        Math.cos(lat2 * Math.PI / 180) *
        Math.sin(lonDifference / 2) *
        Math.sin(lonDifference / 2);

    const c = 2 * Math.atan2(
        Math.sqrt(a),
        Math.sqrt(1 - a)
    );

    return earthRadius * c;
}


// Get references to interface elements
const locationButton = document.getElementById("locationButton");
const nearbyStopsContainer = document.getElementById("nearbyStops");


// Use the browser's current location
locationButton.addEventListener("click", () => {

    if (!navigator.geolocation) {
        nearbyStopsContainer.innerHTML =
            "<p>Location services are not supported by this browser.</p>";

        return;
    }

    nearbyStopsContainer.innerHTML =
        "<p>Finding your location...</p>";

    navigator.geolocation.getCurrentPosition(

        position => {
            const userLat = position.coords.latitude;
            const userLon = position.coords.longitude;

            showUserLocation(userLat, userLon);
        },

        error => {
            nearbyStopsContainer.innerHTML =
                "<p>Unable to access your location.</p>";

            console.error("Location error:", error);
        }
    );
});


// Display Location A and find nearby stops
function showUserLocation(userLat, userLon) {

    const userMarker = L.marker([
        userLat,
        userLon
    ])
        .addTo(map)
        .bindPopup(`
            <strong>Location A</strong><br>
            Your current location
        `)
        .openPopup();

    // Move the map to the user's current location
    map.setView(
        [userLat, userLon],
        15
    );

    findNearbyStops(
        userLat,
        userLon
    );
}


// Find and display the closest stops
function findNearbyStops(userLat, userLon) {

    if (stopData.length === 0) {
        nearbyStopsContainer.innerHTML =
            "<p>Stop data is still loading. Please try again.</p>";

        return;
    }

    const stopsWithDistance = stopData.map(stop => {

        const distance = calculateDistance(
            userLat,
            userLon,
            stop.stop_lat,
            stop.stop_lon
        );

        return {
            ...stop,
            distance: distance
        };
    });

    // Sort stops from nearest to furthest
    stopsWithDistance.sort(
        (a, b) => a.distance - b.distance
    );

    // Display the three nearest stops
    const nearestStops = stopsWithDistance.slice(0, 3);

    nearbyStopsContainer.innerHTML = "";

    nearestStops.forEach(stop => {

        const stopElement = document.createElement("div");

        stopElement.innerHTML = `
            <strong>${stop.stop_name}</strong>
            <span>${formatDistance(stop.distance)}</span>
        `;

        stopElement.classList.add("nearby-stop");


        // Clicking a nearby stop moves the map to that stop
        stopElement.addEventListener("click", () => {

            map.setView(
                [stop.stop_lat, stop.stop_lon],
                17
            );

            const marker = stopMarkers[stop.stop_id];

            if (marker) {
                marker.openPopup();
            }
        });


        nearbyStopsContainer.appendChild(stopElement);
    });
}


// Display distance as metres or kilometres
function formatDistance(distanceKm) {

    if (distanceKm < 1) {
        return `${Math.round(distanceKm * 1000)} m away`;
    }

    return `${distanceKm.toFixed(2)} km away`;
}