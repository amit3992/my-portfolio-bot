import os
import logging
import asyncpg
import httpx

logger = logging.getLogger(__name__)

pool: asyncpg.Pool | None = None
_geo_cache: dict[str, dict] = {}


async def init_db():
    global pool
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.warning("DATABASE_URL not set — analytics disabled")
        return

    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)

    async with pool.acquire() as conn:
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
    logger.info("Analytics database initialized")


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
    if not pool:
        return

    try:
        # Truncate response preview to 200 chars
        if response_preview and len(response_preview) > 200:
            response_preview = response_preview[:200] + "..."

        # Geolocate IP
        geo = await geolocate_ip(ip_address)
        city = geo.get("city")
        country = geo.get("country")

        async with pool.acquire() as conn:
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
