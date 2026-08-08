"""Provenance manifests for the SCI0-011 snapshot.

SoftwareProvenance  — RDKit, Python, git SHA, OS, lock hash
PolicyManifest      — harmonization policy versions, rule-set IDs

Neither is cosmetic metadata, but per GDR-010 (accepted, Option A) they
play different roles in snapshot identity:

  PolicyManifest      — enters `snapshot_sha256` (scientific identity).
                        Changing any policy version produces a new
                        scientific snapshot, because a policy change can
                        change what the records mean.
  SoftwareProvenance  — enters `build_provenance_sha256` ONLY.  It is
                        recorded and fully reportable, but a toolchain or
                        environment change (git SHA, RDKit version, OS, ...)
                        does NOT by itself change scientific snapshot
                        identity — the same data, correctly rebuilt, is the
                        same science regardless of the machine that built it.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ── Lazy RDKit import (optional; records "not_installed" if absent) ────────────
try:
    from rdkit import __version__ as _RDKIT_VERSION_STR  # noqa: N812

    _RDKIT_AVAILABLE = True
except ImportError:
    _RDKIT_VERSION_STR = "not_installed"
    _RDKIT_AVAILABLE = False


def _git_sha(repo_root: Path | None = None) -> str:
    root = repo_root or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:  # noqa: S110
        pass
    return "unknown"


def _git_dirty(repo_root: Path | None = None) -> bool:
    root = repo_root or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def _lockfile_hash(repo_root: Path | None = None) -> str | None:
    root = repo_root or Path.cwd()
    for candidate in [
        "requirements.lock",
        "requirements-lock.txt",
        "pdm.lock",
        "poetry.lock",
        "uv.lock",
    ]:
        p = root / candidate
        if p.exists():
            return hashlib.sha256(p.read_bytes()).hexdigest()
    return None


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


@dataclass(frozen=True, slots=True)
class SoftwareProvenance:
    """Full software provenance — part of snapshot identity.

    ENG §13: RDKit version, Python version, dependency lock hash, git SHA,
    OS, pipeline version.
    """

    python_version: str
    rdkit_version: str
    orthosteric_version: str
    git_sha: str
    git_dirty: bool
    os_platform: str
    os_version: str
    lockfile_hash: str | None
    key_package_versions: dict[str, str]

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "git_dirty": self.git_dirty,
            "git_sha": self.git_sha,
            "key_package_versions": dict(sorted(self.key_package_versions.items())),
            "lockfile_hash": self.lockfile_hash,
            "orthosteric_version": self.orthosteric_version,
            "os_platform": self.os_platform,
            "os_version": self.os_version,
            "python_version": self.python_version,
            "rdkit_version": self.rdkit_version,
        }

    @classmethod
    def collect(cls, repo_root: Path | None = None) -> SoftwareProvenance:
        key_packages = {
            "rdkit": _RDKIT_VERSION_STR,
            "orthosteric": _package_version("orthosteric"),
        }
        for pkg in ("numpy", "pandas"):
            key_packages[pkg] = _package_version(pkg)
        return cls(
            python_version=sys.version,
            rdkit_version=_RDKIT_VERSION_STR,
            orthosteric_version=_package_version("orthosteric"),
            git_sha=_git_sha(repo_root),
            git_dirty=_git_dirty(repo_root),
            os_platform=platform.system(),
            os_version=platform.version(),
            lockfile_hash=_lockfile_hash(repo_root),
            key_package_versions=key_packages,
        )


# ── Lazy policy imports (avoid circular at module level) ──────────────────────


def _get_chem_std_policy() -> str:
    from orthosteric.data.harmonization._chem_standardizer import (  # noqa: PLC0415
        ChemicalStandardizer,
    )

    return f"sci0008b_rdkit_{ChemicalStandardizer().rdkit_version}"


def _get_dedup_policy() -> tuple[str, str]:
    from orthosteric.data.harmonization._deduplicator import Deduplicator  # noqa: PLC0415

    # WITHIN_GROUP_CONFLICT_THRESHOLD is RULE_MISSING until SCI0-016 seals it
    return Deduplicator.POLICY_ID, "RULE_MISSING/SCI0-016_required"


def _get_confidence_policy() -> tuple[str, str, str]:
    try:
        from orthosteric.data.harmonization._confidence import POLICY_VERSION  # noqa: PLC0415

        return (
            f"sci0010_{POLICY_VERSION}",
            "RULE_MISSING/SCI0-010_not_yet_governed",
            "RULE_MISSING/SCI0-010_not_yet_governed",
        )
    except ImportError:
        return "RULE_MISSING", "RULE_MISSING", "RULE_MISSING"


@dataclass(frozen=True, slots=True)
class PolicyManifest:
    """Version-controlled pipeline policy identifiers."""

    chemical_standardization_policy: str
    identifier_harmonization_policy: str
    deduplication_policy: str
    confidence_scoring_policy: str
    adr0003_adjudication_procedure: str
    alphafold_fallback_policy: str
    auditor5_status: str
    cheng_prusoff_status: str
    within_group_conflict_threshold: str
    confidence_assay_quality_rule: str
    confidence_lit_tier_rule: str

    def to_canonical_dict(self) -> dict[str, str]:
        return {
            "adr0003_adjudication_procedure": self.adr0003_adjudication_procedure,
            "alphafold_fallback_policy": self.alphafold_fallback_policy,
            "auditor5_status": self.auditor5_status,
            "chemical_standardization_policy": self.chemical_standardization_policy,
            "cheng_prusoff_status": self.cheng_prusoff_status,
            "confidence_assay_quality_rule": self.confidence_assay_quality_rule,
            "confidence_lit_tier_rule": self.confidence_lit_tier_rule,
            "confidence_scoring_policy": self.confidence_scoring_policy,
            "deduplication_policy": self.deduplication_policy,
            "identifier_harmonization_policy": self.identifier_harmonization_policy,
            "within_group_conflict_threshold": self.within_group_conflict_threshold,
        }

    @classmethod
    def current(cls) -> PolicyManifest:
        chem_std_policy = _get_chem_std_policy()
        dedup_policy, wg_threshold = _get_dedup_policy()
        conf_policy, assay_q_rule, lit_tier_rule = _get_confidence_policy()
        return cls(
            chemical_standardization_policy=chem_std_policy,
            identifier_harmonization_policy="sci0008c_inchikey_v1",
            deduplication_policy=dedup_policy,
            confidence_scoring_policy=conf_policy,
            adr0003_adjudication_procedure="adr0003_procedure_v1.0",
            alphafold_fallback_policy="sci0007_af_fallback_v1.0",
            auditor5_status="INSUFFICIENT_EVIDENCE_frozen",
            cheng_prusoff_status="BLOCKED/AUDITOR-5",
            within_group_conflict_threshold=wg_threshold,
            confidence_assay_quality_rule=assay_q_rule,
            confidence_lit_tier_rule=lit_tier_rule,
        )
