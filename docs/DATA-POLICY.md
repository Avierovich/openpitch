# Data Policy

## Purpose

OpenPitch only works if users trust the data process. This policy defines what sources are allowed, what is excluded, and how corrections are handled.

## 1. Allowed Sources

Preferred sources:

- regulatory filings and official public registries;
- company press releases and public blog posts;
- reputable news coverage;
- public podcast episodes and published transcripts;
- public company websites and careers pages;
- public investor announcements;
- public event pages, reports, or presentations;
- public GitHub or package-registry signals where relevant.

Sources should be durable, linkable, and legal to access without bypassing authentication.

## 2. Disallowed Sources

Do not use:

- leaked private documents;
- confidential investor memos;
- paywalled content copied into the repo;
- auth-walled scraping;
- personal LinkedIn scraping at scale;
- private Discord/Slack messages;
- material obtained by deception;
- full copyrighted transcripts or articles.

If a fact is only available in a paid article, OpenPitch may cite the article URL and extracted fact if legally appropriate, but should not republish the article text.

## 3. Transcript Policy

Podcasts are a major source, but transcript handling must be conservative.

Allowed:

- link to the episode;
- store timestamp locators;
- store short raw phrases needed to support a claim;
- store derived structured claims.

Avoid:

- storing full transcripts;
- republishing long copyrighted passages;
- using unofficial transcript dumps with unclear rights.

Published transcripts should be preferred. Local transcription is a fallback for extraction, not a reason to republish source text.

## 4. Robots.txt And ToS

Adapters should:

- prefer official APIs and RSS feeds;
- respect rate limits;
- avoid aggressive scraping;
- use descriptive user agents where required;
- skip sources that clearly disallow automated access.

OpenPitch should be boringly conservative here. A slower source is better than a legal or reputational problem.

## 5. Source Quality Requirements

Every claim should store:

- source type;
- source name;
- URL or durable locator;
- published date when available;
- extraction date;
- raw phrase or locator supporting the metric;
- confidence.

If a source lacks a date, the claim may still be stored, but confidence and freshness should reflect the uncertainty.

## 6. Correction Policy

Anyone can request a correction by providing public evidence.

A correction request should include:

- company;
- metric;
- value being challenged;
- proposed value or status;
- public source URL;
- explanation of why the current value is wrong, stale, or misleading.

Accepted corrections must preserve history. Values should not be silently overwritten.

## 7. Takedown And Dispute Policy

If a company, source owner, or individual disputes a claim:

1. Acknowledge the dispute.
2. Ask for public evidence or clarification.
3. Review source links and methodology.
4. Update value/confidence/contradiction state if warranted.
5. Keep the audit trail visible.

If a source link or excerpt creates a copyright issue, remove the excerpt and keep a factual citation where appropriate.

## 8. Disclaimers

OpenPitch is public-source, probabilistic intelligence. It is not audited financial data and not investment advice.

Users should verify material figures before relying on them for investment, legal, employment, or commercial decisions.

## 9. Policy For MENA Data

MENA coverage has lower disclosure density than US/global AI startup coverage. No EDGAR equivalent exists across the region, and public metric claims may be rarer.

MENA data should therefore:

- be clearly labeled by segment;
- use lower confidence where sources are thinner;
- prefer regional public outlets and official registries;
- avoid implying parity with US filing-backed coverage.
