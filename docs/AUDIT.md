# Audit — 2026-11-18

Scope: the original custom OpenRGB Matrix driver, Python USB/rendering/CLI and
header-only Qt display pages. This is an AI-assisted source audit, regression
test expansion and hardware exercise, **not** an independent human review or a
guarantee of firmware feature completeness.

| Finding | Impact | Resolution |
|---|---|---|
| SDK exceptions fell through into raw USB | A network/protocol error could create a competing HID handle | Default SDK-only Matrix adapter; explicit opt-in USB backend; regression test |
| FPS cap stretched frame durations | Animation played slower than the source | Absolute source timeline, frame skipping, no catch-up backlog |
| GUI used a separate Qt renderer | Preview differed in EXIF, APNG poster, text layout and scaling | Standalone Qt GUI decodes the exact prepared device frame |
| Windows venv launcher could orphan a player | Old animation retained device/mutex after cancellation | Standalone GUI uses a cooperative QThread with no playback subprocess |
| Static Matrix text overflowed its 7-pixel width | Cropped/missing content | Font-independent measured wrapping; clear error if text cannot fit |
| NaN/infinite timing accepted | Invalid or unbounded loop behavior | Finite range validation before device access |
| Corsair brightness changed before image decode | Invalid files changed the display | Prepare media first, open/apply only after successful decoding |
| Off could skip brightness-zero after black upload failure | LCD backlight might remain on | Backlight-off attempted in finally |
| SDK Off kept its previous frame cache | Reapplying the same frame after Off could be skipped | Invalidate cache on Off |
| Source names could be duplicated | Mirrored an arbitrary module/controller | Reject ambiguity, allow numeric ID, stop after identity change |
| SDK target ID could be reused after rescan | A frame/Off could address a different device | Refresh and verify Matrix name/serial/location before every write; regression test |
| Writer exclusion was Windows-only | Concurrent POSIX writers | Per-user POSIX lock, Windows mutex retained for legacy bridge compatibility |
| Native USB serial was checked after claiming | Momentarily claimed another same-PID device | Compare serial before claim |
| Native failures lacked some diagnostics/released state | Difficult diagnosis, stale transport state | Log short writes/invalid acks/claim/bulk failures, invalidate cache and release bulk |
| Native driver mixed transport and RGB representation | Hard to review independently | Separate controller/adapter, core-only branch from current upstream |
| Packaging depended on local paths/configuration | Not installable on another machine | src layout, pyproject, entry points, optional GUI/USB extras, user settings location |
| Evidence contained local paths and unique device serials | Unsuitable public repository content | Public reports summarize checks; private captures/config/logs not copied |

Resource limits remain: 16 MP decoded source, 2000 cached frames, 64 MiB encoded
cache and 1 MiB Corsair JPEG. Importing modules/discovering the GUI does not write
to hardware. Only the documented display interfaces receive commands.

## Remaining limitations

* Independent human review, especially the upstream contribution-policy decision.
* Asymmetric physical landmark confirmation of the inferred portrait map.
* Full reboot, S5 persistence, first hotplug, every firmware preset and persistent
  animation upload are unverified; LiveDash OLED is out of scope.
* Linux physical USB behavior has not been verified. Compiler/unit checks do not
  replace a physical hardware test.
* openrgb-python 0.3.8 supplies the SDK protocol transport. Its parser, protocol
  compatibility and connection-stage timeouts are external dependencies; this
  audit does not certify that library. No raw fallback hides its errors.
* Locks exclude cooperating local processes, not vendor software or remote SDK
  writers. A program crash or hardware-disconnect can prevent blanking on exit.
* The standalone GUI currently ships English source strings marked for Qt
  translation. Complete translated catalogs and a native OpenRGB plugin are
  future work; the previous custom Russian GUI remains installed separately.

Detailed checks and the actual local results are in [VALIDATION.md](VALIDATION.md).
