# results/ — evaluations, reports and archived artifacts

Everything here is a **light mirror of the experiment data** (`/data` on the training server), copied at project close with
personal paths sanitized. The complete inventory — every file of `/data` with size, mtime, SHA-256 and whether it is in this
repo, in a tarball or left out as regenerable — is `MANIFEST.md`. Internal docs are in Spanish.

| path | what it is |
|---|---|
| `TABLA_MAESTRA.md` | master table: every training run and evaluation cell of the project, with key numbers and artifact paths |
| `MANIFEST.md` | full tree of `/data` (1,597 files) with SHA-256 hashes; tarball hashes in §0 |
| `paper/` | the paper (EN/ES PDFs), `VERIFICACION_PAPER.md` (every number checked against its source artifact), figures (`figs/` ES, `figs_en/` EN) and the scripts that generate them |
| `archive/` | backup copies: final/best checkpoints of all managers and key runs (`archivo_tfg_modelos.tar.gz`), raw per-episode evaluations > 1 MB (`archivo_tfg_evals_raw.tar.gz`) and the 16 rendered episodes cited in the reports (`gifs/`) |
| `hrl_m1/` | Stage 1 — wolf-side hierarchical manager: pre-registrations, STOP reports, paired evaluations (`eval/`), cells, audits, viewing indexes and timelines |
| `hrl_d2/` | Stage D2 — drone-side manager: pre-registration, E0.4 baselines, RUN-D2 and its replication, trade-off figures, viewing index |
| `hrl_e0/` | Stage 0 — options layer validation (interface tax, decoy valley, latencies), forensic analysis that led to world v3.5 |
| `drones/`, `wolves/` | flat MARL campaigns (configs, summaries, evaluation tables, diagnostics) |
| `metro_v35/` | baselines re-measured after the v3.5 physics amendment |

Conventions used throughout: **sev** = livestock lost per episode, averaged over 100 seeds per episode type
(wolves / roe-deer / mixed); confidence intervals are 95 % bootstrap over seed-paired differences; **KNC** = fraction of
kills by a wolf never confirmed by the barrier; "STOP" = a pre-registered decision point signed off by the owner.
