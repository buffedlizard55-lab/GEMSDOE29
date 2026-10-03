# DrivenData access-policy review — 2026-10-03

## Official page reviewed

[DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) was fetched at the user's express request to inspect chunks 1 and 2 (the full page has four fetch chunks). The rendered page says **Last Modified: August 7, 2014**. This is a transcription of the relevant parts, not legal advice; the live official page controls if it changes.

Under **“Prohibited Uses”**, the page says users agree not to:

> “Use any robot, spider or other automatic device, process or means to access the Website for any purpose, including monitoring or copying any of the material on the Website.”

It also says:

> “Use any manual process to monitor or copy any of the material on the Website or for any other unauthorized purpose without our prior written consent.”

The same section separately prohibits actions that could disable, overburden, damage, impair, or interfere with the site or other users. The Terms define use of DrivenData's website broadly, including its content, functionality, and services. They also state that the Terms and applicable competition rules form the agreement governing use.

## Project decision

- **No bot, crawler, browser automation, scheduled request, API poll, leaderboard scraping, or automatic score-feed update** will be built for `drivendata.org`.
- We will not automatically fetch or copy the leaderboard, competition pages, forum, data-download page, or submission endpoint.
- We will not manually monitor/copy leaderboard content into project files without prior written consent from DrivenData. No such consent is present in this workspace.
- A public hyperlink may be provided for the user to open the official page directly; the local site must not embed its contents or claim a fresh score snapshot.
- The requested “current feed” will be a **project-local evidence/status feed** generated only from this repository's own dated research, preregistrations, experiments, review receipts, and release/deploy state. It will explicitly say it is not a DrivenData leaderboard feed and show its local last-updated date.
- Score claims already supplied by the owner/user remain labelled “reported, not organizer-verified.” A link to the official leaderboard is not evidence that a particular account, file, score, or submission relationship has been verified.

## Source link

- DrivenData, [Terms of Use](https://www.drivendata.org/termsofuse/) — relevant clause is in “Prohibited Uses.” The page as fetched displayed the 2014-08-07 last-modified date.

## Access audit for this continuation

The requested Terms page was fetched once for policy verification. A public web search also returned a search-result excerpt from the official problem-description URL while researching the official metric/format source; no leaderboard URL, data-download endpoint, forum, account, or submission endpoint was requested or fetched in this continuation. Do not repeat page reads to monitor current values. The user specifically directed a Terms review, but this project has no written authorization from DrivenData for repeated monitoring or copying.
