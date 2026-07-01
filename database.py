import os
import time
import asyncio
import logging
import asyncpg
import httpx

logger = logging.getLogger(__name__)

pool: asyncpg.Pool | None = None
_geo_cache: dict[str, dict] = {}

# Lazy-reconnect state: the pool is (re)built on demand so the app self-heals
# after the DB was unreachable at startup (e.g. Supabase free-tier auto-pause).
_pool_lock = asyncio.Lock()
_last_attempt = 0.0
_RETRY_INTERVAL = 30.0  # min seconds between reconnect attempts while DB is down


async def _create_schema(conn) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_events (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            user_question TEXT,
            llm_provider TEXT,
            response_preview TEXT,
            latency_ms INTEGER,
            is_error BOOLEAN DEFAULT FALSE,
            error_message TEXT,
            is_fallback BOOLEAN DEFAULT FALSE,
            ip_address TEXT,
            endpoint TEXT,
            session_id TEXT,
            user_agent TEXT,
            city TEXT,
            country TEXT
        )
    """)
    # Add columns if table already exists from previous version
    for col, col_type in [
        ("session_id", "TEXT"),
        ("user_agent", "TEXT"),
        ("city", "TEXT"),
        ("country", "TEXT"),
    ]:
        await conn.execute(f"""
            DO $$ BEGIN
                ALTER TABLE chat_events ADD COLUMN {col} {col_type};
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_snippets (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            label TEXT NOT NULL,
            content TEXT NOT NULL,
            active BOOLEAN DEFAULT TRUE
        )
    """)


async def ensure_pool() -> "asyncpg.Pool | None":
    """Return a live connection pool, (re)creating it if needed.

    Callers use this instead of the module-level `pool` so the app recovers
    automatically once the database becomes reachable again — no restart needed.
    Attempts are throttled so a down DB doesn't get hammered on every request.
    """
    global pool, _last_attempt
    if pool is not None:
        return pool

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return None

    async with _pool_lock:
        if pool is not None:  # another coroutine connected while we waited
            return pool
        if time.monotonic() - _last_attempt < _RETRY_INTERVAL:
            return None
        _last_attempt = time.monotonic()

        # Strip pgbouncer/query params (not accepted by asyncpg); statement_cache_size=0
        # is required for pgbouncer transaction pooling (Supabase :6543).
        clean_url = database_url.split("?")[0]
        try:
            from urllib.parse import urlparse
            p = urlparse(clean_url)
            logger.info(f"DB connect: host={p.hostname}, port={p.port}, db={p.path}, user={p.username}")
        except Exception:
            pass

        try:
            logger.info("Attempting asyncpg.create_pool...")
            new_pool = await asyncpg.create_pool(
                clean_url,
                min_size=1,
                max_size=5,
                statement_cache_size=0,
                timeout=10,
                command_timeout=10,
            )
            async with new_pool.acquire() as conn:
                await _create_schema(conn)
            pool = new_pool
            logger.info("asyncpg pool created successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {type(e).__name__}: {e}")
            logger.warning("Analytics disabled — will retry on a later request")
            pool = None

    return pool


async def reset_pool() -> None:
    """Drop the current pool so the next ensure_pool() reconnects.

    Used when a query fails mid-request (e.g. DB paused after startup) so the
    app doesn't stay wedged on a dead pool.
    """
    global pool, _last_attempt
    async with _pool_lock:
        if pool is not None:
            try:
                await pool.close()
            except Exception:
                pass
        pool = None
        _last_attempt = 0.0  # allow an immediate retry next call


async def init_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.warning("DATABASE_URL not set — analytics disabled")
        return
    if await ensure_pool():
        logger.info("Analytics database initialized")
    else:
        logger.warning("Analytics disabled — app will continue without tracking")


async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None


async def geolocate_ip(ip: str) -> dict:
    """Look up city/country from IP using ip-api.com (free, no key needed)."""
    if not ip or ip in ("127.0.0.1", "::1", "testclient"):
        return {}

    if ip in _geo_cache:
        return _geo_cache[ip]

    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"http://ip-api.com/json/{ip}?fields=city,country,status")
            data = resp.json()
            if data.get("status") == "success":
                result = {"city": data.get("city", ""), "country": data.get("country", "")}
            else:
                result = {}
            _geo_cache[ip] = result
            return result
    except Exception as e:
        logger.debug(f"Geolocation failed for {ip}: {e}")
        return {}


async def log_chat_event(
    user_question: str,
    llm_provider: str = None,
    response_preview: str = None,
    latency_ms: int = None,
    is_error: bool = False,
    error_message: str = None,
    is_fallback: bool = False,
    ip_address: str = None,
    endpoint: str = None,
    session_id: str = None,
    user_agent: str = None,
):
    db = await ensure_pool()
    if not db:
        return

    try:
        # Truncate response preview to 200 chars
        if response_preview and len(response_preview) > 200:
            response_preview = response_preview[:200] + "..."

        # Geolocate IP
        geo = await geolocate_ip(ip_address)
        city = geo.get("city")
        country = geo.get("country")

        async with db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_events
                    (user_question, llm_provider, response_preview, latency_ms,
                     is_error, error_message, is_fallback, ip_address, endpoint,
                     session_id, user_agent, city, country)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                user_question, llm_provider, response_preview, latency_ms,
                is_error, error_message, is_fallback, ip_address, endpoint,
                session_id, user_agent, city, country,
            )
    except Exception as e:
        logger.error(f"Failed to log chat event: {e}")
        await reset_pool()


async def get_knowledge_snippets() -> list[dict]:
    """Fetch all active knowledge snippets."""
    db = await ensure_pool()
    if not db:
        return []
    try:
        async with db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, label, content, created_at FROM knowledge_snippets WHERE active = TRUE ORDER BY created_at DESC"
            )
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to fetch knowledge snippets: {e}")
        await reset_pool()
        return []


async def add_knowledge_snippet(label: str, content: str) -> int | None:
    """Add a new knowledge snippet. Returns the new ID."""
    db = await ensure_pool()
    if not db:
        return None
    try:
        async with db.acquire() as conn:
            row_id = await conn.fetchval(
                "INSERT INTO knowledge_snippets (label, content) VALUES ($1, $2) RETURNING id",
                label, content,
            )
            return row_id
    except Exception as e:
        logger.error(f"Failed to add knowledge snippet: {e}")
        await reset_pool()
        return None


async def delete_knowledge_snippet(snippet_id: int) -> bool:
    """Soft-delete a knowledge snippet."""
    db = await ensure_pool()
    if not db:
        return False
    try:
        async with db.acquire() as conn:
            await conn.execute(
                "UPDATE knowledge_snippets SET active = FALSE WHERE id = $1", snippet_id
            )
            return True
    except Exception as e:
        logger.error(f"Failed to delete knowledge snippet: {e}")
        await reset_pool()
        return False
