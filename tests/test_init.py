import traceback
import pytest
import yaml
from unittest.mock import call, patch, MagicMock, ANY
from click.testing import CliRunner
from kopia_exporter import main

KOPIA_JSON = """
{
  "id": "d17c3a6646315ceef999c03263a02c2c",
  "source": {
    "host": "freenas",
    "userName": "root",
    "path": "/Users/avigano/developer/kopia-exporter/utils"
  },
  "description": "",
  "startTime": "2024-09-01T08:55:44.903686Z",
  "endTime": "2024-09-01T08:55:44.904094Z",
  "rootEntry": {
    "name": "utils",
    "type": "d",
    "mode": "0755",
    "mtime": "2024-08-19T14:35:05.780079377Z",
    "uid": 501,
    "gid": 20,
    "obj": "kc673fec234393693793143dcc8eefb7f",
    "summ": {
      "size": 277,
      "files": 1,
      "symlinks": 0,
      "dirs": 1,
      "maxTime": "2024-08-19T14:35:05.780023377Z",
      "numFailed": 0
    }
  }
}
"""


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_config_file(tmp_path):
    config = {"job": "test-job", "pushgateway": "http://test-pushgateway:9091"}
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)
    return str(config_file)


@patch("subprocess.run")
@patch("kopia_exporter.metrics.Metrics.update_and_push")
def test_snapshot_success(
    update_and_push, mock_subprocess_run, runner, mock_config_file
):
    # Mock the subprocess.run to simulate successful commands
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stdout=b"{}", stderr=b""),
        MagicMock(returncode=0, stdout=KOPIA_JSON.encode(), stderr=b""),
        MagicMock(returncode=0, stdout=b"{}", stderr=b""),
    ]

    # noinspection PyTypeChecker
    result = runner.invoke(
        main,
        [
            "--conf",
            mock_config_file,
            "snapshot",
            "/path/to/snapshot",
            "--zfs",
            "zfs_snapshot",
            "--override-source",
            "/override/path",
        ],
    )

    # Check if an exception occurred and print the traceback
    if result.exception:
        traceback.print_exception(*result.exc_info)

    assert result.exit_code == 0

    expected_calls = [
        call("zfs snapshot zfs_snapshot", shell=True, capture_output=True),
        call(
            "kopia snapshot create --json --override-source /override/path /path/to/snapshot",
            shell=True,
            capture_output=True,
        ),
        call("zfs destroy zfs_snapshot", shell=True, capture_output=True),
    ]

    mock_subprocess_run.assert_has_calls(expected_calls, any_order=False)
    update_and_push.assert_called_once_with(
        ANY, "http://test-pushgateway:9091", "test-job"
    )


@patch("subprocess.run")
@patch("kopia_exporter.metrics.Metrics.update_and_push")
def test_snapshot_success_without_zfs(update_and_push, mock_subprocess_run, runner):
    # Mock the subprocess.run to simulate successful commands
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stdout=KOPIA_JSON.encode(), stderr=b""),
    ]

    # noinspection PyTypeChecker
    result = runner.invoke(main, ["snapshot", "/path/to/snapshot"])

    # Check if an exception occurred and print the traceback
    if result.exception:
        traceback.print_exception(*result.exc_info)

    assert result.exit_code == 0

    expected_calls = [
        call(
            "kopia snapshot create --json /path/to/snapshot",
            shell=True,
            capture_output=True,
        ),
    ]

    mock_subprocess_run.assert_has_calls(expected_calls, any_order=False)
    update_and_push.assert_called_once_with(
        ANY, "pushgateway.cluster.thealvistar.com", "kopia-gw"
    )


@patch("subprocess.run")
@patch("kopia_exporter.metrics.Metrics.update_and_push")
def test_snapshot_kopia_error(update_and_push, mock_subprocess_run, runner):
    # Mock the subprocess.run to simulate a failed kopia snapshot command
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=1, stdout=b"", stderr=b"Kopia snapshot error"),
    ]

    # noinspection PyTypeChecker
    result = runner.invoke(main, ["snapshot", "/path/to/snapshot"])

    assert result.exit_code == 1
    assert "Failed to create snapshot: Kopia snapshot error" in result.output

    expected_calls = [
        call(
            "kopia snapshot create --json /path/to/snapshot",
            shell=True,
            capture_output=True,
        ),
    ]

    mock_subprocess_run.assert_has_calls(expected_calls, any_order=False)
    update_and_push.assert_not_called()


@patch("subprocess.run")
@patch("kopia_exporter.metrics.Metrics.update_and_push")
def test_snapshot_with_cli_override(
    update_and_push, mock_subprocess_run, runner, mock_config_file
):
    mock_subprocess_run.return_value = MagicMock(
        returncode=0, stdout=KOPIA_JSON.encode(), stderr=b""
    )

    # noinspection PyTypeChecker
    result = runner.invoke(
        main,
        [
            "--conf",
            mock_config_file,
            "snapshot",
            "/path/to/snapshot",
            "--job",
            "cli-job",
            "--pushgateway",
            "http://cli-pushgateway:9091",
        ],
    )

    assert result.exit_code == 0
    update_and_push.assert_called_once_with(
        ANY, "http://cli-pushgateway:9091", "cli-job"
    )


@patch("subprocess.run")
@patch("kopia_exporter.metrics.Metrics.update_and_push")
def test_snapshot_without_pushgateway(update_and_push, mock_subprocess_run, runner):
    mock_subprocess_run.return_value = MagicMock(
        returncode=0, stdout=KOPIA_JSON.encode(), stderr=b""
    )

    # noinspection PyTypeChecker
    result = runner.invoke(
        main,
        [
            "snapshot",
            "/path/to/snapshot",
        ],
    )

    assert result.exit_code == 1
    assert "Pushgateway URL is required" in result.output
    update_and_push.assert_not_called()


if __name__ == "__main__":
    pytest.main()
