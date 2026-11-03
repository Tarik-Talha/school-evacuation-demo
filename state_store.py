"""Keep interactive edits private to each browser session."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# =========================================================
# SESSION-ISOLATED EDITS FOR HOSTED DEMO VISITORS
# =========================================================
def session_state():
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx(suppress_warning=True) is None:
        return None
    import streamlit as st
    return st.session_state


def read_json(name, default=None):
    state = session_state()
    if state is not None:
        return copy.deepcopy(state.get('school_storage:' + name, default))
    path = ROOT / 'runtime' / name
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else copy.deepcopy(default)


def write_json(name, value):
    # Serialize first so unsupported or non-finite values cannot be saved.
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    state = session_state()
    if state is not None:
        state['school_storage:' + name] = json.loads(text)
        return
    path = ROOT / 'runtime' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(path)
