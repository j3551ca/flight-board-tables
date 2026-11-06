# Configuration

Start with the [starter configuration](../starter/flight-board-config.yml). Unknown settings fail with an error so a typo cannot silently change the board.

## Board and source

| Setting | Default | Meaning |
| --- | --- | --- |
| `source` | `board.csv` | CSV, JSON array of objects, or Markdown table |
| `title` | `DEPARTURES → PIPELINE STATUS` | Main header |
| `team` | empty | Organization or team name beneath the header |
| `subtitle` | empty | Optional smaller line beneath the team |
| `footer` | empty | Optional explanation beneath the rows |
| `columns` | inferred | Source fields to display, in order |
| `buttons` | none | Optional linked navigation signs |
| `output_dir` | `assets/flight-board` | Dedicated directory for generated files |
| `readme` | `README.md` | File whose marked block is updated; empty disables it |
| `board_link` | source file | URL/path opened when someone clicks the board |
| `table_index` | `0` | Which Markdown table to read, counting from zero |
| `uppercase` | `true` | Render cell values and column labels in uppercase |

Paths stay inside the workspace, including symlink resolution. Use a dedicated output directory: the example workflow stages that directory. Relative `board_link` and button URLs are resolved by GitHub relative to the README, while source/output/config paths are relative to the workspace root. Use HTTPS for external links.

The source table remains untouched. The generated assets are `board.png`, `board.gif`, and optional `sign-1.png` through `sign-6.png`. Removing buttons removes obsolete generated sign files. Other files in the output directory are left alone.

CSV supports quoted cells and embedded newlines. JSON rows must have matching field names and scalar values (strings, numbers, booleans, or null). Quote date-like values in YAML. Markdown link labels are shown without their URLs; explicit `<br>` breaks are preserved. Use the source link to access full text and hyperlinks.

## Using a subfolder

The data and configuration can live anywhere inside your repository. GitHub requires the workflow itself to be directly in `.github/workflows/`.

For example:

```text
.github/workflows/flight-board.yml
monitoring/board.csv
monitoring/flight-board-config.yml
README.md
```

In `monitoring/flight-board-config.yml`:

```yaml
source: monitoring/board.csv
team: Your Team
output_dir: monitoring/assets  # Optional; defaults to assets/flight-board
```

In your workflow, point the Action to the configuration:

```yaml
- uses: j3551ca/flight-board-tables@v2
  with:
    config: monitoring/flight-board-config.yml
```

Update that workflow's push filters:

```yaml
paths:
  - monitoring/board.csv
  - monitoring/flight-board-config.yml
  - .github/workflows/flight-board.yml
```

All filesystem paths resolve from the **repository root**. Moving the configuration does not change that base. The default README remains the root `README.md`; set `readme` if you want a different file. Button URLs and an explicit `board_link` remain relative to whichever README displays them.

## Columns

```yaml
columns:
  - field: Last successful run  # Exact source key, including case
    label: LAST SUCCESS / UTC  # Optional display label
    width: 18                  # Character slots per line
    animate: false             # Keep this value visible throughout the GIF
```

No column names have special behavior. Nothing converts time zones, abbreviates programs, rewrites statuses, or interprets dates. Supply the exact display text you want. Widths can be 4–80 characters; labels and values wrap automatically, and row heights grow to fit their longest cell. Long unbroken tokens wrap too. Content is never silently truncated.

Omit the entire `columns` list to show every field in source order, with widths inferred between 8 and 24 characters. To show only a subset, list that subset. Source hyperlinks and nonselected details remain in the linked source file.

## Airport signs

```yaml
buttons:
  - label: Documentation
    url: docs/guide.md
    icon: ▤
    arrow: ↗
  - label: Runs
    url: https://github.com/YOUR-ORG/YOUR-REPO/actions
    icon: ◆
    arrow: →
```

