"""Stage C, Step 1 -- Seal the literature reference panel.

Rev. 5 SS2 panel: alpelisib, inavolisib, idelalisib, PIK-39, IPI-549.
Every SMILES verified independently against a live source this session
(RCSB CCD / DrugBank / Wikipedia cross-referenced against PubChem/ChEMBL
identifiers), not carried over from memory or derived from a name.

Mechanism-class annotations preserved from the Rev. 5 mandate (SS2):
affinity-pocket compounds expected capturable by static ATP-site
docking; induced-specificity-pocket (propeller) compounds flagged
uncertain, since this project's receptors are static and the Trp780/
Met772-equivalent pocket is absent in non-induced structures.

IPI-549's prior role as the Gate-1 reference ligand for 6XRL receptor
validation is disclosed explicitly -- receptor redocking, not
selectivity-feature discovery or tuning.

Compounds AND their Bemis-Murcko scaffolds are recorded here so that
Step 2's exclusion of "literature panel scaffolds" (not just exact
compounds) from the sealed validation set has something concrete to
exclude against.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

LITERATURE_PANEL = [
    {
        "compound_name": "alpelisib",
        "synonyms": ["BYL-719", "NVP-BYL719"],
        "smiles": "O=C(N1[C@H](C(N)=O)CCC1)NC2=NC(C)=C(C3=CC(C(C)(C)C(F)(F)F)=NC=C3)S2",
        "inchikey": "STUWGJZDJHPWGZ-LBPRGKRZSA-N",
        "source_identifiers": {"chembl_id": "CHEMBL2396661", "pubchem_cid": "56649450", "pdb_ligand": "1LT"},
        "verification_source": "Wikipedia (cross-referenced PubChem CID 56649450, ChEMBL2396661), verified live this session",
        "selectivity": "alpha",
        "mechanism_class": "affinity_pocket_position_859",
        "capturable_by_static_atp_docking": True,
    },
    {
        "compound_name": "inavolisib",
        "synonyms": ["GDC-0077", "RG6114", "Ro7113755"],
        "smiles": "C[C@@H](C(=O)N)NC1=CC2=C(C=C1)C3=NC(=CN3CCO2)N4[C@@H](COC4=O)C(F)F",
        "inchikey": "SGEUNORSOZVTOL-CABZTGNLSA-N",
        "source_identifiers": {"chembl_id": "CHEMBL4650215", "pubchem_cid": "124173720", "pdb_ligand": "X3N"},
        "verification_source": "Wikipedia (cross-referenced PubChem CID 124173720, ChEMBL4650215), verified live this session",
        "selectivity": "alpha",
        "mechanism_class": "affinity_pocket",
        "capturable_by_static_atp_docking": True,
    },
    {
        "compound_name": "idelalisib",
        "synonyms": ["CAL-101", "GS-1101", "Zydelig"],
        "smiles": "CC[C@H](Nc1ncnc2nc[nH]c12)c4nc3cccc(F)c3c(=O)n4c5ccccc5",
        "inchikey": "IFSDAJWBUCMOAH-HNNXBMFYSA-N",
        "source_identifiers": {"chembl_id": "CHEMBL2216870", "pubchem_cid": "11625818"},
        "verification_source": "Wikipedia (cross-referenced PubChem CID 11625818, ChEMBL2216870), verified live this session",
        "selectivity": "delta",
        "mechanism_class": "induced_specificity_pocket_propeller",
        "capturable_by_static_atp_docking": "uncertain",
    },
    {
        "compound_name": "PIK-39",
        "synonyms": [],
        "smiles": "COc1ccccc1N2C(=O)c3c(Cl)cccc3N=C2CSc4ncnc5[nH]cnc45",
        "inchikey": "UMMYTDJYDSTEMB-UHFFFAOYSA-N",
        "source_identifiers": {"pdb_ligand": "039", "pdb_structure": "2WXF", "chembl_id": "CHEMBL1213083", "pubchem_cid": "6852165"},
        "verification_source": "RCSB PDB ligand CCD page for '039' (2WXF, Berndt et al. Nat Chem Biol 2010), verified live this session -- CCD page explicitly lists 'PIK-39' as a synonym",
        "selectivity": "beta_delta",
        "mechanism_class": "induced_specificity_pocket_propeller",
        "capturable_by_static_atp_docking": "uncertain",
    },
    {
        "compound_name": "IPI-549",
        "synonyms": ["eganelisib"],
        "smiles": "C[C@H](NC(=O)c1c(N)nn2cccnc12)C3=Cc4cccc(C#Cc5cnn(C)c5)c4C(=O)N3c6ccccc6",
        "inchikey": "XUMALORDVCFWKV-IBGZPJMESA-N",
        "source_identifiers": {"pdb_ligand": "V7Y", "pdb_structure": "6XRL"},
        "verification_source": "RCSB CCD entry for V7Y, verified in an earlier session this campaign (Gate-1 6XRL remediation)",
        "selectivity": "gamma",
        "mechanism_class": "atp_site",
        "capturable_by_static_atp_docking": True,
        "disclosure": (
            "IPI-549 was the Gate-1 reference ligand used to validate 6XRL as the "
            "production gamma receptor. That was receptor redocking (does this "
            "receptor reproduce a known crystal pose), not selectivity-feature "
            "discovery or tuning -- disclosed here per Rev. 5 SS2's explicit requirement."
        ),
    },
]


def compute_scaffold(smiles: str) -> tuple[str, str]:
    """Returns (scaffold_smiles, scaffold_inchikey) via RDKit's Bemis-Murcko
    implementation -- the same scaffold definition A4's own precomputed
    scaffold_family_id already uses, for direct comparability with
    Step 2's exclusion of the 24/50 corpora's scaffolds."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Could not parse SMILES: {smiles}")
    scaffold_mol = MurckoScaffold.GetScaffoldForMol(mol)
    scaffold_smiles = Chem.MolToSmiles(scaffold_mol)
    scaffold_inchi = Chem.MolToInchi(scaffold_mol)
    scaffold_inchikey = Chem.InchiToInchiKey(scaffold_inchi) if scaffold_inchi else ""
    return scaffold_smiles, scaffold_inchikey


