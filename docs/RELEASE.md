# Publication handoff

The repository is prepared locally. No remote repository, package upload or MR
submission is performed by this preparation. Suggested public name:
**OpenRGB-Display-Control**. Suggested first tag: **v0.1.0a1** (experimental).

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

The provided patch author identity follows the local Git configuration. The
patch includes normal Git author metadata; review that public identity before
posting it. Repository code/docs do not contain private device serials or user
filesystem paths.
