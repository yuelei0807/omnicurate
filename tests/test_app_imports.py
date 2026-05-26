"""Import smoke tests for Streamlit app modules (no server required)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "app"


def _install_streamlit_stub() -> None:
    """Replace streamlit with a no-op stub so page modules can import."""
    st = MagicMock(name="streamlit")

    class _State(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    class _Ctx:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _columns(spec, **kwargs):
        n = spec if isinstance(spec, int) else len(spec)
        return [_Ctx() for _ in range(n)]

    def _tabs(labels):
        return [_Ctx() for _ in labels]

    def _passthrough(fn=None, **_kw):
        return fn if fn is not None else (lambda f: f)

    def _selectbox(*args, **kwargs):
        options = kwargs.get("options")
        if options is None and len(args) >= 2:
            options = args[1]
        if options:
            return options[0]
        return "dim_customer"

    st.session_state = _State()
    st.set_page_config = lambda **kw: None
    st.markdown = lambda *a, **k: None
    st.title = lambda *a, **k: None
    st.caption = lambda *a, **k: None
    st.info = lambda *a, **k: None
    st.error = lambda *a, **k: None
    st.warning = lambda *a, **k: None
    st.code = lambda *a, **k: None
    st.columns = _columns
    st.tabs = _tabs
    st.multiselect = lambda *a, **kw: kw.get("default", [])
    st.selectbox = _selectbox
    st.text_area = lambda *a, **kw: kw.get("value", "")
    st.button = lambda *a, **kw: False
    st.page_link = lambda *a, **kw: None
    st.dataframe = lambda *a, **kw: None
    st.data_editor = lambda *a, **kw: None
    st.altair_chart = lambda *a, **kw: None
    st.download_button = lambda *a, **kw: None
    st.expander = lambda *a, **kw: _Ctx()
    st.stop = lambda: None
    st.cache_resource = _passthrough
    st.cache_data = lambda **_kw: _passthrough
    st.sidebar = types.SimpleNamespace(selectbox=_selectbox)

    sys.modules["streamlit"] = st


def _load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _streamlit_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_streamlit_stub()
    monkeypatch.setenv("STREAMLIT_SERVER_HEADLESS", "true")


def test_app_home_imports() -> None:
    mod = _load_module("app_home", APP_DIR / "Home.py")
    assert hasattr(mod, "st") or True  # module executed without error


def test_data_quality_page_imports() -> None:
    _load_module("app_dq_page", APP_DIR / "pages" / "1_Data_Quality.py")


def test_analytics_page_imports() -> None:
    _load_module("app_analytics_page", APP_DIR / "pages" / "2_Analytics.py")


def test_curated_explorer_page_imports() -> None:
    _load_module("app_explorer_page", APP_DIR / "pages" / "3_Curated_Model_Explorer.py")