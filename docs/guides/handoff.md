# Handoff bundle - the AI-buddy handoff format

When you hit something in the vefr engine you can't unstick alone,
the **handoff bundle** is how you bring a debugging buddy up to
speed in one paste. The engine writes it; you fill in the open
sections; whoever reads it has the full context to help.

## The shape

The bundle is a single markdown file with three sections you
write, plus three the engine fills in:

| Section | Who fills it in | What it holds |
|---|---|---|
| **What I was trying to do** | you | The action you took when it went sideways. "I dropped a new sprite into `town/sprites/` and refreshed the browser." |
| **What I saw instead** | you | The error, the surprise, the symptom. A copy-paste of the error message is perfect. |
| **What I've already tried** | you | A bullet list, even if everything failed. "Validated the pack. Restarted the server. Nothing changed." |
| **Context for the buddy** | engine | The resolved world JSON and the last 50 weave events. |
| **The task** | engine | A four-step checklist for whoever reads the bundle. |

## How to make one

From the Builder tab, click **Package handoff bundle**. The
engine writes a file under `data/handoffs/handoff-<timestamp>.md`
and shows you the path. Open it, fill in the three sections,
paste the whole thing into a chat with a buddy (AI or human).

## Why this shape

| Property | Why it matters |
|---|---|
| Single file | Email it, paste it, attach it. No tool-specific UI. |
| Markdown | Renders in every chat client and editor. |
| The "context" block is fenced JSON | A buddy can pipe it into a tool, or read it directly. |
| The "task" block is short | Keeps the answer focused. A 1-sentence cause + smallest change beats a refactor. |
| The "what I've already tried" block | Saves the buddy from suggesting things you already did. |

## When to make one

- A bug you can't reproduce (the context tells the buddy what
  the engine actually saw)
- A pack you want to hand to a collaborator (the resolved
  world is the contract)
- A question for the engine's author that needs the *exact*
  state of your world, not your description of it

## When NOT to make one

- A clear test failure (paste the failure and the test name)
- A typo (fix the typo)
- A question about the *intent* of the engine (read the docs,
  or ask in chat — the handoff is for runtime state, not
  design questions)
