#!/usr/bin/env python3
"""
AI Ensemble — Comprehensive Test Runner & Report Generator
===========================================================

Usage:
    python scripts/run-tests.py                        # Run backend tests
    python scripts/run-tests.py --coverage              # Run with coverage report
    python scripts/run-tests.py --infra                 # Include infrastructure checks
    python scripts/run-tests.py --quick                 # Run only core tests (skip slow)
    python scripts/run-tests.py --view                  # View most recent report

The script:
  1.  Captures the current git version (tag + commit hash + date)
  2.  Runs pytest against backend/tests/ with JUnit XML output
  3.  Parses results and generates a professional markdown report
  4.  Saves report as: reports/test-report_{VERSION}_{YYYYMMDD}_{HHMM}.md
"""

import argparse
import csv
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
REPORTS_DIR = PROJECT_ROOT / "reports"
TESTS_DIR = BACKEND_DIR / "tests"
VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"


def run_command(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 300) -> Tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd or PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except FileNotFoundError:
        return -2, "", f"Command not found: {cmd[0]}"


def get_git_version() -> Dict[str, str]:
    """Extract git version information for the current HEAD."""
    info = {
        "commit_hash": "unknown",
        "commit_short": "unknown",
        "tag": "no-tag",
        "branch": "unknown",
        "commit_date": "unknown",
        "version_string": "unknown",
    }

    rc, out, _ = run_command(["git", "log", "--format=%H", "-1"])
    if rc == 0:
        info["commit_hash"] = out.strip()
        info["commit_short"] = out.strip()[:12]

    rc, out, _ = run_command(["git", "log", "--format=%cs", "-1"])
    if rc == 0:
        info["commit_date"] = out.strip()

    rc, out, _ = run_command(["git", "describe", "--tags", "--exact-match", "HEAD"])
    if rc == 0:
        info["tag"] = out.strip()

    rc, out, _ = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if rc == 0:
        info["branch"] = out.strip()

    tag_part = info["tag"] if info["tag"] != "no-tag" else info["commit_short"]
    info["version_string"] = f"v{tag_part}"
    if info["tag"] != info["commit_short"]:
        info["version_string"] = f"{tag_part}"

    return info


