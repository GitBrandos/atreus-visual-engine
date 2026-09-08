# Atreus — an AI Character & Simulation Engine

Atreus is a platform for creating and interacting with custom, user-authored
AI characters inside a live simulated environment. It combines a desktop
particle sandbox (the "World Engine") with a lightweight character system
(the "Character Engine") and streams both to a mobile web browser in
real time.

## Architecture

```
Desktop Simulation (pygame, numpy)            atreus/character/
  100,000 particles @ ~60 FPS                   Character (data model)
        │  SimulationLoop.tick() every frame     CharacterRegistry (CRUD)
        ▼                                        DialogueEngine (pluggable)
SharedParticleCache (thread-safe, in-process)         │
  down-sampled to 2,500 particles, refreshed          │ character state
  every 100ms, plus the latest character states        │ (idle/active/reacting)
        │  read by the async broadcast loop ◄──────────┘
        │  (no blocking I/O in the sim thread)
        ▼
FastAPI backend (WebSocket + HTTP)
  broadcasts cache snapshots (incl. character states) every 500ms
  serves character CRUD + chat endpoints
        │  wss://.../ws/particles
        ▼
Mobile Web UI (single HTML page)
  canvas rendering, live metrics, network stats, agent controls,
  character select/chat panel
```

The simulation, cache, character registry, and server all share the same
process and the same `ParticleSystem` / `SharedParticleCache` /
`AgentController` / `CharacterRegistry` instances, so the mobile view
mirrors what's shown on the desktop window. The cache is only ever touched
under a short-lived lock (a numpy slice + copy), so slow network clients
never stall the physics loop.

The `character` package is intentionally optional and decoupled: with zero
characters registered, the particle sandbox behaves exactly as it always
has. A character is pure data (name, description, traits, backstory,
interests, allowed interaction modes) plus a narrow, pluggable
`DialogueEngine` interface for generating responses — no assumption is
built in about tone or content beyond what a given character's traits
specify, so the system supports hobbyist, educational, storytelling, or
customer-service-style characters alike.

Configuration constants live in `atreus/config.py`:

| Constant | Value | Purpose |
| --- | --- | --- |
| `DESKTOP_PARTICLE_COUNT` | 100,000 | Desktop simulation particle count |
| `CACHE_SAMPLE_SIZE` | 2,500 | Particles kept in the shared cache |
| `CACHE_SYNC_INTERVAL_MS` | 100 | How often the cache is refreshed from the sim |
| `STREAM_INTERVAL_MS` | 500 | How often snapshots are broadcast to clients |
| `TARGET_FPS` | 60 | Desktop simulation/render target frame rate |

## Setup

```bash
pip install -r requirements.txt
```

## Running the desktop simulation only

```bash
python -m atreus.simulation.desktop
```

Opens a pygame window rendering 100,000 particles. Controls: `Space` to
pause/resume, `R` to reset, `Esc`/window close to quit.

## Running the desktop simulation + mobile streaming server together

```bash
python -m atreus.synced_system
```

This opens the desktop pygame window **and** starts the FastAPI server on
`http://0.0.0.0:8000`, both driven by the same simulation state.

## Running the FastAPI server standalone

```bash
uvicorn atreus.server.app:app --host 0.0.0.0 --port 8000
```

When run standalone (without the desktop process), the server spins up its
own headless background simulation thread so `/` and `/ws/particles` work
immediately.

Endpoints:

- `GET /` — mobile web UI
- `GET /api/status` — JSON status/metrics (iteration, particle counts, FPS, last update age)
- `POST /api/agent-command` — send `{"action": "pause" | "resume" | "reset" | "set_param", "payload": {...}}`
- `WS /ws/particles` — subscribe to snapshot broadcasts (now including a `character_states` map); send the same JSON command shape to control the simulation over the socket
- `GET /api/characters` — list all registered characters
- `POST /api/characters` — register a new character (`{"id", "name", "description", "backstory", "traits": {...}, "interests": [...], "interaction_modes": [...]}`); trait values and content are validated server-side
- `GET /api/characters/{character_id}` — fetch a single character
- `POST /api/characters/{character_id}/message` — send `{"message": "..."}` and get back `{"text": "...", "state": "idle" | "active" | "reacting"}`; the resulting state is also reflected in subsequent `/ws/particles` snapshots

## Opening the mobile UI from a phone on the same network

1. Find your machine's LAN IP address (e.g. `ifconfig` / `ipconfig`, look for something like `192.168.x.x`).
2. Start the server as above, bound to `0.0.0.0` (the default) so it's reachable from other devices.
3. On your phone (connected to the same Wi-Fi network), open `http://<your-lan-ip>:8000/` in a browser.
4. The page connects to `/ws/particles` automatically and renders the live particle stream, with pause/resume/reset buttons, attraction/jitter sliders, and a character select/chat panel.

## Expected update rates and limitations

- Desktop physics/render: ~60 FPS for 100,000 particles (numpy-vectorized physics and `pygame.surfarray` blitting).
- Cache refresh: every 100ms (down-sampled to 2,500 particles via evenly spaced indices, so the same subset of particles is tracked across updates).
- Mobile broadcast: every 500ms per connected client; actual mobile framerate is therefore ~2 updates/sec, not 60 FPS — this is a deliberate bandwidth/latency tradeoff for phones on Wi-Fi.
- The mobile canvas interpolates nothing between updates (particles "jump" every 500ms); this keeps the client simple at the cost of visual smoothness.
- Agent commands are applied on the next simulation tick after being queued, so there is up to one frame of latency.
- This is a single-process, in-memory architecture: running the desktop simulation and the FastAPI server as separate OS processes will give each its own independent simulation state (no cross-process IPC is implemented). The character registry is likewise in-memory and not yet persisted across restarts.
- The bundled `TemplateDialogueEngine` is a minimal, fully offline, rule-based default; swap in a real inference backend by implementing the `DialogueEngine` protocol in `atreus/character/dialogue.py`.

