# Atreus — an AI Character & Simulation Engine

Atreus is a platform for creating and interacting with custom, user-authored
AI characters inside a live simulated environment. It combines a desktop
particle sandbox (the "World Engine") with a lightweight character system
(the "Character Engine") and streams both to a mobile web browser in
real time.

## Architecture

```
Desktop Simulation (pygame, numpy)            atreus/character/
  100,000 particles @ ~60 FPS                   Character (data model,
        │  SimulationLoop.tick() every frame      incl. position + marker color)
        ▼                                        CharacterRegistry (CRUD)
SharedParticleCache (thread-safe, in-process)   DialogueEngine (pluggable)
  down-sampled to 2,500 particles, refreshed          │
  every 100ms, plus the latest character markers      │ character markers
        │  read by the async broadcast loop ◄──────────┘ (id, name, position,
        │  (no blocking I/O in the sim thread)             color, state)
        ▼
FastAPI backend (WebSocket + HTTP)
  broadcasts cache snapshots (incl. character markers) every 500ms
  serves character CRUD + chat endpoints
        │  wss://.../ws/particles
        ▼
Mobile Web UI (single HTML page)
  canvas rendering (particles + labeled, state-animated character
  markers), live metrics, network stats, agent controls, character
  select/chat panel
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
interests, world position, allowed interaction modes) plus a narrow,
pluggable `DialogueEngine` interface for generating responses — no
assumption is built in about tone or content beyond what a given
character's traits specify, so the system supports hobbyist, educational,
storytelling, or customer-service-style characters alike.

Each character also has a stable, hash-derived `marker_color` and a world
`position`, so it can be rendered as a distinct, labeled marker on the
particle canvas. The marker's appearance is driven by the character's
`state` (`idle` / `active` / `reacting`): replying to a chat message moves a
character into `reacting`, which the mobile UI renders as a pulsing glow
around its marker, visibly tying conversation back to the simulated world.

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
- `WS /ws/particles` — subscribe to snapshot broadcasts (now including a `character_markers` list of `{id, name, position, color, state}`); send the same JSON command shape to control the simulation over the socket
- `GET /api/characters` — list all registered characters
- `POST /api/characters` — register a new character (`{"id", "name", "description", "backstory", "traits": {...}, "interests": [...], "interaction_modes": [...], "position": [x, y]}`); `position` is optional (defaults to the center of the world) and must fall within `WORLD_WIDTH`/`WORLD_HEIGHT`; trait values and content are validated server-side
- `GET /api/characters/{character_id}` — fetch a single character (includes its `position` and stable `marker_color`)
- `POST /api/characters/{character_id}/message` — send `{"message": "..."}` and get back `{"text": "...", "state": "idle" | "active" | "reacting"}`; the resulting state is also reflected in subsequent `/ws/particles` snapshots

## Creating your first character

With the server running (`uvicorn atreus.server.app:app --host 0.0.0.0 --port 8000`, or the desktop+server script from above), you can register and talk to a character entirely from the command line:

```bash
# 1. Register a character. `position` is optional (defaults to the world's
#    center); traits are optional floats in [0.0, 1.0].
curl -X POST http://localhost:8000/api/characters \
  -H "Content-Type: application/json" \
  -d '{
        "id": "nova",
        "name": "Nova",
        "description": "A curious, upbeat guide to the particle world.",
        "backstory": "Nova has watched this particle field drift for as long as it has existed.",
        "traits": {"curiosity": 0.9, "warmth": 0.8},
        "interests": ["astronomy", "cloud formations"],
        "position": [200, 200]
      }'

# 2. Fetch it back -- note the server-assigned, stable `marker_color`.
curl http://localhost:8000/api/characters/nova

# 3. Send it a chat message and see its reply + resulting behavioural state.
curl -X POST http://localhost:8000/api/characters/nova/message \
  -H "Content-Type: application/json" \
  -d '{"message": "What do you see out there?"}'

# 4. List every registered character.
curl http://localhost:8000/api/characters
```

Open `http://localhost:8000/` in a browser and Nova should now be visible as a
labeled, colored marker drifting gently around the particle canvas near
`(200, 200)` — click/tap its marker directly on the canvas (or use the
dropdown in the character panel) to select it, then send it a message from
the chat box to watch its marker pulse while it's `reacting`.

## Opening the mobile UI from a phone on the same network

1. Find your machine's LAN IP address (e.g. `ifconfig` / `ipconfig`, look for something like `192.168.x.x`).
2. Start the server as above, bound to `0.0.0.0` (the default) so it's reachable from other devices.
3. On your phone (connected to the same Wi-Fi network), open `http://<your-lan-ip>:8000/` in a browser.
4. The page connects to `/ws/particles` automatically and renders the live particle stream, with pause/resume/reset buttons, attraction/jitter sliders, and a character select/chat panel. Registered characters appear as labeled, colored markers on the canvas at their world position, drifting gently over time; a marker pulses/glows while that character is `active` or `reacting`. Tapping a marker directly on the canvas selects that character in the chat panel, the same as choosing it from the dropdown.

## Expected update rates and limitations

- Desktop physics/render: ~60 FPS for 100,000 particles (numpy-vectorized physics and `pygame.surfarray` blitting).
- Cache refresh: every 100ms (down-sampled to 2,500 particles via evenly spaced indices, so the same subset of particles is tracked across updates).
- Mobile broadcast: every 500ms per connected client; actual mobile framerate is therefore ~2 updates/sec, not 60 FPS — this is a deliberate bandwidth/latency tradeoff for phones on Wi-Fi.
- The mobile canvas interpolates nothing between updates (particles "jump" every 500ms); this keeps the client simple at the cost of visual smoothness.
- Agent commands are applied on the next simulation tick after being queued, so there is up to one frame of latency.
- This is a single-process, in-memory-first architecture: running the desktop simulation and the FastAPI server as separate OS processes will give each its own independent simulation state (no cross-process IPC is implemented). The character registry persists to `characters.json` (see `atreus.character.store.JSONFileStore`) when run via `uvicorn atreus.server.app:app`, so registered characters survive a restart of that process; tests and custom `create_app(...)` callers that don't pass `character_store` still get a purely in-memory registry.
- Characters wander and gently drift toward nearby particle clusters every simulation tick (`atreus.character.movement.step_characters`); this motion is intentionally not persisted (see `CharacterRegistry.set_position`), so only a character's *last deliberately set* position (e.g. at creation) is durable — the live wandering position is recomputed each run.
- The bundled `TemplateDialogueEngine` is a minimal, fully offline, rule-based default. All dialogue responses (including the default) pass through `atreus.character.dialogue.SafetyGuardedDialogueEngine`, which bounds reply length, fails closed if a backend errors, and blocks obvious prompt-injection markers. Swap in a real inference backend by implementing the `DialogueEngine` protocol and wrapping it the same way: `create_app(dialogue_engine=SafetyGuardedDialogueEngine(MyBackend()))`.