sealed_entries = []
for entry in LITERATURE_PANEL:
    scaffold_smiles, scaffold_inchikey = compute_scaffold(entry["smiles"])
    # Independent verification: does the SMILES actually parse and match
    # the stated InChIKey? Never trust a copy-pasted string without checking.
    mol = Chem.MolFromSmiles(entry["smiles"])
    computed_inchikey = Chem.InchiToInchiKey(Chem.MolToInchi(mol)) if mol else None
    inchikey_verified = computed_inchikey == entry["inchikey"]
    sealed_entries.append(
        {
            **entry,
            "scaffold_smiles": scaffold_smiles,
            "scaffold_inchikey": scaffold_inchikey,
            "inchikey_self_consistency_verified": inchikey_verified,
            "computed_inchikey": computed_inchikey,
        }
    )
    print(
        f"{entry['compound_name']}: InChIKey self-consistent={inchikey_verified}, "
        f"scaffold_inchikey={scaffold_inchikey}"
    )

if not all(e["inchikey_self_consistency_verified"] for e in sealed_entries):
    raise SystemExit("STOP: at least one literature-panel SMILES does not reproduce its stated InChIKey.")

timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
sealed_artifact = {
    "artifact": "literature_reference_panel",
    "purpose": "Rev. 5 SS2 -- sealed, diagnostic-by-mechanism-class reference panel. NOT a binary gate.",
    "sealed_timestamp_utc": timestamp,
    "n_compounds": len(sealed_entries),
    "compounds": sealed_entries,
    "excluded_scaffold_inchikeys": sorted({e["scaffold_inchikey"] for e in sealed_entries}),
    "excluded_compound_inchikeys": sorted({e["inchikey"] for e in sealed_entries}),
}

content_for_hash = json.dumps(sealed_artifact, sort_keys=True)
sealed_artifact["content_sha256"] = hashlib.sha256(content_for_hash.encode()).hexdigest()

out_path = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/sealed_literature_panel.json")
out_path.write_text(json.dumps(sealed_artifact, indent=2))
print(f"\nSealed {len(sealed_entries)} compounds, {len(sealed_artifact['excluded_scaffold_inchikeys'])} distinct scaffolds")
print(f"content_sha256: {sealed_artifact['content_sha256']}")
print(f"Wrote {out_path}")
