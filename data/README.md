# data/ — the database

This directory **is** the database. The daily pipeline (FRD §7) writes here and
commits; the git history of these files is OpenPitch's audit log (BRD NFR-01).

```
companies/<id>.json              one resolved profile per company (FRD §3.3)
claims/<company>/*.json          atomic extracted claims (FRD §3.1)
history/<company>/<metric>.jsonl append-only metric history (FRD §3.4)
sources/registry.json            learned source reliability (FRD §3.6)
events/feed.jsonl + YYYY-MM-DD   the push/integration feed (FRD §8.5)
events/events.xml                RSS/Atom feed
digest/YYYY-MM-DD.md             "what moved today"
universe.json                    current top-50 + ranks + entries/exits
```

Generated content — do not hand-edit; the pipeline is the source of truth.
