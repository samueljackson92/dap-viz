# dap-viz

dap-viz is a Dash viewer for JET DAP files. A DAP file is a key/value record of the control parameters for one pulse (for example `DAP-0103169.txt`).

## Start the viewer

```bash
uv sync
uv run main.py DAP-0103169.txt --port 8050
```

Open http://127.0.0.1:8050 in a browser. Use `--port` to select a different port.

## File format

- Each line starts with a key, then one space, then the value.
- A key has the form `system/name`, for example `sl/NBRequestedPower`.
- When a line ends with `\`, the value continues on the next line.
- The parser reads the file as Latin-1 text.

## Categories

The viewer puts each value into one category. The rules apply in order. The first rule that matches sets the category.

| Category | Rule |
|---|---|
| `empty` | The value has no characters, or only spaces. |
| `error` | The value starts with `****` (a read error from the control system). |
| `numeric` | One integer or floating-point number. The viewer also sets a kind: `flag` (the family has only 0 and 1), `integer` or `float`. |
| `numeric_array` | Two or more numbers with spaces between them. |
| `hex` | A hexadecimal number, for example `0x601b64bc`. |
| `datetime` | A date or a time. |
| `dsl_waveform` | An inline waveform: `name target @ N t0 v0 t1 v1 ... [comment]`. |
| `dsl_timer` | A timer: `CLOCK: npts=N I(n@dt) P(n@dt) ...`. |
| `filepath` | An absolute path, or a file name that ends in `.cfg`, `.txt` and similar. |
| `waveform_ref` | A reference to a stored waveform: `DIR/name:version`. |
| `signal_path` | A JPF-style signal path with three or more parts, for example `pf/CPS/c1_ther/a1`. |
| `dsl_config` | A MARTe/GAM configuration block: `Key = value` with `{ }` blocks. |
| `dsl_typed_list` | A typed list: `R 1.0 I 0 C "text" ...`. |
| `categorical` | A short label that occurs three or more times, or that comes from a key family with few distinct values. |
| `identifier` | A one-word name that is not a label. |
| `text` | All other strings. |

A key family is the key with each number in the name changed to `#`. For example, `Sc/NormCtrl.c3w12` is in the family `Sc/NormCtrl.c#w#`.

## Tabs

- **Overview**: counts by category and by system.
- **Explorer**: a grid of all keys. Filter by category, system or regular expression. Click a row to see the details and a plot for that category.
- **Numerics**: plot a numeric family (a bar chart for one index, a heatmap for two or more) and the distribution of values in a system.
- **Categorical & text**: label counts and a list of text values.
- **Waveforms (DSL)**: plot inline waveforms together, timer sample intervals and waveform references.
- **Config blocks**: compare the fields of the configuration blocks in one family, and the typed lists.
- **File paths**: a treemap of the directory tree.
- **Issues**: read errors and empty values.

## Development

```bash
uv run pytest
uv run ruff format . && uv run ruff check .
uv run ty check
```

## Code layout

- `dap_viz/parser.py`: reads the file into records.
- `dap_viz/classify.py`: category rules and parsers for the DSL values.
- `dap_viz/model.py`: makes the pandas DataFrame.
- `dap_viz/app.py`: makes the Dash application.
- `dap_viz/views/`: one module for each tab, plus shared figures and the detail panel.
