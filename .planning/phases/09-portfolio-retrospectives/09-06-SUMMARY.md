# 09-06 Summary

Completed the inline concentration-risk follow-through in the league drill-in.

- Added `ConcentrationAlertBanner`.
- Wired it to existing `/portfolio/exposure` data.
- Mounted the banner in `league.$leagueId` using the current user's roster player IDs.

Verification:

- `cd frontend && npx tsc --noEmit`
- `cd frontend && npm run build`
