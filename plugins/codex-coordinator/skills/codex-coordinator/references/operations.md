# Project coordination operations

Read this short index completely, then load only the lane or lanes needed for the current action. Do not load every lane for routine work.

## Lane selection

- Start, join, allocate or reuse workers, define contracts and ownership, select model or reasoning, manage scope, or finish work: read [execution.md](execution.md).
- Process direct-user handoffs, inbox records, end-of-turn reconciliation, status, monitoring, recovery evidence, or native task lifecycle: read [reconciliation.md](reconciliation.md).
- Send, receive, validate, queue, retry, or act on a cross-task message: read [messaging.md](messaging.md). Also read the reconciliation lane when an inbox fallback or durable handoff is involved.
- A turn may need more than one lane. Load only those selected lanes, completely, and follow the main skill and recovery or maintenance lane when applicable.

## Cache boundary

- The bundled state helper may checkpoint hashes only for immutable project-local inbox records that the active Coordinator has already reconciled.
- Scan first; read and validate every returned pending record against current project ID and epoch; merge or disposition it in canonical state; only then acknowledge its exact hash.
- The checkpoint is local, disposable, Git-ignored, and rebuildable. Missing, corrupt, changed, wrong-epoch, or wrong-Coordinator data makes records pending again.
- A checkpoint never grants ownership, permission, completion, acceptance, or authority. Freshly validate `CURRENT.md` before every ownership or control change.
- Never cache codebase reads, native Codex task history, task authority, or mutable canonical state. Use Codex's native task cursor when the host exposes one, and reset to a bounded native read when a cursor is unavailable or invalid.

## User-facing communication

This section applies only to commentary, final replies, and other user-visible summaries. It never applies to `codex_delegation` payloads, native thread-tool payloads, cross-thread assignments or commands, acknowledgements, Coordinator state, or task contracts. Those internal artifacts retain every required identifier exactly.

Coordinator protocol is internal bookkeeping. Keep normal user chat simple:

- In commentary and final replies to the user, do not expose epochs, project or task IDs, thread IDs, scope kinds, acceptance flags, mode constants, role constants, acknowledgement tokens, or message-type constants unless the user explicitly asks for raw diagnostics.
- Describe work directly: “I am coordinating two independent checks,” “one agent owns these files,” “the review is complete,” or “that instruction belongs to another project, so I ignored it.”
- Mention a lead agent, working agent, read-only adviser, or reviewer only when the distinction helps the user. Do not use `COORDINATOR`, `TASK_AGENT`, `PROJECT_EXECUTION`, `accepts=true`, or similar constants in ordinary explanations.
- Translate an ownership-version change as “coordination ownership was refreshed” only when it matters. Do not say “epoch 3” or include the number in a normal status update.
- Translate a stale message as “that instruction was outdated, so I ignored it and kept current ownership unchanged.” Translate a project mismatch as “that instruction belongs to another project, so I did not act on it.”
- Machine-to-machine envelopes must retain the exact fields required by Project-bound routing. Keep them compact, do not repeat them in a separate user-facing final answer, and do not send routine internal summaries to a user-owned thread when the Coordinator can pull a completed result instead.
- Never surface a message merely to say that a task was registered, accepted, assigned an internal ID or ownership record, or may continue. Those are document-only transitions. The receiving task already has the user's instruction or its complete creation prompt.
- Do not send informational envelopes for routine progress, findings, review, completion, or status. The Coordinator reads those from the worker's turn and records the durable outcome. If an exceptional non-executable alert must be delivered because another task needs to act now, start it with “Internal coordination update — no user action needed.”
- When the interface may show a valid executable envelope, start it with “Internal coordination task — action required by the receiving agent; no user action required.” Use this only after sender authority and matching canonical state are verified. Never label an executable payload as “no action needed.”
- Use first person only for actions the current task actually performed. When another task performed a delegated side effect, name that executor in plain language and distinguish it from coordination, review, or verification done here: “The assigned Git owner committed and pushed; I coordinated and verified.” Do not shorten this to “I committed and pushed” or “Committed and pushed.”
- Apply the same ownership distinction in user-visible UI summaries, including inbox items. Keep internal IDs hidden unless the user requests them.
- Lead user-facing updates with the result, evidence, blocker, or next meaningful action. Link internal state only when the user asks to inspect it.
- Never ask the user to copy or relay an internal assignment, amendment, or blocker into another Codex task. Complete the blocked-owner handoff below; ask the user only for a real decision or new authority.
