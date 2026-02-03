#!/usr/bin/env python
"""Fit a simple MRP-style multinomial model and poststratify."""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder


def load_data(path: pathlib.Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found at {path}.")
    return pd.read_csv(path)


def build_design_matrix(df: pd.DataFrame, encoder: OneHotEncoder | None = None):
    features = df[["age_group", "gender", "region"]].astype(str)
    if encoder is None:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse=False)
        matrix = encoder.fit_transform(features)
    else:
        matrix = encoder.transform(features)
    return matrix, encoder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--survey", required=True)
    parser.add_argument("--population", required=True)
    parser.add_argument("--polls")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    survey = load_data(pathlib.Path(args.survey), "Survey data")
    population = load_data(pathlib.Path(args.population), "Population benchmarks")

    X, encoder = build_design_matrix(survey)
    y = survey["vote_intent"].astype(str)

    model = LogisticRegression(
        multi_class="multinomial",
        max_iter=1000,
        solver="lbfgs",
    )
    model.fit(X, y)

    pop_matrix, _ = build_design_matrix(population, encoder)
    pop_predictions = model.predict_proba(pop_matrix)

    party_labels = model.classes_.tolist()
    pop_pred_df = pd.DataFrame(pop_predictions, columns=party_labels)
    pop_pred_df["population"] = population["population"].values
    pop_pred_df["region"] = population["region"].values

    if args.polls:
        polls = load_data(pathlib.Path(args.polls), "Polling averages")
        poll_row = polls.iloc[0]
        for party in party_labels:
            if party in polls.columns:
                poll_share = poll_row[party] / 100.0
                model_share = (pop_pred_df[party] * pop_pred_df["population"]).sum()
                model_share /= pop_pred_df["population"].sum()
                if model_share > 0:
                    adjustment = poll_share / model_share
                    pop_pred_df[party] *= adjustment
        # Renormalize after adjustment
        totals = pop_pred_df[party_labels].sum(axis=1)
        pop_pred_df[party_labels] = pop_pred_df[party_labels].div(totals, axis=0)

    region_shares = (
        pop_pred_df.groupby("region")[party_labels + ["population"]]
        .apply(
            lambda df: (df[party_labels].multiply(df["population"], axis=0)).sum()
            / df["population"].sum()
        )
        .reset_index()
    )

    national = (
        pop_pred_df[party_labels].multiply(pop_pred_df["population"], axis=0).sum()
        / pop_pred_df["population"].sum()
    )

    output_dir = pathlib.Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    region_shares.to_csv(output_dir / "party_shares_by_region.csv", index=False)
    national.to_frame(name="share").reset_index().rename(columns={"index": "party"}).to_csv(
        output_dir / "national_vote_share.csv", index=False
    )

    diagnostics = {
        "classes": party_labels,
        "n_obs": int(survey.shape[0]),
        "n_cells": int(population.shape[0]),
    }
    (output_dir / "model_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
