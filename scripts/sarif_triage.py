#!/usr/bin/env python3
"""
sarif_triage.py — CodeQL SARIF CVSS v3.1 Triage and Auto-Scorer.
Parses static analysis results, assigns CVSS base scores, and summarizes risk levels.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import sys
from typing import Any


@dataclass
class TriageFinding:
    rule_id: str
    message: str
    file_path: str
    start_line: int
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    cvss_score: float


class SarifTriager:
    SEVERITY_MAP = {
        "error": "HIGH",
        "warning": "MEDIUM",
        "note": "LOW",
        "none": "INFO",
    }

    def __init__(self, min_fail_cvss: float = 7.0):
        self.min_fail_cvss = float(min_fail_cvss)

    def parse_sarif(self, sarif_dict: dict[str, Any]) -> list[TriageFinding]:
        findings: list[TriageFinding] = []
        runs = sarif_dict.get("runs", [])
        for run in runs:
            rules_by_id = {r.get("id"): r for r in run.get("tool", {}).get("driver", {}).get("rules", [])}
            results = run.get("results", [])
            for res in results:
                rule_id = str(res.get("ruleId") or "UNKNOWN")
                rule_meta = rules_by_id.get(rule_id, {})
                msg = res.get("message", {}).get("text", "")
                
                # Resolve location
                locations = res.get("locations", [])
                file_path = "unknown"
                start_line = 1
                if locations:
                    phys = locations[0].get("physicalLocation", {})
                    file_path = phys.get("artifactLocation", {}).get("uri", "unknown")
                    start_line = phys.get("region", {}).get("startLine", 1)

                # Determine CVSS Score & Severity
                raw_level = str(res.get("level") or rule_meta.get("defaultConfiguration", {}).get("level") or "warning").lower()
                cvss_str = rule_meta.get("properties", {}).get("security-severity")
                if cvss_str:
                    try:
                        cvss_score = float(cvss_str)
                    except ValueError:
                        cvss_score = 5.0
                else:
                    cvss_score = 8.5 if raw_level == "error" else (5.5 if raw_level == "warning" else 2.0)

                severity = self._score_to_severity(cvss_score)
                findings.append(TriageFinding(
                    rule_id=rule_id,
                    message=msg,
                    file_path=file_path,
                    start_line=start_line,
                    severity=severity,
                    cvss_score=cvss_score,
                ))
        return findings

    def _score_to_severity(self, score: float) -> str:
        if score >= 9.0:
            return "CRITICAL"
        if score >= 7.0:
            return "HIGH"
        if score >= 4.0:
            return "MEDIUM"
        if score >= 0.1:
            return "LOW"
        return "INFO"

    def evaluate(self, findings: list[TriageFinding]) -> dict[str, Any]:
        critical_count = sum(1 for f in findings if f.severity == "CRITICAL")
        high_count = sum(1 for f in findings if f.severity == "HIGH")
        medium_count = sum(1 for f in findings if f.severity == "MEDIUM")
        low_count = sum(1 for f in findings if f.severity in {"LOW", "INFO"})

        pass_status = (critical_count == 0) and (high_count == 0)
        return {
            "pass": pass_status,
            "total_findings": len(findings),
            "summary": {
                "CRITICAL": critical_count,
                "HIGH": high_count,
                "MEDIUM": medium_count,
                "LOW": low_count,
            },
        }


def main():
    parser = argparse.ArgumentParser(description="CodeQL SARIF CVSS v3.1 Triage")
    parser.add_argument("sarif_file", help="Path to SARIF JSON file")
    args = parser.parse_args()

    with open(args.sarif_file, "r") as f:
        data = json.load(f)

    triager = SarifTriager()
    findings = triager.parse_sarif(data)
    report = triager.evaluate(findings)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
