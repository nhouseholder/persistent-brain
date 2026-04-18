# Sync strategy — cross-machine persistence

Two different stores, two different sync strategies.

## engram — git sync (first-class)

Engram ships native git sync. It exports memory as small compressed chunks so commits stay lightweight, and imports new chunks from any other machine that pushed to the same remote.

### One-time setup (private sync repo)

```bash
# Create a private repo for your chunks
gh repo create my-engram-sync --private --clone
cd my-engram-sync

# Point engram at it
ln -s "$(pwd)" ~/.engram/sync-repo

# First export
engram sync
git add .engram/
git commit -m "initial engram sync"
git push -u origin main
```

### Ongoing — machine A

```bash
engram sync                    # export new chunks
git -C ~/.engram/sync-repo add . && git commit -m "sync" && git push
```

### Ongoing — machine B

```bash
git -C ~/.engram/sync-repo pull
engram sync --import
```

Or wire it into `brain-sync.sh` (see below).

## mempalace — rsync (no git)

The Chroma vector DB is too large and too churny for git. Use rsync, a shared folder, or a NAS.

### Simple: rsync to a server you own

```bash
# From machine A to machine B
./scripts/brain-sync.sh --rsync user@machine-b:~/.mempalace/
```

That's a full mirror (`rsync -avz --delete`). Running it from both directions in alternation isn't safe — pick one machine as the "writer" or use a shared FS mount.

### Safer: shared mount (iCloud, Dropbox, Syncthing)

Mount the storage, then symlink:

```bash
ln -s /path/to/shared/mempalace ~/.mempalace
```

Syncthing works well because it handles conflicts predictably and you control the servers.

### Avoid iCloud for `.mempalace/`

iCloud throttles large directories and silently rewrites timestamps — ChromaDB hates that. Syncthing or a NAS is safer.

## Recommended combo

- `~/.engram/` → git (private repo)
- `~/.mempalace/` → Syncthing between your machines, OR accept single-machine-only recall and rebuild as needed

If you only work on one laptop, skip the mempalace sync entirely. Engram is what you really need to carry across machines.
