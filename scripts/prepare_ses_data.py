#!/usr/bin/env python
"""Prepare Scottish Election Study microdata for MRP modeling."""

from __future__ import annotations

import argparse
import pathlib

import pandas as pd
import yaml


def load_config(path: pathlib.Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def normalize_columns(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    missing = [value for value in mapping.values() if value not in df.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(
            f"Missing required columns in SES data: {missing_str}. "
            "Update config/data_sources.yaml to match the dataset."
        )
    renamed = df.rename(columns={value: key for key, value in mapping.items()})
    return renamed[list(mapping.keys())]


def bucket_age(series: pd.Series) -> pd.Series:
    bins = [17, 24, 34, 44, 54, 64, 120]
    labels = [
        "18-24",
        "25-34",
        "35-44",
        "45-54",
        "55-64",
        "65+",
    ]
    return pd.cut(series, bins=bins, labels=labels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    config = load_config(pathlib.Path(args.config))
    survey_cfg = config["survey"]
    survey_path = pathlib.Path(survey_cfg["path"])

    if not survey_path.exists():
        raise FileNotFoundError(
            f"SES data not found at {survey_path}. Download it and update the config."
        )

    df = pd.read_csv(survey_path)
    df = normalize_columns(df, survey_cfg["columns"])

    df["age_group"] = bucket_age(df["age"])
    df["gender"] = df["gender"].str.strip().str.title()
    df["region"] = df["region"].str.strip().str.title()
    df["vote_intent"] = df["vote_intent"].str.strip().str.upper()

    output_path = pathlib.Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
