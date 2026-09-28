# IST, table sorting, and navigation state

This complete frontend includes the blue theme and earlier history fixes.

- Formatted timestamps use Asia/Kolkata and show IST. Backend timestamps with no
  offset are interpreted as UTC, consistent with the existing backend. Raw logs
  and evidence retain their original content.
- Click any data-column header to sort ascending; click again for descending.
  Restarts sort numerically, statuses alphabetically, and dates chronologically.
  Action columns are excluded. History sorts the loaded page; use its filters
  to search all saved records.
- Inline pod investigation state now lives above the page routes. Switching to
  another screen and returning retains the selected pod, pending state, error,
  or completed result. No automatic extra investigation is submitted.
- Full browser reloads or closing a tab do not retain in-memory pending state.
  Completed runs are available in persisted Investigation History.

Install: stop Next.js, merge this frontend directory into the project, preserve
your environment configuration, then run:

```powershell
npm ci
node --test tests/*.cjs
npm run build
npm run dev
```

Expected: six regression tests pass. Production build also checked during
packaging. Three existing unused-import warnings and the test renderer's
deprecation notice are not build errors.

Acceptance:
1. In Pods, click Restarts twice and confirm largest restart counts first.
2. Click Status and Name and verify order.
3. Check an investigation timestamp displays IST (UTC+05:30).
4. Start an inline pod investigation, open Deployments, then return to Pods.
   It should still be running or display the result if already finished.
5. Open the saved result and confirm it remains in History.
