# Frontend history integration fix

Merge the included frontend directory into D:\projects\ai-kubernetes-agent.
Keep your environment files. Stop and restart the Next.js process after applying.

From the frontend directory:

```powershell
npm ci
node --test tests/investigation-history.cjs
npm run build
npm run dev
```

The API base defaults to http://localhost:8000/api. Existing NEXT_PUBLIC_API_URL
or NEXT_PUBLIC_API_BASE_URL overrides should point to that same API prefix.
The backend must be running on port 8000.

Changes:
- Removed the duplicate Services navigation item.
- Inline pod investigations now POST /api/v1/investigations and are saved by
  the backend. The inline panel adapts the saved evidence and has an
  "Open saved investigation" link.
- This action is an explicit mutation, not an automatically refetched GET.
- Both investigation entry points invalidate the history query after creation.
- Existing records remain unchanged. Legacy inline requests were not persisted;
  this fix cannot recover them. Run a new investigation.

Acceptance: investigate one pod from its row, open the saved result, then open
Investigation History and confirm the same ID. Refresh the browser and confirm
it remains. No duplicate /services React warning should appear.

Verified here: TypeScript, production build, two mocked integration/regression
tests. Three pre-existing unused-import lint warnings remain in ingresses,
nodes and services pages. Live browser/API verification is still required on
your machine. Backend source changes are not needed.
