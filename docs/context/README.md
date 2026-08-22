# Durable Project Context

This directory is the compact desktop handoff for `player-defense-score`. It captures decisions and operating constraints that are important but cannot be reconstructed reliably from source code alone.

## Reading order

- `current_state.md`: exact migration-time checkpoint and next task.
- `decisions_and_invariants.md`: architectural rules that future work must preserve.
- `working_agreement.md`: how to collaborate safely with Ryan and Git.
- `validation_history.md`: reviewed quantitative milestones.
- `roadmap.md`: completed and planned phases.
- `source_map.md`: traceability back to Git, transcripts, attachments, and migration evidence.

The repository README remains the public project overview. `docs/pipeline_generalization.md` remains the detailed authority for the generalized player-coordinate workflow.

## Archive boundary

The six full browser transcripts, raw conversation JSON, attachment manifest, and account-export ZIP are archival evidence, not runtime prompt material. They should remain outside Git because they are large, contain repetitive historical commands, and may reference local paths, copyrighted footage, or transient download links.

When a historical detail matters, locate it through `source_map.md`, then verify it against the current repository or reviewed artifacts before acting.

## Migration snapshot

- Context snapshot date: 2026-08-22 (America/Phoenix)
- ChatGPT project ID: `g-p-6a79418b44a48191a8a902c2ceb0f859`
- Archived chats: 01–06
- User attachments accounted for: 119 of 119
- Separate browser Sources: none
- Local ignored data files hashed: 856 of 856
- Repository context migration: merged through PR #7 at `1f086ba`
