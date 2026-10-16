"""Personal Discord bot DMs. Uses REST only; no public webhook or gateway needed."""
import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy import text as sa_text

from backend.config import DISCORD_BOT_TOKEN
from backend.models.db import SessionLocal, Setting, Job, Application
from backend.notifier.telegram import STRONG_MATCH_SQL, _format_salary

logger = logging.getLogger("jobnavigator.discord")
BASE_URL = "https://discord.com/api/v10"


def _settings():
    with SessionLocal() as db:
        values = {r.key: r.value for r in db.query(Setting).filter(
            Setting.key.in_(["discord_enabled", "discord_user_id"])).all()}
    return values.get("discord_enabled", "false").lower() == "true", values.get("discord_user_id", "").strip()


async def _post(client, path, payload):
    # Bound retries: a busy or unavailable Discord must not stall the pipeline.
    for attempt in range(3):
        response = await client.post(f"{BASE_URL}{path}", json=payload)
        if response.status_code != 429 or attempt == 2:
            return response
        delay = float(response.json().get("retry_after", 1))
        if not 0 <= delay <= 10:
            return response
        await asyncio.sleep(delay)


async def _send_message(content: str, *, test=False) -> bool:
    enabled, user_id = _settings()
    if not test and not enabled:
        return False
    if not DISCORD_BOT_TOKEN or not re.fullmatch(r"[0-9]{17,20}", user_id):
        logger.warning("Discord requires DISCORD_BOT_TOKEN and a numeric Discord user ID")
        return False
    try:
        async with httpx.AsyncClient(timeout=15, headers={
            "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        }) as client:
            response = await _post(client, "/users/@me/channels", {"recipient_id": user_id})
            if response.status_code != 200:
                logger.warning("Discord could not open DM (HTTP %s)", response.status_code)
                return False
            channel_id = response.json()["id"]
            # Discord content has a 2000 UTF-16 code-unit limit. Chunk conservatively
            # to leave room for emoji; never allow job/email text to ping anyone.
            for offset in range(0, len(content), 950):
                response = await _post(client, f"/channels/{channel_id}/messages", {
                    "content": content[offset:offset + 950],
                    "allowed_mentions": {"parse": []},
                })
                if response.status_code not in (200, 201):
                    logger.warning("Discord DM failed (HTTP %s); check bot access and DM privacy settings", response.status_code)
                    return False
        return True
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        # Do not log response bodies, headers or exception text containing secrets.
        logger.warning("Discord DM failed: network error or invalid API response")
        return False


async def send_job_alert(data):
    job = data.get("job")
    if not job:
        return
    await _send_message(
        f"New job — {data.get('best_score', 0)}% fit\n"
        f"{job.company} · {job.title}\n"
        f"{job.location or 'Unknown location'}{' (Remote)' if job.remote else ''}\n"
        f"Salary: {_format_salary(job.salary_min, job.salary_max)}\n"
        f"Resume scores: {job.cv_scores or 'N/A'}\n"
        f"{job.url or ''}"
    )


async def send_email_alert(data):
    await _send_message(
        f"Application response — {data.get('company', 'Unknown')}\n"
        f"Type: {data.get('type', 'Unknown')} | Role: {data.get('role', '')}\n"
        f"{str(data.get('snippet', ''))[:200]}"
    )


async def send_health_alert(sources):
    return await _send_message("Scrape health alert:\n" + "\n".join(
        f"• {source}: 3 consecutive failures/empty results" for source in sources))


async def send_digest():
    enabled, _ = _settings()
    if not enabled:
        return
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    with SessionLocal() as db:
        threshold_row = db.query(Setting).filter(Setting.key == "fit_score_threshold").first()
        threshold = int(threshold_row.value) if threshold_row else 60
        new = db.query(Job).filter(Job.discovered_at >= start, Job.status == "new").count()
        strong = db.query(Job).filter(Job.discovered_at >= start).filter(
            sa_text(STRONG_MATCH_SQL).bindparams(threshold=threshold)).count()
        active = db.query(Application).filter(Application.status.in_(["applied", "interview"])).count()
        replies = db.query(Application).filter(Application.last_email_received >= start).count()
    if not await _send_message(
        f"JobNavigator Daily — {today:%b %d}\n"
        f"New jobs: {new} | Strong matches: {strong}\n"
        f"Responses: {replies} | Active applications: {active}"
    ):
        raise RuntimeError("Discord digest delivery failed; check bot token, user ID and DM privacy settings")
    from backend.activity import log_activity
    log_activity("discord", f"Daily digest sent: {new} new jobs, {strong} strong matches")


async def send_test_message():
    if not await _send_message("JobNavigator test — Discord DM integration is working!", test=True):
        raise RuntimeError("Discord DM failed; check bot token, user ID, shared server and DM privacy settings")
    from backend.activity import log_activity
    log_activity("discord", "Test DM sent")
    return {"message": "Test DM sent"}
