/* Network-wide prediction delay visualisation.
 * Uses one bulk API request per time window; does not change route/playback logic.
 */
(() => {
    "use strict";
    const COLORS = { early: "#2563eb", low: "#16a34a", medium: "#eab308", high: "#dc2626", insufficient: "#94a3b8", missing: "#cbd5e1" };
    const state = { active: false, stops: [], results: new Map(), coverage: null, layer: null, controller: null, request: 0, loaded: false };
    const $ = id => document.getElementById(id);
    const safe = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
    const finite = value => value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
    const format = (value, suffix = "") => finite(value) ? `${Number(value).toFixed(2)}${suffix}` : "N/A";
    const status = message => { $("networkDelayStatus").textContent = message; };
    const range = { start: "2026-10-17T09:00", end: "2026-10-17T09:15" };

    // Interpret wall-clock time in Australia/Adelaide, including daylight saving.
    // Reject nonexistent/ambiguous local times rather than silently choosing an instant.
    function adelaideInstant(value) {
        const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value || "");
        if (!match) throw new Error("Enter both Adelaide dates and times.");
        const [year, month, day, hour, minute] = match.slice(1).map(Number);
        const wall = Date.UTC(year, month - 1, day, hour, minute);
        const canonical = `${match[1]}-${match[2]}-${match[3]} ${match[4]}:${match[5]}`;
        const formatter = new Intl.DateTimeFormat("en-CA", { timeZone: "Australia/Adelaide", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
        const matches = [];
        for (const offsetMinutes of [570, 630]) {
            const candidate = new Date(wall - offsetMinutes * 60000);
            const parts = Object.fromEntries(formatter.formatToParts(candidate).filter(p => p.type !== "literal").map(p => [p.type, p.value]));
            const actual = `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`;
            if (actual === canonical) matches.push(candidate);
        }
        if (matches.length !== 1) throw new Error("This Adelaide time is invalid or ambiguous due to daylight saving. Choose another time.");
        return matches[0];
    }

    function category(entry) {
        if (!entry) return "missing";
        if (entry.data_status !== "available" || !finite(entry.average_predicted_delay_minutes)) return "insufficient";
        const delay = Number(entry.average_predicted_delay_minutes);
        if (delay < 0) return "early";
        if (delay <= 5) return "low";
        if (delay <= 10) return "medium";
        return "high";
    }
    // These labels classify the mean of historical predictions, not actual arrivals.
    function predictionLabel(entry) {
        const kind = category(entry);
        return {
            early: "Early", low: "On Time", medium: "Delayed",
            high: "Severely Delayed", insufficient: "Insufficient data",
            missing: "No data"
        }[kind];
    }
    function signedMinutes(value) {
        if (!finite(value)) return "N/A";
        const minutes = Number(value);
        return `${minutes > 0 ? "+" : ""}${minutes.toFixed(2)} min`;
    }
    function popup(stop, entry) {
        const availability = entry ? (entry.data_status === "available" ? "Available" : "Insufficient data") : "No data";
        const count = entry && Number.isFinite(Number(entry.prediction_sample_count)) ? String(entry.prediction_sample_count) : "0";
        return `<strong>${safe(stop.stop_name || "Stop")}</strong><br>Stop ID: ${safe(stop.stop_id)}<br>Data: ${availability}` +
            `<br>Average prediction category: <strong>${predictionLabel(entry)}</strong>` +
            `<br>Average predicted delay: ${entry?.data_status === "available" ? signedMinutes(entry.average_predicted_delay_minutes) : "N/A"}` +
            `<br>Predicted on-time: ${entry?.data_status === "available" ? format(entry.predicted_on_time_percentage, "%") : "N/A"}` +
            `<br>Prediction visit samples: ${safe(count)}` +
            `<br>First selected observation: ${safe(entry?.first_selected_observation_time || "N/A")}` +
            `<br>Last selected observation: ${safe(entry?.last_selected_observation_time || "N/A")}` +
            `<br><small>Historical GTFS-Realtime predictions, not actual arrivals or live status.</small>`;
    }
    // Keep map.js in charge of its own overlays; only change visibility here.
    // A layer added asynchronously while delay mode is active is hidden too.
    const hiddenOverlays = new Set();
    function otherOverlays() {
        return [
            // Keep the selected route path visible beneath delay markers in route mode.
            !(state.active && $("networkDelayRouteOnly")?.checked && routeSelect.value)
                && typeof routeGeometryLayer !== "undefined" ? routeGeometryLayer : null,
            typeof routeStopLayer !== "undefined" ? routeStopLayer : null,
            typeof hotspotLayer !== "undefined" ? hotspotLayer : null,
            typeof vehicleLayer !== "undefined" ? vehicleLayer : null
        ].filter(Boolean);
    }
    function syncOtherOverlays() {
        if (state.active) {
            for (const layer of otherOverlays()) {
                if (map.hasLayer(layer)) {
                    hiddenOverlays.add(layer);
                    map.removeLayer(layer);
                }
            }
        } else {
            // Only restore layers that are still current in map.js. Never
            // resurrect a stale route after the user changes the selection.
            const current = new Set(otherOverlays());
            for (const layer of hiddenOverlays) {
                if (current.has(layer) && !map.hasLayer(layer)) layer.addTo(map);
            }
            hiddenOverlays.clear();
        }
    }
    map.on("layeradd", event => {
        if (!state.active) return;
        if (otherOverlays().includes(event.layer)) {
            hiddenOverlays.add(event.layer);
            map.removeLayer(event.layer);
        }
    });

    function setMode(active) {
        if (!active) {
            state.request++;
            state.controller?.abort();
        }
        state.active = active;
        if (state.layer) {
            if (active && state.loaded) state.layer.addTo(map);
            else map.removeLayer(state.layer);
        }
        // Hide the generic blue stops only while displaying prediction data.
        for (const marker of stopMarkers.values()) {
            if (active) map.removeLayer(marker);
            else if (!map.hasLayer(marker)) marker.addTo(map);
        }
        // Delay mode is a separate analytical view. Temporarily hide route,
        // hotspot and playback overlays so they cannot obscure the delay markers.
        syncOtherOverlays();
        if (active && $("networkDelayRouteOnly")?.checked && routeSelect.value &&
            typeof routeGeometryLayer !== "undefined" && routeGeometryLayer) {
            hiddenOverlays.delete(routeGeometryLayer);
            if (!map.hasLayer(routeGeometryLayer)) routeGeometryLayer.addTo(map);
            routeGeometryLayer.setStyle({ color: "#475569", weight: 4, opacity: 0.75 });
            if (state.layer) state.layer.bringToFront?.();
        }
        $("networkDelayControls").hidden = !active;
        if (active && state.loaded) draw();
        if (active && !state.loaded) status("Select a time window and load prediction delays.");
    }
    function draw() {
        if (state.layer) map.removeLayer(state.layer);
        const markers = [];
        const counts = { early: 0, low: 0, medium: 0, high: 0, insufficient: 0, missing: 0 };
        const filter = $("networkDelayFilter").value;
        const routeOnly = $("networkDelayRouteOnly").checked && routeSelect.value;
        // /api/stops includes parent stations; static delay analysis covers only
        // platform stops referenced by the published timetable.
        for (const stop of state.stops) {
            if (Number(stop.location_type || 0) !== 0) continue;
            // Published /api/stops contains referenced platform stops plus parents only.
            if (routeOnly && !Array.isArray(stop.route_ids)) continue;
            if (routeOnly && !stop.route_ids.map(String).includes(String(routeSelect.value))) continue;
            const entry = state.results.get(String(stop.stop_id));
            const kind = category(entry);
            counts[kind]++;
            if (filter === "available" && !["early", "low", "medium", "high"].includes(kind)) continue;
            if (filter !== "all" && filter !== "available" && filter !== kind) continue;
            const marker = L.circleMarker([Number(stop.stop_lat), Number(stop.stop_lon)], {
                radius: kind === "insufficient" || kind === "missing" ? 2.5 : 8,
                color: kind === "insufficient" || kind === "missing" ? COLORS[kind] : "#ffffff",
                fillColor: COLORS[kind], weight: kind === "insufficient" || kind === "missing" ? 0 : 2,
                fillOpacity: kind === "missing" ? 0.25 : kind === "insufficient" ? 0.3 : 0.95
            });
            marker.bindTooltip(safe(stop.stop_name || "Stop"));
            marker.bindPopup(popup(stop, entry));
            marker.on("click", event => { L.DomEvent.stopPropagation(event); selectStop(stop); });
            markers.push(marker);
        }
        state.layer = L.layerGroup(markers);
        if (state.active) state.layer.addTo(map);
        if (state.active && routeOnly && typeof routeGeometryLayer !== "undefined" && routeGeometryLayer) {
            hiddenOverlays.delete(routeGeometryLayer);
            if (!map.hasLayer(routeGeometryLayer)) routeGeometryLayer.addTo(map);
            routeGeometryLayer.setStyle({ color: "#475569", weight: 4, opacity: 0.75 });
            state.layer.bringToFront?.();
        }
        const eligible = state.coverage?.eligible_stop_count;
        const label = !routeOnly && Number.isInteger(eligible) ? `${eligible} eligible network stops · ` : "";
        $("networkDelaySummary").textContent = `${label}${counts.early + counts.low + counts.medium + counts.high} available · ${counts.insufficient} insufficient · ${counts.missing} no data · ${markers.length} displayed${routeOnly ? ` · route ${routeSelect.value}` : ""}`;
        $("networkDelayViewNote").textContent = filter === "available"
            ? "Showing only stops with calculated averages. Choose another filter to inspect data coverage."
            : filter === "all"
                ? "All eligible stops shown as small dots for missing/insufficient data; zoom in to inspect individual stops."
                : "Showing the selected delay or coverage category.";
    }
    function resetOnFailure(message) {
        // Invalidate any in-flight response before clearing the displayed result.
        state.request++;
        state.controller?.abort();
        state.loaded = false;
        state.results.clear();
        state.coverage = null;
        if (state.layer) { map.removeLayer(state.layer); state.layer = null; }
        if (!state.active) for (const marker of stopMarkers.values()) if (!map.hasLayer(marker)) marker.addTo(map);
        $("networkDelaySummary").textContent = "No delay data loaded";
        status(message);
    }
    async function load() {
        if (!state.active) return;
        if ($("networkDelayRouteOnly").checked && !routeSelect.value) {
            status("Choose a route above, or change Analysis scope to Whole network.");
            return;
        }
        const request = ++state.request;
        state.controller?.abort();
        state.controller = new AbortController();
        state.loaded = false;
        if (state.layer) map.removeLayer(state.layer);
        if (!state.active) return;
        for (const marker of stopMarkers.values()) map.removeLayer(marker);
        status("Loading prediction delays…");
        try {
            const start = adelaideInstant($("networkDelayStart").value);
            const end = adelaideInstant($("networkDelayEnd").value);
            const duration = end - start;
            if (duration <= 0 || duration > 3600000) throw new Error("Select a time window greater than 0 and at most 60 minutes.");
            const params = new URLSearchParams({ start_time: start.toISOString(), end_time: end.toISOString(), scope: "static", min_samples: $("networkDelayMinSamples").value });
            if ($("networkDelayRouteOnly").checked && routeSelect.value) params.set("route_id", routeSelect.value);
            const response = await fetch(`${API_BASE_URL}/api/analysis/stop-delays?${params}`, { signal: state.controller.signal });
            if (request !== state.request) return;
            if (!response.ok) {
                let detail = "";
                try { const body = await response.json(); detail = body.error || body.code || ""; } catch (_) { /* non-JSON error */ }
                throw new Error(`Delay API returned ${response.status}${detail ? `: ${String(detail)}` : ""}.`);
            }
            const data = await response.json();
            if (request !== state.request || !state.active) return;
            if (!Array.isArray(data.stops)) throw new Error("Invalid stop-delays response: stops array missing.");
            if (data.static_catalog?.version !== "1710") throw new Error("Unexpected static GTFS catalogue version; expected 1710.");
            state.coverage = { ...data.coverage, eligible_stop_count: data.static_catalog.eligible_stop_count };
            state.results = new Map(data.stops.map(item => [String(item.stop_id), item]));
            state.loaded = true;
            draw();
            status(`Loaded ${data.stops.length} stop records. Window: ${start.toISOString()} – ${end.toISOString()} · min ${params.get("min_samples")} samples · historical predictions.`);
        } catch (error) {
            if (request !== state.request || error.name === "AbortError") return;
            console.error("Network delay map:", error);
            resetOnFailure(error.message);
        }
    }
    function setup() {
        const section = document.createElement("section");
        section.className = "sidebar-section";
        section.innerHTML = `<div class="section-heading"><span class="section-number">7</span><div><h3>Network-Wide Prediction Delays</h3><p>Explore historical predicted delays across Adelaide Metro stops.</p></div></div>
          <label class="network-delay-toggle"><input id="networkDelayToggle" type="checkbox"> Enable network delay map</label>
          <div id="networkDelayControls" class="info-card network-delay-card" hidden>
          <label for="networkDelayStart">Start (Adelaide time)</label><input id="networkDelayStart" type="datetime-local" value="${range.start}">
          <label for="networkDelayEnd">End (Adelaide time; max 1 hour)</label><input id="networkDelayEnd" type="datetime-local" value="${range.end}">
          <label for="networkDelayMinSamples">Minimum prediction samples</label><select id="networkDelayMinSamples"><option value="1">1 (exploratory)</option><option value="5">5</option><option value="10" selected>10 (default)</option><option value="20">20</option></select>
          <label for="networkDelayScope">Analysis scope</label><select id="networkDelayScope"><option value="route" selected>Selected route + coloured stops</option><option value="network">Whole network (exploratory)</option></select>
          <label for="networkDelayRoutePicker">Route to analyse</label><select id="networkDelayRoutePicker"><option value="">Choose a route</option></select>
          <label class="network-delay-toggle" hidden><input id="networkDelayRouteOnly" type="checkbox" checked> Only selected route</label>
          <button id="networkDelayLoad" type="button">Load prediction delays</button>
          <label for="networkDelayFilter">Show markers</label><select id="networkDelayFilter"><option value="available" selected>Available delays (recommended)</option><option value="all">All eligible stops (coverage)</option><option value="early">Early average (&lt;0 min)</option><option value="low">0–5 min</option><option value="medium">&gt;5–10 min</option><option value="high">&gt;10 min</option><option value="insufficient">Insufficient data</option><option value="missing">No data</option></select>
          <div class="network-delay-legend"><strong>Average predicted delay (minutes)</strong>
          <span><i style="background:${COLORS.early}"></i> Early (&lt;0)</span><span><i style="background:${COLORS.low}"></i> On Time (0–5)</span><span><i style="background:${COLORS.medium}"></i> Delayed (&gt;5–10)</span><span><i style="background:${COLORS.high}"></i> Severely Delayed (&gt;10)</span><span><i style="background:${COLORS.insufficient}"></i> Insufficient</span><span><i style="background:${COLORS.missing}"></i> No data</span></div>
          <p id="networkDelaySummary">No delay data loaded</p><p id="networkDelayViewNote" class="network-delay-view-note">Only calculated delays are shown by default to avoid overcrowding.</p><p id="networkDelayStatus" role="status">Choose a window and load data.</p>
          <p class="hotspot-note">Categories describe average predicted delays, not individual service punctuality or validated reliability. Predictions are not actual arrivals. N/A does not mean zero delay. Requires the approved October v2 database and complete static GTFS publication.</p></div>`;
        document.querySelector(".sidebar").appendChild(section);
        const styles = document.createElement("style");
        styles.textContent = `.network-delay-card{display:flex;flex-direction:column;gap:10px}.network-delay-card[hidden]{display:none}.network-delay-card label{font-size:12px;font-weight:600}.network-delay-card input[type=datetime-local]{width:100%;padding:9px;border:1px solid #d0d5dd;border-radius:7px}.network-delay-card button{padding:11px;border:0;border-radius:8px;background:#1d2939;color:white;font-weight:600;cursor:pointer}.network-delay-toggle{display:flex;align-items:center;gap:8px;font-size:13px}.network-delay-legend{display:grid;gap:6px;font-size:12px}.network-delay-legend span{display:flex;align-items:center;gap:8px}.network-delay-legend i{width:12px;height:12px;border-radius:50%;display:inline-block;border:1px solid #64748b}#networkDelayStatus,#networkDelaySummary{font-size:12px;line-height:1.5;overflow-wrap:anywhere}`;
        document.head.appendChild(styles);
        const picker = $("networkDelayRoutePicker");
        function syncPicker() {
            const current = routeSelect.value || picker.value;
            picker.innerHTML = routeSelect.innerHTML;
            picker.value = [...picker.options].some(option => option.value === current) ? current : "";
        }
        syncPicker();
        // Routes load asynchronously; keep the two selectors in sync.
        new MutationObserver(syncPicker).observe(routeSelect, { childList: true });
        picker.addEventListener("change", () => {
            routeSelect.value = picker.value;
            routeSelect.dispatchEvent(new Event("change", { bubbles: true }));
        });
        $("networkDelayScope").addEventListener("change", () => {
            const routeOnly = $("networkDelayScope").value === "route";
            $("networkDelayRouteOnly").checked = routeOnly;
            picker.disabled = !routeOnly;
            if (state.active) {
                syncOtherOverlays();
                if (routeOnly && routeSelect.value && routeGeometryLayer) {
                    hiddenOverlays.delete(routeGeometryLayer);
                    routeGeometryLayer.addTo(map);
                    routeGeometryLayer.setStyle({ color: "#475569", weight: 4, opacity: 0.75 });
                }
                resetOnFailure("Scope changed. Load predictions to update the map.");
            }
        });
        $("networkDelayToggle").addEventListener("change", event => setMode(event.target.checked));
        $("networkDelayLoad").addEventListener("click", load);
        // A changed query must never leave the previous window's colours visible.
        for (const id of ["networkDelayStart", "networkDelayEnd", "networkDelayMinSamples"]) {
            $(id).addEventListener("change", () => {
                if (state.active) resetOnFailure("Analysis settings changed. Load prediction delays again.");
            });
        }
        $("networkDelayFilter").addEventListener("change", () => { if (state.loaded) draw(); });
        $("networkDelayRouteOnly").addEventListener("change", () => {
            if (state.loaded) resetOnFailure("Route filter changed. Reload predictions to apply it.");
        });
        routeSelect.addEventListener("change", () => {
            picker.value = routeSelect.value;
            if (state.active && $("networkDelayRouteOnly").checked) {
                resetOnFailure("Route changed. Load prediction delays for the selected route.");
            }
        });
        window.addEventListener("adelaide:stops-loaded", event => { state.stops = event.detail.stops; if (state.active && state.loaded) draw(); });
        if (typeof stopData !== "undefined" && stopData.length) state.stops = stopData;
    }
    setup();
})();
