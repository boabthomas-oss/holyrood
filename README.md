# Scottish Parliament Election MRP Starter

This repository provides a minimal, offline-friendly starter kit for building a
multilevel regression and poststratification (MRP) model for the upcoming
Scottish Parliament election using:

- **Scottish Election Study (SES)** survey microdata (download separately)
- **Ongoing polling** (national/region polls you maintain locally)
- **Population benchmarks** for poststratification (e.g., census or NRS tables)

Because the execution environment cannot access GitHub directly, the workflow is
built around **local CSV inputs** that you download from
<https://github.com/ScottishElectionStudy> and polling sources on your own
machine, then place into `data/`.

## Quick start

1. **Install dependencies** (use a virtual environment):

   ```bash
   pip install -r requirements.txt
   ```

2. **Download SES data** and place the raw file in `data/`.
   Update `config/data_sources.yaml` with the filename and column mappings.

3. **Add polling data** as `data/polls.csv` (template in
   `config/polling_template.csv`).

4. **Prepare the modeling dataset**:

   ```bash
   python scripts/check_inputs.py --config config/data_sources.yaml
   python scripts/prepare_ses_data.py --config config/data_sources.yaml --out data/processed_ses.csv
   python scripts/prepare_polling_data.py --polls data/polls.csv --out data/processed_polls.csv
   ```

5. **Fit MRP and poststratify**:

   ```bash
   python scripts/fit_mrp.py \
     --survey data/processed_ses.csv \
     --population data/population_benchmarks.csv \
     --polls data/processed_polls.csv \
     --out data/mrp_outputs
   ```

## Data inputs

## Required files (please provide or place locally)

To run the pipeline, I need the following files from you (or for you to place
in `data/` and confirm the paths in `config/data_sources.yaml`):

1. **SES survey microdata** (CSV) — the Scottish Election Study dataset you want
   to model (e.g., `data/SES_2024.csv`). This must include respondent ID, age,
   gender, region, and vote intention columns (mapped in `config/data_sources.yaml`).

2. **Polling data** (CSV) — ongoing polling in the format of
   `config/polling_template.csv` saved as `data/polls.csv` (or update the config
   path).

3. **Population benchmarks** (CSV) — poststratification table with at least
   `age_group`, `gender`, `region`, and `population`, saved as
   `data/population_benchmarks.csv` (or update the config path).

If you want me to proceed end-to-end, please upload these files here or tell me
where to fetch them so I can load them into the pipeline.

### SES survey microdata
Download the relevant SES dataset from the Scottish Election Study GitHub org
and save it locally (e.g., `data/SES_2024.csv`). Use
`config/data_sources.yaml` to map the dataset's column names onto the variables
needed for the model.

### Polling data
Use `config/polling_template.csv` as a template for tracking ongoing polling
(weekly or daily). The polling adjustment in `fit_mrp.py` is intentionally
lightweight: it computes recent national vote intention averages and shifts the
MRP predictions accordingly.

### Population benchmarks
Provide a `data/population_benchmarks.csv` with at least the following columns:

- `age_group`
- `gender`
- `region`
- `population`

You can extend the benchmarks to include other poststrat dimensions (e.g.,
education or 2016 vote) by updating `config/data_sources.yaml` and the
corresponding scripts.

## Outputs

The final model writes:

- `data/mrp_outputs/party_shares_by_region.csv`
- `data/mrp_outputs/national_vote_share.csv`
- `data/mrp_outputs/model_diagnostics.json`

## Notes

- The scripts are designed to be **transparent and editable** rather than a
  single black-box pipeline.
- The modeling approach uses a **multinomial logit with hierarchical-style
  effects approximated via grouped features**. You can swap in a fully Bayesian
  engine (e.g., PyMC, Stan) if desired.
