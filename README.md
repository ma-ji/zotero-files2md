# zotero-files2md

Export file attachments (for example PDF, Word, HTML, CSV, images) stored in a Zotero library to Markdown using [Docling](https://github.com/docling-project/docling), driven entirely through the official Zotero Web API via [PyZotero](https://github.com/urschrei/pyzotero).

## Features

- Uses Zotero Web API (no direct database access required)
- Authenticates with a Zotero API key (user or group libraries supported)
- Discovers imported file attachments with optional collection/tag filters (collection **keys**)
- Downloads eligible attachments (imported files only) and converts them to Markdown via Docling
- Organises exported Markdown by parent item and attachment titles
- Supports dry-run mode, overwrite behaviour, chunk-size tuning
- Provides both a CLI and a Python API for programmatic usage

## Requirements

- Python 3.11+
- A Zotero Web API key with at least read access to the target library
- The Zotero library ID (numeric)
- Network access to `https://api.zotero.org`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install .
# or for development
pip install -e .[dev]
```

### Install directly from GitHub

You can install the package without cloning:

```bash
pip install git+https://github.com/ma-ji/zotero-files2md.git#egg=zotero-files2md
```

To upgrade the package to the latest version from GitHub:

```bash
pip install --upgrade git+https://github.com/ma-ji/zotero-files2md.git#egg=zotero-files2md
```

To install a specific tag or branch, append `@ref`, for example:

```bash
pip install git+https://github.com/ma-ji/zotero-files2md.git@v0.1.0#egg=zotero-files2md
pip install git+https://github.com/ma-ji/zotero-files2md.git@main#egg=zotero-files2md
```

You can also install extras (for example, development dependencies) with:

```bash
pip install "git+https://github.com/ma-ji/zotero-files2md.git#egg=zotero-files2md[dev]"
```

## CLI Usage

```bash
zotero-files2md export \
    ./markdown-output \
    --api-key "$ZOTERO_API_KEY" \
    --library-id 123456 \
    --library-type user \
    --collection ABCD1234 \
    --tag "LLM" \
    --limit 20 \
    --chunk-size 50 \
    --overwrite \
    --option ignore_images=true \
    --log-level debug
```

### Arguments

| Argument | Description |
| --- | --- |
| `output_dir` | Directory where Markdown files will be written. Created if missing. |

### Options

| Option | Description |
| --- | --- |
| `--api-key` | Zotero Web API key (prompted if not provided; honours `ZOTERO_API_KEY`). |
| `--library-id` | Target Zotero library ID (numeric; honours `ZOTERO_LIBRARY_ID`). |
| `--library-type` | Library type (`user` or `group`). Default: `user`. |
| `--collection/-c KEY` | Filter attachments by collection key (repeatable; obtain keys via the Zotero web UI or API). |
| `--tag/-t NAME` | Filter attachments by tag name (repeatable). |
| `--limit N` | Stop after processing `N` attachments. |
| `--chunk-size N` | Number of attachments to request per API call (default 100). |
| `--overwrite` | Overwrite existing Markdown files instead of skipping. |
| `--skip-existing` | Skip downloading attachments if the target Markdown file already exists locally. |
| `--dry-run` | List target files without downloading attachments or writing Markdown. |
| `--option/-o KEY=VALUE` | Forward options to the Docling converter (currently accepted for forward compatibility; most options are not yet mapped into Docling's configuration). |
| `--log-level LEVEL` | Logging verbosity (`critical`, `error`, `warning`, `info`, `debug`). Default: `info`. |

### Markdown Output Layout

For each processed attachment:

```
output_dir/
└── <parent-item-slug>/
    └── <attachment-title-slug>.md
```

For example:

```
/exports/
└── smith-2023-foundations/
    └── appendix-a-methods.md
```

## Programmatic Usage

```python
from pathlib import Path
from zotero_files2md import export_library
from zotero_files2md.settings import ExportSettings

settings = ExportSettings(
    api_key="your-api-key",
    library_id="123456",
    library_type="user",
    output_dir=Path("./markdown-output"),
    collections={"ABCD1234"},
    markdown_options={"write_images": "true"},
    overwrite=True,
    skip_existing=False,  # Set to True to skip downloading attachments if output exists
    chunk_size=50,
)

summary = export_library(settings)
print(summary)
```

## Development

```bash
pip install -e .[dev]
pytest
```

## Notes & Limitations

- The Zotero Web API only provides access to attachments that are stored in Zotero (`imported_file` / `imported_url`). Linked file attachments (`linked_file`) are skipped automatically.
- Ensure the API key has sufficient permissions for the target library (read at minimum).
- API rate limits apply; adjust `--chunk-size` or insert breaks between runs if necessary.
- When running in `--dry-run` mode, attachments are enumerated but files are not downloaded and no Markdown is written.
- When one or more `--collection` keys are supplied, only those collections are queried (via the Zotero `collection_items` endpoint). Provide collection **keys** rather than names; you can copy the key from the Zotero web UI URL.
