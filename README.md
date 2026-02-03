# Holyrood SCOOP utilities

## Quick start (offline / proxied environments)

These scripts and tests require `pandas` and `pytest`, but the repository does **not** install
Python dependencies automatically. In restricted or offline environments, install dependencies
from a prebuilt wheel cache, a local mirror, or a managed environment such as Conda or Colab.

Example (local venv with an offline wheel cache):

```bash
python -m venv .venv
. .venv/bin/activate
pip install --no-index --find-links /path/to/wheels -r requirements.txt
```

Example (Conda):

```bash
conda create -n holyrood python=3.10 pandas pytest
conda activate holyrood
```

Once dependencies are available, run:

```bash
pytest -q
```

## Scripts

- `scripts/fetch_scoop.py`: download SCOOP wave files and `scoopTrackerLatest.dta`.
- `scripts/prepare_scoop_tracker.py`: clean tracker data into `data/processed/scoop_tracker.csv`.
- `scripts/build_polls_from_scoop.py`: aggregate tracker data into `data/polls.csv`.

## Dependency notes

- `requirements.txt` lists runtime and test dependencies.
- Optional: `requirements-dev.txt` can be used to pin development tools separately; install
  only after ensuring you have access to a package source (offline mirror, wheel cache, etc.).
- Tests assume dependencies are already installed; CI or local runs should **not** attempt
  implicit installs during test execution.
