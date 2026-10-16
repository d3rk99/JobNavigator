"""Discord transport tests: real HTTP request construction with no external DMs."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.notifier import discord, notifications


@pytest.fixture
def transport(monkeypatch):
    calls = []
    responses = []
    real_client = httpx.AsyncClient

    def handler(request):
        import json
        calls.append((request, json.loads(request.content)))
        if responses:
            status, body = responses.pop(0)
            return httpx.Response(status, json=body)
        return httpx.Response(200, json={"id": "123456789012345678"})

    monkeypatch.setattr(discord, "DISCORD_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(discord, "_settings", lambda: (True, "234567890123456789"))
    monkeypatch.setattr(discord.httpx, "AsyncClient", lambda **kw: real_client(
        transport=httpx.MockTransport(handler), **kw))
    return calls, responses


@pytest.mark.asyncio
async def test_opens_personal_dm_then_sends_without_mentions(transport):
    calls, _ = transport
    assert await discord._send_message("A role @everyone")
    assert calls[0][0].url.path == "/api/v10/users/@me/channels"
    assert calls[0][1] == {"recipient_id": "234567890123456789"}
    assert calls[0][0].headers["Authorization"] == "Bot fake-token"
    assert calls[1][0].url.path == "/api/v10/channels/123456789012345678/messages"
    assert calls[1][1] == {"content": "A role @everyone", "allowed_mentions": {"parse": []}}


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["open", "send"])
async def test_blocked_dms_are_failures(transport, stage):
    calls, responses = transport
    if stage == "send":
        responses.append((200, {"id": "123"}))
    responses.append((403, {"code": 50007}))
    assert not await discord._send_message("hello")
    assert len(calls) == (1 if stage == "open" else 2)


@pytest.mark.asyncio
async def test_test_message_does_not_claim_success_on_failure(transport, monkeypatch):
    transport[1].append((401, {}))
    activity = AsyncMock()
    monkeypatch.setattr("backend.activity.log_activity", activity)
    with pytest.raises(RuntimeError, match="Discord DM failed"):
        await discord.send_test_message()
    activity.assert_not_called()


@pytest.mark.asyncio
async def test_disabled_transport_and_missing_config_do_not_send(transport, monkeypatch):
    monkeypatch.setattr(discord, "_settings", lambda: (False, "234567890123456789"))
    assert not await discord._send_message("disabled")
    assert await discord._send_message("explicit test", test=True)
    transport[0].clear()
    monkeypatch.setattr(discord, "DISCORD_BOT_TOKEN", "")
    assert not await discord._send_message("missing token", test=True)
    monkeypatch.setattr(discord, "DISCORD_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(discord, "_settings", lambda: (True, "bad/id"))
    assert not await discord._send_message("invalid recipient")
    assert not transport[0]


@pytest.mark.asyncio
async def test_rate_limits_retry_and_stop(transport, monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(discord.asyncio, "sleep", sleep)
    transport[1].extend([(429, {"retry_after": 0.1})] * 3)
    assert not await discord._send_message("hello")
    assert len(transport[0]) == 3
    assert sleep.await_count == 2


@pytest.mark.asyncio
async def test_long_unicode_messages_are_split_without_data_loss(transport):
    content = "😀" * 2100
    assert await discord._send_message(content)
    chunks = [p["content"] for _, p in transport[0][1:]]
    assert "".join(chunks) == content
    assert all(len(c.encode("utf-16-le")) // 2 <= 2000 for c in chunks)


@pytest.mark.asyncio
async def test_network_failure_is_safe(transport, monkeypatch):
    monkeypatch.setattr(discord, "_post", AsyncMock(side_effect=httpx.ConnectError("secret")))
    assert not await discord._send_message("hello")


@pytest.mark.asyncio
async def test_job_email_and_health_payloads(monkeypatch):
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(discord, "_send_message", send)
    job = SimpleNamespace(company="Example", title="Engineer", location="Denver", remote=True,
                          salary_min=100000, salary_max=120000, cv_scores={"Resume": 90},
                          url="https://example.com/jobs/1")
    await discord.send_job_alert({"job": job, "best_score": 90})
    assert "90% fit" in send.call_args.args[0]
    assert job.url in send.call_args.args[0]
    await discord.send_email_alert({"company": "Example", "type": "interview", "snippet": "Let's talk"})
    assert "Let's talk" in send.call_args.args[0]
    await discord.send_health_alert(["Example"])
    assert "3 consecutive failures" in send.call_args.args[0]


@pytest.mark.asyncio
async def test_dispatch_attempts_discord_when_telegram_raises(monkeypatch):
    monkeypatch.setattr(notifications.telegram, "send_job_alert", AsyncMock(side_effect=RuntimeError()))
    send = AsyncMock()
    monkeypatch.setattr(notifications.discord, "send_job_alert", send)
    with pytest.raises(RuntimeError, match="Notification delivery failed"):
        await notifications.send_job_alert({"best_score": 90})
    send.assert_awaited_once_with({"best_score": 90})


def test_discord_settings_default_to_off(test_db):
    assert discord._settings() == (False, "")
    from backend.models.db import Setting
    test_db.add_all([Setting(key="discord_enabled", value="true"),
                     Setting(key="discord_user_id", value="234567890123456789")])
    test_db.commit()
    assert discord._settings() == (True, "234567890123456789")


@pytest.mark.asyncio
@pytest.mark.parametrize("delivered", [True, False])
async def test_digest_records_success_only_after_delivery(test_db, monkeypatch, delivered):
    from backend.models.db import Setting, ActivityLog
    test_db.add(Setting(key="discord_enabled", value="true"))
    test_db.commit()
    # PostgreSQL JSON expression is covered by test_digest_strong_match_sql;
    # SQLite supports the remaining real aggregation queries in this test.
    monkeypatch.setattr(discord, "STRONG_MATCH_SQL", "1 = :threshold")
    send = AsyncMock(return_value=delivered)
    monkeypatch.setattr(discord, "_send_message", send)
    if delivered:
        await discord.send_digest()
    else:
        with pytest.raises(RuntimeError, match="digest delivery failed"):
            await discord.send_digest()
    assert "New jobs: 0" in send.call_args.args[0]
    assert test_db.query(ActivityLog).filter(ActivityLog.type == "discord").count() == int(delivered)


def test_user_id_validation_rejects_numeric_json_values():
    from backend.seed import invalid_setting_values
    assert invalid_setting_values({"discord_user_id": "234567890123456789"}) == []
    assert invalid_setting_values({"discord_user_id": ""}) == []
    assert invalid_setting_values({"discord_user_id": 234567890123456789})
    assert invalid_setting_values({"discord_user_id": "not-a-user"})


def test_settings_preserve_snowflake_digits(test_db):
    from backend.models.db import Setting
    from backend.api.routes_settings import get_settings
    user_id = "234567890123456789"
    test_db.add(Setting(key="discord_user_id", value=user_id))
    test_db.commit()
    assert get_settings(db=test_db)["discord_user_id"] == user_id


def test_test_endpoint_reports_delivery_failure(api_client, monkeypatch):
    send = AsyncMock(return_value={"message": "Test DM sent"})
    monkeypatch.setattr(discord, "send_test_message", send)
    response = api_client.post("/api/discord/test")
    assert response.status_code == 200
    assert response.json() == {"message": "Test DM sent"}
    send.side_effect = RuntimeError("Discord DM failed; check settings")
    response = api_client.post("/api/discord/test")
    assert response.status_code == 502
    assert "check settings" in response.json()["detail"]


@pytest.mark.asyncio
async def test_matched_email_notifies_once_after_status_is_saved(test_db, monkeypatch):
    from backend.email_monitor import gmail_client as gmail
    from backend.models.db import Job, Application
    job = Job(external_id="discord-email-test", company="Example", title="Engineer")
    test_db.add(job)
    test_db.flush()
    app = Application(job_id=job.id, status="applied")
    test_db.add(app)
    test_db.commit()
    monkeypatch.setattr(gmail, "_get_access_token", AsyncMock(return_value="fake-gmail"))
    monkeypatch.setattr(gmail, "_build_gmail_query", lambda db: "test")
    monkeypatch.setattr(gmail, "classify_email", lambda *args: {"classification": "positive", "confidence": 1})
    monkeypatch.setattr(gmail, "_match_email_to_application", lambda *args: app)
    monkeypatch.setattr(gmail, "_extract_body", lambda payload: "Interview invitation")
    real_client = httpx.AsyncClient

    def handler(request):
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "email-1"}]})
        return httpx.Response(200, json={"payload": {"headers": [
            {"name": "From", "value": "recruiter@example.com"},
            {"name": "Subject", "value": "Interview"}]}})

    monkeypatch.setattr(gmail.httpx, "AsyncClient", lambda **kw: real_client(
        transport=httpx.MockTransport(handler), **kw))
    send = AsyncMock(side_effect=RuntimeError("Discord unavailable"))
    monkeypatch.setattr(notifications, "send_email_alert", send)
    await gmail.check_emails()
    assert app.status == "interview"
    send.assert_awaited_once_with({"company": "Example", "role": "Engineer",
                                  "type": "positive", "snippet": "Interview invitation"})
    await gmail.check_emails()
    assert send.await_count == 1
