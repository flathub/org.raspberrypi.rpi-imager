# SPDX-License-Identifier: Apache-2.0
"""Reject Qt copy relocations that can break GUI startup with reduced-relocation Qt."""
from pathlib import Path
import subprocess
import sys

binary = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/files/bin/rpi-imager")
result = subprocess.run(
    ["readelf", "--wide", "--relocs", str(binary)],
    check=True, capture_output=True, text=True,
)
bad = [line for line in result.stdout.splitlines() if "_COPY" in line and "@Qt_6" in line]
if bad:
    sys.exit("Qt copy relocations found; rebuild with -fPIC:\n" + "\n".join(bad))
print("Qt relocation check passed")
