import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "capture_camera_check.py"
spec = importlib.util.spec_from_file_location("capture_camera_check", MODULE_PATH)
camera_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera_check)


class FakeSerial:
    def __init__(self, header: bytes, chunks: list[bytes]):
        self.header = header
        self.chunks = iter(chunks)
        self.command = b""

    def write(self, data: bytes) -> None:
        self.command += data

    def readline(self) -> bytes:
        return self.header

    def read(self, size: int) -> bytes:
        return next(self.chunks, b"")


class CameraCaptureTests(unittest.TestCase):
    def test_default_output_is_in_esp32_capture_folder(self):
        self.assertEqual(
            camera_check.DEFAULT_OUTPUT,
            MODULE_PATH.parents[1] / "captures" / "camera-check.jpg",
        )

    def test_receives_fragmented_jpeg(self):
        port = FakeSerial(b"CEKRIR_JPEG 5\n", [b"\xff\xd8", b"x\xff\xd9"])
        self.assertEqual(camera_check.capture(port), b"\xff\xd8x\xff\xd9")
        self.assertEqual(port.command, b"c")

    def test_rejects_excessive_size(self):
        port = FakeSerial(b"CEKRIR_JPEG 2000001\n", [])
        with self.assertRaisesRegex(RuntimeError, "size"):
            camera_check.capture(port)

    def test_rejects_truncated_image(self):
        port = FakeSerial(b"CEKRIR_JPEG 5\n", [b"\xff\xd8"])
        with (
            patch.object(camera_check.time, "monotonic", side_effect=[0, 0, 0, 0, 100]),
            self.assertRaisesRegex(RuntimeError, "Incomplete"),
        ):
            camera_check.capture(port)


if __name__ == "__main__":
    unittest.main()
