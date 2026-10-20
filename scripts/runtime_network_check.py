#!/usr/bin/env python3
"""
Muted - Runtime Network Check.
Launches the built Zed binary inside an isolated network namespace under strace
and fails if the process attempts any non-loopback connection or DNS lookup.
Linux only. Requires strace, unshare (util-linux) and xvfb-run.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

SOCKADDR = re.compile(r"\{sa_family=(AF_INET6?|AF_UNIX),([^}]*)\}")
IPV4 = re.compile(r'sin_port=htons\((\d+)\), sin_addr=inet_addr\("([^"]+)"\)')
IPV6 = re.compile(r'sin6_port=htons\((\d+)\).*?inet_pton\(AF_INET6, "([^"]+)"')
UNIX_PATH = re.compile(r'sun_path="([^"]+)"')
RESOLVER_SOCKETS = ("/run/systemd/resolve/", "/var/run/nscd/")


def is_loopback(address: str) -> bool:
    return address.startswith("127.") or address in ("::1", "::ffff:127.0.0.1")


def find_external_attempts(strace_log: str) -> list:
    attempts = []
    for family, body in SOCKADDR.findall(strace_log):
        if family == "AF_UNIX":
            path = UNIX_PATH.search(body)
            if path and path.group(1).startswith(RESOLVER_SOCKETS):
                attempts.append(f"dns:{path.group(1)}")
            continue
        if family == "AF_INET":
            match = IPV4.search(body)
            if match and not is_loopback(match.group(2)):
                attempts.append(f"{match.group(2)}:{match.group(1)}")
        else:
            match = IPV6.search(body)
            if match and not is_loopback(match.group(2)):
                attempts.append(f"[{match.group(2)}]:{match.group(1)}")
    return list(dict.fromkeys(attempts))


def run_isolated(binary: str, seconds: int, log_path: str) -> None:
    home = tempfile.mkdtemp(prefix="zed-privacy-home-")
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "XDG_DATA_HOME": os.path.join(home, ".local", "share"),
        "XDG_CACHE_HOME": os.path.join(home, ".cache"),
        "ZED_ALLOW_ROOT": "true",
        "ZED_ALLOW_EMULATED_GPU": "1",
    }
    command = [
        "unshare", "--user", "--map-root-user", "--net",
        "timeout", "--preserve-status", "--signal=TERM", str(seconds),
        "xvfb-run", "--auto-servernum",
        "strace", "-f", "-qq", "-s", "256", "-o", log_path,
        "-e", "trace=connect,sendto,sendmsg,sendmmsg",
        binary, "--user-data-dir", os.path.join(home, "zed-data"), home,
    ]
    subprocess.run(command, env=env, check=False)


def main():
    parser = argparse.ArgumentParser(description="Fail if Zed opens network connections at startup.")
    parser.add_argument("--binary", required=True, help="Path to the built zed binary")
    parser.add_argument("--seconds", type=int, default=90, help="How long to keep Zed running")
    parser.add_argument("--log", default="strace-network.log", help="Where to write the strace log")
    args = parser.parse_args()

    run_isolated(args.binary, args.seconds, args.log)
    with open(args.log, encoding="utf-8", errors="ignore") as f:
        log = f.read()
    if not log:
        print("❌ [FAIL] strace log is empty; Zed did not start under tracing.")
        sys.exit(1)

    attempts = find_external_attempts(log)
    if attempts:
        print("🚨 Network attempts detected at startup:")
        for attempt in attempts:
            print(f"   - {attempt}")
        sys.exit(1)
    print(f"✅ [PASS] No external network attempts in {args.seconds}s of idle startup.")


if __name__ == "__main__":
    main()
