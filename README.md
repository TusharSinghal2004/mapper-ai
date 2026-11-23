# Integration Atlas

A plain-language case study: can an AI assistant work with these 100 apps?

## Open it locally (Windows)

From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/serve.py
```

Open http://localhost:8000. The page explains the results without requiring technical knowledge. Every app record visibly lists its category and one-line purpose, exact authentication methods, access requirements, API coverage, existing MCP, buildability, blocker, source URLs, confidence, and check date. Numbered links beside each field point to the shared app references. Field-by-field claim support still requires a human audit. Paygent Connect has no established official source and is visibly flagged.

## Run the real Composio workflow

Copy `.env.example` to `.env` and add your Composio project key. `.env` is excluded from Git and the source ZIP. Never put a real key in `.env.example`.

```powershell
.\.venv\Scripts\python.exe scripts/research.py --transport composio --limit 5
.\.venv\Scripts\python.exe scripts/research.py --transport composio --limit 100
```

You can also double-click `start-local.cmd` to open the local server.

The **Recheck 5 apps** button uses the local server to check Zendesk, Google Ads, Ahrefs, QuickBooks, and Consensus. The server reads the key locally. It never sends the key to the browser. The page and command line share a process lock, so only one research run can be active at a time.

### What Composio actually does

1. Load the project key from the private `.env` file.
2. Use the installed **Composio Python SDK** to create a user-scoped session with `mcp=True`.
3. Connect the official **MCP Python client** to the returned session URL using the SDK-provided headers.
4. Discover the session tool list at runtime. Call **COMPOSIO_REMOTE_WORKBENCH** over MCP to fetch the official documentation URLs already in the dataset. Individual vendor apps are explicitly disabled; no customer accounts are connected.
5. Run a fixed Python page-reader in the hosted workbench. It fetches in bounded batches, strips HTML, saves source hashes, and returns up to 12,000 characters of readable text per page.
6. Transfer larger results as compressed chunks to avoid stdout-preview truncation. Verify a SHA-256 hash after reconstruction. Preserve the Composio log IDs and the actual tool responses.
7. Save evidence and possible review leads. A keyword mention is a lead, not proof of a claim. Delete the temporary Composio session after the run.

The recorded 100-app Composio run retrieved 207 of 226 source URLs, covering 93 apps through 72 MCP workbench calls. The seven retrieval gaps were Salesforce, Discord, Coda, Binance, Paygent Connect, PitchBook, and Otter AI. The full run is preserved in `dist/composio-full-run.json` and `dist/composio-full-results.json`, even after a new sample check. These counts measure evidence collection, not claim accuracy.

The workflow **really uses both Composio's SDK and MCP**. It currently refreshes known sources; it does not independently discover documentation across the open web. An exploratory catalog lookup returned no Composio Search tools for this project, so the working path uses the discovered hosted workbench. No vendor actions are executed. No new LLM framework is needed.

Optional extraction: add `OPENAI_API_KEY` to `.env` and run with `--extract`. This reuses the original structured-extraction function, asks for source quotes, and checks quote presence. Candidate findings are saved separately; reviewed app records are never overwritten automatically. A quote match or a successful page fetch is not an accuracy score. The optional extraction path has not been exercised unless a run's results contain `candidateFindings`.

## Proof and files

- `dist/apps.json`: all 100 reviewed app records, source URLs and uncertainty notes.
- `data/first-pass.json`: the initial consolidated research snapshot.
- `dist/verification.json`: 10 targeted follow-up checks by AI, not humans.
- `dist/composio-status.json`: actual latest run status, counts, SDK versions and Composio log IDs.
- `dist/composio-results.json`: the latest evidence returned through Composio MCP.
- `data/composio-runs/`: timestamped evidence, raw tool receipts, errors and source hashes. Failed runs are kept.
- `data/evidence/`: original AI researchers’ official-doc search and read logs.
- `scripts/research.py`: original direct-fetch pipeline; still runnable without Composio.
- `.agents/skills/composio/`: repository-local Composio skill installed with the user-requested command.

The original 100-app study used three AI researchers and ordinary web tools. Composio was added afterward and run as a real evidence-refresh stage. The page distinguishes those stages. No human audit or authenticated vendor integration test is claimed.

The first Composio batch exposed truncated workbench stdout. The corrected version transfers compressed chunks and verifies their hash. Both the failed and successful receipts remain in the run history.

## Deploy the case study on Vercel

Push this `atlas` folder as your GitHub repository, or select `atlas` as Vercel's Root Directory when uploading the parent folder. Choose **Other** as the framework and **dist** as the Output Directory. No build command is required. `vercel.json` includes the static output configuration.

Vercel hosts the case study, saved findings, and recorded evidence. The one-click research button runs only with `scripts/serve.py` on your computer; a static Vercel page cannot launch the local Python process. Visitors can still view all research and download the runnable source. Do not add your Composio key to client-side code.

## Understanding the research decisions

- **Looks ready to build** (`buildable`): documented software tools and a plausible developer access route. Permission and usage limits still apply.
- **Possible, with conditions** (`conditional`): a material payment, admin, production review, or scope requirement must be met.
- **Runs on your computer** (`local`): a command-line tool, rather than a cloud account connection.
- **Not yet clear** (`unknown`): insufficient evidence.

Access is the primary credential path; trial and real-customer-data conditions appear in the notes. Authentication methods can overlap. Confidence is a qualitative research judgment, not a measured probability. Missing MCP evidence does not mean no MCP server exists.

Human checkpoints: resolve ambiguous vendor names, confirm subscription entitlements, personally read the selected sources, and try credential issuance. Accuracy across all 100 apps has not been statistically measured.

## Rebuild the portable source download

```powershell
.\.venv\Scripts\python.exe scripts/package.py
```

The packager uses an explicit file allowlist. It excludes `.env`, installed packages, Git metadata and caches. It never changes research results. `scripts/assemble.py` documents the original consolidation and requires the three research JSON files from the parent folder; it is not needed to rerun Composio research.

## App logos and visual identity

The overview, statistics, findings, glossary, workflow, verification, navigation, and app headers share dark navy backgrounds, light text, and mint-green accents. All 100 records include a local visual mark: 78 marks from Composio’s public logo library, 21 matching website icons, and a clearly labeled initials placeholder for unresolved Paygent Connect. Asset origins and hashes are in `dist/logos.json`; files are in `dist/assets/logos/`. These identify the apps and do not imply endorsement. The page does not depend on a remote image service at runtime. Refresh the assets with `python scripts/fetch_logos.py`.

## Research downloads

The main data download is `dist/integration-atlas.xlsx`: a formatted Excel workbook containing all 100 apps, readable column widths, wrapped text, compact row heights, frozen headings and app names, filterable tables, and an Evidence tab with 226 clickable documentation URLs. A missing-source row explicitly flags Paygent Connect. Plain CSV and developer JSON remain available separately.

`scripts/export_xlsx.mjs` rebuilds the workbook using the Codex-bundled Artifact Tool. `scripts/patch_excel_links.py` adds native Excel hyperlink elements after export because the bundled renderer does not implement HYPERLINK formulas. The export contains plain cell values and native hyperlinks, with no formulas needed for navigation.