Zero to six signs are supported. They share one evenly spaced row, automatically adjusting widths to their count. Three is a practical default for legibility. Labels can wrap to two lines; very long labels produce an error rather than clipping. Icons are text glyphs in the bundled font, so use simple symbols such as `▤`, `◆`, or `⚙`. Arrow options are `↑ ↗ → ↘ ↓ ↙ ← ↖`. Omit `icon` or `arrow` to use `◆` and `↗`.

Remove this section or set `buttons: []` to remove all signs. The board moves up naturally without an empty navigation row.

## Animation

```yaml
animation:
  enabled: true
  rounds: 3
  max_cells: 4
  min_rotations: 3
  max_rotations: 6
  frames_per_flip: 6
  frame_ms: 60
  pause_ms: 4000
  seed: 27
```

These are the defaults. `max_cells` limits simultaneous whole values, not letters. All letters in a selected cell begin together and settle independently. The seed makes regeneration deterministic for unchanged inputs. Change it for a different choreography.

One round lasts up to `max_rotations × frames_per_flip × frame_ms` milliseconds, followed by a still pause. There is also an initial still pause. GIF frame durations are stored in hundredths of a second, so prefer multiples of 10 ms. The encoder may merge identical frames without changing their combined duration.

Set `enabled: false` under `animation` to show the PNG in the README. A single-frame GIF is still generated for consumers expecting that filename. If all columns are protected, the GIF is static regardless of the enabled setting.

## Theme

```yaml
theme:
  font_size: 22
  background: '#111921'
  panel: '#1b2732'
  card: '#293946'
  edge: '#3d4c58'
  text: '#f5edda'
  accent: '#f0c66a'
  muted: '#c1ced8'
```

Quote hex colors in YAML. The board scales to the README width. For readability, use fewer columns or shorter display values instead of shrinking the font excessively. The bundled font supports Latin, Greek and Cyrillic, but not all scripts or emoji.

## CLI and Action inputs

The CLI has only three arguments (plus `--help`):

| Argument | Purpose |
| --- | --- |
| `--config` | Select the YAML configuration file. |
| `--workspace` | Select the repository root; defaults to the current directory. |
| `--validate-only` | Check configuration, data, and layout without writing files. |

All board settings live in YAML. Unspecified settings use the documented defaults.

The Action has **one input**, `config`, defaulting to `flight-board-config.yml`. All board settings belong in that file. For example:

```yaml
- uses: j3551ca/flight-board-tables@v2
  with:
    config: flight-board-config.yml
```

The Action and local CLI use the same entry point and configuration.

**Previously used `flightboard-tables` or `flightboard_template`?** Change the workflow reference to `j3551ca/flight-board-tables@v2`. GitHub does not redirect Action references after a repository rename.

**Migrating from v1:** move `source`, `title`, `team`, `output-dir` (as `output_dir`), and `readme` inputs into YAML. Replace `no-animation` with `animation: {enabled: false}`, `no-buttons` with `buttons: []`, and `no-readme` with `readme: ''`. The existing v1 tags remain available.

Outputs: `assets-dir`, `readme` (empty if disabled), and `image`. The Action uses an isolated Python environment on Linux runners. Local rendering also works on macOS and Windows with Python 3.11+.

## README updates and limits

Place these markers wherever you want the board:

```html
<!-- flight-board:start -->
<!-- flight-board:end -->
```

Only that block is replaced. With no markers, a block is appended. Duplicate, missing, or reversed markers fail without overwriting the README. For a README that should never be edited, set `readme: ''` and embed the generated assets yourself.

The renderer caps input at 5 MB / 100 rows, cell text at 2,000 characters, board width at 4,000 pixels, and still size at six megapixels. Animation is limited to 220 million total palette-frame pixels to keep memory reasonable. Exceeding a limit produces guidance to reduce rows, widths, font size or animation rounds. Large inventories belong in a linked source table with a smaller summary board.
