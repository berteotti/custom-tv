# 2. Make it the Home button

> [!WARNING]
> This step runs commands as root on your TV. It worked on the TV listed in the README, but it hasn't been tested on any other. Take the backup in step 3 before you change anything, and keep the rollback command handy.

At level 1, the remote's Home button still opens Samsung's launcher (`com.samsung.tv.csfs`). The TV decides what Home opens from a per-user setting. Developer Mode doesn't let you change that setting, but a short root session can.

## How the root session works

Developer Mode alone gives no root access. The SDK's package-installer channel runs as UID 901. From there, Samsung's own capability-bearing .NET runtime and archive launcher can open a **temporary** UID/GID 0 session. The process keeps Samsung's `User` SMACK label, so even root can't touch every file.

The implementation comes from [chris-ritsen/samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root/tree/4ad2c4d3b0d0e0da4b5b7ebe4a787e94596f416b). It's vendored in `tools/vendor/samsung-tv-root/` with a small runtime-detection patch, and [UPSTREAM.md](../tools/vendor/samsung-tv-root/UPSTREAM.md) has the details. It installs no kernel exploit, firmware change or permanent service.

Each `tools/tv-root.py` call opens a session, runs your commands and closes the session again. Each call:

- reports each command's exit code
- checks that the TV's system authentication files are unchanged
- cleans up after itself

Commands time out after 45 seconds, and each output stream is capped at 1 MiB. Don't run two sessions at once.

## What you need

- [Level 1](1-install.md) done, with TV Home installed.
- Python 3.12. Other recent versions are probably fine but haven't been tested.
- A .NET SDK that can build `net6.0` projects ([download](https://dotnet.microsoft.com/download)).
- **Firewall:** the root session works by having the TV connect back to your computer on an ephemeral port. If you run a host firewall (UFW, firewalld, iptables), allow inbound TCP from the TV's IP before step 2. On UFW: `sudo ufw allow from <TV_IP>` (and `sudo ufw delete allow from <TV_IP>` when you're done).

## Step 1: build the helpers

```bash
tools/build-helpers.sh
```

This compiles the two root payloads, the Home-routing helper and the notification helper from the source in this repo. No prebuilt binaries are included.

## Step 2: check access

```bash
export TV_IP=192.168.1.50
```

```bash
tools/tv-root.py --command 'id'
```

Look for `uid=0` in the output and `"system_files_unchanged": true` in the report. Quote remote commands with single quotes so your computer's shell doesn't expand them.

## Step 3: back up

```bash
tools/tv-root.py --command "$(cat extras/backup-tv-state.sh)"
```

```bash
~/tizen-studio/tools/sdb -s "$TV_IP:26101" pull /home/owner/share/tmp/sdk_tools/tv-home-backup.tgz .
```

The first command takes consistent SQLite snapshots of the package, app-service, notification and app-context databases. It saves them with the systemd override folders in one archive. The second command copies that archive to your computer. Compare its SHA-256 with the one printed by the first command, and keep it private.

> **Tizen 6.5 note:** `sdb pull` from this path may fail with "You cannot pull files from this path". If so, pull the archive through the root session instead:
>
> ```bash
> tools/tv-root.py --command 'base64 /home/owner/share/tmp/sdk_tools/tv-home-backup.tgz' \
>   | python3 -c "import base64,json,sys; r=json.load(sys.stdin); d=base64.b64decode(r['commands'][0]['stdout']); open('tv-home-backup.tgz','wb').write(d); print(len(d),'bytes')"
> ```

The archive is for diagnosis and careful recovery. **Never copy the snapshots over the live databases.** Use the rollback commands below instead.

## Step 4: read the current Home

```bash
tools/home-routing.py
```

This should print `home=com.samsung.tv.csfs`. If it prints anything else, stop. The helper only switches between `com.samsung.tv.csfs` and `TvHomeLnch.Home`, and it refuses to overwrite an assignment it doesn't expect.

## Step 5: switch to TV Home

```bash
tools/home-routing.py --set custom
```

Then open another app and press **Home** on the remote. TV Home should appear.

## Switch back to Samsung's Home

```bash
tools/home-routing.py --set stock
```

Always do this **before** uninstalling TV Home.

## What the routing helper does

`tools/home-routing/Program.cs` is staged on the TV, run once through the root session and then deleted. It:

1. drops to the TV owner (UID 5001, GID 100), whose preferences decide Home
2. reads the current target through Samsung's native app-operation API
3. refuses to continue unless the target is the one it expects
4. sets the new target and reads it back
5. sets the old target back if the read-back doesn't match

## Tested TVs

| Model | Year | Tizen | .NET runtime | Result |
| --- | --- | --- | --- | --- |
| QN55S95BAFXZA (S95B) | 2022 | 6.5 | 3.1.3 | Root, home routing and backup all work |

Older Tizen versions (6.5 and earlier) ship with .NET 3.1 instead of 6.0. `build-helpers.sh` builds for both runtimes, and the helper scripts detect which one the TV has.

## Known gaps

Persistence after a cold reboot was **not** verified on either test TV. If Home reverts after unplugging the TV, run step 5 again.
