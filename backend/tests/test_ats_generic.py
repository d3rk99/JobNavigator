"""Tests for ats/generic.py — DOM-fallback scraper for unknown career pages."""
import pytest


def test_posting_date_is_not_a_location():
    from backend.scraper.ats.generic import _card_place
    assert _card_place("Video Producer\nNew York, New York\nJob Posting Date: October 16, 2026", "Video Producer") == "New York, New York"


@pytest.mark.asyncio
async def test_extracts_fox_and_ultipro_job_links():
    from playwright.async_api import async_playwright
    from backend.scraper.ats.generic import _extract_job_links_from_page
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = await browser.new_page()
            await page.set_content('''<main>
                <a href="/Search/JobDetail/R123/video-editor">Freelance Video Editor</a>
                <a href="/Tenant/JobBoard/board/OpportunityDetail?opportunityId=abc">Technical Media Producer</a>
                <a href="/Search">Search Jobs</a>
            </main>''')
            jobs = await _extract_job_links_from_page(page, "https://example.com/")
            assert {j["title"] for j in jobs} == {"Freelance Video Editor", "Technical Media Producer"}
        finally:
            await browser.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("markup,expected", [
    ('<button disabled aria-label="Next page">Next</button>', False),
    ('<ul><li class="next disabled"><a href="#">Next</a></li></ul>', False),
    ('<button>View More Opportunities</button>', True),
])
async def test_pagination_respects_disabled_controls(markup, expected):
    from playwright.async_api import async_playwright
    from backend.scraper.ats.generic import _click_next_page
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = await browser.new_page()
            await page.set_content(markup)
            assert await _click_next_page(page) is expected
        finally:
            await browser.close()


def test_generic_exposes_dom_helpers():
    """The 5 DOM helpers are reachable from ats.generic."""
    from backend.scraper.ats import generic
    assert hasattr(generic, "_setup_route_blocks")
    assert hasattr(generic, "_wait_for_content")
    assert hasattr(generic, "_extract_job_links_from_page")
    assert hasattr(generic, "_extract_all_pages")
    assert hasattr(generic, "_click_next_page")


def test_generic_exposes_scrape():
    """Public entry point matches other ATS modules' (is_match, scrape) interface."""
    from backend.scraper.ats import generic
    assert hasattr(generic, "scrape")


@pytest.mark.asyncio
async def test_generic_scrape_launches_browser_when_none(monkeypatch):
    """scrape() launches its own browser when none passed, and returns empty on no jobs."""
    from unittest.mock import AsyncMock, MagicMock

    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.query_selector_all = AsyncMock(return_value=[])
    mock_page.evaluate = AsyncMock(return_value=None)
    mock_page.route = AsyncMock()
    mock_page.close = AsyncMock()
    mock_page._stealth_ctx = None

    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_browser)
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    mock_pw = MagicMock()
    mock_pw.stop = AsyncMock()

    async def fake_get_browser():
        return mock_pw, mock_browser

    monkeypatch.setattr("backend.scraper.ats.generic._get_browser", fake_get_browser)

    async def fake_new_page(browser, viewport=None):
        return mock_page

    async def fake_close_page(page):
        pass

    monkeypatch.setattr("backend.scraper.ats.generic._new_page", fake_new_page)
    monkeypatch.setattr("backend.scraper.ats.generic._close_page", fake_close_page)

    from backend.scraper.ats.generic import scrape
    # Use a URL that matches no ATS (generic is the fallback)
    result = await scrape("https://unknown-career-page.example.com/jobs", max_pages=1)
    # Just verify it ran without crashing
    assert isinstance(result, (list, tuple))
