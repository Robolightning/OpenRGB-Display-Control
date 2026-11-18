# Native Matrix driver handoff

Target: [OpenRGB GitLab](https://gitlab.com/CalcProgrammer1/OpenRGB), `master`.
The native branch was started at `5bcfa9ae01536d2dd45b0c6e5b15677513f7a6d5`
on 2026-11-18. It is independent of the earlier Commander Core fix.

The handoff includes a core-only patch, protocol/device issue draft, MR draft,
and native transport tests. It does not include the Python player or custom GUI.

To inspect/apply in a separate clean OpenRGB checkout:

```
git switch -c asus-x670e-anime-matrix <base-commit-above>
git am /path/to/0001-Add-X670E-Extreme-AniMe-Matrix-driver.patch
```

Use the project's normal qmake build instructions. Controller sources/headers
are found recursively by OpenRGB.pro. Device metadata is included for generated
udev/support tooling. No build-system platform exception is introduced.

**Submission is not authorized by technical preparation alone.** OpenRGB's
[CONTRIBUTING.md](https://gitlab.com/CalcProgrammer1/OpenRGB/-/blob/master/CONTRIBUTING.md)
generally disallows AI-generated submissions and expects a human to understand
and manually vet submitted code. This implementation used AI assistance. No
independent human review is claimed, and no MR has been submitted by this task.
The intended author must resolve that policy and validation requirement honestly.
