#!/usr/bin/env python3
"""
Merge Opentrons destination mapping with enumeration outputs to produce an authoritative plate map.

Inputs:
- destination_plate_layout.csv (from opentrons_extract_destination_map.py)
- library_final_products.csv   (from enumeration)

Join strategy:
- Convert OT numeric indices (Sulfonyl chloride #, Amine #) to enumeration IDs:
    S_{num:03d}
    Amine_ID_{num:03d}

Outputs:
- authoritative_plate_map_96.csv
- qc_report.txt (summary + errors)
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def s_id(n: int) -> str:
    return f"S_{n:03d}"


def amine_id(n: int) -> str:
    return f"Amine_ID_{n:03d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest-map", type=Path, required=True, help="destination_plate_layout.csv")
    ap.add_argument("--products", type=Path, required=True, help="library_final_products.csv")
    ap.add_argument("--out", type=Path, default=Path("authoritative_plate_map_96.csv"))
    ap.add_argument("--qc", type=Path, default=Path("qc_report.txt"))
    args = ap.parse_args()

    df_dest = pd.read_csv(args.dest_map)
    df_prod = pd.read_csv(args.products)

    # Normalize OT indices → enum IDs
    df_dest["S_ID"] = df_dest["Sulfonyl chloride #"].astype(int).map(s_id)
    df_dest["Amine_ID"] = df_dest["Amine #"].astype(int).map(amine_id)

    # Merge: one row per well
    keep_cols_prod = [c for c in df_prod.columns if c in ("ProductID", "S_ID", "Amine_ID", "SMILES", "Status")]
    dfm = df_dest.merge(df_prod[keep_cols_prod], on=["S_ID", "Amine_ID"], how="left")

    # Authoritative columns (plus keep ProductID/Status)
    out_cols = [
        "Well",
        "Sulfonyl chloride #",
        "Amine #",
        "Sulfonyl source well",
        "Amine source well",
        "S_ID",
        "Amine_ID",
        "ProductID",
        "SMILES",
        "Status",
    ]
    dfm = dfm[out_cols]

    # QC
    missing = dfm[dfm["SMILES"].isna()].copy()
    n_total = len(dfm)
    n_missing = len(missing)

    lines = []
    lines.append(f"Total wells: {n_total}")
    lines.append(f"Missing SMILES: {n_missing}")
    if n_missing:
        lines.append("Missing rows (Well, S_ID, Amine_ID):")
        for _, r in missing.iterrows():
            lines.append(f"  {r['Well']}, {r['S_ID']}, {r['Amine_ID']}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    dfm.to_csv(args.out, index=False)
    args.qc.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"✅ Wrote {args.out}")
    print(f"✅ Wrote {args.qc}")

    # Fail hard if anything missing (useful in CI later)
    return 1 if n_missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
