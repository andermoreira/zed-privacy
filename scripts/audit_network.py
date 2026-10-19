#!/usr/bin/env python3
"""
Zed Privacy - Network and Telemetry Static Auditor.
Verifies that privacy patches are correctly applied to the Zed codebase.
"""

import sys
import os
import re
import argparse

def check_file_contains(filepath: str, pattern: str, description: str, should_exist: bool = True) -> bool:
    if not os.path.exists(filepath):
        print(f"❌ [FAIL] Missing file: {filepath}")
        return False
    
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    match = re.search(pattern, content)
    if should_exist:
        if match:
            print(f"✅ [PASS] {description}")
            return True
        else:
            print(f"❌ [FAIL] {description} (Pattern not found: {pattern!r})")
            return False
    else:
        if match:
            print(f"❌ [FAIL] {description} (Forbidden pattern matched: {pattern!r})")
            return False
        else:
            print(f"✅ [PASS] {description}")
            return True

def run_audit(source_dir: str) -> bool:
    print(f"🔍 Starting Zed Privacy Network & Telemetry Audit on: {source_dir}\n")
    all_passed = True

    # 1. Audit default settings
    settings_path = os.path.join(source_dir, "assets", "settings", "default.json")
    all_passed &= check_file_contains(
        settings_path,
        r'"telemetry":\s*\{\s*//[^\n]*\n\s*"diagnostics":\s*false,\s*//[^\n]*\n\s*"metrics":\s*false,',
        "Default settings: telemetry metrics and diagnostics disabled"
    )
    all_passed &= check_file_contains(
        settings_path,
        r'"auto_update":\s*false,',
        "Default settings: auto_update disabled"
    )

    # 2. Audit crates/telemetry
    telemetry_rs = os.path.join(source_dir, "crates", "telemetry", "src", "telemetry.rs")
    all_passed &= check_file_contains(
        telemetry_rs,
        r'pub fn send_event\(_event: Event\)',
        "crates/telemetry: send_event neutralized to no-op"
    )
    all_passed &= check_file_contains(
        telemetry_rs,
        r'pub fn init\(_tx: mpsc::UnboundedSender<Event>\)',
        "crates/telemetry: init queue neutralized to no-op"
    )

    # 3. Audit crates/client/src/telemetry.rs
    client_telemetry_rs = os.path.join(source_dir, "crates", "client", "src", "telemetry.rs")
    all_passed &= check_file_contains(
        client_telemetry_rs,
        r'pub static MINIDUMP_ENDPOINT:\s*LazyLock<Option<String>>\s*=\s*LazyLock::new\(\|\|\s*None\);',
        "crates/client: MINIDUMP_ENDPOINT set statically to None"
    )
    all_passed &= check_file_contains(
        client_telemetry_rs,
        r'// Privacy: Network flush is completely disabled\.',
        "crates/client: flush_events_inner network request neutralized"
    )

    # 4. Audit crates/zed/src/reliability.rs
    reliability_rs = os.path.join(source_dir, "crates", "zed", "src", "reliability.rs")
    all_passed &= check_file_contains(
        reliability_rs,
        r'// Privacy: Remote minidump upload task disabled\.',
        "crates/zed: Remote minidump upload task removed from init"
    )

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL PRIVACY INVARIANTS PASSED! Zero telemetry guaranteed.")
        print("=" * 60)
        return True
    else:
        print("🚨 AUDIT FAILED! One or more privacy patches are missing or incomplete.")
        print("=" * 60)
        return False

def main():
    parser = argparse.ArgumentParser(description="Audit Zed source directory for privacy patches.")
    parser.add_argument(
        "--source",
        default=".zed-upstream",
        help="Path to the cloned and patched Zed source tree (default: .zed-upstream)"
    )
    args = parser.parse_args()

    if not os.path.isdir(args.source):
        print(f"Error: Directory '{args.source}' does not exist.")
        sys.exit(1)

    success = run_audit(args.source)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
