#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
set -eu
cd "$(dirname "$0")/.."
flatpak build build sh -c 'c++ -std=c++20 -fPIC -shared tests/resources.cpp -o build/resources-test.so $(pkg-config --cflags --libs Qt6Core) -ldl'
flatpak-builder --run --env=LD_PRELOAD="$PWD/build/resources-test.so" \
    build org.raspberrypi.rpi-imager.yaml rpi-imager
