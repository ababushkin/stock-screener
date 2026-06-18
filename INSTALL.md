# Installing the stock-screener pack

This repo is a self-contained Claude Code plugin: 6 skills (`/stock-screen`,
`/stock-signal`, `/stock-model`, `/stock-timing`, `/stock-portfolio`,
`/stock-explain`) plus two MCP servers (`yf`, `edgar`).

## Prerequisite

[`uv`](https://docs.astral.sh/uv/) must be on `PATH`. The MCP servers run via
`uv run --script`, which resolves their Python dependencies into an ephemeral
environment from the inline [PEP 723](https://peps.python.org/pep-0723/) block
at the top of each `mcp/*/server.py` — **no virtualenv to build or maintain**.

```bash
uv --version   # any recent version; tested on 0.5.x
```

> If you launch Claude Code from a GUI (desktop app) rather than a terminal,
> make sure `uv` is on the GUI's inherited `PATH` (e.g. symlink it into
> `/usr/local/bin`), or the MCP servers won't spawn.

## Option A — install as a plugin (recommended, any machine)

Skills load through Claude Code's plugin system (no symlinks, survives repo
renames). From inside Claude Code:

```
/plugin marketplace add /path/to/stock-screener      # or: ababushkin/stock-screener (GitHub)
/plugin install stock-screener@stock-screener
/mcp                                                 # verify yf + edgar show ✓ Connected
```

`/plugin marketplace add` accepts the repo's local path or its GitHub
`owner/repo`. The marketplace and the plugin share the name `stock-screener`,
hence `stock-screener@stock-screener`.

After install, confirm a skill is live, e.g. run `/stock-portfolio`.

## Option B — run straight from the repo (development)

The repo-root `.mcp.json` registers `yf`/`edgar` (also via `uv run`) whenever
this directory is the project, so the MCP servers work with zero install.
Skills, in dev, are loaded by symlinking each into `~/.claude/skills/`:

```bash
for s in stock-model stock-portfolio stock-screen stock-signal stock-timing stock-explain; do
  ln -sfn "$PWD/skills/$s" ~/.claude/skills/"$s"
done
```

## Migrating from the old symlink install

Earlier this pack was installed purely as global symlinks in
`~/.claude/skills/` pointing at the repo. That breaks silently if the repo is
moved or renamed (the links dangle and the skills vanish with no error). If you
adopt **Option A**, remove those symlinks so skills don't double-load:

```bash
for s in stock-model stock-portfolio stock-screen stock-signal stock-timing stock-explain; do
  rm -f ~/.claude/skills/"$s"
done
```

Don't run Option A (plugin) and Option B (symlinks) in the same workspace — the
skill names collide. When both a project `.mcp.json` and the plugin define
`yf`/`edgar`, the project scope wins; there's no error, but pick one to avoid
confusion.
