# Codex Coordinator Privacy Policy

Effective date: 23 July 2026

Codex Coordinator is an open-source plugin maintained by Six Ideas. This policy covers the plugin's own data handling. OpenAI Codex and any external service chosen by the user have their own terms and privacy policies.

## Data used by schema 2

For an explicitly enabled repository, the boundary board uses only:

- the Git repository and primary-worktree path;
- a committed project ID and fixed local state paths;
- exact native Codex task IDs supplied to the state helper;
- short task titles and bounded goals;
- repository-relative claimed paths, exclusive action names, dependency IDs, status, revisions, and timestamps.

The board does not read or store prompts, reasoning, transcript text, commentary, tool calls, tool output, source code, provider responses, private Codex databases, rollout logs, or full-turn ledgers. Native Codex remains responsible for task transcripts. A native assignment or terminal return with no visible receipt may leave one routing-only pending record containing project, assignment, kind, sender, recipient, repository, creation time, and pending state; it contains no task content or result.

## Storage and transmission

The plugin has no publisher-operated server, account, analytics service, advertising system, data broker, or telemetry endpoint.

- `.codex/coordination/project.yaml` may be committed.
- Active claims, routing-only pending delivery records, and compact cold receipts are local and designed to remain Git-ignored.
- SessionStart reads the marker and may count recognized pending-delivery filenames for the exact current task. It reads no record body and makes no network request.
- UserPromptSubmit reads the pending prompt and current working directory only to require and compare one local `GOAL_ASSIGNMENT` `Repository:` with the task's Git worktree. It stores and transmits nothing.
- The state helper and Doctor make no network request.

Six Ideas does not receive local board records through the plugin.

## Model and third-party processing

The schema-2 file runtime makes no separate model call. Goal supervision uses the user's existing Codex task and native task tools, which OpenAI processes under the user's account agreement and privacy settings. The appointed goal Coordinator sets one native Codex pin after its goal and claim are active; the plugin stores no separate pin record, and only the user removes that pin. If the user explicitly requests unattended goal supervision, Codex may store and run one temporary heartbeat attached to that Coordinator task. The heartbeat names only the exact known assignments needed to continue the goal; the plugin does not copy it into repository state. It is removed when the goal completes, stops, needs a user decision, or can no longer verify those assignments. OpenAI's privacy policy is available at <https://openai.com/policies/privacy-policy/>.

If the user asks Codex to use Git hosting, web search, connectors, or another external service, that service's data practices apply. Coordinator neither monitors those providers nor grants authority to use them.

The retired observer and AI-review components are not shipped in the schema-2 base package. Their old implementation remains only in historical Git revisions. They are never imported or started by the base runtime.

## Sharing and sale

Codex Coordinator does not sell personal information, transmit local coordination data to Six Ideas, or share it with advertisers or data brokers.

## Retention and deletion

Active claim records move to small cold receipts at a terminal boundary. Pending delivery records are deleted after verified native receipt or recipient action and are not archived. Archives are not ordinary runtime input. Cold receipts remain only in the user's local project until the user runs the confirmed purge operation or removes them through their own repository-retention process. Users may deactivate a project while preserving all state or separately request a confirmed purge. Purge does not delete native Codex tasks or transcripts. Repository and Git history may retain files a user deliberately committed.

## Security

Schema 2 caps every board record, rejects unknown fields and unsafe paths, isolates project IDs, serializes mutations, and keeps project enablement explicit. The board is advisory metadata, not a sandbox or filesystem lock. No software can guarantee absolute security.

Report suspected vulnerabilities through <https://github.com/eyeinthesky6/codex-coordinator/security/policy>.

## Changes and contact

Material changes will be published with a new effective date. Support routes are listed at <https://github.com/eyeinthesky6/codex-coordinator/blob/main/SUPPORT.md>.
