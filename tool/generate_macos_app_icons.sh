#!/bin/bash
# Regenerates the macOS app icon set from tool/app_icon_source.png.
# Run from the repo root.
set -euo pipefail

cd "$(dirname "$0")/.."

flutter test --update-goldens tool/generate_macos_app_icon_test.dart

src="tool/app_icon_source.png"
dst="macos/Runner/Assets.xcassets/AppIcon.appiconset"

for size in 16 32 64 128 256 512 1024; do
  magick "$src" -resize "${size}x${size}" "$dst/app_icon_${size}.png"
done

echo "Updated macOS app icons in $dst"
