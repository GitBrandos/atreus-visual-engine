"""Shared configuration constants for the Atreus visual engine.

These values tie together the desktop simulation, the sync/cache layer,
and the mobile streaming backend so that all three stay consistent.
"""

# --- Desktop simulation -----------------------------------------------------
#: Number of particles simulated by the desktop (pygame) sandbox.
DESKTOP_PARTICLE_COUNT = 100_000

#: Target desktop simulation/render frame rate.
TARGET_FPS = 60

#: Desktop simulation world size (pixels).
WORLD_WIDTH = 1280
WORLD_HEIGHT = 720

# --- Sync / cache layer -------------------------------------------------------
#: Number of particles kept in the down-sampled cache shared with the backend.
CACHE_SAMPLE_SIZE = 2_500

#: How often (in milliseconds) the cache is refreshed from the simulation.
CACHE_SYNC_INTERVAL_MS = 100

# --- Mobile streaming ---------------------------------------------------------
#: How often (in milliseconds) cache snapshots are broadcast to WebSocket clients.
STREAM_INTERVAL_MS = 500

#: Default host/port for the FastAPI streaming server.
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# --- Character persistence ----------------------------------------------------
#: Default path for the on-disk character store, relative to the process's
#: working directory. Set to ``None`` (e.g. via `create_app(character_store=None)`)
#: to run with a purely in-memory registry (handy for tests).
CHARACTER_STORE_PATH = "characters.json"
