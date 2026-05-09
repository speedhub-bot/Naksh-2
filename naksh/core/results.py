"""Per-job result directory + final zip bundling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import SETTINGS
from ..utils.files import append_dedupe, append_line, zip_directory


CATEGORIES = (
    "Hits", "XGPU", "XGP", "Normal", "2fa", "Bad", "Errors",
    "Capture", "MS_Balance", "MS_Points", "MS_Payments",
    "Hypixel_Capture", "Donut_Capture",
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

    def make_zip(self) -> Path:
        return zip_directory(
            self.job_dir,
            self.job_dir.with_suffix(".zip"),
            include_patterns=("*.txt",),
        )

    def hits_file(self) -> Path:
        return self.path_for("Hits")
