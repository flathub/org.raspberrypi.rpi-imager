# Raspberry Pi Imager Flatpak

This manifest packages **Raspberry Pi Imager v2.0.11.1** as
`org.raspberrypi.rpi-imager`, using the KDE 6.11 runtime. The upstream release
and all seven external libraries are pinned by tag and commit.

## Build and run

Install Flatpak and the host `flatpak-builder` runner, add the Flathub remote,
then install the official build tools:

```sh
flatpak install --user flathub org.kde.Platform//6.11 org.kde.Sdk//6.11 org.flatpak.Builder
flatpak run org.flatpak.Builder --user --force-clean --keep-build-dirs --repo=repo --compose-url-policy=full --mirror-screenshots-url=https://dl.flathub.org/media build org.raspberrypi.rpi-imager.yaml
flatpak-builder --run build org.raspberrypi.rpi-imager.yaml rpi-imager
```

To install the locally built application:

```sh
flatpak run org.flatpak.Builder --user --install --force-clean build org.raspberrypi.rpi-imager.yaml
```

To install a provided bundle, use the same per-user scope as the runtime:

```sh
flatpak install --user ./build/org.raspberrypi.rpi-imager-2.0.11.1-x86_64.flatpak
flatpak run org.raspberrypi.rpi-imager
```

Downloads happen before the build sandbox starts. All FetchContent sources
are supplied by the manifest; timezone and wireless-country data use the
snapshots included in the upstream source. No build-time network access is
needed. To verify this after downloading sources:

```sh
flatpak run org.flatpak.Builder --user --download-only build org.raspberrypi.rpi-imager.yaml
flatpak run org.flatpak.Builder --user --force-clean --disable-download build org.raspberrypi.rpi-imager.yaml
```

## Changes required for 2.x

The old manifest targets 1.9.6. Its large `remove-vendoring.patch` no longer
matches upstream's split CMake files. This package uses upstream's bundled
library build, with explicit offline sources including the newly required
curl and libusb. Unused dependency submodules are disabled. Upstream now
patches libarchive's static zstd detection itself.

Two small build patches give nghttp2's generated `config.h` priority over
Imager's header and preserve the exact release version despite downstream
patches. Explicit `-fPIC` avoids Qt data copy relocations associated with
startup crashes in the earlier 2.x packaging attempt.

`fix-offline-timezones.patch` explicitly embeds upstream's `timezones.txt` at
`:/timezones.txt`. With online generation disabled, upstream otherwise omits
this resource, leaving the time-zone selector empty. The country list is
already embedded by upstream.

Upstream's Linux application expects root and uses direct device opens and
unmount system calls. Flatpak cannot elevate through `pkexec`; `--device=all`
alone does not grant permission to open host block devices. The Flatpak
patch (including its `flatpak-udisks2.h` helper) instead uses the host's UDisks2 service to:

- Unmount the selected disk and its partitions in the host mount namespace.
- Request an authorized read/write descriptor with exclusive access.
- Keep that descriptor and lock when toggling direct I/O.
- Stop on denied authorization, cancellation, or busy filesystems.

The GUI runs as the normal user. The host must provide UDisks2 (2.7.3 or
newer) and a working polkit authentication agent. Host policy still decides
which devices the user can access. No host helper or polkit policy is installed.
USB boot/fastboot access separately depends on the host's USB device
permissions; udev rules inside a Flatpak cannot change those permissions.

Upstream's `com.raspberrypi` desktop file is renamed to the existing
`org.raspberrypi` Flatpak ID. The launcher retains `%u` and the Pi Connect
URI association. The session bus service and interface use the Flatpak ID,
so callbacks can reach the running instance with the default bus permission. The application does not generate a host launcher pointing
at its sandbox-only `/app/bin` path. Metadata is generated from upstream’s
template, with the release version and date derived from the pinned commit.
The metadata patch adds developer information and HTTPS screenshot URLs.
License files for the application and external libraries are installed under
`/app/share/licenses/org.raspberrypi.rpi-imager`.

File selection uses upstream’s desktop portal integration. Static access to
`/media` and `/run/media` and the accessibility bus wildcard are unnecessary;
UDisks2 supplies authorized block-device descriptors independently of these
folder permissions.

## Validation

Build with `--keep-build-dirs` so the helper tests compile the actual patched
source. After building, check the packaged time-zone resource and mock UDisks2 behavior:

```sh
./tests/run.sh
```

The resource check runs the actual executable with a test-only replacement
for its main function, after Qt has registered its embedded resources. It
requires a populated list containing Europe/London, America/New_York, and
Asia/Tokyo. Run just this check with `./tests/resources.sh`.

