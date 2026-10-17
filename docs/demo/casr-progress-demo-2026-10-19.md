# CASR progress demo — Monday 19 October 2026

SCRUM-235 / S4-C05. Preparation and individual local rehearsal: 16 October 2026,
Australia/Adelaide. This is a **progress demonstration, not final acceptance**.
Audience: Jamie Mackenzie / CASR. No full-team rehearsal or client meeting has
occurred as part of this task. Names, presenter roles and meeting time need group confirmation.

## 1. Readiness at a glance

Repository baseline: `main` / `origin/main` at `4bef170`, merge PR #53
(SCRUM-234). SCRUM-232 was previously merged in PR #52. The frontend was inspected
again; no new geometry, vehicle, playback or recorded-banner integration was present.
No production or teammate frontend source was changed by this task.

| Status | Can we demonstrate it? | Evidence / boundary |
| --- | --- | --- |
| WORKING | Flask startup on demo copy, routes/stops/performance APIs | Actual local HTTP requests, 16 October |
| WORKING | Existing Leaflet map, stop markers, G10/M44/506 route selection and statistics | Actual browser rehearsal, 16 October; 354 stops / 3 routes |
| WORKING | Recorded vehicle history by route/time, paginated | HTTP API + existing offline fallback; not rendered as vehicles in UI |
| WORKING | Official geometry and trip/stop relationships | Map-data API; 8 variants / 3,529 points; not drawn as route lines in UI |
| WORKING | Real September Trip Updates and derived delays | Repository + fallback samples; not a new raw-history HTTP endpoint |
| PARTIALLY WORKING | Complete integrated historical map experience | Existing map/statistics work, geometry/vehicle/time UI missing |
| PARTIALLY WORKING | Production reliability assurance | Local recovery tests exist; CASR scheduled restart, backup and sustained growth evidence pending |
| NOT IMPLEMENTED in current frontend | Official shape/variant rendering; historical vehicle markers and playback | Do not select controls that do not exist or promise animation |
| NOT IMPLEMENTED in current frontend | Recorded-data banner | State the label/date verbally and keep this guide visible during screen share |

**Say before any screen demo:** “Recorded Historical Data — September 2026.
These observations are from 26 September, 9 to 11 am Adelaide time, not live today.”
September offset is **+09:30**, not October daylight-saving +10:30. Version 1692
is appropriate for these September observations, not evidence of current October service.

## 2. Data and evidence to keep open

Demo source DB:
`D:\Adelaide study\2026\ICT Capstone Project\CASR historical data\analysis\demo_dataset\adelaide_metro_demo.db`

Map data:
`D:\Adelaide study\2026\ICT Capstone Project\CASR historical data\analysis\demo_map_data`

Do not point v2 repository queries at the legacy original 5.59 GiB DB. Do not
run a live collector, regenerate artifacts, or use the CASR Windows machine during
this meeting. Use a fresh disposable demo copy, preserving the source.

