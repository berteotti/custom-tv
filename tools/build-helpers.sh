#!/bin/bash
# Build the .NET helpers that run on the TV (only needed for docs/2-set-as-home.md and extras).
# Requires a .NET SDK that can target net6.0 (`dotnet --list-sdks`).
# Builds both net6.0 and netcoreapp3.1 so the tools work on Tizen 6.5 (.NET 3.1) and newer.
set -euo pipefail

TOOLS="$(cd "$(dirname "$0")" && pwd)"
VENDOR="$TOOLS/vendor/samsung-tv-root"

for project in "$VENDOR"/payload-source/*.csproj; do
  dotnet build "$project" --configuration Release --output "$VENDOR/samsung_tv_root/payloads/common"
  dotnet restore "$project" -p:TargetFramework=netcoreapp3.1
  dotnet build "$project" --configuration Release --no-restore -p:TargetFramework=netcoreapp3.1 --output "$VENDOR/samsung_tv_root/payloads/common31"
done
for project in "$TOOLS"/home-routing/HomeRouting.csproj "$TOOLS"/notification-settings/NotificationSettings.csproj; do
  outdir="$(dirname "$project")/out"
  dotnet build "$project" --configuration Release --output "$outdir"
  dotnet restore "$project" -p:TargetFramework=netcoreapp3.1
  dotnet build "$project" --configuration Release --no-restore -p:TargetFramework=netcoreapp3.1 --output "${outdir}31"
done
