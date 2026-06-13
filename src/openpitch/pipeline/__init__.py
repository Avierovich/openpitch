"""The daily producer pipeline (FRD §7).

Stages, each an independent/resumable module:
  1. select universe   (VC-attention score → top 50)
  2. collect           (per-source adapters)
  3. transcribe        (podcasts without published transcripts)
  4. extract           (LLM → Claims)
  5. reconcile         (Claims → ResolvedValues + history)
  6. score sources     (reliability meta-learning)
  7. publish           (JSON, history, events, digest, dashboard build)
"""
