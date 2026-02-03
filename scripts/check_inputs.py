#!/usr/bin/env python
"""Check for required local data files and summarize next steps."""

from __future__ import annotations

import argparse
import pathlib

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="config/data_sources.yaml",
        help="Path to data_sources.yaml",
    )
    args = parser.parse_args()

    config_path = pathlib.Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found at {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    required = {
        "SES survey microdata": pathlib.Path(config["survey"]["path"]),
        "Polling data": pathlib.Path(config["polling"]["path"]),
        "Population benchmarks": pathlib.Path(config["poststrat"]["path"]),
    }

    missing = [label for label, path in required.items() if not path.exists()]

    if not missing:
        print("All required data files are present.")
        return

    print("Missing required files:")
    for label in missing:
        print(f"- {label} ({required[label]})")

    print("\nNext steps:")
    print("1) Download SES microdata from https://github.com/ScottishElectionStudy")
    print("2) Add polling data using config/polling_template.csv")
    print("3) Add population benchmarks with age_group/gender/region/population")
    print("4) Update config/data_sources.yaml if paths differ")


if __name__ == "__main__":
    main()
