# Release process

Public repository: [OpenRGB-Display-Control](https://github.com/Robolightning/OpenRGB-Display-Control).
The initial version is **v0.1.0a1**, published as an experimental pre-release.
GitHub release artifacts are separate from PyPI; no PyPI publication is implied.

Before a public tag, review the audit/provenance and exact hardware scope. Keep
the inferred physical map and untested reboot/hotplug/Linux limitations visible.
Do not label the release "100% supported" or "official OpenRGB plugin".

Local checks:

```
python -m pip install ".[dev,gui]" -c constraints-tested.txt
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m build
```

Publish only tracked project files and source/wheel artifacts after reviewing
their contents. Do not add .venv, USB captures, ui.ini, whole-machine logs, vendor
DLLs or the old custom OpenRGB executable. No test requires public account
credentials or device access. Prepared CI is not a claimed successful remote run.

For the native Matrix driver, use the separate branch/patch described in
[upstream/README.md](../upstream/README.md). Its MR draft is deliberately marked
Draft while manual human vetting and physical validation remain outstanding.
Do not bundle Commander Core or the Python player into that MR.

The driver patch includes normal Git author metadata. Repository code/docs do
not contain private device serials or user filesystem paths. See GitHub Actions
for hosted checks; historical local validation is recorded separately.
