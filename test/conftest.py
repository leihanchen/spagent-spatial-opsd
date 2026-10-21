"""Opt-in CPU/offline collection; new pytest modules are included by default."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent

# CLI scripts have positional arguments, not pytest fixtures. Their mock paths
# are exercised by test_mock_cli.py; the Pi3 LLM demo requires a live model.
CPU_IGNORE = {
    "test_tool.py": "mixed live-service CLI; mock paths covered by test_mock_cli.py",
    "test_orient_anything_v2_tool.py": "CLI; mock paths covered by test_mock_cli.py",
    "test_pi3_llm.py": "live VLM and reconstruction services",
}
CPU_LIVE_CASES = {
    "test_molmo2_tool.py::test_molmo2_live_qa": "live Molmo2 server",
    "test_sana_tool.py::test_sana_tool_real_service": "live Sana server",
    "test_qwen_image_edit_tool.py::test_optional_real_dashscope_edit": "paid DashScope API",
    "yolo26/test_yolo26_tool_real.py::test_yolo26_tool_real_detection": "local YOLO weights and real inference",
}


def pytest_addoption(parser):
    parser.addoption("--cpu-only", action="store_true",
                     help="Run offline CPU tests; exclude documented live/weight-dependent cases")


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: optional real-backend integration")


def pytest_ignore_collect(collection_path, config):
    if config.getoption("--cpu-only"):
        relative = collection_path.relative_to(ROOT).as_posix()
        if relative in CPU_IGNORE:
            return True
    return None


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--cpu-only"):
        return
    for item in items:
        relative = item.path.relative_to(ROOT).as_posix()
        key = relative + "::" + (getattr(item, "originalname", None) or item.name)
        if key in CPU_LIVE_CASES:
            item.add_marker(pytest.mark.skip(reason="CPU lane excludes " + CPU_LIVE_CASES[key]))


def pytest_report_header(config):
    if config.getoption("--cpu-only"):
        return ["CPU/offline lane: new test modules are collected automatically."] + [
            "Not collected: " + path + " (" + reason + ")"
            for path, reason in sorted(CPU_IGNORE.items())
        ]


def pytest_sessionfinish(session, exitstatus):
    """Missing dependencies or new skip markers must not silently pass CI."""
    if not session.config.getoption("--cpu-only"):
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    unexpected = [report.nodeid for report in reporter.stats.get("skipped", [])
                  if not any(report.nodeid.endswith(key) for key in CPU_LIVE_CASES)]
    if unexpected:
        reporter.write_sep("=", "Unexpected skips in CPU lane: " + ", ".join(unexpected), red=True)
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
