#!/usr/bin/env python3
"""
Extract destination plate mapping from an Opentrons protocol (Flex API 2.x).

Outputs:
- destination_plate_layout.csv: Well, Sulfonyl chloride #, Amine #, Sulfonyl source well, Amine source well
- (optional) source_plate_layout.csv: SourceWell, ReagentClass, ReagentNumber, ReagentName, Volume_uL

Assumptions (matches your protocol):
- liquids defined via protocol.define_liquid(name="Amine 1" / "SulfonylCl 1" etc.)
- loaded into source_plate['A1'].load_liquid(liquid=amine_1, volume=50)
- transfers via left_pipette.transfer(..., source_plate['A2'], sulfonyl_dest_1, ...)
- destination well lists defined as list comps, e.g.
    sulfonyl_dest_1 = [dest_plate.wells_by_name()[well] for well in ['A1','A2',...]]
"""

from __future__ import annotations

import argparse
import ast
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


RE_AMINE = re.compile(r"^Amine\s+(\d+)\s*$", re.IGNORECASE)
RE_SULF = re.compile(r"^SulfonylCl\s+(\d+)\s*$", re.IGNORECASE)


def _const_str(node: ast.AST) -> Optional[str]:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _subscript_well(node: ast.AST) -> Tuple[Optional[str], Optional[str]]:
    """Return (base_name, well_str) for source_plate['A1'] style."""
    if not isinstance(node, ast.Subscript):
        return None, None

    base = node.value
    base_name = base.id if isinstance(base, ast.Name) else None

    sl = node.slice
    if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
        return base_name, sl.value

    # for older AST nodes (rare on modern Python)
    if hasattr(ast, "Index") and isinstance(sl, ast.Index) and isinstance(sl.value, ast.Constant):
        if isinstance(sl.value.value, str):
            return base_name, sl.value.value

    return base_name, None


def _well_sort_key(w: str) -> Tuple[int, int]:
    """Column-major sort: A1,B1,...H1,A2,..."""
    row = w[0].upper()
    col = int(w[1:])
    row_order = "ABCDEFGH".index(row)
    return col, row_order


