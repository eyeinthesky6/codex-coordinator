# Codex Coordinator Privacy Policy

Effective date: 21 July 2026

Codex Coordinator is an open-source plugin maintained by Six Ideas. This policy covers the plugin's own data handling. OpenAI Codex and any external service chosen by the user have their own terms and privacy policies.

## Data used by schema 2

For an explicitly enabled repository, the boundary board uses only:

- the Git repository and primary-worktree path;
- a committed project ID and fixed local state paths;
- exact native Codex task IDs supplied to the state helper;
- short task titles and bounded goals;
- repository-relative claimed paths, exclusive action names, dependency IDs, status, revisions, and timestamps.

The board does not read or store prompts, reasoning, transcript text, commentary, tool calls, tool output, source code, provider responses, private Codex databases, rollout logs, or full-turn ledgers. Native Codex remains responsible for task transcripts.

## Storage and transmission

The plugin has no publisher-operated server, account, analytics service, advertising system, data broker, or telemetry endpoint.

- `.codex/coordination/project.yaml` may be committed.
- Active claims and compact cold receipts are local and designed to remain Git-ignored.
- SessionStart reads only the marker and makes no network request.
- The state helper and Doctor make no network request.

Six Ideas does not receive local board records through the plugin.

## Model and third-party processing

The schema-2 core makes no separate model call. It runs inside the user's existing Codex session, which OpenAI processes under the user's account agreement and privacy settings. OpenAI's privacy policy is available at <https://openai.com/policies/privacy-policy/>.

If the user asks Codex to use Git hosting, web search, connectors, or another external service, that service's data practices apply. Coordinator neither monitors those providers nor grants authority to use them.

The retired observer and AI-review components are not shipped in the schema-2 base package. Their old implementation remains only in historical Git revisions. They are never imported or started by the base runtime.

## Sharing and sale

Codex Coordinator does not sell personal information, transmit local coordination data to Six Ideas, or share it with advertisers or data brokers.

## Retention and deletion

Active records move to small cold receipts at a terminal boundary. Archives are not ordinary runtime input. Users may deactivate a project while preserving all state or separately request a confirmed purge. Purge does not delete native Codex tasks or transcripts. Repository and Git history may retain files a user deliberately committed.

## Security

Schema 2 caps every board record, rejects unknown fields and unsafe paths, isolates project IDs, serializes mutations, and keeps project enablement explicit. The board is advisory metadata, not a sandbox or filesystem lock. No software can guarantee absolute security.

Report suspected vulnerabilities through <https://github.com/eyeinthesky6/codex-coordinator/security/policy>.

## Changes and contact

Material changes will be published with a new effective date. Support routes are listed at <https://github.com/eyeinthesky6/codex-coordinator/blob/main/SUPPORT.md>.