| Evidence | Open this existing project material | Safe spoken claim |
| --- | --- | --- |
| A — Collection pipeline | [Runner architecture](../architecture/historical-collection-runner.md); `scripts/collect_realtime_history.py`, `backend/realtime/collector.py`, `backend/services/pipeline.py` | Fetch/decode/validate/convert/delay/transaction are implemented; default 60-second wait follows each attempt |
| B — Original September data | [ID audit provenance](../integration/gtfs-id-consistency.md) | Original snapshot: 684,212 positions / 16,547,359 updates, about 72 hours; unchanged archive, not today's live service |
| C — Storage reduction | [Full C04 replay table](../architecture/historical-storage-optimisation.md#full-c04-replay) | **81.62% in controlled full-dataset replay**, 5.590 → 1.028 GiB; not independently confirmed multi-day CASR production growth |
| D — S3-C05 / SCRUM-189 reliability | [Recovery evidence](../architecture/historical-collection-reliability.md); `backend/tests/test_historical_reliability.py` | 31 local cases, process restart/crash, rollback/restore, injected API failures; 360 simulated cycles, not six hours of real unattended collection |
| E — Stored-history IDs | [Audit results](../integration/gtfs-id-consistency.md#results); [audit JSON](../integration/evidence/gtfs-id-consistency-1692.json) | 100% checked non-empty stored route/trip/stop IDs match pinned static references; not 100% raw-feed capture or proof every prediction is accurate |
| F — Demo dataset | [Dataset](../integration/recorded-demo-dataset.md); [manifest](../integration/evidence/recorded-demo.manifest.json) | 1,792 positions, 22,256 retained updates, 55 trips, 354 stops in fixed two-hour window |
| G — Backend integration | [SCRUM-234 validation](../integration/e2e-demo-validation.md); `backend/tests/test_e2e_integration.py` | SCRUM-234 baseline: 245 passed; this rehearsal: 14 focused tests passed, plus actual HTTP/fallback checks |
| H — Frontend progress | Browser + [prior team report](../testing/sprint4-recorded-data-integration-test-report.md) | Only visible, tested map/stops/statistics; no current route-line or playback claim |

The demo's 1,242 ledger rows are **import timestamp groups**, not original CASR
uptime. UI “Services analysed” / API `total_services` counts retained prediction
observations (G10 10,743; M44 7,319; 506 4,194), not unique trips/completed services.
Suppression means these are not uniformly sampled operational punctuality estimates.
`actual_arrival` is reconstructed predicted arrival, not independently measured arrival.

## 3. Startup — PowerShell

Use an environment containing Flask, flask-cors, GTFS/protobuf bindings, tzdata,
jsonschema (pytest for tests). The executable below was actually used locally;
teammates must replace **only `$demoPython`** with their already prepared Python
environment path. Do not rely on an unverified system `python` or install dependencies
during the meeting. No PowerPoint/new fallback app is required.

### Terminal A — verify fallback, copy DB, start backend

```powershell
Set-Location 'D:\Adelaide study\2026\ICT Capstone Project\git hub clone\adelaide-metro-analysis'
$demoPython = 'C:\Users\alan0\.codex\.chatgpt-projects\g-p-6a7804d5fc8c81918baf61aa478ca352\s4-db01-worktree\.venv\Scripts\python.exe'
$demoSource = 'D:\Adelaide study\2026\ICT Capstone Project\CASR historical data\analysis\demo_dataset\adelaide_metro_demo.db'
$mapData = 'D:\Adelaide study\2026\ICT Capstone Project\CASR historical data\analysis\demo_map_data'
if (-not (Test-Path -LiteralPath $demoPython)) { throw 'Configure demoPython first' }
if (-not (Test-Path -LiteralPath $demoSource)) { throw 'Demo DB missing' }
if (-not (Test-Path -LiteralPath $mapData)) { throw 'Map artifacts missing' }
& $demoPython -m backend.services.e2e_demo_check --database "$demoSource" --map-data "$mapData"
if ($LASTEXITCODE -ne 0) { throw 'Fallback verification failed; investigate before demo' }
$demoRun = Join-Path $env:TEMP ('adelaide-demo-235-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path "$demoRun" | Out-Null
Copy-Item -LiteralPath "$demoSource" -Destination (Join-Path $demoRun 'demo.db')
$env:ADELAIDE_METRO_DATABASE_PATH = Join-Path $demoRun 'demo.db'
$env:ADELAIDE_METRO_DEMO_MAP_DATA_PATH = $mapData
& $demoPython -m flask --app backend.api.app run --host 127.0.0.1 --port 5000 --no-reload
```

Set environment **before** Flask imports. Ensure 5000/8000 are free; if occupied,
inspect the owner instead of killing another person's server. Backend port 5000
is hardcoded in current frontend JS. Bind locally, not to the public network.

### Terminal B — existing frontend

```powershell
Set-Location 'D:\Adelaide study\2026\ICT Capstone Project\git hub clone\adelaide-metro-analysis'
$demoPython = 'C:\Users\alan0\.codex\.chatgpt-projects\g-p-6a7804d5fc8c81918baf61aa478ca352\s4-db01-worktree\.venv\Scripts\python.exe'
& $demoPython -m http.server 8000 --bind 127.0.0.1
```

Open [existing frontend](http://127.0.0.1:8000/frontend/). Say the recorded label
before screen sharing. Leaflet 1.9.4 JS/CSS comes from unpkg; OSM tiles need network/cache.
Do not assume cached resources will work on another laptop.

### Terminal C — short, readable API demonstration

These exact GET/hashtable patterns were tested against running Flask on 16 October.
The hashtable safely encodes the `+09:30` offset.

```powershell
$base = 'http://127.0.0.1:5000'
Invoke-RestMethod "$base/api/routes" | Format-Table route_id,route_short_name
(Invoke-RestMethod "$base/api/stops").Count
Invoke-RestMethod "$base/api/routes/G10/performance" | Format-List
$history = Invoke-RestMethod "$base/api/routes/G10/vehicle-positions" -Method Get -Body @{start_time='2026-09-26T09:00:00+09:30';end_time='2026-09-26T11:00:00+09:30';limit=3;offset=0}
$history.positions | Format-Table vehicle_id,trip_id,latitude,longitude,timestamp
$history.next_offset
$geometry = Invoke-RestMethod "$base/api/routes/G10/map-data"
$geometry.geometry.features | ForEach-Object { [pscustomobject]@{Shape=$_.properties.shape_id;Points=$_.geometry.coordinates.Count} }
Invoke-RestMethod "$base/api/stops/100618/routes" | Format-Table route_id
```

Expected: routes 506/G10/M44; 354 stops; G10 page size 3 / next_offset 3,
sample vehicle 1828 at 09:00:43; G10 3 shapes (1,232 points in total).
Map geometry is GeoJSON `[longitude,latitude]`. Do not concatenate variants into
one route or present shape availability as tested frontend route rendering.

## 4. Recommended team runbook — 8 to 10 minutes

| Time | Action | Suggested role (group must confirm actual person) |
| --- | --- | --- |
| 0:00–0:30 | State progress-demo scope and recorded date/window | Opening/timekeeper |
| 0:30–2:00 | Map, 354 stops, select G10 then M44/506; explain observation counts | Existing frontend presenter |
| 2:00–6:30 | Deliver the English backend script below; show two short API outputs and storage table | Backend/data presenter (your section) |
| 6:30–7:30 | Show any newly integrated geometry/playback **only if** tested before meeting; otherwise show geometry JSON/fallback, clearly not animation | Frontend presenter / backup operator |
| 7:30–9:00 | Limitations, CASR evidence request, client questions and next steps | Closing/Q&A coordinator |

No existing team assignments are asserted. Keep fallback pre-run and ready;
switch after ~20 seconds of a failed screen interaction instead of troubleshooting
through the meeting. If time is only five minutes, show G10 only, use three
minutes of the script and offer other examples in questions. Do not read Chinese
translations aloud during the English demo; they are study/rehearsal support.

## 5. Your speaking script — English + Chinese

Target **3–5 minutes**, English only, with short pauses and two brief screen cues.
The seven English paragraphs contain **411 whitespace-delimited words**: about
3.4 minutes at 120 words/minute, plus pauses/screens. This is a planning estimate,
not a timed human speaking rehearsal. This S4-C05 task is demo preparation;
the earlier S3-C05 reliability testing is separate evidence.

### 1 — Project and data overview

**English:** Hi Jamie. I will briefly explain our backend progress and the data behind the prototype. Today we are using recorded Adelaide Metro data from 26 September, from nine to eleven in the morning. We chose three routes: G10, M44 and 506. This is historical data, not a live feed. It gives us a fixed example that we can check and demonstrate again.

**中文：** Jamie 你好，我会简要介绍后端进展和原型使用的数据。今天展示的是 9 月 26 日上午 9 点到 11 点的 Adelaide Metro 历史记录，选用了 G10、M44 和 506。它不是当前实时数据，固定样本方便我们重复检查和演示。

### 2 — My backend contribution

**English:** My work focused on collecting realtime feeds, processing the records, and connecting them to the historical database. The backend decodes the feed, checks the required fields, and converts valid records into a consistent format. It also uses the static timetable to calculate predicted delays. This gives the API and analysis layer a shared source of data.

**中文：** 我的工作主要是实时 feed 采集、记录处理，以及与历史数据库的连接。后端负责解码、检查必要字段、统一有效记录的格式，并结合静态时刻表计算预测延迟，让 API 和分析层使用一致的数据来源。

### 3 — Historical collection

**English:** The collector normally waits sixty seconds after each collection attempt. If a temporary network error happens, it retries a limited number of times. Valid records are saved together in one SQLite transaction. If the write fails, that transaction is rolled back. We tested recovery after network failures and process restarts locally. We still need confirmation of automatic restart on the CASR computer.

**中文：** collector 默认在每轮尝试结束后等待 60 秒。临时网络错误会触发有限次数的重试。有效记录在同一个 SQLite transaction 中保存，写入失败会 rollback。网络故障和进程重启恢复已在本地测试，但 CASR 电脑的自动重启仍需确认。

### 4 — Storage optimisation

**English:** The earlier database grew quickly because many predictions were repeated without changing. We now keep changes and periodic checkpoints, use compact timestamps, and reconstruct the arrival time when it is queried. In a controlled replay of the full historical dataset, the file went from about 5.59 to 1.03 gibibytes. That was an 81.62 percent reduction. This is a benchmark result, not yet a confirmed long-running production result.

**中文：** 原数据库增长较快，一个主要原因是未变化的预测被反复保存。优化后保留变化和周期 checkpoint，使用紧凑时间戳，并在查询时还原到站时间。完整历史数据的受控 replay 中，文件从约 5.59 GiB 降到 1.03 GiB，减少 81.62%。这是 benchmark 结果，不是已确认的长期生产运行结果。

### 5 — Real data and integration

**English:** Our demo contains 1,792 vehicle positions and 22,256 retained prediction observations. We can query them by route and time, and return route statistics through the API. Here is a real vehicle record, and here are the official route shapes. The previous integration suite passed 245 tests. We also checked that the stored history IDs match the selected static references. That does not prove every prediction is accurate.

**中文：** 演示数据包含 1,792 条车辆位置和 22,256 条保留的预测观察记录。后端支持按线路和时间查询，并通过 API 返回线路统计。这里展示一条真实车辆记录及官方路线 shape。上一项集成测试有 245 个通过，历史数据 ID 也与对应静态资料匹配，但这不代表每条预测都准确。

### 6 — Current limitations

**English:** The current frontend shows the map, stops and route statistics. Route-line rendering and historical vehicle playback are not connected yet. The recorded-data banner is also missing. The map needs internet resources, but our backend fallback works offline. The displayed observation count is not a count of unique bus services.

**中文：** 当前前端可以显示地图、站点和线路统计。路线线条、历史车辆回放尚未接入，也缺少历史数据 banner。地图依赖网络资源，但后端 fallback 可离线运行。界面上的记录数量不能理解为独立公交班次数。

### 7 — Next steps

**English:** Next, we will coordinate the remaining frontend integration and verify it before presenting it as complete. From CASR, recent collector logs, a v2 backup and restart feedback would help us confirm deployment behaviour. We would also like your feedback on which historical queries are most useful for researchers.

**中文：** 下一步需要与前端协调，接入后再验证，不能提前宣称完成。希望 CASR 提供近期 collector logs、v2 backup 和重启反馈，以确认部署行为，也希望了解研究人员最需要哪些历史查询。

## 6. Likely client questions — short spoken answers

| Question | Simple English answer | 中文提示 |
| --- | --- | --- |
| Where does the GTFS data come from? | We use Adelaide Metro's GTFS-Realtime feeds and an archived official static timetable. Today's replay uses static version 1692. | 区分动态 feed 与静态时刻表；归档下载时间不作无证据声明。 |
| Is this live or recorded? | Recorded. It is 26 September, nine to eleven am Adelaide time. We have not shifted the dates to make it look live. | 固定九月历史数据，不伪装实时。 |
| How often does it collect? | By default, it waits sixty seconds after each attempt. Requests and retries can make the actual interval longer. | 不是保证每个自然分钟成功一次。 |
| What if the API fails? | Temporary errors get bounded retries. Failed cycles are logged, and the next cycle can try again. Permanent errors such as HTTP 403 are not retried. | 默认初次请求后最多再试两次，每次间隔五秒；不是无限重试。 |
| What about a power outage? | SQLite transactions and stored state help recovery, and we tested abrupt process exits locally. Automatic restart depends on Windows scheduling. Real power-loss recovery on CASR hardware is still unconfirmed. | 不把进程 crash 测试说成真实断电测试；停机期间未采集的数据无法凭空补回。 |
| Why was the database so large? | Many unchanged predictions were stored repeatedly. Trip Update tables and indexes used most of the space. | 不归咎于 Vehicle Positions；重复状态和索引是重点。 |
| How did you reduce storage? | We store changes and periodic checkpoints, use integer timestamps, and derive arrival time when queried. Full replay measured 81.62 percent less space. | 默认 15 分钟 checkpoint；是受控 replay，不是生产承诺。 |
| How do you know the data is correct? | We checked validation rules, ID relationships, time calculations, database integrity and integration tests. All checked stored IDs matched. This does not prove complete raw-feed capture or perfect predictions. | “100%”只适用于已检查存储 ID 的匹配，不是全面数据正确率。 |
| Can researchers query historical delays? | Yes. The repository supports route, stop and time filters. The API exposes route and stop summaries; more researcher-specific exports can be agreed with you. | 当前 performance HTTP endpoint 尚无时间筛选；原始更新可通过 repository/fallback 查，不虚构新 API。 |
| Can it show historical routes? | Official route shapes and recorded positions are available from the backend. Drawing them with a timeline is still frontend work. | shape API 已就绪，不等于图形 playback 已完成。 |
| What is already working? | Collection, processing, historical storage, backend queries, APIs, and the current stop-and-statistics map are working in our local checks. | 本地证据，不宣称 CASR 已全量验收。 |
| What remains unfinished? | Route and vehicle rendering, playback controls, the recorded-data label, and production deployment confirmation. | 另需改正 Services analysed 的含义；不用演示不存在的按钮。 |
| What support do you need from CASR? | Recent logs, a v2 database backup, and confirmation of scheduled startup after a restart. We also need your priorities for research queries and punctuality definitions. | 请求资料即可；本任务不代表已联系客户。 |

If asked about on-time percentages: current provisional code treats negative delay
as early, 0–5 minutes as on time, >5–10 as delayed, >10 as severe. These are
retained-prediction statistics, not independent completed-service performance.
Ask CASR to confirm operational definitions and boundaries before interpreting them
as research findings. Do not promise a live demo or a production recovery guarantee.

## 7. Fallback and failure handling

Run the existing command from Terminal A (before Flask or in another prepared
terminal with the same `$demoPython`, `$demoSource`, `$mapData` variables):

```powershell
& $demoPython -m backend.services.e2e_demo_check --database "$demoSource" --map-data "$mapData"
```

Tested on 16 October against current main. Uses a disposable copy, real repository
queries and Flask test-client; validates all route geometry contracts and history
pages. Does not require the Flask server, frontend server, tiles, live feed or
CASR computer. Do not use `python -O` (checks include assertions).

Show only these fields rather than reading the entire JSON:

| Route | Vehicles | Retained updates | Variants | Geometry points | Real predicted delay example |
| --- | ---: | ---: | ---: | ---: | --- |
| G10 | 741 | 10,743 | 3 | 1,232 | Trip 1135909 / stop 100618: scheduled 09:03:26, predicted 09:05:24, +118 sec |
| M44 | 793 | 7,319 | 3 | 1,381 | Trip 945499 / stop 100083: scheduled 09:05:00, predicted 09:04:45, -15 sec |
| 506 | 258 | 4,194 | 2 | 916 | Trip 944476 / stop 100308: scheduled 08:57:12, predicted 09:05:15, +483 sec |

All example dates are 26 September 2026, Adelaide +09:30. A scheduled arrival can
precede 09:00 because selection is by **observation time**, not scheduled arrival.
End-exclusive 11:00 applies to observation selection. Fallback confirms missing
map route 404 and missing artifacts 503. Source DB SHA-256 remained
`735de9404b6fe46d52fe0b102004e6993815157b8f5905341afbf9cada465aa2`.

- Tiles/CDN unavailable: immediately switch to terminal fallback and saved screenshot;
  identify screenshots as recorded evidence, not current successful offline UI.
- Geometry/playback not integrated: show map-data/vehicle JSON, explicitly no animation.
- Flask fails: use server-independent fallback; check configured path/environment/port later.
- Map-data 503: check all four artifacts (`route-shapes.geojson`, `stops.geojson`,
  `trip-map.json`, `manifest.json`) and configured directory; do not improvise regeneration.
- Both backend and artifact checks fail: show prior verified evidence, disclose the
  current failure, and offer follow-up. Do not claim a successful live demonstration.
- UI misleading count/banner: explain observations/date verbally and show this guide;
  request the frontend owner's label correction, do not silently edit their code.

## 8. Rehearsal record and risks

Individual local rehearsal, **not a full team rehearsal**:

- Main safely updated to `4bef170`; documentation branch created from it.
- Fresh temporary copy used by actual Flask at 127.0.0.1:5000; frontend at :8000.
- Routes/stops actual HTTP returned 3 / 354. Performance, map-data and three-row
  historical vehicle pages succeeded on G10/M44/506; next_offset = 3.
- Stop 100618 routes API returned G10.
- Browser selected G10 → M44 → 506. Counts/average delay/on-time display:
  G10 10,743 / 0.2 min / 38.0%; M44 7,319 / -0.7 min / 29.4%;
  506 4,194 / 2.1 min / 67.3%. Tiles and stop markers visibly rendered.
- [Current rehearsal screenshot](evidence/rehearsal-506-2026-10-16.png).
  Stop detail popups/geolocation were not independently re-tested in this short
  rehearsal; do not substitute previous teammate evidence for a new claim.
- Existing fallback succeeded; original DB hash unchanged. No new full historical
  replay/ID audit performed. Earlier 81.62% / 100% evidence is cited, not remeasured.
- Focused tests: `python -m pytest backend/tests/test_e2e_integration.py -q`:
  **14 passed in 2.70 seconds**. Earlier SCRUM-234 full suite: 245 passed;
  full suite not repeated for documentation-only work.
- No automated text-to-speech/human timed speaking rehearsal or other participant
  involvement. Speaking duration is estimated; group should practise it aloud.

Main meeting risks: wrong Python environment; missing untracked local data on a
teammate laptop; fixed API port conflicts; missing map artifact configuration;
CDN/tiles/network failure; unsupported playback expectations; incorrect September
offset; misleading observation counts; treating benchmark/import ledger as production
proof. This guide and the existing offline fallback address the demonstrable scope,
not final frontend completion or production certification.

## 9. Team confirmation / final rehearsal checklist

- [ ] Confirm meeting time/timezone, screen-sharing laptop and driver with the group.
- [ ] Confirm actual people for opening, frontend, backend/data, backup operator,
  timekeeping and Q&A; no assignments have been made by this task.
- [ ] Backend operator verifies Python dependencies, exact demo paths and free ports.
- [ ] Run fallback before the meeting; keep its output and benchmark/ID report open.
- [ ] Frontend owner confirms present feature status; add recorded banner and correct
  observation label if coordinated. Re-test any new feature before including it.
- [ ] Test on the actual screen-sharing laptop and network, including CDN/tiles.
- [ ] Agree switch-to-fallback cue after ~20 seconds and who performs it.
- [ ] Read English script aloud with a timer; aim 3–5 minutes without Chinese; trim
  code explanation first if over time. Whole team target 8–10 minutes.
- [ ] Agree who asks CASR for recent logs/v2 backup/scheduled-restart evidence and
  who captures research priorities and punctuality-definition feedback.
- [ ] Run one genuine group rehearsal; mark it completed only after participants join.
- [ ] Stop demo-owned Flask/frontend servers with Ctrl+C after rehearsal/meeting.
  Temporary copies can be cleaned later after verifying their exact paths;
  never delete or overwrite the original archive/demo source.

SCRUM-235 preparation is review-ready after guide review and push. Pending group
coordination/timed speaking remain explicit checklist items; not evidence of a
completed team rehearsal. Do not automatically merge, update Jira or start SCRUM-236.
