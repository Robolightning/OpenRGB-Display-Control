# Contributing

Keep protocol changes restricted to the documented USB interfaces and firmware.
Add regression coverage for correctness/resource ownership failures. Run pytest,
ruff and a wheel/sdist build. Tests must not access physical devices by default.
Record OS, model, firmware, tested behavior and failures for hardware checks;
remove unique serials, personal paths and full-machine logs from public reports.

Explain AI assistance and provenance honestly. Generated output is not a human
review. Preserve third-party notices. Do not describe this independent project
as an official OpenRGB plugin or promise untested model/firmware support.

Changes for the native Matrix driver belong in the separate OpenRGB worktree.
Read that project's current CONTRIBUTING.md; its policy generally disallows AI
generated submissions and expects manual understanding/vetting by a human author.
This repository cannot grant an exception to another project's policy.
