#!/usr/bin/env python
"""Normalize polling data for use as a national adjustment."""

from __future__ import annotations

import argparse
import pathlib

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--polls", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--recent-days", type=int, default=30)
    args = parser.parse_args()

    polls_path = pathlib.Path(args.polls)
    if not polls_path.exists():
        raise FileNotFoundError(
            f"Polling data not found at {polls_path}. Add polls.csv first."
        )

    df = pd.read_csv(polls_path)
    df["fieldwork_end"] = pd.to_datetime(df["fieldwork_end"], errors="coerce")

    cutoff = df["fieldwork_end"].max() - pd.Timedelta(days=args.recent_days)
    recent = df[df["fieldwork_end"] >= cutoff].copy()

    party_columns = [
        column
        for column in df.columns
        if column not in {"pollster", "fieldwork_start", "fieldwork_end", "sample_size"}
    ]

    if recent.empty:
        raise ValueError(
            "No polls within the requested window. Adjust --recent-days or add data."
        )

    weights = recent["sample_size"].fillna(0)
    weighted = (recent[party_columns].multiply(weights, axis=0)).sum()
    weighted_total = weights.sum()

    if weighted_total == 0:
        raise ValueError("Polling sample sizes sum to zero.")

    averages = (weighted / weighted_total).to_frame().T
    averages["window_start"] = cutoff.date().isoformat()
    averages["window_end"] = recent["fieldwork_end"].max().date().isoformat()

    output_path = pathlib.Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    averages.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