def parse_protocol(protocol_path: Path) -> Tuple[List[Dict], List[Dict]]:
    code = protocol_path.read_text(encoding="utf-8")
    tree = ast.parse(code)

    run_node = None
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == "run":
            run_node = n
            break
    if run_node is None:
        raise ValueError("Could not find run(protocol) function in protocol.")

    # 1) reagent variables -> (class, num, name)
    reagent_vars: Dict[str, Dict] = {}
    for stmt in run_node.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            var = stmt.targets[0].id
            call = stmt.value
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "define_liquid":
                name = None
                for kw in call.keywords:
                    if kw.arg == "name":
                        name = _const_str(kw.value)
                if not name:
                    continue

                mA = RE_AMINE.match(name)
                mS = RE_SULF.match(name)
                if mA:
                    reagent_vars[var] = {"class": "amine", "num": int(mA.group(1)), "name": name}
                elif mS:
                    reagent_vars[var] = {"class": "sulfonyl", "num": int(mS.group(1)), "name": name}

    # 2) source well -> reagent var
    source_well_map: Dict[str, Dict] = {}
    for node in ast.walk(run_node):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "load_liquid"):
            continue

        # expect: source_plate['A1'].load_liquid(...)
        base, well = _subscript_well(node.func.value)
        if base != "source_plate" or not well:
            continue

        liquid_var = None
        vol = None
        for kw in node.keywords:
            if kw.arg == "liquid" and isinstance(kw.value, ast.Name):
                liquid_var = kw.value.id
            if kw.arg == "volume" and isinstance(kw.value, ast.Constant):
                vol = kw.value.value

        if liquid_var:
            source_well_map[well] = {"liquid_var": liquid_var, "volume": vol}

    # 3) list vars: sulfonyl_dest_1 = [dest_plate.wells_by_name()[well] for well in ['A1',...]]
    dest_lists: Dict[str, List[str]] = {}
    for stmt in run_node.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            var = stmt.targets[0].id
            val = stmt.value
            if isinstance(val, ast.ListComp) and val.generators:
                gen = val.generators[0]
                if isinstance(gen.iter, (ast.List, ast.Tuple)):
                    wells = []
                    for elt in gen.iter.elts:
                        s = _const_str(elt)
                        if s:
                            wells.append(s)
                    if wells:
                        dest_lists[var] = wells

    # 4) transfer calls: left_pipette.transfer(vol, source_plate['A2'], sulfonyl_dest_1, ...)
    transfers = []
    for stmt in run_node.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "transfer":
                args = call.args
                if len(args) < 3:
                    continue

                base, src_well = _subscript_well(args[1])
                if base != "source_plate" or not src_well:
                    continue

                dest_arg = args[2]
                dest_wells = None
                if isinstance(dest_arg, ast.Name) and dest_arg.id in dest_lists:
                    dest_wells = dest_lists[dest_arg.id]
                elif isinstance(dest_arg, ast.List):
                    dest_wells = [s for s in (_const_str(e) for e in dest_arg.elts) if s]

                if dest_wells:
                    transfers.append({"src_well": src_well, "dest_wells": dest_wells})

    # Build destination map: well -> sulfonyl#/amine# and source wells
    dest_map: Dict[str, Dict] = {}
    for t in transfers:
        src_well = t["src_well"]
        src_info = source_well_map.get(src_well)
        if not src_info:
            continue

        rv = src_info["liquid_var"]
        rinfo = reagent_vars.get(rv)
        if not rinfo:
            continue

        for dw in t["dest_wells"]:
            rec = dest_map.setdefault(
                dw,
                {
                    "Well": dw,
                    "Sulfonyl chloride #": "",
                    "Amine #": "",
                    "Sulfonyl source well": "",
                    "Amine source well": "",
                },
            )
            if rinfo["class"] == "sulfonyl":
                rec["Sulfonyl chloride #"] = rinfo["num"]
                rec["Sulfonyl source well"] = src_well
            elif rinfo["class"] == "amine":
                rec["Amine #"] = rinfo["num"]
                rec["Amine source well"] = src_well

    # source layout (optional)
    source_rows = []
    for well, d in source_well_map.items():
        rv = d["liquid_var"]
        rinfo = reagent_vars.get(rv, {"class": "unknown", "num": "", "name": rv})
        source_rows.append(
            {
                "SourceWell": well,
                "ReagentClass": rinfo["class"],
                "ReagentNumber": rinfo["num"],
                "ReagentName": rinfo["name"],
                "Volume_uL": d.get("volume", ""),
            }
        )

    # destination rows sorted column-major
    dest_rows = [dest_map[w] for w in sorted(dest_map.keys(), key=_well_sort_key)]

    return dest_rows, source_rows


def write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", type=Path, required=True, help="Path to Opentrons protocol .py")
    ap.add_argument("--out-dest", type=Path, default=Path("destination_plate_layout.csv"))
    ap.add_argument("--out-source", type=Path, default=None, help="Optional: write source_plate_layout.csv")
    args = ap.parse_args()

    dest_rows, source_rows = parse_protocol(args.protocol)

    write_csv(
        args.out_dest,
        dest_rows,
        ["Well", "Sulfonyl chloride #", "Amine #", "Sulfonyl source well", "Amine source well"],
    )

    if args.out_source:
        write_csv(
            args.out_source,
            source_rows,
            ["SourceWell", "ReagentClass", "ReagentNumber", "ReagentName", "Volume_uL"],
        )

    print(f"✅ Wrote {args.out_dest} ({len(dest_rows)} rows)")
    if args.out_source:
        print(f"✅ Wrote {args.out_source} ({len(source_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
