# Getting free model access

harness-fleet runs entirely on models that cost **$0**. You do not need a paid account, and you can
decide later whether paying for faster or stronger models is worth it. Pick one of the three
options below — the first is the least work.

Nothing here is charged unless you choose to add credit yourself.

---

## Option 1 — OpenRouter (one signup, about two minutes)

OpenRouter is a gateway that serves free models from many providers behind one key. harness-fleet already
knows which of its models are free and will use only those.

1. Make a free account: <https://openrouter.ai/> → **Sign in**
2. Create a key: <https://openrouter.ai/keys> → **Create Key** → copy it (it starts with `sk-or-`)
3. Give the key to harness-fleet:

   ```bash
   export OPENROUTER_API_KEY="sk-or-paste-yours-here"
   harness-fleet doctor
   ```

   `doctor` should now say `openrouter  configured`. To keep the key for future terminal windows,
   add that `export` line to your shell profile (`~/.zshrc` on macOS, `~/.bashrc` on Linux).

If you used the one-click installer, re-running it with the key set also copies the key into your
Claude Desktop / Cursor configuration, so your assistant can use it too:

```bash
OPENROUTER_API_KEY="sk-or-..." ./install.sh
```

**What you get:** the free models — the ones whose name ends in `:free` (about twenty today) plus
OpenRouter's own `openrouter/free`. They have daily request caps set by OpenRouter: plenty for real
work on hundreds of records, not for millions. Run `harness-fleet routes` to see exactly what is available
to you right now.

---

## Option 2 — OpenCode (a terminal tool with its own free models)

OpenCode ships free hosted models of its own; they appear in `harness-fleet routes` as `opencode/...`.

```bash
# macOS / Linux
curl -fsSL https://opencode.ai/install | bash
# or:    brew install anomalyco/tap/opencode
# Windows: choco install opencode    (or use WSL)

opencode auth login          # choose "opencode" and sign in
```

Or run `opencode` and type `/connect`, pick `opencode`, and sign in at
<https://opencode.ai/auth>.

**Worth knowing:** OpenCode's own gateway asks for billing details during signup. Its free models
stay free, but if you would rather not enter card details, use OpenRouter or a local model instead.

---

## Option 3 — A model on your own machine (no signup, no limits)

```bash
# install from https://ollama.com/download, then:
ollama pull llama3.2
harness-fleet routes add ollama/llama3.2 --provider ollama --free
```

Nothing to sign up for, no daily cap, and your data never leaves the computer. Local models are
slower and weaker than the hosted free ones, which is fine for triage and extraction.

---

## Checking what you have

```bash
harness-fleet doctor     # is each AI tool installed? is your OpenRouter key set?
harness-fleet routes     # the $0 routes available right now (add --all to see everything)
harness-fleet studio     # click-to-choose page for picking which tools and models runs may use
```

If `doctor` shows no usable routes, nothing is connected yet — pick one of the three options above
and re-run `doctor`.