The host needs `dbus-run-session`, Python 3, `python3-dbus`, and
`python3-gi`. The C++ checks compile against the Flatpak SDK. They use a
private mock bus and temporary files, never real storage devices. Coverage
includes D-Bus object decoding, device/partition matching, unmount failures,
authorization cancellation, descriptor ownership, and close-on-exec.

To check the exact version and exercise raw, gzip, xz, and zstd image writing
with verification into temporary regular files:

```sh
flatpak-builder --run build org.raspberrypi.rpi-imager.yaml python3 tests/smoke.py
```

Beyond the successful manual write tests recorded below, confirm cancellation
of an authorization request, writing with a mounted partition, and repeated
writes using a disposable SD card. Check X11 startup and a Pi Connect browser
callback. Mock tests cannot verify host polkit policy or physical I/O.

Run Flathub’s checks on the manifest and exported repository:

```sh
flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest org.raspberrypi.rpi-imager.yaml
flatpak run --command=flatpak-builder-lint org.flatpak.Builder repo repo
```

If a previous build was exported without screenshot mirroring, regenerate
its cleanup stage so cached metadata is not reused:

```sh
flatpak run org.flatpak.Builder --user --force-clean --build-only --keep-build-dirs build org.raspberrypi.rpi-imager.yaml
flatpak run org.flatpak.Builder --user --finish-only --disable-cache --repo=repo --compose-url-policy=full --mirror-screenshots-url=https://dl.flathub.org/media build org.raspberrypi.rpi-imager.yaml
```

Validation completed locally on 2026-09-06, x86_64 with KDE 6.11:

- Offline source build with the official Builder; manifest and exported
  repository lint passed without exceptions.
- Embedded time-zone list: 432 entries, including Europe/London.
- Mock UDisks2 authorization, cancellation, unmounting, and descriptor tests.
- Exact release version and raw/gzip/xz/zstd writes with verification.
- Headless GUI startup, OS catalogue retrieval over HTTP/2, and introspection
  of the callback interface under `org.raspberrypi.rpi-imager`.
- Application and external-library licenses present; screenshot media
  committed to the exported repository.

The host runner is used for tests because the installed official Builder
app’s `--run` mode returned status 1 even for a successful empty command on
this machine. Building and linting with that app succeeded.

Fedora 44 Workstation was also checked on 2026-09-06 in a VMware x86_64 VM.
The previously installed KDE 6.9 package (`7b03adce6183`) crashed in Qt's
Wayland startup and contained Qt copy relocations, including
`QCoreApplication::self`. The current package (`976e5ec57c9a`, KDE 6.11)
passed a 30-second Wayland startup check with the normal VMware OpenGL
renderer, fetched the OS catalogue, and stayed running on a subsequent
normal launch. No new coredump was recorded. This automated check covers
startup; the subsequent manual write results are recorded below.

The contributor reports successful image writing and completed verification
on all three systems:

| System | Architecture confirmed for this test | Result |
| --- | --- | --- |
| Ubuntu 24.04 | Not specified | Write and verification passed |
| Fedora 44 | Not specified | Write and verification passed |
| Raspberry Pi OS | ARM64 (aarch64) | Flatpak write and verification passed |

These are contributor-reported functional results, including a successful
ARM64 Flatpak run. The exact package commits, storage devices, image formats,
and display protocols were not recorded for these manual tests. They do not
establish coverage of cancellation, mounted partitions, repeated writes,
or Pi Connect sign-in.

`tests/run.sh` includes a binary relocation guard. It requires host
`readelf` (binutils) and rejects Qt copy relocations to catch omission of
the `-fPIC` build options. It can also check an installed executable:

```sh
python3 tests/relocations.py /path/to/rpi-imager
```

## Submission follow-up

The technical changes on this branch were produced with AI assistance,
including packaging, patches, documentation, and tests. Flathub’s
[requirements](https://docs.flathub.org/docs/for-app-authors/requirements)
require disclosure and reserve submission commit messages, PR descriptions,
and review responses for human authorship. The earlier commit `88ee093` has
an AI-written message; its suitability or replacement must be resolved by
the contributor before submission. No submission or exception PR is created
by these build instructions.

Remaining validation covers the specific storage scenarios above, X11
startup, and browser sign-in. Inspect the aarch64 Flathub CI build before
merging; the successful ARM64 manual test does not replace that CI check.
Consult the current
[maintenance requirements](https://docs.flathub.org/docs/for-app-authors/maintenance)
when preparing the update to upstream’s `master` branch.

References: [upstream release](https://github.com/raspberrypi/rpi-imager/releases/tag/v2.0.11.1),
[earlier Flathub 2.x attempt](https://github.com/flathub/org.raspberrypi.rpi-imager/pull/65),
[UDisks2 block-device API](https://storaged.org/doc/udisks2-api/latest/gdbus-org.freedesktop.UDisks2.Block.html).
