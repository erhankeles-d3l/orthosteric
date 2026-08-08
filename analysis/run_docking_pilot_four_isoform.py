"""Four-isoform cross-docking pilot: PI3Kalpha/beta/gamma/delta, same
compound panel, real receptors for all four isoforms.

Extends analysis/run_docking_pilot.py (which covered alpha/gamma/delta
only) by resolving PI3Kbeta via the governed GDR-006 AlphaFold fallback,
per this session's explicit instruction to resolve it through a
legitimate governed route rather than declaring the work impossible.

PI3Kbeta resolution (real, this session)
-------------------------------------------
No human PIK3CB (P42338) PDB structure exists (verified, unchanged from
prior sessions). Per SCI0-007's AlphaFold admissibility rules (mean
pLDDT >= 70; source confirmed by UniProt accession match; only when no
admissible PDB exists) and GDR-006 (AlphaFold features included with an
explicit is_alphafold indicator), fetched the real AlphaFold model for
P42338 (AF-P42338-F1-model_v6, global mean pLDDT = 86.38 -- admissible).

Box derivation for beta (no co-crystallized ligand to center on): used
UniProt's own curated domain annotation for P42338 -- the "G-loop"
(glycine-rich ATP-binding loop, canonical UniProt residues 778-784,
part of the "PI3K/PI4K catalytic" domain 772-1053) -- as the box center.
This is a REAL, non-arbitrary, independently-curated structural
annotation (not derived by this pipeline, not guessed), and AlphaFold's
residue numbering matches UniProt canonical numbering exactly, so no
alignment step is needed. Local pLDDT at the G-loop itself (89.30, over
60 atoms) exceeds the global mean, confirming high confidence exactly
where the box is centered.

Receptors, all four isoforms:
  PI3Kalpha: 8EXL (1.989 A, ligand 799) -- EXPERIMENTAL_RECEPTOR, tier D1
  PI3Kbeta:  AF-P42338 (mean pLDDT 86.38) -- ALPHAFOLD_RECEPTOR, tier D2
  PI3Kgamma: 6AUD (2.015 A, ligand BWY) -- EXPERIMENTAL_RECEPTOR, tier D1
  PI3Kdelta: 6PYR (2.21 A, ligand P5J) -- EXPERIMENTAL_RECEPTOR, tier D1

Same 5-compound pilot panel as the alpha/gamma/delta pilot, for direct
comparability. A4 is read-only throughout (not touched by this script).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Documents/orthosteric/src")

from rdkit import Chem
from rdkit.Chem import AllChem

from orthosteric.data.sources.structural._docking_record import (
    DockingBox,
    DockingComplexRecord,
    DockingOutcome,
    ReceptorSourceClass,
)

WORKDIR = Path("/home/ubuntu/docking_pilot")
RECEPTOR_DIR = WORKDIR / "receptors"
LIGAND_DIR = WORKDIR / "ligands"

SEED = 42
EXHAUSTIVENESS = 8
NUM_MODES = 5
PIPELINE_VERSION = "docking_pipeline_v1_vina1.2.7_meeko0.7.1"
RETRIEVAL_TS = "2026-08-06T00:00:00Z"

# ── Beta: AlphaFold receptor prep (no ligand to strip; already protein-only) ─
BETA_UNIPROT = "P42338"
BETA_MEAN_PLDDT = 86.38
BETA_GLOOP_RANGE = (778, 784)  # UniProt-curated "G-loop" domain annotation


def gloop_centroid_and_local_plddt(af_pdb: Path) -> tuple[tuple[float, float, float], float]:
    coords, plddts = [], []
    for line in af_pdb.read_text().splitlines():
        if line.startswith("ATOM"):
            resnum = int(line[22:26])
            if BETA_GLOOP_RANGE[0] <= resnum <= BETA_GLOOP_RANGE[1]:
                x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
                coords.append((x, y, z))
                plddts.append(float(line[60:66]))  # pLDDT stored in B-factor column
    n = len(coords)
    centroid = (sum(c[0] for c in coords) / n, sum(c[1] for c in coords) / n, sum(c[2] for c in coords) / n)
    return centroid, sum(plddts) / len(plddts)


def prepare_receptor_pdbqt(protein_pdb: Path) -> Path:
    out_pdbqt = protein_pdb.with_suffix(".pdbqt")
    if out_pdbqt.exists():
        return out_pdbqt  # already prepared (alpha/gamma/delta from prior run)
    result = subprocess.run(
        [sys.executable, "/home/ubuntu/.local/bin/mk_prepare_receptor.py",
         "--read_pdb", str(protein_pdb), "-o", str(protein_pdb.with_suffix("")),
         "-p", "-a", "--default_altloc", "A"],
        capture_output=True, text=True, timeout=120,
    )
    if not out_pdbqt.exists():
        raise RuntimeError(f"Receptor prep failed for {protein_pdb}: {result.stdout}\n{result.stderr}")
    return out_pdbqt


def dock(receptor_pdbqt: Path, ligand_pdbqt: Path, box_center, box_size=(20.0, 20.0, 20.0)):
    from vina import Vina  # noqa: PLC0415

    v = Vina(sf_name="vina", seed=SEED, verbosity=0)
    v.set_receptor(str(receptor_pdbqt))
    v.set_ligand_from_file(str(ligand_pdbqt))
    v.compute_vina_maps(center=list(box_center), box_size=list(box_size))
    v.dock(exhaustiveness=EXHAUSTIVENESS, n_poses=NUM_MODES)
    return v.energies(n_poses=NUM_MODES)


print("=== Beta receptor: GDR-006 AlphaFold fallback ===")
beta_pdb = RECEPTOR_DIR / "AF-P42338.pdb"
beta_pdbqt = prepare_receptor_pdbqt(beta_pdb)
beta_centroid, beta_gloop_plddt = gloop_centroid_and_local_plddt(beta_pdb)
print(f"  AF-{BETA_UNIPROT} global mean pLDDT: {BETA_MEAN_PLDDT} (SCI0-007 threshold: >=70, admissible)")
print(f"  G-loop (residues {BETA_GLOOP_RANGE}) local mean pLDDT: {beta_gloop_plddt:.2f}")
print(f"  G-loop centroid (box center): {beta_centroid}")
print(f"  Receptor PDBQT: {beta_pdbqt.name}")

RECEPTORS = {
    "PI3Kalpha": {
        "pdbqt": RECEPTOR_DIR / "8EXL_protein_only.pdbqt", "centroid": None,  # filled below
        "source_class": ReceptorSourceClass.EXPERIMENTAL_RECEPTOR,
        "receptor_id": "8EXL", "box_derivation": "centroid_of_cocrystallized_ligand:799@8EXL",
    },
    "PI3Kbeta": {
        "pdbqt": beta_pdbqt, "centroid": beta_centroid,
        "source_class": ReceptorSourceClass.ALPHAFOLD_RECEPTOR,
        "receptor_id": f"AF-{BETA_UNIPROT}",
        "box_derivation": f"centroid_of_uniprot_curated_gloop_domain:{BETA_GLOOP_RANGE[0]}-{BETA_GLOOP_RANGE[1]}@AF-{BETA_UNIPROT}",
    },
    "PI3Kgamma": {
        "pdbqt": RECEPTOR_DIR / "6AUD_protein_only.pdbqt", "centroid": None,
        "source_class": ReceptorSourceClass.EXPERIMENTAL_RECEPTOR,
        "receptor_id": "6AUD", "box_derivation": "centroid_of_cocrystallized_ligand:BWY@6AUD",
    },
    "PI3Kdelta": {
        "pdbqt": RECEPTOR_DIR / "6PYR_protein_only.pdbqt", "centroid": None,
        "source_class": ReceptorSourceClass.EXPERIMENTAL_RECEPTOR,
        "receptor_id": "6PYR", "box_derivation": "centroid_of_cocrystallized_ligand:P5J@6PYR",
    },
}
# re-derive alpha/gamma/delta centroids from their original PDBs (same
# method as the prior alpha/gamma/delta pilot; recomputed here for a
# fully self-contained script rather than hardcoding stale numbers)
_LIGAND_CCD = {"PI3Kalpha": ("8EXL", "799"), "PI3Kgamma": ("6AUD", "BWY"), "PI3Kdelta": ("6PYR", "P5J")}
for iso, (pdb_id, ccd) in _LIGAND_CCD.items():
    raw = (RECEPTOR_DIR / f"{pdb_id}.pdb").read_text().splitlines()
    coords = []
    for line in raw:
        if line.startswith("HETATM") and line[17:20].strip() == ccd:
            x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
            coords.append((x, y, z))
    centroid = (sum(c[0] for c in coords) / len(coords), sum(c[1] for c in coords) / len(coords), sum(c[2] for c in coords) / len(coords))
    RECEPTORS[iso]["centroid"] = centroid

print("\n=== Full four-isoform receptor panel ===")
for iso, r in RECEPTORS.items():
    print(f"  {iso}: {r['receptor_id']} ({r['source_class'].value}), box center={r['centroid']}")

PILOT_LIGANDS = {
    "LY294002": "O=C1c2ccccc2Oc2cc(N3CCOCC3)ccc12",
    "Quercetin": "Oc1cc(O)c2c(=O)c(O)c(-c3ccc(O)c(O)c3)oc2c1",
    "Staurosporine_core": "CN[C@@H]1C[C@H]2O[C@@](C)([C@@H]1OC)n3c4ccccc4c5c6CNC(=O)c6c7c8ccccc8n2c7c35",
    "Simple_pyrimidine": "Cc1ccc(-c2nc(N)nc(N)n2)cc1",
    "Morpholino_quinazoline": "COc1cc2ncnc(N3CCOCC3)c2cc1OC",
}

print(f"\n=== Cross-docking: {len(PILOT_LIGANDS)} compounds x {len(RECEPTORS)} isoforms ===")
records = []
t0 = time.time()
comparative: dict[str, dict[str, float | None]] = {cid: {} for cid in PILOT_LIGANDS}

for cid, smi in PILOT_LIGANDS.items():
    ligand_pdbqt = LIGAND_DIR / f"{cid}.pdbqt"
    if not ligand_pdbqt.exists():
        print(f"  {cid}: ligand PDBQT missing (should have been prepared by the prior pilot)")
        continue
    for iso, r in RECEPTORS.items():
        box = DockingBox(
            center_x=r["centroid"][0], center_y=r["centroid"][1], center_z=r["centroid"][2],
            size_x=20.0, size_y=20.0, size_z=20.0, derivation_method=r["box_derivation"],
        )
        try:
            energies = dock(r["pdbqt"], ligand_pdbqt, r["centroid"])
            best_score = float(energies[0][0])
            comparative[cid][iso] = best_score
            print(f"  {cid} vs {iso} ({r['receptor_id']}, {r['source_class'].value}): score={best_score:.2f} kcal/mol")
            records.append(DockingComplexRecord(
                compound_id=cid, inchikey=None, isoform=iso,
                outcome=DockingOutcome.SUCCESS,
                receptor_source_class=r["source_class"], receptor_identifier=r["receptor_id"],
                receptor_preparation_software="meeko", receptor_preparation_version="0.7.1",
                ligand_smiles=smi,
                ligand_preparation_software="rdkit+meeko", ligand_preparation_version="2026.03.5+0.7.1",
                docking_engine="AutoDock Vina", docking_engine_version="1.2.7",
                docking_box=box, exhaustiveness=EXHAUSTIVENESS, num_modes=NUM_MODES, seed=SEED,
                pose_rank=1, docking_score=best_score,
                pipeline_version=PIPELINE_VERSION, retrieval_timestamp=RETRIEVAL_TS,
            ))
        except Exception as e:
            comparative[cid][iso] = None
            print(f"  {cid} vs {iso}: DOCKING FAILED ({e})")
            records.append(DockingComplexRecord(
                compound_id=cid, inchikey=None, isoform=iso,
                outcome=DockingOutcome.DOCKING_ENGINE_FAILED,
                receptor_source_class=r["source_class"], receptor_identifier=r["receptor_id"],
                ligand_smiles=smi, pipeline_version=PIPELINE_VERSION,
                retrieval_timestamp=RETRIEVAL_TS, failure_reason=str(e)[:300],
            ))

elapsed = time.time() - t0
print(f"\nTotal cross-docking wall time: {elapsed:.1f}s")

# ── Comparative four-isoform report ──────────────────────────────────────────
print("\n=== Comparative four-isoform structural profile ===")
print(f"{'Compound':<24}{'alpha':>8}{'beta':>8}{'gamma':>8}{'delta':>8}{'a-b':>8}{'a-g':>8}{'a-d':>8}  classification")
classifications = {}
for cid in PILOT_LIGANDS:
    s = comparative[cid]
    a, b, g, d = s.get("PI3Kalpha"), s.get("PI3Kbeta"), s.get("PI3Kgamma"), s.get("PI3Kdelta")
    if None in (a, b, g, d):
        classifications[cid] = "unresolved"
        print(f"{cid:<24}{'N/A':>8}" * 1)
        continue
    # Vina score is more negative = stronger predicted binding. Delta_dock
    # convention: dock(alpha) - dock(other); a MORE NEGATIVE alpha score
    # (stronger alpha binding) with LESS negative others => positive
    # differential favors alpha (matches the project's pAct_alpha - pAct_X
    # sign convention: larger => alpha-preferential).
    d_ab, d_ag, d_ad = b - a, g - a, d - a
    diffs = [d_ab, d_ag, d_ad]
    if all(x > 1.0 for x in diffs):
        cls = "alpha-selective (computational)"
    elif all(abs(x) <= 1.0 for x in diffs):
        cls = "non-selective (computational)"
    elif min(diffs) < -1.0:
        cls = "other-isoform-selective (computational)"
    else:
        cls = "intermediate/ambiguous (computational)"
    classifications[cid] = cls
    print(f"{cid:<24}{a:>8.2f}{b:>8.2f}{g:>8.2f}{d:>8.2f}{d_ab:>8.2f}{d_ag:>8.2f}{d_ad:>8.2f}  {cls}")

out_path = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/docking_pilot_four_isoform_A4.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps([r.to_dict() for r in records], indent=2))
print(f"\nWrote {out_path} ({len(records)} records)")

comparative_out = {
    cid: {
        "docking_scores": comparative[cid],
        "delta_dock": {
            "alpha_vs_beta": comparative[cid].get("PI3Kbeta", 0) - comparative[cid].get("PI3Kalpha", 0)
            if None not in (comparative[cid].get("PI3Kalpha"), comparative[cid].get("PI3Kbeta")) else None,
            "alpha_vs_gamma": comparative[cid].get("PI3Kgamma", 0) - comparative[cid].get("PI3Kalpha", 0)
            if None not in (comparative[cid].get("PI3Kalpha"), comparative[cid].get("PI3Kgamma")) else None,
            "alpha_vs_delta": comparative[cid].get("PI3Kdelta", 0) - comparative[cid].get("PI3Kalpha", 0)
            if None not in (comparative[cid].get("PI3Kalpha"), comparative[cid].get("PI3Kdelta")) else None,
        },
        "classification": classifications[cid],
    }
    for cid in PILOT_LIGANDS
}
comp_path = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/docking_pilot_four_isoform_comparative_A4.json")
comp_path.write_text(json.dumps(comparative_out, indent=2))
print(f"Wrote {comp_path}")

n_success = sum(1 for r in records if r.outcome == DockingOutcome.SUCCESS)
n_total = len(records)
n_complete = sum(1 for cls in classifications.values() if cls != "unresolved")
print(f"\nSuccess rate: {n_success}/{n_total} ({100*n_success/n_total:.1f}%)")
print(f"Compounds with complete four-isoform profiles: {n_complete}/{len(PILOT_LIGANDS)}")
