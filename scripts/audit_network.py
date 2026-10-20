#!/usr/bin/env python3
"""
Muted - Network and Telemetry Static Auditor.
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
    print(f"🔍 Starting Muted Network & Telemetry Audit on: {source_dir}\n")
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
    all_passed &= check_file_contains(
        settings_path,
        r'"auto_install_extensions":\s*\{\s*"html":\s*false,',
        "Default settings: html extension not auto-installed at startup"
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
    all_passed &= check_file_contains(
        telemetry_rs,
        r'unbounded_send\(',
        "crates/telemetry: no events pushed to the telemetry queue",
        should_exist=False
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
    all_passed &= check_file_contains(
        client_telemetry_rs,
        r'http_client\.send\(',
        "crates/client: telemetry performs no HTTP sends",
        should_exist=False
    )

    # 4. Audit crates/zed/src/reliability.rs
    reliability_rs = os.path.join(source_dir, "crates", "zed", "src", "reliability.rs")
    all_passed &= check_file_contains(
        reliability_rs,
        r'// Privacy: Remote minidump upload task disabled\.',
        "crates/zed: Remote minidump upload task removed from init"
    )
    all_passed &= check_file_contains(
        reliability_rs,
        r'upload_previous_minidumps\(client\)',
        "crates/zed: upload_previous_minidumps is never called",
        should_exist=False
    )

    # 5. Audit startup fetches
    extension_host_rs = os.path.join(source_dir, "crates", "extension_host", "src", "extension_host.rs")
    all_passed &= check_file_contains(
        extension_host_rs,
        r'if extension_ids\.is_empty\(\) \{\s*return Task::ready\(Ok\(Vec::new\(\)\)\);',
        "crates/extension_host: no update check without installed extensions"
    )
    registry_store_rs = os.path.join(source_dir, "crates", "project", "src", "agent_registry_store.rs")
    all_passed &= check_file_contains(
        registry_store_rs,
        r'if store\.agents\.is_empty\(\) \{\s*store\.refresh\(cx\);',
        "crates/project: agent registry is not fetched on init",
        should_exist=False
    )

    # 6. Audit rebrand (binary, data dirs and bundle must not collide with Zed)
    paths_rs = os.path.join(source_dir, "crates", "paths", "src", "paths.rs")
    all_passed &= check_file_contains(
        paths_rs,
        r'pub const APP_NAME: &str = "Muted";',
        "crates/paths: APP_NAME is Muted (separate config and data dirs)"
    )
    zed_cargo_toml = os.path.join(source_dir, "crates", "zed", "Cargo.toml")
    all_passed &= check_file_contains(
        zed_cargo_toml,
        r'\[\[bin\]\]\nname = "muted"\npath = "src/main.rs"',
        "crates/zed: main binary is named muted"
    )
    all_passed &= check_file_contains(
        zed_cargo_toml,
        r'identifier = "io\.github\.andermoreira\.Muted"',
        "crates/zed: stable bundle identifier is not Zed's"
    )
    mac_instance_rs = os.path.join(source_dir, "crates", "zed", "src", "zed", "mac_only_instance.rs")
    all_passed &= check_file_contains(
        mac_instance_rs,
        r'let port = MUTED_PORT_OFFSET\s*\+\s*match',
        "crates/zed: macOS single-instance port never hands off to a running Zed"
    )

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL PATCH MARKERS PRESENT. This is a static check, not proof of zero network traffic.")
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
