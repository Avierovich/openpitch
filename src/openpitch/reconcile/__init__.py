"""Confidence model + reconciliation engine (FRD §4–5) — the hard, valuable core.

  confidence.py  multiplicative confidence (tier × speaker × qualifier × decay)
                 + corroboration (FRD §4)
  engine.py      cluster claims → weighted estimate + range + contradiction flag,
                 append history, never overwrite (FRD §5)
  reliability.py source-reliability meta-learning (FRD §5.4)
  implied.py     self-anchored / qualitative implied estimates (FRD §5.5; v1 scope)

To implement next — this is the recommended first build target since the MCP
server and dashboard are just readers on top of what this produces.
"""
