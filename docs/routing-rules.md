# Routing rules — when to use which store

The two memory stores overlap in scope but serve different purposes. Confusing them wastes tokens, duplicates data, and makes recall slower.

## Mental model

| | engram | mempalace |
|---|---|---|
| **Shape** | Structured (title, type, what/why/where/learned) | Verbatim text (full turns) |
| **Size** | Small — hundreds to low thousands of entries per project | Large — every turn captured |
| **Search** | Keyword (FTS5) | Semantic vector (ChromaDB) |
| **Write cadence** | Explicit — agent decides "this matters" | Automatic — hook captures everything |
| **Read cadence** | Session start + on demand | On demand only |
| **Portability** | Git-syncable | Too big for git; rsync only |
| **LLM needed?** | No (keyword) | No for retrieval; optional for rerank |

## Decision table

| You want to save… | Use |
|---|---|
| "Nick prefers tabs over spaces" | engram — preference |
| "We chose GraphQL over REST because of N+1 in the old stack" | engram — decision |
| "The auth flow is OAuth → JWT refresh → session cookie" | engram — architecture |
| "Parser crashed on UTF-16 input — fix: normalize to UTF-8 in preprocess.py" | engram — fix |
| "Merge freeze starts Thursday" | engram — fact |
| The entire 40-turn debugging session you just had | mempalace — automatic, no action needed |
| "What did I say about the deploy pipeline two weeks ago?" | mempalace.search |
| The raw back-and-forth with the user about API naming | mempalace (auto) — but distill the decision into engram |

## The "one fact, one store" rule

If a fact is structured and recurring, it goes to **engram**. Mempalace will still have the raw turn that produced it, but you should search engram first — it's cheaper, faster, and already deduplicated.

If you catch the agent saving the same fact to both stores, the routing is wrong. Fix the agent's instructions, not the stores.

## Session-start protocol

Every new session, the agent should:

1. Call `engram.mem_context` with the project scope → up to 20 structured memories. Fast and cheap.
2. Call `engram.mem_context` with `scope=global` → up to 5 role/preference facts. Also cheap.
3. **Do not** preemptively call `mempalace.search`. Only query it when the conversation needs context you can't answer from engram.

This keeps session-start context load small (< 2K tokens) while ensuring no preference/decision is missed.

## Corrections propagate to engram immediately

Mempalace preserves the raw correction turn automatically. But the structured truth needs to update in engram right away — otherwise the agent keeps surfacing the old value.

Protocol when the user corrects something:

1. Find the engram entry that held the wrong value (`mem_search`).
2. `mem_update` it: mark the old claim `[superseded]` with date and reason, add the new value.
3. Confirm back to the user, briefly.

Do not defer corrections to a "review later" step. Stale memory beats no memory, but only barely.

## Token economy

- Cap `mem_context` retrieval at 20 entries unless the user asks for more detail.
- `mempalace.search` is the expensive tier — call sparingly.
- If both stores answer a question, prefer engram. It's curated; mempalace is raw.
