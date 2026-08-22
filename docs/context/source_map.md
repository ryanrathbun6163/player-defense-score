# Source Map

## Authority map

| Subject | Primary authority | Supporting archive |
|---|---|---|
| Public purpose, current pipeline, roadmap | GitHub `main` README after PR #6 | Chat 06 post-export delta |
| Stage order and modes | `src/pipeline/planner.py` | Chats 05–06 |
| Manifest/path contract | `src/pipeline/possession.py`, `configs/*_pipeline.json` | Chat 05 |
| Execution/resume behavior | `src/pipeline/execution.py`, tests | Chats 05–06 |
| Gate rules | `src/pipeline/generalization_gate.py`, `docs/pipeline_generalization.md` | Chats 05–06 |
| Possession 003 result | `configs/possession_003_generalization_evidence.json` | Chat 06 |
| Git history | repository commits and merged PRs | transcripts only for rationale |
| Generated local evidence | ignored `data/` tree plus hash manifest | attachment/archive manifests |
| Collaboration and Git rules | `AGENTS.md`, `working_agreement.md` | Chat 05 opening checkpoint |

## Conversation map

| Chat | Durable contribution |
|---|---|
| 01 — Project Setup, Video Prep & RF-DETR Detection | Project goal, learning context, environment setup, first clip, RF-DETR detection, ByteTrack tracking. |
| 02 — Tracking, Team Classification & Player ReID | Tracking audit, court filtering, uniform features, team classification, OSNet embeddings, early ReID segmentation. |
| 03 — ReID Validation & Final Player Track Consolidation | ReID decisions, ten-player identity consolidation, visualization, calibration development, terminal camera-motion failure analysis. |
| 04 — Court Calibration, Player Coordinates & Trajectory Refinement | Stable court motion, coordinate export, visualization, audited trajectory correction/interpolation, Possession 001 baseline. |
| 05 — Pipeline Generalization & Multi-Possession Validation | Hardcoding audit, manifest/runner design, review gates, Possession 002 failures, explicit workflow rules. |
| 06 — Possession 003 Validation & Generalization Gate Completion | Possession 002 completion, Possession 003 full run, empirical gate pass, PR #5 closeout, README PR #6 post-export delta. |

## Migration archive

The external migration package contains:

- six raw exported conversation objects plus the chat-06 live delta;
- six readable active-path transcripts;
- a manifest for 119 exported user attachments;
- a manifest for 38 historical `sandbox:/...` artifact links;
- proof that the browser Sources tab was empty;
- a SHA-256 manifest for all 856 files in the local ignored `data/` tree;
- generated-package checksums.

Original account-export ZIP SHA-256:

`BBB7BCC3E7F0C0B01229B8DE2C3522AA87259DD5456165050766F3B61B245C97`

The original ZIP remains the binary source of truth and should not be modified or discarded.

## Historical artifact rule

The transcripts contain 38 assistant-generated download links. They are evidence that an artifact once existed, not proof that it remains current or complete. Reconcile any needed artifact against current source files, Git commits, configs, local outputs, and hashes. Do not rebuild the repository by replaying old ZIP commands.
