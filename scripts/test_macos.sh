#!/usr/bin/env bash
# Tests du moteur Swift (harnais swiftc, sans cible XCTest).
set -euo pipefail
cd "$(dirname "$0")/.."

SRC="macos/TauxBdC/TauxBdC"
OUT="$(mktemp -d)/test_core"

swiftc -parse-as-library -o "$OUT" \
  "$SRC/Localization.swift" \
  "$SRC/Services/Models.swift" \
  "$SRC/Services/AppDataPaths.swift" \
  "$SRC/Services/RateCache.swift" \
  "$SRC/Services/BoCRateService.swift" \
  "$SRC/Services/CSVBatch.swift" \
  "$SRC/Services/FileFormats.swift" \
  macos/tests/test_core.swift

"$OUT"
