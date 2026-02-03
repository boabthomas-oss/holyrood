#!/usr/bin/env python3
"""Build polling rows from processed SCOOP tracker data."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import pandas as pd

DEFAULT_URL = "https://github.com/ScottishElectionStudy/Scottish_Opinion_Monitor"
DEFAULT_PARTY_CONFIG = "config/party_columns.json"


def load_template_columns(path: Path) -> list[str]:
    header = pd.read_csv(path, nrows=0)
    return list(header.columns)


def infer_group_column(df: pd.DataFrame) -> pd.Series:
    if "wave" in df.columns:
        return df["wave"].astype(str)
    if "interview_date" in df.columns:
        dates = pd.to_datetime(df["interview_date"], errors="coerce")
        return dates.dt.to_period("M").astype(str)
    return pd.Series(["unknown"] * len(df))


def load_party_config(path: Path) -> tuple[list[str], str]:
    config = json.loads(path.read_text(encoding="utf-8"))
    return config["parties"], config.get("dk_label", "DK/NA")


def compute_vote_shares(
    df: pd.DataFrame,
    vote_col: str,
    weight_col: str | None,
    parties: list[str],
    dk_label: str,
) -> tuple[dict[str, float], int]:
    filtered = df[df[vote_col].notna()].copy()
    filtered = filtered[filtered[vote_col] != dk_label]
    if weight_col and weight_col in filtered.columns:
        weights = filtered[weight_col].fillna(0)
    else:
        if weight_col:
            warnings.warn(
                f"Weight column '{weight_col}' missing; using unweighted counts.",
                stacklevel=2,
            )
        weights = pd.Series(1, index=filtered.index)
    total_weight = weights.sum()
    shares: dict[str, float] = {}
    for party in parties:
        party_weight = weights[filtered[vote_col] == party].sum()
        shares[party] = round((party_weight / total_weight) * 100, 2) if total_weight else 0.0
    return shares, int(filtered.shape[0])


def build_polls(
    input_path: Path,
    output_path: Path,
    template_path: Path,
    party_config_path: Path,
    url: str = DEFAULT_URL,
) -> pd.DataFrame:
    df = pd.read_csv(input_path)

    df = df.copy()
    df["_group"] = infer_group_column(df)

    ballot_columns = []
    if "vote_constituency_std" in df.columns:
        ballot_columns.append(("constituency", "vote_constituency_std"))
    elif "vote_constituency" in df.columns:
        ballot_columns.append(("constituency", "vote_constituency"))

    if "vote_list_std" in df.columns:
        ballot_columns.append(("list", "vote_list_std"))
    elif "vote_list" in df.columns:
        ballot_columns.append(("list", "vote_list"))

    weight_col = "weight" if "weight" in df.columns else None
    if weight_col is None:
        warnings.warn("Weight column not found; using unweighted counts.", stacklevel=2)

    parties, dk_label = load_party_config(party_config_path)
    # Ensure fixed party columns for downstream MRP workflows.
    rows = []
    for group_value, group_df in df.groupby("_group"):
        fieldwork_end = None
        if "interview_date" in group_df.columns:
            max_date = pd.to_datetime(group_df["interview_date"], errors="coerce").max()
            if pd.notna(max_date):
                fieldwork_end = max_date.date().isoformat()
        for ballot_name, vote_col in ballot_columns:
            shares, sample_size = compute_vote_shares(
                group_df,
                vote_col,
                weight_col,
                parties,
                dk_label,
            )
            row = {
                "wave": group_value,
                "ballot": ballot_name,
                "pollster": "YouGov",
                "client": "Scottish Election Study",
                "source": "SCOOP tracker",
                "url": url,
                "fieldwork_end": fieldwork_end,
                "sample_size": sample_size,
            }
            row.update({party: shares.get(party, 0.0) for party in parties})
            rows.append(row)

    result = pd.DataFrame(rows)
    template_columns = load_template_columns(template_path)
    for column in template_columns:
        if column not in result.columns:
            result[column] = pd.NA
    result = result[template_columns]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build polling rows from SCOOP tracker data.")
    parser.add_argument(
        "--input",
        default="data/processed/scoop_tracker.csv",
        help="Path to processed SCOOP tracker CSV",
    )
    parser.add_argument(
        "--output",
        default="data/polls.csv",
        help="Output polling CSV path",
    )
    parser.add_argument(
        "--template",
        default="config/polling_template.csv",
        help="Polling template CSV path",
    )
    parser.add_argument(
        "--party-config",
        default=DEFAULT_PARTY_CONFIG,
        help="Party configuration JSON path",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Source URL to include in output",
    )
    args = parser.parse_args()

    build_polls(
        Path(args.input),
        Path(args.output),
        Path(args.template),
        Path(args.party_config),
        url=args.url,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
