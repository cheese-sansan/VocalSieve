from types import SimpleNamespace

from vocalsieve import doctor


class GoodTranscriber:
    effective_device = "cpu"

    def __init__(self, config):
        self.config = config

    def prepare(self):
        return None


class BadTranscriber(GoodTranscriber):
    def prepare(self):
        raise RuntimeError("probe failed")


def test_deep_diagnostics_reports_success(monkeypatch):
    monkeypatch.setattr(doctor, "FasterWhisperTranscriber", GoodTranscriber)
    checks = doctor.run_diagnostics(deep=True, device="cpu", model_size="tiny")
    probe = next(check for check in checks if check.name == "Inference probe")
    assert probe.ok
    assert "tiny on cpu" in probe.detail


def test_deep_diagnostics_reports_failure(monkeypatch):
    monkeypatch.setattr(doctor, "FasterWhisperTranscriber", BadTranscriber)
    checks = doctor.run_diagnostics(deep=True, device="cuda", model_size="tiny")
    probe = next(check for check in checks if check.name == "Inference probe")
    assert not probe.ok
    assert "probe failed" in probe.detail


def test_windows_cuda_library_success_path(monkeypatch):
    monkeypatch.setattr(doctor, "_is_windows", lambda: True)
    monkeypatch.setattr(doctor, "configure_runtime", lambda: None)
    monkeypatch.setattr(doctor.ctypes, "WinDLL", lambda name: SimpleNamespace())
    checks = doctor._windows_cuda_libraries()
    assert all(check.ok for check in checks)
