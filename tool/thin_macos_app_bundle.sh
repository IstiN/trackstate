#!/usr/bin/env bash

read_file_mode() {
  local file_path="$1"
  stat -f '%Lp' "$file_path"
}

preserve_file_mode() {
  local source_path="$1"
  local target_path="$2"
  local file_mode=""

  file_mode="$(read_file_mode "$source_path")"
  chmod "$file_mode" "$target_path"
}

thin_macho_to_arm64() {
  local binary_path="$1"
  local file_output=""
  local thinned_path="${binary_path}.arm64"

  if [[ ! -f "$binary_path" ]]; then
    return
  fi

  file_output="$(file "$binary_path")"
  if [[ "$file_output" != *"Mach-O"* ]]; then
    return
  fi

  if [[ "$file_output" == *"Mach-O universal binary"* ]]; then
    lipo -thin arm64 "$binary_path" -output "$thinned_path"
    preserve_file_mode "$binary_path" "$thinned_path"
    mv "$thinned_path" "$binary_path"
  fi
}

thin_app_bundle_to_arm64() {
  local app_bundle_path="$1"

  while IFS= read -r -d '' bundle_file; do
    thin_macho_to_arm64 "$bundle_file"
  done < <(find "$app_bundle_path" -type f -print0)
}
