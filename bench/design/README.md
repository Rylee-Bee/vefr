# The style kit

## What a style kit is

A style kit is a small folder of files that decides how a web page looks.
Think of it as a paint card and a rule book for a room.
The paint card gives you the colours you may use.
The rule book says where each colour goes.
This kit also comes with a checker: a small program that looks at a page and tells you, in plain words, what is wrong with it.

## The one command

Run this from the top folder of the repository:

```bash
uv run --offline --group test python3 -m bench.design.run --html bench/design/kit-template/passing.html --brief gallery-project
```

That is the whole command.
It needs no model server, no account, no key, and no network.
`--brief gallery-project` names the short description of the page the checker expects.
`--group test` only loads the checker itself.
If a run ever says the page checker is missing, install it once on your machine:

```bash
uv run --group test playwright install chromium
```

## What you will see

- Plain sentences that say what passed and what failed.
- A score line, for example: `Score: 6 of 6 checks passed — PASS.`
- A small table with the file name, the pass mark, the score, and how long it took.
- A note telling you where your screenshot (a picture of the page) was saved.
- The screenshot lands in a fresh folder inside `bench/runs/design/`.
- Each run makes a new folder, named after the date and time, such as `bench/runs/design/20261001T105727/`.
- The picture inside is named after your page, such as `passing.png`.

## A 25-minute exercise: change one rule

The rules live in `kit-template/guide.md`, section "Before you ship".
You will break one rule, read what the checker says, fix it, then break it again.

1. (2 minutes) Copy the kit so you have your own to play with:
   `cp -r bench/design/kit-template my-style-kit`
2. (3 minutes) Run the one command on the passing page (`--html my-style-kit/passing.html`).
   You should see `6 of 6` and `PASS`.
3. (3 minutes) Run it on the failing page (`--html my-style-kit/failing.html`).
   You should see `5 of 6` and `fail`.
4. (3 minutes) Read the sentences under "What the checks found".
   One sentence names the broken rule: the page has a hand-written colour in it.
5. (5 minutes) Open `my-style-kit/failing.html` in a text editor.
   Find the line with `<h1`.
   Delete exactly ` style="color:#ff8800"` from that line.
   That is the ONE edit — touch nothing else.
6. (4 minutes) Run the command on `failing.html` again.
   The score line now says `PASS`. That is your green.
7. (5 minutes) Break it on purpose.
   Put ` style="color:#ff8800"` back on that heading, or use any colour you like.
   Run the command again: one red sentence comes back, and the score says `fail`.

Total: about 25 minutes.
The tool prints plain words, not colours: `PASS` is your green and `fail` is your red.

## Two copies that must stay identical

`kit-template/guide.md` is an exact copy of `bench/design/guide.md`.
`kit-template/workbench.css` is an exact copy of `bench/design/workbench.css`.
They sit two folders below the originals.
They are kept identical on purpose, so a test can catch it if the two copies ever drift apart.
Do not edit, tidy or improve these two copies.

## Running a model against the same kit later

Later, you can let a model build a page and score it with the same checks:

```bash
python3 -m bench.design.run MODEL
```

`MODEL` is the name of the model to run.
This path needs a model server: a separate program that serves a model, plus the settings to reach it.
That is exactly why the offline path exists — with it, you can run, read and edit the kit with no model at all.
