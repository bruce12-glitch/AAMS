"""Verify privacy setup without loading a native inference runtime or models."""
import os
import runpy
import sys
from pathlib import Path
from types import ModuleType


def test_telemetry_is_disabled_before_face_library_import(monkeypatch):
    monkeypatch.setenv('ORT_DISABLE_TELEMETRY', '0')
    calls = []
    runtime = ModuleType('onnxruntime')

    def disable():
        assert os.environ['ORT_DISABLE_TELEMETRY'] == '1'
        calls.append('disabled')

    runtime.disable_telemetry_events = disable
    face_app = ModuleType('insightface.app')
    face_app.FaceAnalysis = object()
    monkeypatch.setitem(sys.modules, 'onnxruntime', runtime)
    monkeypatch.setitem(sys.modules, 'insightface.app', face_app)
    source = Path(__file__).parents[1] / 'app' / 'face_engine.py'
    namespace = runpy.run_path(str(source))
    assert namespace['_FaceAnalysis'] is face_app.FaceAnalysis
    assert calls == ['disabled']
