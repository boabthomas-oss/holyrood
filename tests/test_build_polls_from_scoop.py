import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.build_polls_from_scoop import build_polls


def load_party_config() -> tuple[list[str], str]:
    config = json.loads(Path("config/party_columns.json").read_text(encoding="utf-8"))
    return config["parties"], config.get("dk_label", "DK/NA")


def test_vote_shares_sum_to_100(tmp_path):
    input_path = tmp_path / "scoop_tracker.csv"
    template_path = tmp_path / "polling_template.csv"
    output_path = tmp_path / "polls.csv"

    template_path.write_text(
        "wave,ballot,pollster,client,source,url,fieldwork_end,sample_size,SNP,LAB,CON,LD,GRN,REF,ALBA,OTH\n",
        encoding="utf-8",
    )

    df = pd.DataFrame(
        {
            "wave": ["1", "1", "1", "2", "2"],
            "interview_date": [
                "2024-01-05",
                "2024-01-06",
                "2024-01-07",
                "2024-02-01",
                "2024-02-02",
            ],
            "vote_constituency_std": ["SNP", "LAB", "DK/NA", "CON", "LD"],
            "vote_list_std": ["SNP", "LAB", "GRN", "CON", "DK/NA"],
            "weight": [1.0, 1.0, 1.0, 2.0, 1.0],
        }
    )
    df.to_csv(input_path, index=False)

    party_config = Path("config/party_columns.json")
    output = build_polls(input_path, output_path, template_path, party_config)

    parties, _ = load_party_config()
    for _, row in output.iterrows():
        total = sum(row[party] for party in parties)
        assert total == pytest.approx(100.0, abs=0.1)


def test_party_completeness(tmp_path):
    input_path = tmp_path / "scoop_tracker.csv"
    template_path = tmp_path / "polling_template.csv"
    output_path = tmp_path / "polls.csv"

    template_path.write_text(
        "wave,ballot,pollster,client,source,url,fieldwork_end,sample_size,SNP,LAB,CON,LD,GRN,REF,ALBA,OTH\n",
        encoding="utf-8",
    )

    df = pd.DataFrame(
        {
            "wave": ["1", "1", "1"],
            "interview_date": ["2024-01-05", "2024-01-06", "2024-01-07"],
            "vote_constituency_std": ["SNP", "LAB", "SNP"],
            "weight": [1.0, 1.0, 1.0],
        }
    )
    df.to_csv(input_path, index=False)

    party_config = Path("config/party_columns.json")
    output = build_polls(input_path, output_path, template_path, party_config)

    parties, _ = load_party_config()
    row = output.iloc[0]
    for party in parties:
        assert party in output.columns
        if party not in {"SNP", "LAB"}:
            assert row[party] == pytest.approx(0.0, abs=0.01)
