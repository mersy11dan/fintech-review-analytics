"""Shared utility functions for the project."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_project_path(*parts: str) -> Path:
    """Return an absolute path inside the project root."""
    return PROJECT_ROOT.joinpath(*parts)


def ensure_directory(path: Path) -> Path:
    """Create a directory when missing and return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path
