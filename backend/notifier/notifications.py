"""Route pipeline notifications to configured transports."""
import logging

from backend.notifier import telegram, discord

logger = logging.getLogger("jobnavigator.notifications")


async def _dispatch(method, *args):
    failures = []
    for transport in (telegram, discord):
        try:
            await getattr(transport, method)(*args)
        except Exception:
            logger.warning("%s notification failed (%s)", transport.__name__, method)
            failures.append(transport.__name__)
    if failures:
        raise RuntimeError("Notification delivery failed: " + ", ".join(failures))


async def send_job_alert(data):
    await _dispatch("send_job_alert", data)


async def send_email_alert(data):
    await _dispatch("send_email_alert", data)


async def send_digest():
    await _dispatch("send_digest")
