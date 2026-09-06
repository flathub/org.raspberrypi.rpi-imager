# SPDX-License-Identifier: Apache-2.0
"""Run inside the built Flatpak: write/verify temporary files, never devices."""
import gzip
import hashlib
import lzma
import os
from pathlib import Path
import subprocess
import tempfile

with tempfile.TemporaryDirectory(prefix='rpi-imager-smoke-') as directory:
    root = Path(directory)
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen',
               XDG_CONFIG_HOME=str(root / 'config'), XDG_CACHE_HOME=str(root / 'cache'))
    app = '/app/bin/rpi-imager'
    version = subprocess.run([app, '--version'], env=env, capture_output=True, text=True, timeout=30)
    assert version.returncode == 0, version.stderr
    assert version.stdout.strip() == 'Raspberry Pi Imager v2.0.11.1', version.stdout
    data = bytes(range(256)) * 32768  # 8 MiB, deterministic and sector-aligned
    source = root / 'source.img'
    source.write_bytes(data)
    (root / 'source.img.gz').write_bytes(gzip.compress(data))
    (root / 'source.img.xz').write_bytes(lzma.compress(data))
    subprocess.run(['zstd', '-q', str(source), '-o', str(root / 'source.img.zst')], check=True)
    expected = hashlib.sha256(data).digest()
    for suffix in ('', '.gz', '.xz', '.zst'):
        destination = root / 'destination.img'
        destination.write_bytes(bytes(len(data)))
        assert destination.is_file() and not destination.is_symlink()
        # This option admits our regular temporary output file; no /dev path
        # is accepted from the user or passed to the application.
        result = subprocess.run([app, '--cli', '--enable-writing-system-drives',
                                 '--disable-eject', str(source) + suffix, str(destination)],
                                env=env, capture_output=True, text=True, timeout=90)
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'Write successful.' in result.stderr, result.stderr
        assert hashlib.sha256(destination.read_bytes()).digest() == expected, suffix
        print(f'Write and verification passed: {suffix or "raw"}', flush=True)
