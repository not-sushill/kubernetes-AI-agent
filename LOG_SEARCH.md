# Search and filter retained pod logs

Install: stop backend/frontend, extract this cumulative source ZIP into
D:\projects\ai-kubernetes-agent, restart both servers, then Ctrl+F5 the browser.
It includes the previous AI assistance and working container terminal features.
No new dependencies. Existing .env, databases and local backups are excluded.

Open Pods -> View Logs.

- Fetch last 1h, 6h, 12h, 24h, 48h, 7 days, or since a custom IST date/time.
- Choose 200 to 100,000 most recent lines within that window; default 5,000 with no time cutoff.
- Optionally specify a regular or init-container name.
- Select Previous container instance to request the preceding instance's logs.
- Click Load logs; it fetches a snapshot, not a continuous stream.
- Search by literal text, with optional case sensitivity.
- Error keywords matches error, exception, fatal, panic, failed or failure.
  It is a keyword filter, not a parser or diagnosis; other error formats can be missed.
- Include 0, 2, 5 or 10 lines of context around matches.
- Download the displayed filtered lines and context as a text file.

For an early-morning error: Last 24h -> 50,000 lines -> Load logs -> search by
exception name, request ID, or Error keywords. If the container restarted, also
check Previous container instance. Fetched first/last timestamps are shown in IST;
raw log timestamps and contents remain unchanged for correlation/export.

The search applies to the fetched lines ONLY. A line-cap warning means older
lines can be missing even inside your selected window. No matches does not prove
that no incident occurred. Fewer than the requested maximum also does not prove
complete historical coverage. Current-container and previous-container retrieval
errors are displayed as unavailable, not silently presented as empty success.

kubectl logs exposes retained container output and does not reconstruct rotated
files or deleted-pod history. Logs written only inside application files are not
included in stdout/stderr retrieval. For reliable overnight/longer history across
pod replacement, a central log collector and retained store must be installed or
an existing one connected. This update does not install or configure one.

Validation: 190 backend tests, 22 frontend tests and frontend production build.
Live Kubernetes log availability must be checked locally. Existing unused-import
warnings remain in Services, Ingresses and Nodes pages.

Kubernetes references:
https://kubernetes.io/docs/reference/kubectl/generated/kubectl_logs/
https://kubernetes.io/docs/concepts/cluster-administration/logging/

## Pod-switch filter correction

Log options are now scoped to the selected namespace/pod. A different pod starts
with current-instance logs, the default container, and no time cutoff, rather
than inheriting another pod's previous-instance/container filter. The viewer shows
the applied request settings separately from draft form controls. If previous logs
are unavailable, Load current container logs switches back with one click.
Kubectl stderr is surfaced (limited to 2,000 characters) to explain missing previous
instances, invalid container names or access errors. No automatic fallback masks
which instance was retrieved. Focused verification: 7 backend log tests and 3
frontend log tests, plus production frontend build.

## Keyword highlighting

Search matches are now highlighted in yellow, including repeated occurrences.
Case sensitive controls the typed query. With Error keywords enabled, matching
error words are highlighted too. Context remains visible without marking unrelated
text. Log contents are rendered as escaped text, not HTML; downloads retain the
original text without display markup.

## Log display recovery update

Use Load latest current logs (reset filters) to fetch 5,000 current-instance lines
with no time cutoff or named-container override. This also clears search filters.
Quiet containers can have retained output older than the previous 24-hour default.

Search now highlights in the full fetched set by default. Enable Show matching
lines only to filter to matches and context. Show all fetched logs clears the
search without changing the fetched snapshot. Output is paged at 500 lines to
bound highlighted rendering; Next page exposes later lines. Download displayed
set exports the whole selected set, not only the current page.

The exact reported blank screen was not reproduced from live user data. Mounted
component tests verify normal logs, highlighted matches, explicit filtering,
reset, and later pages. Five focused frontend tests and production build pass.
