import json
import os
from pathlib import Path
from typing import Any

import pypdf


class PDFFingerprintRegistry:
    def __init__(self, fixtures_dir: Path | None = None) -> None:
        if fixtures_dir is None:
            # Resolve to root fixtures/pdf
            self.fixtures_dir = Path(__file__).resolve().parents[3] / "fixtures" / "pdf"
        else:
            self.fixtures_dir = fixtures_dir

    def _get_fingerprints(self) -> dict[str, dict[str, Any]]:
        """Scans the fixtures directory for fingerprint json files."""
        fingerprints: dict[str, dict[str, Any]] = {}
        search_dirs = [self.fixtures_dir, Path("/fixtures/pdf"), Path("fixtures/pdf")]

        for search_dir in search_dirs:
            if search_dir.is_dir():
                for filename in os.listdir(search_dir):
                    if filename.endswith(".fingerprint.json"):
                        template_key = filename[:-17]  # strip .fingerprint.json
                        if template_key not in fingerprints:
                            try:
                                with open(search_dir / filename, encoding="utf-8") as f:
                                    data = json.load(f)
                                    fingerprints[template_key] = data
                            except Exception:
                                pass
        return fingerprints

    def match_document(
        self, filepath: str, analysis: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Matches a document against registered fingerprints."""
        fingerprints = self._get_fingerprints()
        matches: list[dict[str, Any]] = []

        reader = None
        try:
            reader = pypdf.PdfReader(filepath)
        except Exception:
            pass

        for _, fp in fingerprints.items():
            if self._evaluate_match(analysis, fp, reader):
                matches.append(fp)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Ambiguous matches: reject (return None)
            return None
        return None

    def _evaluate_match(
        self,
        analysis: dict[str, Any],
        fp: dict[str, Any],
        reader: pypdf.PdfReader | None,
    ) -> bool:
        # 1. Page count must match
        if analysis.get("page_count") != fp.get("pageCount"):
            return False

        # 2. Page sizes must match within tolerance
        fp_sizes = fp.get("pageSizes", [])
        pages = analysis.get("pages", [])
        for idx, page in enumerate(pages):
            if idx >= len(fp_sizes):
                return False
            fp_size = fp_sizes[idx]
            width_diff = abs(page["width"] - fp_size["width"])
            height_diff = abs(page["height"] - fp_size["height"])
            tolerance = fp_size.get("tolerance", 2.0)
            if width_diff > tolerance or height_diff > tolerance:
                return False

        # 3. Required AcroForm fields must be present
        required_fields = fp.get("requiredAcroFormFields", [])
        if required_fields:
            if not analysis.get("has_acroform"):
                return False
            # Get actual field names
            actual_fields = {f["name"] for f in analysis.get("acroform_fields", [])}
            for req_field in required_fields:
                if req_field not in actual_fields:
                    return False

        # 4. Optional Text Markers must be present if specified
        text_markers = fp.get("optionalTextMarkers", [])
        if text_markers:
            if not reader:
                return False
            # Extract text to search for markers
            full_text = ""
            for page in reader.pages:
                try:
                    full_text += page.extract_text() or ""
                except Exception:
                    pass
            for marker in text_markers:
                if marker not in full_text:
                    return False

        return True
