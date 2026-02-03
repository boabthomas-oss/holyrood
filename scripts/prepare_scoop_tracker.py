#!/usr/bin/env python3
"""Prepare SCOOP tracker data from scoopTrackerLatest.dta."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

DK_LABELS = {
    "don't know",
    "dont know",
    "dk",
    "don't know/no reply",
    "refused",
    "no answer",
    "not answered",
    "na",
    "n/a",
    "none",
    "none of these",
    "would not vote",
    "won't vote",
    "prefer not to say",
    "unknown",
}

PARTY_RECODE_MAP = {
    "scottish national party": "SNP",
    "snp": "SNP",
    "labour": "LAB",
    "lab": "LAB",
    "conservative": "CON",
    "conservative and unionist": "CON",
    "tory": "CON",
    "liberal democrat": "LD",
    "lib dem": "LD",
    "libdem": "LD",
    "green": "GRN",
    "scottish greens": "GRN",
    "ukip": "OTH",
    "uk independence party": "OTH",
    "reform uk": "REF",
    "reform": "REF",
    "brexit party": "REF",
    "alba": "ALBA",
    "alba party": "ALBA",
    "independent": "OTH",
    "other": "OTH",
    "none": "DK/NA",
    "no vote": "DK/NA",
    "would not vote": "DK/NA",
    "don't know": "DK/NA",
    "dont know": "DK/NA",
    "refused": "DK/NA",
}

COLUMN_CANDIDATES = {
    "respondent_id": ["respondent_id", "resp_id", "id", "caseid", "pid"],
    "interview_date": ["interview_date", "int_date", "date", "interviewdate"],
    "age": ["age", "age_years"],
    "gender": ["gender", "sex"],
    "education": ["education", "educ", "qualification", "educ_level"],
    "region": ["region", "gor", "scot_region", "rgn"],
    "past_vote": ["past_vote", "pastvote", "p_vote", "past_vote_westminster"],
    "constitution": ["constitution", "indyref", "independence", "const_pref"],
    "vote_constituency": [
        "holyrood_constituency_vote",
        "vote_constituency",
        "constituency_vote",
        "holyrood_const_vote",
    ],
    "vote_list": [
        "holyrood_list_vote",
        "vote_list",
        "list_vote",
        "holyrood_list",
    ],
    "vote_westminster": [
        "westminster_vote",
        "vote_westminster",
        "wst_vote",
    ],
    "weight": ["weight", "wt", "weighting", "survey_weight"],
    "wave": ["wave", "scoop_wave"],
}


def normalize_label(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def find_column(columns: list[str], candidates: list[str]) -> str | None:
    lower = {col.lower(): col for col in columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return None


def standardize_gender(value: object) -> str:
    label = normalize_label(value)
    if not label:
        return "DK/NA"
    if "male" in label or label == "m" or label == "man":
        return "Male"
    if "female" in label or label == "f" or label == "woman":
        return "Female"
    if "non" in label or "other" in label:
        return "Other"
    if label in DK_LABELS:
        return "DK/NA"
    return "Other"


def standardize_region(value: object) -> str:
    label = str(value).strip()
    if not label:
        return "Unknown"
    return label.title()


def recode_party(value: object) -> str:
    label = normalize_label(value)
    if not label:
        return "DK/NA"
    if label in DK_LABELS:
        return "DK/NA"
    return PARTY_RECODE_MAP.get(label, "OTH")


def build_age_group(series: pd.Series) -> pd.Series:
    bins = [18, 25, 35, 45, 55, 65, 75, 200]
    labels = [
        "18-24",
        "25-34",
        "35-44",
        "45-54",
        "55-64",
        "65-74",
        "75+",
    ]
    return pd.cut(series, bins=bins, right=False, labels=labels)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare SCOOP tracker data.")
    parser.add_argument(
        "--input",
        default="data/raw/scoop/scoopTrackerLatest.dta",
        help="Path to scoopTrackerLatest.dta",
    )
    parser.add_argument(
        "--output",
        default="data/processed/scoop_tracker.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--profile",
        default="data/processed/scoop_tracker_profile.json",
        help="Profile JSON output path",
    )
    parser.add_argument(
        "--drop-dk",
        action="store_true",
        help="Drop DK/Refused rows from vote intention columns",
    )
    args = parser.parse_args()

    df = pd.read_stata(args.input, convert_categoricals=True)

    column_map: dict[str, str] = {}
    for key, candidates in COLUMN_CANDIDATES.items():
        matched = find_column(list(df.columns), candidates)
        if matched:
            column_map[key] = matched

    selected = {}
    for key, column in column_map.items():
        selected[key] = df[column]

    data = pd.DataFrame(selected)

    if "age" in data:
        data["age_group"] = build_age_group(data["age"])

    if "gender" in data:
        data["gender_std"] = data["gender"].map(standardize_gender)

    if "region" in data:
        data["region_std"] = data["region"].map(standardize_region)

    for vote_col in ["vote_constituency", "vote_list", "vote_westminster", "past_vote"]:
        if vote_col in data:
            raw_col = f"{vote_col}_raw"
            data[raw_col] = data[vote_col]
            data[vote_col] = data[vote_col].map(recode_party)

    if "vote_constituency" in data:
        data["vote_constituency_std"] = data["vote_constituency"]
    if "vote_list" in data:
        data["vote_list_std"] = data["vote_list"]

    dk_flags = []
    for vote_col in ["vote_constituency", "vote_list", "vote_westminster", "past_vote"]:
        if vote_col in data:
            flag_col = f"{vote_col}_dk"
            data[flag_col] = data[vote_col] == "DK/NA"
            dk_flags.append(flag_col)

    if dk_flags:
        data["dk_refused_any"] = data[dk_flags].any(axis=1)

    if args.drop_dk and dk_flags:
        data = data.loc[~data["dk_refused_any"]].copy()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_path, index=False)

    profile = {
        "row_count": int(len(data)),
        "missingness": data.isna().mean().to_dict(),
        "party_shares": {},
        "party_shares_raw": {},
    }

    if "interview_date" in data:
        counts = data["interview_date"].value_counts(dropna=False).sort_index()
        profile["counts_by_interview_date"] = counts.to_dict()

    if "wave" in data:
        counts = data["wave"].value_counts(dropna=False).sort_index()
        profile["counts_by_wave"] = counts.to_dict()

    for vote_col in ["vote_constituency", "vote_list", "vote_westminster", "past_vote"]:
        if vote_col in data:
            shares = (
                data[vote_col]
                .value_counts(dropna=False, normalize=True)
                .mul(100)
                .round(2)
                .to_dict()
            )
            profile["party_shares"][vote_col] = shares
            raw_col = f"{vote_col}_raw"
            if raw_col in data:
                raw_shares = (
                    data[raw_col]
                    .astype(str)
                    .value_counts(dropna=False, normalize=True)
                    .mul(100)
                    .round(2)
                    .to_dict()
                )
                profile["party_shares_raw"][vote_col] = raw_shares

    profile_path = Path(args.profile)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
