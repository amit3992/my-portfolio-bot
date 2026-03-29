import os
from html import escape
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse
from database import pool

router = APIRouter()

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")


def verify_token(token: str):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Dashboard not configured")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


def esc(val: str | None, max_len: int = 0) -> str:
    """HTML-escape and optionally truncate a string."""
    if not val:
        return ""
    text = escape(val)
    if max_len and len(text) > max_len:
        text = text[:max_len] + "..."
    return text


def parse_user_agent(ua: str | None) -> str:
    """Extract a short browser/device label from a User-Agent string."""
    if not ua:
        return "-"
    ua_lower = ua.lower()
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        device = "Mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device = "Tablet"
    else:
        device = "Desktop"

    if "chrome" in ua_lower and "edg" not in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser = "Safari"
    elif "edg" in ua_lower:
        browser = "Edge"
    else:
        browser = "Other"

    return f"{browser} / {device}"


@router.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard(token: str = Query(...)):
    verify_token(token)

    if not pool:
        return HTMLResponse("<h1>Database not connected</h1>", status_code=503)

    async with pool.acquire() as conn:
        # Total counts
        total = await conn.fetchval("SELECT COUNT(*) FROM chat_events")
        today = await conn.fetchval(
            "SELECT COUNT(*) FROM chat_events WHERE timestamp >= CURRENT_DATE"
        )
        this_week = await conn.fetchval(
            "SELECT COUNT(*) FROM chat_events WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'"
        )

        # Unique visitors
        unique_ips = await conn.fetchval(
            "SELECT COUNT(DISTINCT ip_address) FROM chat_events WHERE ip_address IS NOT NULL"
        )
        unique_sessions = await conn.fetchval(
            "SELECT COUNT(DISTINCT session_id) FROM chat_events WHERE session_id IS NOT NULL"
        )
        unique_ips_today = await conn.fetchval(
            "SELECT COUNT(DISTINCT ip_address) FROM chat_events WHERE ip_address IS NOT NULL AND timestamp >= CURRENT_DATE"
        )

        # Error stats
        total_errors = await conn.fetchval(
            "SELECT COUNT(*) FROM chat_events WHERE is_error = TRUE"
        )
        fallbacks = await conn.fetchval(
            "SELECT COUNT(*) FROM chat_events WHERE is_fallback = TRUE"
        )

        # LLM breakdown
        provider_rows = await conn.fetch(
            "SELECT llm_provider, COUNT(*) as cnt FROM chat_events WHERE llm_provider IS NOT NULL GROUP BY llm_provider ORDER BY cnt DESC"
        )

        # Avg latency
        avg_latency = await conn.fetchval(
            "SELECT ROUND(AVG(latency_ms)) FROM chat_events WHERE latency_ms IS NOT NULL"
        ) or 0

        # Top locations
        locations = await conn.fetch(
            """SELECT city, country, COUNT(*) as cnt
               FROM chat_events WHERE country IS NOT NULL AND country != ''
               GROUP BY city, country ORDER BY cnt DESC LIMIT 10"""
        )

        # Browser/device breakdown
        browsers = await conn.fetch(
            """SELECT user_agent, COUNT(*) as cnt
               FROM chat_events WHERE user_agent IS NOT NULL
               GROUP BY user_agent ORDER BY cnt DESC LIMIT 20"""
        )

        # Recent sessions with conversation counts
        sessions = await conn.fetch(
            """SELECT session_id, ip_address, city, country, user_agent,
                      MIN(timestamp) as first_seen, MAX(timestamp) as last_seen,
                      COUNT(*) as msg_count
               FROM chat_events WHERE session_id IS NOT NULL
               GROUP BY session_id, ip_address, city, country, user_agent
               ORDER BY last_seen DESC LIMIT 20"""
        )

        # Recent questions (last 50)
        recent = await conn.fetch(
            """SELECT timestamp, user_question, llm_provider, latency_ms,
                      is_error, is_fallback, error_message, city, country, session_id
               FROM chat_events ORDER BY timestamp DESC LIMIT 50"""
        )

        # Recent errors
        errors = await conn.fetch(
            """SELECT timestamp, user_question, error_message, llm_provider
               FROM chat_events WHERE is_error = TRUE ORDER BY timestamp DESC LIMIT 20"""
        )

        # Top questions
        top_questions = await conn.fetch(
            """SELECT user_question, COUNT(*) as cnt
               FROM chat_events WHERE user_question IS NOT NULL
               GROUP BY user_question ORDER BY cnt DESC LIMIT 15"""
        )

    # --- Build HTML fragments ---

    # Provider breakdown
    provider_html = ""
    for row in provider_rows:
        pct = round(row["cnt"] / total * 100, 1) if total > 0 else 0
        provider_html += f"""
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee">
            <span style="font-weight:600;text-transform:capitalize">{esc(row['llm_provider']) or 'unknown'}</span>
            <span>{row['cnt']} ({pct}%)</span>
        </div>"""

    # Locations
    location_html = ""
    for loc in locations:
        city = esc(loc["city"]) or "Unknown"
        country = esc(loc["country"]) or "Unknown"
        location_html += f"""
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee">
            <span>{city}, {country}</span>
            <span style="font-weight:600;color:#3b82f6">{loc['cnt']}</span>
        </div>"""

    # Browser/device breakdown (aggregate by parsed label)
    browser_counts: dict[str, int] = {}
    for b in browsers:
        label = parse_user_agent(b["user_agent"])
        browser_counts[label] = browser_counts.get(label, 0) + b["cnt"]
    browser_html = ""
    for label, cnt in sorted(browser_counts.items(), key=lambda x: -x[1]):
        browser_html += f"""
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee">
            <span>{label}</span>
            <span style="font-weight:600;color:#3b82f6">{cnt}</span>
        </div>"""

    # Sessions table
    session_rows = ""
    for s in sessions:
        first_seen = s["first_seen"].strftime("%b %d %H:%M") if s["first_seen"] else ""
        last_seen = s["last_seen"].strftime("%b %d %H:%M") if s["last_seen"] else ""
        loc = f'{esc(s["city"]) or "?"}, {esc(s["country"]) or "?"}' if s["country"] else "-"
        device = parse_user_agent(s["user_agent"])
        sid = (s["session_id"] or "")[:8]
        session_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee"><code>{sid}...</code></td>
            <td style="padding:8px;border-bottom:1px solid #eee">{loc}</td>
            <td style="padding:8px;border-bottom:1px solid #eee">{device}</td>
            <td style="padding:8px;border-bottom:1px solid #eee">{s['msg_count']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;white-space:nowrap">{first_seen}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;white-space:nowrap">{last_seen}</td>
        </tr>"""

    # Recent questions
    recent_rows = ""
    for r in recent:
        ts = r["timestamp"].strftime("%b %d %H:%M") if r["timestamp"] else ""
        error_badge = '<span style="color:#ef4444;font-weight:600">ERR</span>' if r["is_error"] else ""
        fallback_badge = '<span style="color:#f59e0b;font-weight:600">FB</span>' if r["is_fallback"] else ""
        badges = f"{error_badge} {fallback_badge}".strip()
        question = esc(r["user_question"], 80)
        latency = f'{r["latency_ms"]}ms' if r["latency_ms"] else "-"
        provider = esc(r["llm_provider"]) or "-"
        loc = f'{esc(r["city"]) or "?"}, {esc(r["country"]) or "?"}' if r["country"] else "-"
        recent_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;white-space:nowrap">{ts}</td>
            <td style="padding:8px;border-bottom:1px solid #eee">{question}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-transform:capitalize">{provider}</td>
            <td style="padding:8px;border-bottom:1px solid #eee">{latency}</td>
            <td style="padding:8px;border-bottom:1px solid #eee">{loc}</td>
            <td style="padding:8px;border-bottom:1px solid #eee">{badges}</td>
        </tr>"""

    # Errors
    error_rows = ""
    for e in errors:
        ts = e["timestamp"].strftime("%b %d %H:%M") if e["timestamp"] else ""
        question = esc(e["user_question"], 60)
        err_msg = esc(e["error_message"], 100)
        error_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;white-space:nowrap">{ts}</td>
            <td style="padding:8px;border-bottom:1px solid #eee">{question}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;color:#ef4444">{err_msg}</td>
        </tr>"""

    # Top questions
    top_q_html = ""
    for q in top_questions:
        question = esc(q["user_question"], 70)
        top_q_html += f"""
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee">
            <span>{question}</span>
            <span style="font-weight:600;color:#3b82f6">{q['cnt']}</span>
        </div>"""

    error_rate = round(total_errors / total * 100, 1) if total > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Bot Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; color: #1e293b; padding: 24px; }}
        .header {{ margin-bottom: 32px; }}
        .header h1 {{ font-size: 24px; font-weight: 700; }}
        .header p {{ color: #64748b; margin-top: 4px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 32px; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
        .card .label {{ font-size: 13px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }}
        .card .value {{ font-size: 28px; font-weight: 700; margin-top: 4px; }}
        .card .value.green {{ color: #22c55e; }}
        .card .value.red {{ color: #ef4444; }}
        .card .value.blue {{ color: #3b82f6; }}
        .card .value.amber {{ color: #f59e0b; }}
        .card .value.purple {{ color: #8b5cf6; }}
        .section {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 24px; }}
        .section h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0; }}
        .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }}
        .three-col {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
        th {{ text-align: left; padding: 8px; border-bottom: 2px solid #e2e8f0; font-size: 12px; text-transform: uppercase; color: #64748b; letter-spacing: 0.5px; }}
        code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
        .refresh {{ display: inline-block; margin-top: 8px; color: #3b82f6; text-decoration: none; font-size: 14px; }}
        .refresh:hover {{ text-decoration: underline; }}
        @media (max-width: 768px) {{
            .two-col, .three-col {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Portfolio Bot Analytics</h1>
        <p>Real-time tracking for your chatbot</p>
        <a class="refresh" href="javascript:location.reload()">Refresh</a>
    </div>

    <div class="grid">
        <div class="card">
            <div class="label">Total Questions</div>
            <div class="value blue">{total}</div>
        </div>
        <div class="card">
            <div class="label">Today</div>
            <div class="value green">{today}</div>
        </div>
        <div class="card">
            <div class="label">This Week</div>
            <div class="value">{this_week}</div>
        </div>
        <div class="card">
            <div class="label">Unique Visitors</div>
            <div class="value purple">{unique_ips}</div>
        </div>
        <div class="card">
            <div class="label">Visitors Today</div>
            <div class="value purple">{unique_ips_today}</div>
        </div>
        <div class="card">
            <div class="label">Sessions</div>
            <div class="value purple">{unique_sessions}</div>
        </div>
        <div class="card">
            <div class="label">Avg Latency</div>
            <div class="value">{avg_latency}ms</div>
        </div>
        <div class="card">
            <div class="label">Error Rate</div>
            <div class="value {'red' if error_rate > 5 else 'green'}">{error_rate}%</div>
        </div>
        <div class="card">
            <div class="label">Fallbacks</div>
            <div class="value amber">{fallbacks}</div>
        </div>
    </div>

    <div class="three-col">
        <div class="section">
            <h2>LLM Providers</h2>
            {provider_html or '<p style="color:#94a3b8">No data yet</p>'}
        </div>
        <div class="section">
            <h2>Top Locations</h2>
            {location_html or '<p style="color:#94a3b8">No data yet</p>'}
        </div>
        <div class="section">
            <h2>Browsers / Devices</h2>
            {browser_html or '<p style="color:#94a3b8">No data yet</p>'}
        </div>
    </div>

    <div class="section">
        <h2>Recent Sessions</h2>
        <table>
            <thead>
                <tr>
                    <th>Session</th>
                    <th>Location</th>
                    <th>Device</th>
                    <th>Messages</th>
                    <th>First Seen</th>
                    <th>Last Seen</th>
                </tr>
            </thead>
            <tbody>
                {session_rows or '<tr><td colspan="6" style="padding:16px;color:#94a3b8">No sessions yet</td></tr>'}
            </tbody>
        </table>
    </div>

    <div class="two-col">
        <div class="section">
            <h2>Most Asked Questions</h2>
            {top_q_html or '<p style="color:#94a3b8">No data yet</p>'}
        </div>
        <div class="section">
            <h2>Recent Errors</h2>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Question</th>
                        <th>Error</th>
                    </tr>
                </thead>
                <tbody>
                    {error_rows or '<tr><td colspan="3" style="padding:16px;color:#94a3b8">No errors - looking good!</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <div class="section">
        <h2>Recent Questions</h2>
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Question</th>
                    <th>Provider</th>
                    <th>Latency</th>
                    <th>Location</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {recent_rows or '<tr><td colspan="6" style="padding:16px;color:#94a3b8">No questions yet</td></tr>'}
            </tbody>
        </table>
    </div>
</body>
</html>"""

    return HTMLResponse(html)
