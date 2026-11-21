
from pathlib import Path

import numpy as np
import pandas as pd

MASK_FILE = Path(
    "data/processed/study_area_mask_50m_preview.csv"
)

RESULT_FILE = Path(
    "data/processed/area_weighted_daily_tmax_preview.csv"
)


def main():
    assert MASK_FILE.exists(), "Mask file is missing"
    assert RESULT_FILE.exists(), "Temperature output is missing"

    mask = pd.read_csv(MASK_FILE)
    result = pd.read_csv(RESULT_FILE)

    # 1. Verify the geographic grid.
    assert len(mask) == 42993
    assert mask["in_study_area"].sum() == 17463

    # 2. Verify temporal coverage.
    assert len(result) == 31

    dates = pd.to_datetime(result["date"])

    assert dates.min() == pd.Timestamp("2020-07-01")
    assert dates.max() == pd.Timestamp("2020-07-31")
    assert dates.is_unique

    # 3. Verify valid observations.
    assert (result["valid_cells"] == 17463).all()

    columns = [
        "weighted_mean_tmax_c",
        "maximum_tmax_c",
    ]

    assert result[columns].notna().all().all()
    assert np.isfinite(result[columns].to_numpy()).all()

    # 4. Verify logical temperature relationships.
    assert (
        result["maximum_tmax_c"]
        >= result["weighted_mean_tmax_c"]
    ).all()

    # 5. Verify a known reference result.
    first_day = result.iloc[0]

    assert np.isclose(
        first_day["weighted_mean_tmax_c"],
        23.271,
        atol=0.001,
    )

    print("=== PIPELINE INTEGRATION TEST ===")
    print("Geographic grid: PASS")
    print("Selected cells: PASS")
    print("Temporal coverage: PASS")
    print("Missing values: PASS")
    print("Temperature consistency: PASS")
    print("Reference result: PASS")
    print("\nAll integration checks passed.")


if __name__ == "__main__":
    main()
