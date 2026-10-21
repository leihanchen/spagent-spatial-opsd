"""Run existing CLI-only mock checks in-process so socket blocking still applies."""
import inspect
from pathlib import Path
import runpy
import sys

from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script,extra", [
    ("test/qwenvl/test_qwenvl_tool.py", []),
    ("test/wan/test_wan_tool.py", ["--duration", "3"]),
    ("test/test_orient_anything_v2_tool.py", ["--task", "orientation"]),
    ("test/test_orient_anything_v2_tool.py", ["--task", "symmetry"]),
    ("test/test_orient_anything_v2_tool.py", ["--task", "relative_rotation"]),
])
def test_mock_cli(script, extra, monkeypatch, tmp_path):
    image = tmp_path / "input.jpg"
    Image.new("RGB", (64, 48), color=(80, 120, 60)).save(image)
    args = [str(ROOT / script), "--use_mock", "--image_path", str(image), *extra]
    if "relative_rotation" in extra:
        args += ["--image_path2", str(image)]
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(ROOT / script), run_name="__main__")


@pytest.mark.parametrize("name", ["molmo2", "veo", "sora", "vace", "wilddet3d",
                                  "flowseek", "paddleocr_vl", "oneformer"])
def test_direct_tool_mock(name, tmp_path, monkeypatch):
    namespace = runpy.run_path(str(ROOT / "test/test_tool.py"))
    function = namespace["test_" + name]
    image = tmp_path / "input.jpg"
    Image.new("RGB", (64, 48), color=(80, 120, 60)).save(image)
    monkeypatch.chdir(tmp_path)
    if name == "vace":
        # VACE's mock returns a fixed path but does not render a video. Supply
        # an explicit file fixture to test the CLI's output-copy behavior.
        output = tmp_path / "outputs/mock_vace_video.mp4"
        output.parent.mkdir()
        output.write_bytes(b"mock-video-copy-fixture")
    available = dict(image_path=str(image), image_paths=[str(image)],
                     image1_path=str(image), image2_path=str(image),
                     prompt="Point to the object", prompt_text="object",
                     device="cpu", use_mock=True, output_dir=str(tmp_path / "out"),
                     duration=3)
    kwargs = {k: v for k, v in available.items() if k in inspect.signature(function).parameters}
    result = function(**kwargs)
    assert result, "CLI helper reported failure"
    if name == "vace":
        assert Path(result).read_bytes() == b"mock-video-copy-fixture"


def test_cpu_lane_blocks_network(request):
    if not request.config.getoption("--cpu-only"):
        pytest.skip("CPU lane enforcement check")
    import socket
    from pytest_socket import SocketBlockedError
    with pytest.raises(SocketBlockedError):
        socket.socket()
