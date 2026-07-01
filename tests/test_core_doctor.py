from pathlib import Path

from nono_sports.core.config import (
    ENV_DATA_ROOT,
    ENV_XDG_CONFIG_HOME,
    user_config_env_path,
)
from nono_sports.core.doctor import (
    format_doctor_report,
    run_common_doctor,
    run_garmin_doctor,
    run_strava_doctor,
)
from nono_sports.core.paths import ensure_strava_v1_directories


def _isolate_doctor_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_XDG_CONFIG_HOME, str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv(ENV_DATA_ROOT, "")


def test_common_doctor_reports_error_when_data_root_is_missing(
    monkeypatch,
    tmp_path,
) -> None:
    _isolate_doctor_environment(monkeypatch, tmp_path)

    report = run_common_doctor()

    assert report.status == "error"
    assert any(check.name == "data root" for check in report.checks)


def test_common_doctor_reports_ok_for_valid_environment(monkeypatch, tmp_path) -> None:
    _isolate_doctor_environment(monkeypatch, tmp_path)
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setenv(ENV_DATA_ROOT, str(data_root))
    env_path = user_config_env_path()
    env_path.parent.mkdir(parents=True)
    env_path.write_text(f"{ENV_DATA_ROOT}={data_root}\n")
    env_path.chmod(0o600)
    state_dir = tmp_path / "state" / "nono-sports"
    state_dir.mkdir(parents=True)
    state_dir.chmod(0o700)

    report = run_common_doctor()

    assert report.status == "ok"
    assert "status=ok" in format_doctor_report(report)


def test_strava_doctor_checks_expected_directories_and_token(
    monkeypatch,
    tmp_path,
) -> None:
    _isolate_doctor_environment(monkeypatch, tmp_path)
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setenv(ENV_DATA_ROOT, str(data_root))
    env_path = user_config_env_path()
    env_path.parent.mkdir(parents=True)
    env_path.write_text(f"{ENV_DATA_ROOT}={data_root}\n")
    env_path.chmod(0o600)
    state_dir = tmp_path / "state" / "nono-sports"
    state_dir.mkdir(parents=True)
    state_dir.chmod(0o700)
    token_path = state_dir / "strava_tokens.json"
    token_path.write_text("{}\n")
    token_path.chmod(0o600)
    ensure_strava_v1_directories(data_root)

    report = run_strava_doctor()

    assert report.status == "ok"
    assert any(check.name == "Strava token store" for check in report.checks)


def test_garmin_doctor_warns_before_garmin_is_installed(
    monkeypatch,
    tmp_path,
) -> None:
    _isolate_doctor_environment(monkeypatch, tmp_path)
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setenv(ENV_DATA_ROOT, str(data_root))

    report = run_garmin_doctor()

    assert report.status == "warning"
    assert any(check.name == "Garmin Connect library" for check in report.checks)