def run_pytest(extra_args: Optional[List[str]] = None) -> Tuple[int, str, str]:
    """Run pytest and return (returncode, xml_output_path, raw_stdout)."""
    os.chdir(str(BACKEND_DIR))

    junit_xml = REPORTS_DIR / "pytest-results.xml"
    python = str(VENV_PYTHON if VENV_PYTHON.exists() else sys.executable)

    cmd = [
        python, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        f"--junitxml={junit_xml}",
    ]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'='*60}")
    print(f"  Running: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    rc, stdout, stderr = run_command(cmd, cwd=BACKEND_DIR, timeout=600)

    if junit_xml.exists():
        xml_content = junit_xml.read_text()
    else:
        xml_content = ""

    return rc, xml_content, stdout + "\n" + stderr


def parse_junit_xml(xml_content: str) -> Dict[str, Any]:
    """Parse JUnit XML into a structured results dictionary."""
    if not xml_content.strip():
        return {"testsuite": {"name": "pytest", "tests": 0, "failures": 0, "errors": 0, "skipped": 0, "testcases": []}}

    root = ET.fromstring(xml_content)
    testsuite = root[0] if root.tag == "testsuites" else root

    total = int(testsuite.get("tests", 0))
    failures = int(testsuite.get("failures", 0))
    errors = int(testsuite.get("errors", 0))
    skipped = int(testsuite.get("skipped", 0))
    time_sec = float(testsuite.get("time", 0))

    testcases = []
    for tc in testsuite.iter("testcase"):
        classname = tc.get("classname", "").replace("tests.", "")
        name = tc.get("name", "")
        tc_time = float(tc.get("time", 0))
        status = "PASSED"
        message = ""

        failure = tc.find("failure")
        error = tc.find("error")
        skipped_el = tc.find("skipped")

        if failure is not None:
            status = "FAILED"
            message = (failure.get("message", "") or failure.text or "")[:500]
        elif error is not None:
            status = "ERROR"
            message = (error.get("message", "") or error.text or "")[:500]
        elif skipped_el is not None:
            status = "SKIPPED"
            message = (skipped_el.get("message", "") or skipped_el.text or "")[:200]

        testcases.append({
            "class": classname,
            "name": name,
            "status": status,
            "time": tc_time,
            "message": message,
        })

    # Compute passed count
    passed = total - failures - errors - skipped

    return {
        "testsuite": {
            "name": testsuite.get("name", "pytest"),
            "tests": total,
            "passed": passed,
            "failures": failures,
            "errors": errors,
            "skipped": skipped,
            "time": time_sec,
        },
        "testcases": testcases,
    }


def group_by_module(testcases: List[Dict]) -> Dict[str, List[Dict]]:
    """Group test cases by module (class name prefix)."""
    groups: Dict[str, List[Dict]] = {}
    for tc in testcases:
        module = tc["class"].split(".")[0] if tc["class"] else "other"
        if module not in groups:
            groups[module] = []
        groups[module].append(tc)
    return groups


def classify_test_name(name: str) -> str:
    """Map test name to functional area for reporting."""
    mapping = [
        ("register", "User Registration"),
        ("login", "User Login / Auth"),
        ("duplicate", "Duplicate Handling"),
        ("invalid", "Input Validation"),
        ("short", "Input Validation"),
        ("unauthenticated", "Access Control"),
        ("invalid_token", "Token Validation"),
        ("health", "Health Check"),
        ("create_discussion", "Discussion Creation"),
        ("list_discussions", "Discussion Listing"),
        ("discussion_isolation", "Data Isolation"),
        ("create_message", "Message Creation"),
        ("list_messages", "Message Retrieval"),
        ("wrong_discussion", "Access Control"),
        ("empty_question", "Input Validation"),
        ("save_provider", "Provider Save"),
        ("list_providers", "Provider Listing"),
        ("update_existing", "Provider Update"),
        ("discover_models", "Model Discovery"),
        ("multiple_providers", "Provider Management"),
        ("provider_data_isolation", "Data Isolation"),
        ("proxy_chat_no_credentials", "Proxy Chat"),
        ("proxy_chat_with_rag", "RAG Injection"),
        ("proxy_chat_invalid", "Proxy Chat"),
        ("proxy_chat_requires", "Input Validation"),
        ("chat_request_schema", "Schema Validation"),
        ("encrypt_decrypt", "Encryption"),
        ("different_uek", "UEK Isolation"),
        ("wrong_uek", "UEK Security"),
        ("encrypt_field", "Field Encryption"),
        ("decrypt_field", "Field Decryption"),
        ("rate_limiting", "Rate Limiting"),
        ("cors", "CORS Headers"),
        ("extract_ddg", "URL Extraction"),
        ("search_web_no_engines", "RAG Pipeline"),
        ("search_web_deduplicates", "RAG Deduplication"),
        ("search_web_one_engine_fails", "RAG Resilience"),
        ("search_web_respects", "RAG Limits"),
        ("extract_content_empty", "Content Extraction"),
        ("get_retrieved_context_no", "RAG Pipeline"),
        ("get_retrieved_context_returns", "RAG Context"),
        ("get_retrieved_context_engine", "Engine Attribution"),
        ("topic_categories", "Topic Coverage"),
        ("all_topics_have", "Topic Coverage"),
        ("classify_", "Topic Classification"),
        ("generic_query", "Topic Classification"),
        ("enrich_", "Query Enrichment"),
        ("sub_keyword", "Sub-Keyword Scoring"),
        ("no_topic_dominated", "Classifier Robustness"),
        ("data_isolation", "Data Isolation"),
        ("encrypted_discussion", "Encrypted Storage"),
    ]
    for pattern, area in mapping:
        if pattern in name:
            return area
    return "General"


def generate_report(
    version_info: Dict[str, str],
    pytest_results: Dict[str, Any],
    raw_output: str,
    pytest_rc: int,
    coverage_results: Optional[str] = None,
    infra_results: Optional[str] = None,
    start_time: float = 0,
) -> str:
    """Generate the full markdown report."""
    ts = datetime.datetime.now()
    suite = pytest_results["testsuite"]
    testcases = pytest_results["testcases"]
    groups = group_by_module(testcases)
    duration = time.time() - start_time

    # Build status badges
    if suite["failures"] == 0 and suite["errors"] == 0:
        overall_badge = "🟢 **PASS**"
        overall_status = "All tests passed successfully."
    elif suite["failures"] > 0 or suite["errors"] > 0:
        overall_badge = "🔴 **FAIL**"
        overall_status = f"{suite['failures'] + suite['errors']} test(s) failed. Requires investigation."
    else:
        overall_badge = "🟡 **INCOMPLETE**"
        overall_status = "Test execution did not complete."

    # === Build report ===
    lines = []
    _a = lines.append
    _a(f"# 🧪 AI Ensemble — Test Execution Report")
    _a(f"")
    _a(f"**Report generated:** {ts.strftime('%Y-%m-%d %H:%M:%S')}  ")
    _a(f"**Git commit:** `{version_info['commit_hash']}`  ")
    _a(f"**Git tag:** `{version_info['tag']}`  ")
    _a(f"**Git branch:** `{version_info['branch']}`  ")
    _a(f"**Test run duration:** {duration:.1f}s  ")
    _a(f"")
    _a(f"---")
    _a(f"")

    # === Executive Summary ===
    _a(f"## 📊 Executive Summary")
    _a(f"")
    _a(f"| Metric | Value |")
    _a(f"|--------|-------|")
    _a(f"| **Overall Status** | {overall_badge} |")
    _a(f"| **Total Tests** | {suite['tests']} |")
    _a(f"| **Passed** | {suite['passed']} |")
    _a(f"| **Failed** | {suite['failures']} |")
    _a(f"| **Errors** | {suite['errors']} |")
    _a(f"| **Skipped** | {suite['skipped']} |")
    _a(f"| **Pass Rate** | {100 * suite['passed'] / max(suite['tests'], 1):.1f}% |")
    _a(f"| **Execution Time** | {suite['time']:.2f}s |")
    _a(f"")
    _a(f"**Verdict:** {overall_status}  ")
    _a(f"")

    # === Environment ===
    _a(f"## 🖥️ Test Environment")
    _a(f"")
    _a(f"| Parameter | Value |")
    _a(f"|----------|-------|")
    _a(f"| **Host** | {platform.node()} |")
    _a(f"| **OS** | {platform.system()} {platform.release()} |")
    _a(f"| **Python** | {platform.python_version()} |")
    _a(f"| **Git Version** | `{version_info['version_string']}` |")
    _a(f"| **Git Commit** | `{version_info['commit_hash']}` |")
    _a(f"| **Git Tag** | `{version_info['tag']}` |")
    _a(f"| **Test Framework** | pytest {_get_pytest_version()} |")
    _a(f"| **Report File** | `{_get_report_filename(version_info, ts)}` |")
    _a(f"")

    # === Functional Area Coverage ===
    _a(f"## ✅ Functional Area Coverage")
    _a(f"")
    _a(f"| Functional Area | Tests | Passed | Failed | Errors | Status |")
    _a(f"|----------------|------:|-------:|-------:|-------:|--------|")

    area_stats: Dict[str, Dict] = {}
    for tc in testcases:
        area = classify_test_name(tc["name"])
        if area not in area_stats:
            area_stats[area] = {"total": 0, "passed": 0, "failed": 0, "errors": 0}
        area_stats[area]["total"] += 1
        if tc["status"] == "PASSED":
            area_stats[area]["passed"] += 1
        elif tc["status"] == "FAILED":
            area_stats[area]["failed"] += 1
        elif tc["status"] == "ERROR":
            area_stats[area]["errors"] += 1

    for area, stats in sorted(area_stats.items()):
        badge = "🟢" if stats["failed"] == 0 and stats["errors"] == 0 else "🔴"
        _a(f"| **{area}** | {stats['total']} | {stats['passed']} | {stats['failed']} | {stats['errors']} | {badge} |")
    _a(f"")

    # === Detailed Results by Module ===
    _a(f"## 📋 Detailed Test Results")
    _a(f"")

    for module_name in sorted(groups.keys()):
        tcs = groups[module_name]
        mod_passed = sum(1 for t in tcs if t["status"] == "PASSED")
        mod_failed = sum(1 for t in tcs if t["status"] in ("FAILED", "ERROR"))
        mod_badge = "🟢" if mod_failed == 0 else "🔴"

        _a(f"### {mod_badge} `{module_name}` — {mod_passed}/{len(tcs)} passed")
        _a(f"")
        _a(f"| Test Name | Status | Time (s) | Notes |")
        _a(f"|-----------|--------|---------:|-------|")

        for tc in tcs:
            status_badge = {
                "PASSED": "🟢 PASSED",
                "FAILED": "🔴 FAILED",
                "ERROR": "⛔ ERROR",
                "SKIPPED": "🟡 SKIPPED",
            }.get(tc["status"], tc["status"])

            msg = tc["message"][:120].replace("\n", " ") if tc["message"] else "—"
            _a(f"| `{tc['name']}` | {status_badge} | {tc['time']:.2f} | {msg} |")

        _a(f"")

    # === Failed Tests Detail ===
    failures = [tc for tc in testcases if tc["status"] in ("FAILED", "ERROR")]
    if failures:
        _a(f"## 🔥 Failed Tests — Root Cause Analysis")
        _a(f"")
        for i, tc in enumerate(failures, 1):
            _a(f"### {i}. `{tc['class']}::{tc['name']}`")
            _a(f"")
            _a(f"- **Status:** {tc['status']}  ")
            _a(f"- **Module:** `{tc['class']}`  ")
            _a(f"- **Test:** `{tc['name']}`  ")
            if tc["message"]:
                _a(f"- **Error:**")
                _a(f"```")
                _a(f"{tc['message'][:800]}")
                _a(f"```")
            _a(f"")

    # === Coverage Report ===
    if coverage_results:
        _a(f"## 📈 Code Coverage Summary")
        _a(f"")
        _a(f"```")
        _a(f"{coverage_results}")
        _a(f"```")
        _a(f"")

    # === Infrastructure Checks ===
    if infra_results:
        _a(f"## 🏗️ Infrastructure Verification")
        _a(f"")
        _a(f"{infra_results}")
        _a(f"")

    # === Raw Output ===
    _a(f"## 📜 Raw Test Output (last 80 lines)")
    _a(f"")
    _a(f"```")
    out_lines = raw_output.split("\n")
    _a("\n".join(out_lines[-80:]))
    _a(f"```")
    _a(f"")

    # === Footer ===
    _a(f"---")
    _a(f"*Report auto-generated by `scripts/run-tests.py` at {ts.strftime('%Y-%m-%d %H:%M:%S')}*  ")
    _a(f"*Source version: `{version_info['version_string']}` (`{version_info['commit_short']}`)*  ")

    return "\n".join(lines)


def _get_pytest_version() -> str:
    try:
        import pytest as p
        return p.__version__
    except Exception:
        return "unknown"


def _get_report_filename(version_info: Dict[str, str], ts: datetime.datetime) -> str:
    safe_version = version_info["version_string"].replace("/", "-").replace(":", "-")
    return f"test-report_{safe_version}_{ts.strftime('%Y%m%d_%H%M')}.md"


def check_infrastructure() -> str:
    """Run infrastructure health checks and return markdown."""
    lines = []
    _a = lines.append
    _a(f"### Kubernetes Cluster")
    _a(f"")
    _a(f"```")

    rc, out, _ = run_command(["kubectl", "get", "pods", "-n", "ai-ensemble"])
    if rc == 0:
        _a(out.strip())
    else:
        _a("kubectl not available or cluster unreachable")

    _a(f"```")
    _a(f"")

    rc, out, _ = run_command(["kubectl", "get", "svc", "-n", "ai-ensemble"])
    if rc == 0:
        _a(f"```")
        _a(out.strip())
        _a(f"```")
        _a(f"")

    # Check Docker Compose
    _a(f"### Docker Compose")
    _a(f"")
    rc, out, _ = run_command(["docker", "compose", "ps", "--services"], cwd=PROJECT_ROOT, timeout=30)
    if rc == 0:
        _a(f"```")
        _a(out.strip())
        _a(f"```")
    else:
        _a(f"Docker Compose not available  ")
    _a(f"")

    return "\n".join(lines)


def run_coverage() -> str:
    """Run pytest with coverage and return output."""
    python = str(VENV_PYTHON if VENV_PYTHON.exists() else sys.executable)
    cmd = [
        python, "-m", "pytest",
        "tests/",
        "--cov=app/",
        "--cov-report=term",
        "--tb=short",
    ]
    rc, stdout, stderr = run_command(cmd, cwd=BACKEND_DIR, timeout=600)
    return stdout + "\n" + stderr


def view_latest_report() -> None:
    """Find and display the most recent report."""
    reports = sorted(REPORTS_DIR.glob("test-report_*.md"), reverse=True)
    if not reports:
        print("No reports found in reports/")
        return
    latest = reports[0]
    print(f"\n{'='*60}")
    print(f"  Latest report: {latest.name}")
    print(f"{'='*60}\n")
    print(latest.read_text())


def main():
    parser = argparse.ArgumentParser(
        description="AI Ensemble — Comprehensive Test Runner & Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--coverage", action="store_true", help="Include code coverage report")
    parser.add_argument("--infra", action="store_true", help="Include infrastructure checks")
    parser.add_argument("--quick", action="store_true", help="Skip slow tests (e.g., provider discovery)")
    parser.add_argument("--view", action="store_true", help="View most recent report")
    parser.add_argument("-o", "--output", type=str, help="Output report filename (default: auto-generated)")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.view:
        view_latest_report()
        return

    start_time = time.time()

    # Step 1: Get version info
    print("🔍 Gathering version information...")
    version_info = get_git_version()
    print(f"   Version: {version_info['version_string']}")
    print(f"   Commit:  {version_info['commit_short']}")
    print(f"   Tag:     {version_info['tag']}")
    print(f"   Branch:  {version_info['branch']}")

    # Step 2: Run tests
    extra_args = []
    if args.quick:
        extra_args = ["-k", "not discover_models and not proxy_chat"]
        print("\n⚡ Quick mode: skipping slow tests (discover_models, proxy_chat)\n")

    pytest_rc, xml_content, raw_output = run_pytest(extra_args)
    pytest_results = parse_junit_xml(xml_content)

    suite = pytest_results["testsuite"]
    total = suite["tests"]
    passed = suite["passed"]
    failed = suite["failures"]
    errors = suite["errors"]

    print(f"\n{'='*60}")
    print(f"  RESULTS: {total} tests | ✅ {passed} passed | ❌ {failed} failed | ⚠️ {errors} errors")
    print(f"{'='*60}")

    # Step 3: Optional coverage
    coverage_output = None
    if args.coverage:
        print("\n📈 Running coverage...")
        coverage_output = run_coverage()

    # Step 4: Optional infrastructure checks
    infra_output = None
    if args.infra:
        print("\n🏗️ Running infrastructure checks...")
        infra_output = check_infrastructure()

    # Step 5: Generate report
    print("\n📝 Generating report...")
    report = generate_report(
        version_info=version_info,
        pytest_results=pytest_results,
        raw_output=raw_output,
        pytest_rc=pytest_rc,
        coverage_results=coverage_output,
        infra_results=infra_output,
        start_time=start_time,
    )

    # Step 6: Save report
    ts = datetime.datetime.now()
    if args.output:
        report_path = REPORTS_DIR / args.output
    else:
        report_name = _get_report_filename(version_info, ts)
        report_path = REPORTS_DIR / report_name

    report_path.write_text(report)
    print(f"\n✅ Report saved: {report_path}")

    # Step 7: Return exit code
    if failed > 0 or errors > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
