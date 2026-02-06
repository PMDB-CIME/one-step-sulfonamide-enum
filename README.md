# One-Step Sulfonamide Enumeration App

## Overview

This repository contains a **one-step virtual library enumeration tool** for generating sulfonamides from:

- **Sulfonyl chlorides**
- **Primary or secondary amines**

The application performs a Cartesian enumeration of all sulfonyl chloride × amine pairs using an RDKit-defined sulfonamide coupling reaction and produces analysis-ready outputs suitable for medicinal chemistry, library design, and screening logistics.

This project is derived from, and structurally aligned with, the three-step amido–sulfonamide enumeration workflow, but has been simplified to a **single synthetic transformation**.

This repository represents the chemistry and plate-mapping foundation for a future Opentrons-integrated enumeration workflow.

---

## Chemistry

**Reaction:**

```
R–SO2–Cl  +  H–NR'R''   →   R–SO2–NR'R''
```

- Accepts aliphatic and aromatic primary or secondary amines
- Reaction failures are handled gracefully (see below)

SMARTS (conceptual):
```
[S](=O)(=O)Cl + [N;H1,H2] → [S](=O)(=O)N
```

---

## Repository Structure

```
one-step-sulfonamide-enum/
├── scripts/
│   └── one-step-sulfonamide-enum96.py
├── examples/
│   ├── SulfonylCl.csv
│   └── Amines.csv
├── opentrons/
├── README.md
└── requirements.txt
```

The structure mirrors the original multi-step enumeration repository to ensure consistency across related projects.

---

## Input Files

Inputs are provided as CSV files.

### Required Columns

Each input CSV **must** contain a SMILES column:

- `SMILES` (preferred)
- `smiles` or `Smiles` are also accepted

### Optional / Recommended Columns

| File | Preferred ID Column | Purpose |
|----|----|----|
| Sulfonyl chlorides | `S_ID` | Stable reagent identifier |
| Amines | `Amine_ID` | Stable reagent identifier |
| Either | `name` | Human-readable label |

If ID columns are not present, IDs will be auto-generated.

---

## Usage

### Basic Enumeration

```bash
python scripts/one-step-sulfonamide-enum96.py \
  --sulfonyl-chlorides examples/SulfonylCl.csv \
  --amines examples/Amines.csv \
  --out-basename library
```

### With Structure File and Preview

```bash
python scripts/one-step-sulfonamide-enum96.py \
  --sulfonyl-chlorides examples/SulfonylCl.csv \
  --amines examples/Amines.csv \
  --out-basename library \
  --emit-sdf \
  --preview
```

### Strict ID Enforcement

Require `S_ID` and `Amine_ID` columns to be present:

```bash
python scripts/one-step-sulfonamide-enum.py \
  --sulfonyl-chlorides examples/SulfonylCl.csv \
  --amines examples/Amines.csv \
  --strict-ids
```

---

## Outputs

Given `--out-basename library`, the following files are produced:

| File | Description |
|----|----|
| `library_final_products.csv` | Main enumeration output with descriptors |
| `library_plate_map_96.csv` | 96-well destination plate map (A1-H12) |
| `library_final_products.sdf` | Structure file with per-molecule metadata (optional) |
| `library_preview.png` | Grid image of first N products (optional) |

---

## Output CSV Columns

The final products CSV includes:

- `ProductID`
- `S_ID`
- `Amine_ID`
- `SMILES`
- `Status` (reaction outcome)

Plus calculated RDKit descriptors:

- Molecular weight (MolWt)
- cLogP
- TPSA
- HBD / HBA
- Rotatable bonds
- Ring count
- Fraction Csp³

---

## Reaction Robustness

If a sulfonamide coupling fails (e.g. incompatible functional groups, unusual valence), the app:

- Emits a **fallback product** created by combining the two reactants as disconnected fragments
- Flags the entry with:

```
Status = FALLBACK_COMBINEMOLS
```

This ensures:

- Enumeration completeness
- Stable product indexing
- No silent product loss

---

## Plate Mapping

For this release, products are assigned to a **single 96-well plate**:

- Rows: A–H
- Columns: 1–12
- Well IDs: A1–H12
- Ordering: column-major (A1, B1, … H1, A2, … H12)

This ordering is chosen to align with standard Opentrons liquid-handling conventions.
Future releases will validate this mapping directly against the Opentrons dispense protocol.

---

## Requirements

- Python ≥ 3.9
- RDKit
- pandas

Install dependencies (example):

```bash
conda create -n sulfonamide-enum python=3.10 rdkit pandas -c conda-forge
conda activate sulfonamide-enum
```

---

## Provenance

This tool is derived from the **three-step amido–sulfonamide enumeration workflow** and maintains:

- Output compatibility
- Plate-mapping logic
- Failure-tolerant enumeration philosophy

The simplified one-step design is intended for rapid library ideation and early SAR exploration.

---

## License

MIT License (see LICENSE file)

---

## Opentrons Plate Mapping and QC

This repository includes tooling to **validate that the virtual enumeration matches the Opentrons dispense protocol** and to generate a single, authoritative plate map linking **destination wells to Product SMILES**.

The workflow uses the Opentrons protocol as the source of truth for **well-level reagent dispensing**, and the enumeration output as the source of truth for **chemistry**.

---

## Generating the Opentrons Destination Plate Map

The Opentrons protocol defines:
- which **sulfonyl chloride** and **amine** are dispensed
- from which **source wells**
- into which **destination wells**

To extract this mapping:

```bash
python tools/opentrons_extract_destination_map.py \
  --protocol opentrons/protocols/one-step-dispense.py \
  --out-dest destination_plate_layout.csv \
  --out-source source_plate_layout.csv
```

### Outputs
- `destination_plate_layout.csv`  
  Maps each destination well to:
  - Sulfonyl chloride #
  - Amine #
  - Sulfonyl source well
  - Amine source well

- `source_plate_layout.csv`  
  Documents reagent identity and source plate layout used by the robot.

---

## Generating the Authoritative Plate Map (Well → SMILES)

To combine **robot dispense truth** with **enumeration chemistry**, merge the Opentrons mapping with the enumeration output:

```bash
python tools/merge_authoritative_plate_map.py \
  --dest-map destination_plate_layout.csv \
  --products library_final_products.csv \
  --out authoritative_plate_map_96.csv \
  --qc qc_report.txt
```

### Outputs
- `authoritative_plate_map_96.csv`  
  The single source of truth linking:
  - Destination well (A1–H12)
  - Reagent identities
  - Source wells
  - ProductID
  - Product SMILES
  - Reaction status

- `qc_report.txt`  
  Quality control summary confirming:
  - Total wells processed
  - Missing SMILES (must be zero for a valid run)

---

## Interpretation and Downstream Use

- `library_plate_map_96.csv`  
  Reflects the **enumeration’s internal ordering** and should not be used for robotic execution.

- `destination_plate_layout.csv`  
  Reflects **Opentrons dispense behavior** only (no chemistry).

- **`authoritative_plate_map_96.csv`**  
  This is the file that should be used for:
  - sample registration
  - LC/MS plate setup
  - screening metadata
  - structure–well traceability

---

## Notes

- All generated plate maps and QC files are intentionally excluded from version control via `.gitignore`.
- Enumeration and Opentrons logic are kept separate and reconciled explicitly to prevent silent mismatches.
- This design ensures that **every SMILES assigned to a destination well is provably correct**.
