# JobNavigator operating playbook

Research checked October 16, 2026. Recommendations below are tailored to this fork's local Ollama and Discord setup. Suggested changes are distinguished from settings already applied.

## Communities and support

- [JobNavigator issues](https://github.com/vesaias/JobNavigator/issues): report reproducible application bugs, with sanitized logs and version/commit. The upstream repository currently has GitHub Discussions disabled.
- [Author's r/coolgithubprojects discussion](https://www.reddit.com/r/coolgithubprojects/comments/1wbhvql/jobnavigator_selfhosted_job_search_and_track_suite/): practical questions and implementation discussion. This is a discussion thread, not a dedicated support group.
- [Author's r/SideProject discussion](https://www.reddit.com/r/SideProject/comments/1wbh1bt/jobnavigator_selfhosted_job_search_suite/): context about the project and scraper maintenance.
- [JobSpy issues](https://github.com/speedyapply/JobSpy/issues): problems with the underlying keyword-search library. Diagnose whether a failure belongs here or in JobNavigator first.

I could not verify a dedicated official JobNavigator Discord or Slack community. Do not treat unrelated Discord servers as official support.

## Current operating baseline

- Four keyword searches: video editor, video producer, broadcast engineer and broadcast producer; nationwide US, including remote and onsite opportunities. LinkedIn and Indeed each request 20 results, looking back 72 hours, on the six-hour global schedule.
- All four keyword searches passed live runs with 40 listings seen each. There is overlap between searches and boards; counts are not unique opportunities.
- Levels.fyi: US video search, two pages, relevant video/broadcast title filters, twelve-hour interval. Fixed its newer opaque job IDs; a direct live scrape returned 15 listings and a sampled detail contained a description and employer application URL. The complete app run passed and imported six jobs matching the title filters.
- Ollama qwen2.5:7b on the local GPU; Light scoring, scoring/tailoring concurrency one, provisional notification threshold 70. One actual Light score completed successfully.
- Discord notifications and daily digest configured. Digest cron is 15:00 UTC: 9 a.m. Denver during daylight time and 8 a.m. during standard time.
- LinkedIn Personal was subsequently re-enabled by the user. Its session now passes sign-in, but a live preview returned zero jobs; the recommended collection visibly reported "No matching jobs found." The separate session used for extension imports was also refreshed successfully. Jobright remains paused because no account exists.
- Chrome extension 2.2.0 is installed and its dashboard presence marker was verified. Both extension inboxes are enabled with Light scoring; LinkedIn capture has video/broadcast title filters. A real popup-to-backend import remains to be verified. In the popup, confirm Connected, enable LinkedIn capture, browse LinkedIn collections, then send the captured jobs to JobNavigator.

## Recommended next improvements, in priority order

1. **Add selected employers' career pages.** Choose 10–20 broadcast, media, university athletics or esports employers you would actually accept. Use a supported ATS feed when available, relevant title filters and the real base résumé. Validate one manual run before scheduling. Start at six hours; consider a shorter interval only for priority employers. This is my proposed starting cadence, not a universal rate limit.
2. **Review a sample before broadening discovery.** Mark 10–20 results as useful or irrelevant. Check employer, location, seniority, start-date compatibility and real requirements. Adjust queries and exclusions from those decisions. A model score is a ranking aid, not a hiring probability.
3. **Use Full scoring selectively.** Keep cheap Light scoring for incoming listings; use Full reports, tailoring and cover letters for saved roles worth pursuing. Consider separate editing/production and broadcast résumés using only verified experience.
4. **Expand one query at a time.** Candidate terms are videographer, multimedia producer, creative producer and esports production. Measure relevant new jobs after a week before keeping each search. Avoid a large batch of overlapping searches that only creates duplicate scores and notifications.
5. **Keep human review before submitting applications.** Review generated claims, eligibility answers and attachments. Automate discovery, ranking, drafts and reminders first. Do not invent metrics, skills or employment history.
6. **Review health and persistence.** Check failed/empty sources in Monitor; empty results can also mean a quiet feed. Keep Docker Desktop running for local schedules. Verify a local backup and restore procedure; database/settings backups contain credentials and personal information. Set a dashboard API key and the same key in the extension before expanding access beyond the current local setup.

The [official getting-started guide](https://github.com/vesaias/JobNavigator/blob/main/docs/GETTING-STARTED.md) supports modest board result counts, multiple base résumés, Light/Full scoring choices, company-level filters and manual validation before scheduled searches. The steps above apply that guidance to this installation.

## Dependency upgrade worth testing separately

This fork pins python-jobspy 1.1.82. [JobSpy 1.3.0 release notes](https://github.com/speedyapply/JobSpy/releases/tag/v1.3.0) describe fixes to age, remote/hybrid and nationwide results, plus internal API changes. They also state that LinkedIn's logged-out search ignores remote and job-type filters. Verify arrangement and employment type in the listing itself.

Do not assume an upgrade will resolve a site's HTTP 403 response. Test an upgrade in an isolated image against this fork's search adapter, schema, dependencies and all enabled boards before replacing the working runtime. No dependency upgrade was applied as part of this research.
