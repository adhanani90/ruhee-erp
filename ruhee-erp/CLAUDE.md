@AGENTS.md

# Claude Code notes

- You work in Sam's development bench. `<bench>/apps/ruhee_erp` is this repository. You may read `apps/frappe`, `apps/erpnext` and `apps/posawesome`, but never edit them.
- Do one card per session. Start from `docs/STATUS.md` and the card, and read only the files the card points to.
- Verify before you claim. Run the code or the tests, or quote the source line. Mark anything else "unverified".
- You have no Frappe Cloud dashboard access. When a card needs the dashboard, write exact numbered steps for Sam and wait for his confirmation before assuming they happened.
- Never run destructive commands against staging or production (drop-site, reinstall, restore, `bench --force`) without Sam's explicit go-ahead in the current session.
- Treat the PR description as the session's record: what changed, what you checked, the evidence, and any open issues.
