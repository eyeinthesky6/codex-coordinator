# Codex Coordinator Privacy Policy

Effective date: 19 July 2026

Codex Coordinator is an open-source plugin maintained by Six Ideas. This policy describes the
plugin's own data handling. OpenAI Codex and any third-party service a user chooses to access have
their own terms and privacy policies.

## Data the plugin uses

Codex Coordinator uses local information needed to coordinate work in repositories where the user
enables it. Depending on the feature used, that information can include:

- repository paths and Git worktree metadata;
- Codex task titles, status, timing, and bounded native event metadata;
- Coordinator project markers, task contracts, handoff records, and declared write paths;
- local Mission Control settings and Doctor result receipts; and
- a capped, redacted task-contract summary when the user explicitly starts AI Review.

Regular Doctor does not read application source code or task transcript bodies. AI Review is
separate, user-triggered, and limited to the allowlisted summary described in the project
documentation.

## Where data is stored

The plugin has no publisher-operated server, account system, analytics service, advertising system,
or telemetry endpoint.

- A repository may contain a small committed `.codex/coordination/project.yaml` marker.
- Other coordination records are local to the repository and are designed to remain Git-ignored.
- Mission Control preferences and Doctor receipts are stored in the operating system's local
  application-data directory.
- Mission Control binds to `127.0.0.1` and accepts localhost requests only.

Six Ideas does not receive these local records through the plugin.

## Model and third-party processing

Most Coordinator behavior follows instructions inside the user's existing Codex session. OpenAI
processes that session under the agreement and privacy choices for the user's OpenAI account.

Regular Doctor is deterministic and uses no model call. When the user explicitly starts AI Review,
Codex receives a capped and redacted task-contract packet. The packet excludes literal project and
task identifiers, repository roots, file paths, URLs, transcripts, application code, configuration,
environment data, skills, and memories. Six Ideas does not receive the packet or the model response.

If a user asks Codex to use Git hosting, web search, connectors, or another external service, that
service's data practices apply to the user's chosen action. Codex Coordinator does not grant itself
authority to use those services.

OpenAI's current privacy policy is available at
<https://openai.com/policies/privacy-policy/>.

## Sharing and sale

Codex Coordinator does not sell personal information. It does not transmit local coordination data
to Six Ideas or share it with advertisers or data brokers.

## Retention and deletion

Users control the local files created by the plugin. To remove them, users can disable Coordinator
for a repository, delete that repository's local Git-ignored coordination state, remove Mission
Control's local application-data directory, and uninstall the plugin. Repository history may retain
the public project marker or any records a user deliberately committed.

## Security

The plugin is designed to keep mutable coordination state local, bind Mission Control to the
loopback interface, and preserve Codex approval and sandbox boundaries. No software can guarantee
absolute security. Please report suspected vulnerabilities through the private route in
<https://github.com/eyeinthesky6/codex-coordinator/security/policy>.

## Changes and contact

Material changes to this policy will be published with an updated effective date. Questions can be
raised through the project's support routes:
<https://github.com/eyeinthesky6/codex-coordinator/blob/main/SUPPORT.md>.
