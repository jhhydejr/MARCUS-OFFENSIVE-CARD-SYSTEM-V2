# Marcus Offensive CAD v4.0.0

Primary workflow: paste one call per line, choose a card type, and generate one printable PDF packet.

Render deployment commands:

- Build: `pip install -e .`
- Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`

# Marcus Offensive CAD System v3.0.0

# Marcus Offensive CAD System v2.4.5

Executable, deterministic football play-card compilation from approved database objects.

## v2.4.1 — Canonical Call-Order Enforcement

- Enforces the Chief Engineer-approved offensive slot order:
  personnel, formation, variation, motion, shift, protection, play, tag.
- Enforces the approved defensive slot order:
  structure, front, game, pressure, blitz, coverage.
- Optional slots may be omitted, but present slots cannot move ahead of earlier slots.
- Emits explicit `CALL_ORDER_VIOLATION` blockers instead of guessing intent.
- Preserves all approved football definitions unchanged.

## v2.1.0 — Real Football Database Integration

- Builds a live index from the actual JSON football database at startup.
- Links every resolved play-call object to its stored source file when one exists.
- Keeps catalog-only objects explicit instead of inventing a source file.
- Writes `database_resolution.json` for every rendered card and hashes it in the manifest.
- Adds database integration regression tests using the target play call.
- Changes no approved football knowledge.
- 95 automated tests pass.

Executable, deterministic football play-card compilation from approved database objects.

## v2.0.5 — End-to-End Batch Pipeline

- Runs every play through the same `PipelineController.compile_play()` path used by single-play compilation.
- Isolates blocked calls so later calls continue.
- Writes a per-play `pipeline_report.json`, batch summary, validation report, and hashed batch manifest.
- Supports strict assignment mode for an entire batch.
- Changes no approved football knowledge.


## v2.0.4 — End-to-End Pipeline Controller

- Adds one `PipelineController.compile_play()` entry point for the complete call-to-card workflow.
- Runs parse/resolution, coordinates, assignments, PlayCard, DrawingScene, layout, SVG, PNG, PDF, and integrity validation.
- Writes `pipeline_report.json` for both successful and blocked calls.
- Adds the `marcus-cad run` command.
- Changes no approved football knowledge.
- 86 automated tests pass.

## v2.0.2 — Card Output Integrity

- Verifies every generated card artifact against its SHA-256 before the card is accepted.
- Rejects missing files, missing hashes, changed files, and paths outside the card output directory.
- Writes `output_integrity.json` and records its hash in `manifest.json`.
- Adds SHA-256 coverage for `validation.json`.
- Changes no approved football knowledge, geometry, assignments, or drawing rules.
- 80 automated tests pass.

## v2.0.1 — Drawing Scene Validation

- Adds executable validation for drawing-scene layer order, object counts, offensive player completeness, and assignment-binding player references.
- Writes `drawing_scene_validation.json` for every rendered card.
- Records the validation artifact and SHA-256 in the card manifest.
- Blocks rendering when the drawing scene violates the renderer contract.
- Changes no approved football definitions, coordinates, assignments, or drawing rules.

## v2.0.0 — Drawing Scene Engine

- Adds one deterministic `DrawingScene` object between the PlayCard and SVG renderer.
- Enforces the layer order: field template, defense, offense, assignments, labels/metadata.
- Renders all 11 offensive players through the scene contract.
- Writes `drawing_scene.json` for every rendered card and records its SHA-256 in the card manifest.
- Embeds drawing-scene identity and layer order in the SVG master metadata.
- Changes no approved football definitions, coordinates, assignments, or drawing rules.
- 74 automated tests pass.

## v1.9.8 — renderer-bound assignment objects

- Attaches canonical assignment IDs, types, and names directly to each rendered offensive player SVG object.
- Preserves complete assignment metadata in SVG master metadata for downstream PNG/PDF exports and validation.
- Leaves assignment attributes absent when no approved complete assignment package exists.
- Adds renderer-binding regression tests.
- Changes no approved football definitions, coordinates, or drawing rules.
- 70 automated tests pass.

## v1.9.6 milestone — canonical assignment object registry

- Adds an executable registry for assignment objects stored under `database/offense/assignments/`.
- Validates that every referenced assignment ID exists in the database.
- Enforces assignment-object approval status and player eligibility.
- Rejects duplicate assignment object IDs and malformed assignment records.
- Preserves the target play as `FORMATION_ONLY`; no routes, blocks, protections, or reads were invented.
- Changes no approved football definitions, coordinates, or drawings.
- 64 automated tests pass.

## Commands

```bash
pytest -q
PYTHONPATH=src python -m marcus_cad run "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ" --out output/pipeline
PYTHONPATH=src python -m marcus_cad compile "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"
PYTHONPATH=src python -m marcus_cad draw "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ" --out output/target
PYTHONPATH=src python -m marcus_cad draw "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ" --out output/strict --require-assignments
PYTHONPATH=src python -m marcus_cad batch examples/known_calls.txt --out output/batch
PYTHONPATH=src python -m marcus_cad certify --out output/certification
```

## Permanent operating rule

The database and executable validators are the source of truth. Assignment knowledge is loaded only from Chief-Engineer-approved assignment objects; missing football knowledge is reported, never synthesized.


## v1.9.7

Adds canonical assignment binding. Complete, approved player-to-assignment maps are bound to player objects and persisted in `assignment_bindings.json` and SVG metadata. Incomplete or unapproved maps produce no bindings and no football knowledge is inferred.


## v1.9.9

Adds one immutable PlayCard object that combines the resolved call, approved coordinates, assignment state, and validation before output generation. Each card now includes `play_card.json` and its SHA-256 in `manifest.json`.


## v2.0.3 — Play Card Layout Engine

Cards now load one approved layout contract from `styles/card_layout.json`. The engine validates title, diagram, notes, validation, and metadata regions before rendering, persists the layout and validation report with every card, and records the layout identity in SVG metadata and the card manifest.


## v2.0.6 — Release Certification Engine

- Adds `marcus-cad certify` as one repeatable release-certification command.
- Parses every project JSON file and verifies the canonical registries load.
- Verifies catalog example calls resolve without changing football knowledge.
- Compiles the approved target call through SVG, PNG, PDF, and output-integrity validation.
- Writes `certification_report.json` with `CERTIFIED` or `FAILED` status.
- 92 automated tests pass.

## v2.1.1

Adds database source-integrity validation for every resolved football object. Each card now includes `database_resolution_validation.json`; rendering stops if a recorded source file is missing, malformed, outside the project, or does not contain the resolved canonical ID.


## v2.2.0 — Approved Drawing Asset Reuse

- Validates the exact approved drawing bundle selected by each resolved play call.
- Reuses the stored SVG template and approved supporting asset files instead of recreating them.
- Fingerprints reused assets with SHA-256 and writes `asset_reuse.json` with every card.
- Stops rendering when a required registered SVG, PNG, or metadata file is missing or escapes its drawing directory.
- Preserves canonical coordinate generation from the approved formation geometry registry.
- Changes no football definitions, coordinates, assignments, or drawing rules.
- 101 automated tests pass.


## v2.2.1 Drawing Asset Inventory

Release certification now inventories every catalog drawing, verifies every approved drawing has a complete reusable asset bundle, and preserves incomplete unapproved drawings as explicit findings rather than silently certifying them.

## v2.3.0 — Database Health Engine

- Adds `marcus-cad database-health` for deterministic football database auditing.
- Detects malformed JSON, duplicate canonical definitions, broken explicit object references, circular references, and staged/orphaned objects.
- Writes `reports/database_health.json`.
- Release certification now includes database health as a required PASS check.
- Orphaned/staged objects are reported for review but are not changed or deleted automatically.



## v2.4.0 — Coach-approved call grammar

Canonical offensive order: personnel, formation, variation, motion, shift, protection, play, tag. Personnel, formation, and play are required.

Canonical defensive order: structure, front, game, pressure, blitz, coverage. Structure and coverage are required when a defensive call is supplied after `VS`.
## v2.4.2 — Numbered Call Slot Report

Every generated card now includes `call_slots.json`, which displays the Chief Engineer-approved numbered offensive and defensive call slots. Each slot is marked `PRESENT`, `OPTIONAL_OMITTED`, `MISSING_REQUIRED`, or `NOT_CALLED`. This report distinguishes optional omissions from required missing football knowledge without inventing objects.



## v2.4.3 — Scout Card vs Play Card

- Adds canonical card types `SCOUT_CARD` and `PLAY_CARD`.
- Scout cards require offensive slots 1 (personnel) and 2 (formation); slot 7 (play) is optional.
- Play cards require offensive slots 1 (personnel), 2 (formation), and 7 (play).
- Defensive requirements remain structure and coverage when a defense is called.
- `call_slots.json`, `validation.json`, and `manifest.json` record the selected card type.
- CLI `draw` and `run` commands accept `--card-type SCOUT_CARD|PLAY_CARD`.


## v2.4.4 — Batch Card-Type Enforcement

- Batch compilation now accepts one explicit card type for the entire batch.
- Scout-card batches allow offensive slot 7 to be omitted.
- Play-card batches require offensive slot 7 on every call.
- `batch_summary.json`, `validation_report.json`, and `batch_manifest.json` record the selected card type.
- CLI `batch` accepts `--card-type SCOUT_CARD|PLAY_CARD`.


## v2.4.5 — Mixed Scout/Play Card Batches

- JSON batch inputs may set `card_type` independently for each call.
- One batch may now contain both `SCOUT_CARD` and `PLAY_CARD` records.
- Each call keeps its own required-slot validation; play cards still require offensive slot 7 and scout cards do not.
- Legacy TXT files and JSON string arrays remain supported and inherit the batch default card type.
- Batch summary, validation report, and manifest record each item’s card type; the batch is labeled `MIXED` when both types are present.
- No football knowledge was changed or invented.

## Web application (Render)

This release includes a FastAPI web application with one play-call input, card-type selector, Draw button, preview, and output links.

Local start:

```bash
pip install -e .
uvicorn app:app --host 0.0.0.0 --port 8000
```

Render settings:

- Build Command: `pip install -e .`
- Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`


## v3.0.0 Consolidated Baseline

- Consolidates full v2.5.0 with patches v2.5.1 through v3.0.0.
- Includes Formation Card, Scout Card, and Play Card modes.
- Includes multiline batch generation through the simplified web interface.
- Includes approved Formation Cards, five field locations, and GUN default backfield.
- Verified with 131 passing tests and 12 approved Formation Card smoke tests.
