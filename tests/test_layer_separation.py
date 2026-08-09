"""
Mechanical checks for the layer-separation rule (brief point 10):
- No provider SDK / model library imported outside app/adapters/.
- No FastAPI import in app/services/.

Uses ast to inspect actual import statements rather than grepping text,
so a mention of "fastapi" in a docstring or comment can't trip a false
positive.
"""

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent / "app"
ADAPTERS_DIR = APP_ROOT / "adapters"
SERVICES_DIR = APP_ROOT / "services"

# Third-party SDK / model-library top-level modules that only adapters/
# is allowed to import. Extend this list as new real adapters are added.
_PROVIDER_SDK_MODULES = {
    "faster_whisper",
    "google",  # google.genai
    "mutagen",
}

_FASTAPI_MODULE = "fastapi"


def _imported_top_level_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def _python_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.py"))


def test_no_provider_sdk_imported_outside_adapters():
    offenders = {}
    for path in _python_files(APP_ROOT):
        if ADAPTERS_DIR in path.parents:
            continue
        found = _imported_top_level_modules(path) & _PROVIDER_SDK_MODULES
        if found:
            offenders[str(path.relative_to(APP_ROOT.parent))] = found

    assert not offenders, f"Provider SDK imported outside adapters/: {offenders}"


def test_no_fastapi_imported_in_services():
    offenders = {}
    for path in _python_files(SERVICES_DIR):
        found = _imported_top_level_modules(path) & {_FASTAPI_MODULE}
        if found:
            offenders[str(path.relative_to(APP_ROOT.parent))] = found

    assert not offenders, f"FastAPI imported in services/: {offenders}"
