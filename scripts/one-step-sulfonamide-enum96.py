#!/usr/bin/env python3
"""
One-step sulfonamide virtual library enumeration

Chemistry:
  Sulfonyl chloride + primary/secondary amine  ->  sulfonamide

Inputs:
  - Sulfonyl chlorides CSV (must include a SMILES column)
  - Amines CSV (must include a SMILES column)

Outputs (given --out-basename X):
  - X_final_products.csv            (always; includes descriptors)
  - X_final_products.sdf            (if --emit-sdf)
  - X_preview.png                   (if --preview [N])
  - X_plate_map_1536.csv            (always; plate layout for final products)

Notes:
  - Failure-tolerant: if the reaction fails, we still emit a "best-effort" product
    by combining the two input molecules as disconnected fragments (CombineMols).
  - IDs: preferred columns S_ID and Amine_ID (fallback to `id` or auto-generated).
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem, Draw, rdMolDescriptors, Descriptors
from rdkit.Chem import rdChemReactions as Rxn

# -------------------------
# Substructure queries (used for input validation)
# -------------------------
Q_SOF2CL = Chem.MolFromSmarts("[S](=O)(=O)Cl")
Q_AMINE = Chem.MolFromSmarts("[N;H1,H2]")


# -------------------------
# Reaction SMARTS
# -------------------------
RXN_SULFONAMIDE = Rxn.ReactionFromSmarts("[*:1][S:2](=[O:3])(=[O:4])[Cl:5].[N:6]>>[*:1][S:2](=[O:3])(=[O:4])[N:6]")



# -------------------------
# Plate utilities (96-well)
# 8 rows (A..H) x 12 cols (1..12), column-major (A1,B1,..,H1,A2,..)
# -------------------------
def row_labels_96() -> List[str]:
    return list("ABCDEFGH")


def plate_assign_96(n: int) -> List[Dict[str, object]]:
    """Assign wells in an Opentrons-friendly 96-well order.

    - Well names: A1..H12 (no leading zeros)
    - Fill order: column-major (A1,B1,...,H1,A2,...,H12)
    - Plate increments every 96 assignments (if n > 96)
    """
    rows = row_labels_96()  # ['A'..'H']
    n_rows, n_cols = len(rows), 12
    recs: List[Dict[str, object]] = []
    plate = 1

    for i in range(n):
        idx = i % (n_rows * n_cols)
        col = (idx // n_rows) + 1      # 1..12
        r = idx % n_rows               # 0..7
        row = rows[r]
        well = f"{row}{col}"

        recs.append({"Plate": plate, "Row": row, "Col": col, "Well": well})

        if (i + 1) % (n_rows * n_cols) == 0:
            plate += 1

    return recs

def first_sanitized_product_smiles(rxn: Rxn.ChemicalReaction, reactants: Tuple[Chem.Mol, ...]) -> Optional[str]:
    try:
        out_sets = rxn.RunReactants(reactants)
    except Exception:
        return None

    for pset in out_sets:
        for p in pset:
            try:
                Chem.SanitizeMol(p)
                # canonical isomeric SMILES for deterministic output
                return Chem.MolToSmiles(p, isomericSmiles=True)
            except Exception:
                continue
    return None


def best_effort_product(s_mol: Chem.Mol, a_mol: Chem.Mol) -> Tuple[str, str]:
    """
    Returns (product_smiles, status)
      status:
        OK_REACTION            reaction succeeded
        FALLBACK_COMBINEMOLS   reaction failed; emitted disconnected fragments
    """
    smi = first_sanitized_product_smiles(RXN_SULFONAMIDE, (s_mol, a_mol))
    if smi:
        return smi, "OK_REACTION"

    combo = Chem.CombineMols(s_mol, a_mol)
    try:
        Chem.SanitizeMol(combo, catchErrors=True)
    except Exception:
        pass
    return Chem.MolToSmiles(combo, isomericSmiles=True), "FALLBACK_COMBINEMOLS"


# -------------------------
# Descriptors (keep compact + broadly useful)
# -------------------------
def calc_descriptors(m: Chem.Mol) -> Dict[str, float]:
    # Use RDKit’s standard descriptor functions (fast + stable)
    return {
        "MolWt": Descriptors.MolWt(m),
        "LogP": Descriptors.MolLogP(m),
        "TPSA": rdMolDescriptors.CalcTPSA(m),
        "HBD": rdMolDescriptors.CalcNumHBD(m),
        "HBA": rdMolDescriptors.CalcNumHBA(m),
        "RotBonds": rdMolDescriptors.CalcNumRotatableBonds(m),
        "RingCount": rdMolDescriptors.CalcNumRings(m),
        "FracCSP3": rdMolDescriptors.CalcFractionCSP3(m),
    }


def prep_for_sdf(m: Chem.Mol) -> Chem.Mol:
    m = Chem.AddHs(m)
    AllChem.Compute2DCoords(m)
    return m


# -------------------------
# Input loading
# -------------------------
@dataclass(frozen=True)
class Reagent:
    smiles: str
    rid: str
    name: str


def _pick_smiles_col(df: pd.DataFrame) -> str:
    # Accept common variants, prefer exact "SMILES" then "smiles"
    for c in ["SMILES", "smiles", "Smiles"]:
        if c in df.columns:
            return c
    raise ValueError("Input CSV must contain a SMILES column (SMILES/smiles).")


def load_reagents_csv(path: Path, preferred_id_col: str, default_prefix: str, strict_ids: bool) -> List[Reagent]:
    df = pd.read_csv(path)
    smi_col = _pick_smiles_col(df)

    # ID selection
    if preferred_id_col in df.columns:
        id_col = preferred_id_col
    elif "id" in df.columns and not strict_ids:
        id_col = "id"
    elif strict_ids:
        raise ValueError(f"{path}: missing required ID column '{preferred_id_col}' (strict mode).")
    else:
        id_col = None  # will auto-generate

    # Name optional
    name_col = "name" if "name" in df.columns else ("Name" if "Name" in df.columns else None)

    reagents: List[Reagent] = []
    for i, row in df.iterrows():
        smi_raw = str(row[smi_col]).strip()
        mol = Chem.MolFromSmiles(smi_raw)
        if mol is None:
            continue
        smi = Chem.MolToSmiles(mol, isomericSmiles=True)

        rid = str(row[id_col]).strip() if id_col else f"{default_prefix}{i:06d}"
        nm = str(row[name_col]).strip() if name_col else rid
        reagents.append(Reagent(smiles=smi, rid=rid, name=nm))

    return reagents


# -------------------------
# Enumeration
# -------------------------
def enumerate_one_step(
    sulfonyls: List[Reagent],
    amines: List[Reagent],
) -> Iterable[Tuple[int, Reagent, Reagent, str, str]]:
    """
    Yields tuples:
      (ProductID, sulfonyl_reagent, amine_reagent, product_smiles, status)
    """
    pid = 0
    for s in sulfonyls:
        s_mol = Chem.MolFromSmiles(s.smiles)
        if s_mol is None or not s_mol.HasSubstructMatch(Q_SOF2CL):
            # Still allow, but it will likely go to fallback
            pass

        for a in amines:
            a_mol = Chem.MolFromSmiles(a.smiles)
            if a_mol is None or not a_mol.HasSubstructMatch(Q_AMINE):
                # Still allow, but it will likely go to fallback
                pass

            prod_smi, status = best_effort_product(s_mol, a_mol)
            yield pid, s, a, prod_smi, status
            pid += 1


# -------------------------
# Writers
# -------------------------
def write_outputs(
    out_basename: Path,
    products: List[Dict[str, object]],
    emit_sdf: bool,
    preview_n: int,
):
    # CSV
    csv_path = out_basename.with_name(out_basename.name + "_final_products.csv")
    df = pd.DataFrame(products)
    df.to_csv(csv_path, index=False)

    # Plate map
    pm_path = out_basename.with_name(out_basename.name + "_plate_map_96.csv")
    pm = pd.DataFrame(plate_assign_96(len(products)))
    pm["ProductID"] = df["ProductID"].values
    pm["ProductSMILES"] = df["SMILES"].values
    pm["S_ID"] = df["S_ID"].values
    pm["Amine_ID"] = df["Amine_ID"].values
    pm.to_csv(pm_path, index=False)

    # SDF (optional)
    if emit_sdf:
        sdf_path = out_basename.with_name(out_basename.name + "_final_products.sdf")
        w = Chem.SDWriter(str(sdf_path))
        for i, row in df.iterrows():
            m = Chem.MolFromSmiles(row["SMILES"])
            if m is None:
                continue
            m = prep_for_sdf(m)

            # Name + traceability props
            m.SetProp("_Name", f"{row['ProductID']} | {row['S_ID']} x {row['Amine_ID']}")
            m.SetProp("ProductID", str(row["ProductID"]))
            m.SetProp("S_ID", str(row["S_ID"]))
            m.SetProp("Amine_ID", str(row["Amine_ID"]))
            m.SetProp("Status", str(row["Status"]))

            # Plate props
            well = pm.loc[i, "Well"]
            m.SetProp("Well", str(well))

            # Descriptor props (keep as strings)
            for k in ["MolWt", "LogP", "TPSA", "HBD", "HBA", "RotBonds", "RingCount", "FracCSP3"]:
                if k in row and pd.notna(row[k]):
                    m.SetProp(k, str(row[k]))

            w.write(m)
        w.close()

    # Preview (optional)
    if preview_n > 0:
        png_path = out_basename.with_name(out_basename.name + "_preview.png")
        mols, legends = [], []
        for i in range(min(preview_n, len(df))):
            m = Chem.MolFromSmiles(df.loc[i, "SMILES"])
            if m is None:
                continue
            mols.append(m)
            legends.append(f"{df.loc[i,'ProductID']} | {pm.loc[i,'Well']}")
        if mols:
            img = Draw.MolsToGridImage(mols, molsPerRow=6, subImgSize=(250, 200), legends=legends)
            img.save(str(png_path))


# -------------------------
# CLI
# -------------------------
def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="One-step sulfonamide enumeration: sulfonyl chloride × amine")
    p.add_argument("--sulfonyl-chlorides", type=Path, required=True, help="CSV with sulfonyl chloride SMILES")
    p.add_argument("--amines", type=Path, required=True, help="CSV with amine SMILES")

    p.add_argument("--out-basename", type=str, default="library", help="Output basename")
    p.add_argument("--emit-sdf", action="store_true", help="Write final SDF (adds per-mol props)")
    p.add_argument("--preview", type=int, nargs="?", const=24, default=0, help="Write preview PNG of first N (default 24).")
    p.add_argument("--strict-ids", action="store_true", help="Require preferred ID columns: S_ID and Amine_ID")

    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    out_base = Path(args.out_basename)

    sulfonyls = load_reagents_csv(args.sulfonyl_chlorides, preferred_id_col="S_ID", default_prefix="S_", strict_ids=args.strict_ids)
    amines = load_reagents_csv(args.amines, preferred_id_col="Amine_ID", default_prefix="A_", strict_ids=args.strict_ids)

    if not sulfonyls or not amines:
        print("[ERROR] One or more input lists are empty after parsing.", file=sys.stderr)
        return 2

    total = len(sulfonyls) * len(amines)
    print(f"Sulfonyl chlorides: {len(sulfonyls)} | Amines: {len(amines)} | Products: {total}")

    products: List[Dict[str, object]] = []
    for pid, s, a, prod_smi, status in enumerate_one_step(sulfonyls, amines):
        pmol = Chem.MolFromSmiles(prod_smi)
        if pmol is None:
            # last resort: keep SMILES and no descriptors
            desc = {}
        else:
            desc = calc_descriptors(pmol)

        rec: Dict[str, object] = {
            "ProductID": pid,
            "S_ID": s.rid,
            "Amine_ID": a.rid,
            "SMILES": prod_smi,
            "Status": status,
        }
        rec.update(desc)
        products.append(rec)

    write_outputs(out_base, products, emit_sdf=args.emit_sdf, preview_n=args.preview)

    print(f"✅ Wrote {out_base.name}_final_products.csv")
    print(f"✅ Wrote {out_base.name}_plate_map_96.csv")
    if args.emit_sdf:
        print(f"✅ Wrote {out_base.name}_final_products.sdf")
    if args.preview:
        print(f"✅ Wrote {out_base.name}_preview.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))