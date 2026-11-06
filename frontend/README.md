# Adelaide Metro frontend

This is editable HTML, CSS and JavaScript; no exporter or build step is required.

## Run locally

From the repository root, start the backend in one terminal (see `../docs/client-handover.md`), then start the frontend in another:

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory frontend
```

Open http://127.0.0.1:8000. The frontend currently uses the Flask API at http://127.0.0.1:5001; change `API_BASE_URL` in `js/map.js` for a different environment.

The historical prediction overlay is in `js/network-delays.js`. It reports predictions, **not measured actual arrivals**.
