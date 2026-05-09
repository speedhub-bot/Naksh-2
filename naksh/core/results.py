"""Per-job result directory + final zip bundling.

Knows how to:
- Write results into a per-category text file
- Dedupe lines for capture-style files
- Sort numeric capture files (MS_Points / MS_Balance) by value descending,
  so the best hits land at the top of each file
- Bundle everything into a single ``.zip`` for delivery
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from ..config import SETTINGS
from ..utils.files import append_dedupe, append_line, zip_directory

log = logging.getLogger(__name__)


CATEGORIES = (
    # Hit / status pools
    "Hits", "XGPU", "XGP", "Normal", "MSA", "2fa", "Bad", "Errors",
    # Pretty capture
    "Capture",
    # Microsoft enrichment
    "MS_Balance", "MS_Points", "MS_Payments",
    "MS_Subscriptions", "MS_RedeemHistory", "MS_Orders", "MS_Profile",
    # Xbox enrichment
    "Xbox_Profile",
    # Minecraft / external
    "Hypixel_Capture", "Hypixel_Bans",
    "Donut_Capture", "Donut_Bans",
)

# Files that should be sorted (descending) by the leading numeric value at job
# end. Each entry: (category, regex_extracting_number).
SORTED_DESCENDING = (
    ("MS_Points", re.compile(r"\| points=([0-9]+)")),
    ("MS_Balance", re.compile(r"\| value=([0-9]+(?:\.[0-9]+)?)")),
)


@dataclass
class ResultStore:
    """Filesystem result store for one check job."""
    job_dir: Path
    job_label: str

    @classmethod
    def for_job(cls, user_id: int, job_id: int | str) -> "ResultStore":
        label = f"{user_id}_{job_id}"
        path = SETTINGS.results_dir / label
        path.mkdir(parents=True, exist_ok=True)
        return cls(job_dir=path, job_label=label)

    def path_for(self, category: str) -> Path:
        if category not in CATEGORIES:
            raise ValueError(f"unknown category {category!r}")
        return self.job_dir / f"{category}.txt"

    def write(self, category: str, line: str) -> None:
        append_line(self.path_for(category), line)

    def write_dedupe(self, category: str, line: str) -> None:
        append_dedupe(self.path_for(category), line)

    # ------------------------------------------------------------------
    def finalize(self) -> None:
        """Apply post-job transforms (sorting, summary) before zipping."""
        for category, pattern in SORTED_DESCENDING:
            self._sort_descending(self.path_for(category), pattern)

    def _sort_descending(self, path: Path, pattern: re.Pattern) -> None:
        if not path.exists():
            return
        try:
            lines = [ln for ln in path.read_text(
                encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
            def key(line: str) -> float:
                m = pattern.search(line)
                return -float(m.group(1)) if m else 0.0  # negative → desc
            lines.sort(key=key)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as e:
            log.warning("sort failed for %s: %s", path, e)

    def make_zip(self) -> Path:
        return zip_directory(
            self.job_dir,
            self.job_dir.with_suffix(".zip"),
            include_patterns=("*.txt",),
        )

    def hits_file(self) -> Path:
        return self.path_for("Hits")
