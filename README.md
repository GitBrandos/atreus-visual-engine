# Atreus Visual Engine

Atreus Visual Engine is a desktop particle sandbox that streams a live,
down-sampled view of its simulation to a mobile web browser.

## Architecture

```
Desktop Simulation (pygame, numpy)
  100,000 particles @ ~60 FPS
        │  SimulationLoop.tick() every frame
        ▼
SharedParticleCache (thread-safe, in-process)
  down-sampled to 2,500 particles, refreshed every 100ms
        │  read by the async broadcast loop (no blocking I/O in the sim thread)
        ▼
FastAPI backend (WebSocket + HTTP)
  broadcasts cache snapshots to all connected clients every 500ms
        │  wss://.../ws/particles
        ▼
Mobile Web UI (single HTML page)
  canvas rendering, live metrics, network stats, agent controls
```

The simulation, cache, and server all share the same process and the same
`ParticleSystem` / `SharedParticleCache` / `AgentController` instances, so
the mobile view mirrors what's shown on the desktop window. The cache is
only ever touched under a short-lived lock (a numpy slice + copy), so slow
network clients never stall the physics loop.

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

## Monica character module

`atreus/character/` adds an isolated Monica character layer (personality,
conversation state, and reply backends) alongside the existing simulation —
nothing in `atreus/simulation`, `atreus/protocol`, `atreus/agents`, or
`atreus/server` is affected by it.

`OpenAIReplyBackend` (`atreus/character/openai_backend.py`) generates
Monica's replies via the OpenAI Chat Completions API. It reads its API key
from the `OPENAI_API_KEY` environment variable — never hard-code it or
commit it to source control. Set it before use, e.g.:

```bash
export OPENAI_API_KEY="sk-..."
```

or place it in a local `.env` file (already listed in `.gitignore`) and
load it into your shell/session before running Atreus. Without
`OpenAIReplyBackend`, `MonicaCharacter` defaults to a dependency-free
`EchoReplyBackend`.

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
- `WS /ws/particles` — subscribe to snapshot broadcasts; send the same JSON command shape to control the simulation over the socket

## Opening the mobile UI from a phone on the same network

1. Find your machine's LAN IP address (e.g. `ifconfig` / `ipconfig`, look for something like `192.168.x.x`).
2. Start the server as above, bound to `0.0.0.0` (the default) so it's reachable from other devices.
3. On your phone (connected to the same Wi-Fi network), open `http://<your-lan-ip>:8000/` in a browser.
4. The page connects to `/ws/particles` automatically and renders the live particle stream, with pause/resume/reset buttons and attraction/jitter sliders.

## Expected update rates and limitations

- Desktop physics/render: ~60 FPS for 100,000 particles (numpy-vectorized physics and `pygame.surfarray` blitting).
- Cache refresh: every 100ms (down-sampled to 2,500 particles via evenly spaced indices, so the same subset of particles is tracked across updates).
- Mobile broadcast: every 500ms per connected client; actual mobile framerate is therefore ~2 updates/sec, not 60 FPS — this is a deliberate bandwidth/latency tradeoff for phones on Wi-Fi.
- The mobile canvas interpolates nothing between updates (particles "jump" every 500ms); this keeps the client simple at the cost of visual smoothness.
- Agent commands are applied on the next simulation tick after being queued, so there is up to one frame of latency.
- This is a single-process, in-memory architecture: running the desktop simulation and the FastAPI server as separate OS processes will give each its own independent simulation state (no cross-process IPC is implemented).
