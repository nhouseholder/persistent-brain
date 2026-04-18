# Persistent Brain — Memory Rules

You have two MCP memory servers available: **engram** (structured) and **mempalace** (verbatim). Route every memory operation through these rules.

## When to use engram (`mem_save`, `mem_context`, `mem_search`)

Save to engram when the content is **structured and recurring**:

- Decisions + the reasoning behind them
- User preferences (coding style, tools, tone)
- Architectural facts (stack, deploy targets, data contracts)
- Bug-fix takeaways ("X failed because Y, the fix is Z")
- Names, roles, commitments, deadlines
- Any fact the user explicitly asks you to remember

`mem_save` fields: `title`, `type` (decision / preference / architecture / fix / fact), `what`, `why`, `where`, `learned`.

## When to use mempalace (`mempalace.search`, `mempalace.wake_up`)

Query mempalace when you need **raw conversation recall**:

- "Did we discuss X before?"
- "What did I say last week about Y?"
- Searching for context across many past sessions
- Pulling verbatim exchanges you don't need to paraphrase

Mempalace captures full conversations automatically. You don't need to explicitly save to it — just search when you need recall.

## Session start protocol

Before your first substantive reply in a new session:

1. Call `engram.mem_context` with the current project name → up to 20 structured memories.
2. Call `engram.mem_context` with `scope=global` → up to 5 preferences/role facts.
3. Do **not** preemptively query mempalace. Only search mempalace when the user asks about prior conversations or you genuinely can't answer without transcript context.

Treat the returned memories as authoritative. Do not ask the user to repeat anything that's already in them.

## Never double-write

One fact lives in one store. If it belongs in engram (structured, recurring), save it there and do not also push it to mempalace. Mempalace captures the raw turn automatically.

## Corrections

If the user corrects something you said or a memory you surfaced:

1. Update the relevant engram entry immediately (`mem_update` — mark the old value superseded, add the correction).
2. Do not wait until the "end" of the session — corrections are high-priority writes.

## Scope hierarchy (hybrid)

Every project has:
- Its own engram DB (`~/.engram/<project>.db`)
- Its own mempalace palace (`~/.mempalace/<project>/`)

Plus a **global** engram DB + mempalace palace for user-level prefs and role facts.

When the agent starts in a project directory, it should load both the project brain AND the global brain on session start (step 1 + 2 above). Never write global-level facts (preferences, role) to a project brain, and never write project-specific facts to the global brain.

## Token economy

- Cap `mem_context` retrieval at 20 entries unless the user asks for more.
- Only call `mempalace.search` on demand. It's the expensive tier.
- If both stores return the same fact, trust engram (it's the curated one).
