# Validation record — 2026-11-18

This record deliberately excludes unique serials, personal paths and whole-PC
logs. "Passed" means the stated check ran locally; it does not imply remote CI,
physical visual confirmation, a complete fresh OpenRGB build or all-model support.

| Check | Actual local result |
|---|---|
| Windows 11 / Python 3.14.7 pytest | 52 passed, including four offscreen GUI tests |
| Linux WSL / Python 3.12.3 pytest | 48 passed, GUI module skipped (Qt not installed in that test venv) |
| Python lint / formatting | Ruff check and format verification |
| Python packaging | Isolated setuptools wheel and sdist build; wheel CLI install/version/status exercised |
| Native Matrix source compilation | MSVC (Windows), GCC 13.3/Linux syntax compilation of all three .cpp files against upstream headers |
| Native transport executable with simulated USB | Passed on Windows and Linux |
| Refactored native transport, physical Matrix | Windows frame upload, repeated identical frame, Off readback=0; zero warnings |
| New companion, physical Matrix via existing native SDK | Three-frame APNG, text, Off writes succeeded |
| New companion, physical Corsair LCD | Three-frame APNG, text, black JPEG + brightness-zero writes succeeded |
| Unrelated RGB during companion test | Colors/identity unchanged; original Matrix mode/colors restored |
| Production after isolated native exercise | Existing binary preserved; 12-device lighting snapshot restored; AsusFanControlService running |
| Prepared native patch | Applies cleanly to its recorded upstream base; contains no GUI/Python/Commander changes |
| Standalone GUI visual check | Both pages opened and inspected; stepped portrait Matrix and circular LCD preview |

The tests cover Corsair exact report boundaries, final flags/padding, ASUS
topology/wire offsets, invalid buffers, Off/readback, SDK fail-closed behavior,
cache invalidation, preparation before device writes, timing/cancellation, FPS
skipping, long stalls, transparency/EXIF, APNG posters, cache limits, text fitting,
writer locks, no GUI autoplay and serialization of replacement/Off workers.

Historical owner observations confirmed hardware Off, uniform Matrix red,
native Direct after the private USB-context fix, Corsair OpenRGB text and the
separate RGB ring remaining off. The newly inferred stepped portrait map has not
yet received asymmetric physical landmark confirmation; byte/layout tests are
not a substitute for that observation.

Not run/claimed: full reboot, S5 persistence, first hotplug, physical Linux USB,
other firmware/model families, persistent animation uploads, every vendor
preset, LiveDash OLED control, independent human review, or hosted CI runs.
Compiler checks do not represent a clean full OpenRGB build. Performance numbers
from earlier experiments are not advertised as guaranteed frame rates.
