import importlib.util
from pathlib import Path
import subprocess


path = Path(__file__).parents[1] / "scripts" / "plan_verification.py"
spec = importlib.util.spec_from_file_location("plan_verification", path)
assert spec and spec.loader
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


def test_docs_only_never_requests_e2e():
    plan = planner.plan_for_paths(["docs/verification-run-policy.md", "README.md"])
    assert plan["e2eRequired"] is False
    assert plan["fullRequired"] is False


def test_fsrs_statistics_change_targets_stats_and_keeps_final_full():
    plan = planner.plan_for_paths(["anki_study_report/fsrs_service.py", "web-dashboard/src/pages/FsrsStatisticsPage.tsx"])
    assert plan["targetedScope"] == "stats"
    assert plan["e2eRequired"] is True
    assert plan["fullRequired"] is False
    assert plan["resourceTelemetry"] is False
    assert plan["warmCacheRepeat"] is False


def test_shared_server_and_payload_cannot_be_silently_downgraded():
    plan = planner.plan_for_paths(["anki_study_report/dashboard_server.py"])
    assert plan["e2eRequired"] is True
    assert plan["targetedScope"] == "full"
    assert plan["fullRequired"] is True


def test_stats_target_is_preserved_when_shared_shell_also_requires_final_full():
    plan = planner.plan_for_paths(["anki_study_report/fsrs_service.py", "web-dashboard/src/app/router.tsx", ".github/workflows/ci-e2e.yml"])
    assert plan["targetedScope"] == "stats"
    assert plan["fullRequired"] is True
    assert any("ci-e2e" in reason for reason in plan["reasons"])


def test_multiple_product_scopes_escalate_to_full():
    plan = planner.plan_for_paths(["web-dashboard/src/pages/CardsPage.tsx", "anki_study_report/statistics_service.py"])
    assert plan["fullRequired"] is True
    assert plan["targetedScope"] == "full"


def test_changed_paths_compares_real_refs():
    head = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    local_master = subprocess.run(
        ["git", "rev-parse", "--verify", "refs/heads/master"],
        check=False,
        capture_output=True,
        text=True,
    )
    base = "master" if local_master.returncode == 0 else "origin/master"
    assert "tests/test_verification_planner.py" in planner.changed_paths(base, head)
