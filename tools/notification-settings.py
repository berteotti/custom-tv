#!/usr/bin/env python3
"""Read or change only Software Update popup notification preferences."""
import argparse
import asyncio
import json
import os
import re
import shlex
import sys
import uuid
from pathlib import Path, PurePosixPath

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS / "vendor/samsung-tv-root"))
from samsung_tv_root.archive_root import probe
from samsung_tv_root.sdb import SdbClient, find_sdb

MODES = ("quiet", "restore")
HELPER_FILES = (
    "NotificationSettings.dll",
    "NotificationSettings.deps.json",
    "NotificationSettings.runtimeconfig.json",
)


def _detect_runtime(client):
    """Return 'out31' for .NET 3.1 TVs or 'out' for .NET 6+."""
    result = client.capture(
        "/usr/bin/dotnet --list-runtimes 2>&1"
        " || readlink -f /usr/share/dotnet.tizen/netcoreapp",
        timeout=15,
    )
    output = result.output.split("\n[exit:")[0]
    for line in output.splitlines():
        if re.match(r"Microsoft\.NETCore\.App [6-9]\.", line):
            return "out"
    return "out31"


def _resolve_helper(parser, client):
    """Find the compiled helper directory for this TV's runtime."""
    suffix = _detect_runtime(client)
    directory = TOOLS / "notification-settings" / suffix
    files = [directory / name for name in HELPER_FILES]
    if all(path.is_file() for path in files):
        return files
    fallback = TOOLS / "notification-settings/out"
    files = [fallback / name for name in HELPER_FILES]
    if all(path.is_file() for path in files):
        return files
    parser.error("Compiled helper missing; run tools/build-helpers.sh first.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tv", default=os.environ.get("TV_IP"), help="TV IP address (default: $TV_IP)")
    parser.add_argument("--set", choices=MODES, dest="target")
    args = parser.parse_args()
    if not args.tv:
        parser.error("pass --tv <ip> or set TV_IP")
    client = SdbClient(find_sdb(), args.tv)
    client.connect()
    client.require_device()
    files = _resolve_helper(parser, client)
    remote = PurePosixPath("/home/owner/share/tmp/sdk_tools") / ("tvhome-notification-" + uuid.uuid4().hex)
    created = client.capture("mkdir -m 777 " + str(remote), timeout=20)
    if "[exit:0]" not in created.output:
        raise RuntimeError("Could not create temporary helper directory: " + created.output)
    try:
        for path in files:
            client.push(path, remote / path.name)
        command = "set -eu; chmod 755 " + str(remote) + "; /usr/bin/dotnet " + str(remote / "NotificationSettings.dll")
        if args.target:
            command += " " + shlex.quote(args.target)
        report = asyncio.run(probe(args.tv, commands=(command,)))
        print(json.dumps(report, indent=2))
        return int(
            not report.get("system_files_unchanged")
            or not report.get("staging_cleaned")
            or any(c["exit_code"] != 0 or c["timed_out"] for c in report["commands"])
        )
    finally:
        cleanup = client.capture("rm -rf " + str(remote), timeout=20)
        if "[exit:0]" not in cleanup.output:
            raise RuntimeError("Temporary helper cleanup failed: " + cleanup.output)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
