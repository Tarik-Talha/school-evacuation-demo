"""Resolve bundled source plans independently of the original workstation."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parent
PLAN_ROOT = ROOT / "assets" / "plans"


# =========================================================
# PORTABLE SOURCE ASSETS WITH PATH AND HASH VALIDATION
# =========================================================
def source_plan(relative_path, expected_sha256=None):
    """Only return an existing, unmodified asset inside this project's plans."""
    candidate = (ROOT / relative_path).resolve()
    if not candidate.is_relative_to(PLAN_ROOT.resolve()) or not candidate.is_file():
        raise ValueError("Kaynak planın proje içindeki kopyası bulunamadı.")
    if expected_sha256 and hashlib.sha256(candidate.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("Plan fotoğrafı kaynak kaydıyla eşleşmiyor.")
    return candidate
