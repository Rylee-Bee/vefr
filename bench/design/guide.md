# Workbench: how to build a page
## Starter page

```html
<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Page name · Tool name</title>
<link rel="stylesheet" href="/workbench.css">
</head>
<body class="wb-page">
<a class="wb-btn wb-btn--quiet" href="#main" style="position:absolute;left:-999px">Skip to content</a>
<header class="wb-topbar"><div class="wb-wrap">
  <nav aria-label="Breadcrumb"><ol class="wb-crumbs">
    <li><a href="/">Tool name</a></li><li aria-current="page">Page name</li>
  </ol></nav>
</div></header>
<main id="main" class="wb-wrap">
  <h1 class="wb-h1">Page name</h1>
  <p class="wb-lede">One sentence on what this page is for.</p>
  <!-- sections: wb-h2, then cards, tiles, tables or updates -->
</main>
</body>
</html>
```

## Choosing a component

| You have | Use |
|---|---|
| Collections of pictures (art sets, projects) | Picture card grid |
| Many pictures in one collection | Tile grid |
| Rows of like things with columns (builds, docs, runs) | Table |
| Dated news | Update list |
| Nothing yet | Empty state |
| Status of one thing | Tag |
| Where you are | Top bar with breadcrumbs |

## Before you ship: checklist

1. Only `wb-` classes and `--wb-*` tokens; no raw hex colours in the page.
2. Text contrast: `wb-text` and `wb-text-dim` only on `wb-bg`, `wb-surface` or `wb-raise`.
3. Every control at least 44px; every link that looks like a button uses `wb-btn`.
4. Tab through the page: focus is visible everywhere and the order makes sense.
5. Nothing moves: no transitions, animations or autoplay.
6. At 390px wide: no sideways scroll; tables scroll inside `wb-table-wrap`.
7. Every status has a word; every meaningful image has `alt`.
8. Words: sentence case, verbs on buttons, errors say what to do next.

## Component: TopBar
The top bar holds the breadcrumb trail (where you are) and at most one or two quiet links.

```html
<header class="wb-topbar"><div class="wb-wrap">
  <nav aria-label="Breadcrumb"><ol class="wb-crumbs">
    <li><a href="/">Gallery</a></li>
    <li><a href="/vefr/">VEFR</a></li>
    <li aria-current="page">Sticker icons</li>
  </ol></nav>
</div></header>
```

- The last crumb is the current page: plain text with `aria-current="page"`, never a link.
- Crumb links are 44px tall; don't put anything else in the `ol`.

## Component: Button
Buttons and button-looking links: one family, three weights.

```html
<div class="wb-actions">
  <a class="wb-btn wb-btn--primary" href="…">Play newest build</a>
  <a class="wb-btn" href="…">All updates</a>
  <button class="wb-btn wb-btn--quiet" type="button">Copy link</button>
</div>
```

- `wb-btn--primary`: the one main action on a page. Only one per view.
- `wb-btn`: everything else. `wb-btn--quiet`: low-emphasis actions, shown as accent text.
- Use `<a>` when it goes somewhere and `<button type="button">` when it does something. The label is a verb phrase in sentence case.
- Disabled: `disabled` on a button, `aria-disabled="true"` on a link, and say why in the label ("Publishing…").

## Component: Tag
Tags state one fact about a thing; counts label a section.

```html
<span class="wb-tag wb-tag--success">✓ Live</span>
<span class="wb-tag wb-tag--danger">✕ Build failed</span>
<span class="wb-count">21 sets</span>
```

- Every status tag carries a word, and ideally a symbol (✓ ! ✕). Colour is never the only signal: `wb-success` and `wb-danger` are close in lightness.
- Tags are not buttons. If it's clickable, use `wb-btn`.

## Component: PictureCard
A picture card shows a collection at a glance: a mosaic of up to four previews, a title, a meta line and an optional note. The whole card is one link.

```html
<div class="wb-cards">
  <a class="wb-card" href="/vefr/art/sticker-icons/">
    <div class="wb-mosaic" aria-hidden="true">
      <img src="…/view/bell.webp" alt=""> <!-- up to four -->
    </div>
    <span class="wb-card__title">Sticker icons</span>
    <span class="wb-card__meta">27 images · 26 Sep</span>
    <span class="wb-card__note">Optional one-line note.</span>
  </a>
</div>
```

- One image: add `wb-mosaic--one` (the image fills the frame). No images: `wb-mosaic--empty`.
- The mosaic is decorative (`aria-hidden`, `alt=""`): the title names the card.
- Transparent images sit on the checkerboard (`wb-check-a` and `wb-check-b`), so cut-outs read correctly.

## Component: TileGrid
An image grid: every picture visible on the page, each linking to its full-size file.

```html
<ul class="wb-tiles" style="list-style:none">  <!-- add wb-tiles--big for wide art -->
  <li><figure class="wb-tile">
    <a href="bell.png"><img src="view/bell.webp" alt="Bell"></a>
    <figcaption>bell</figcaption>
  </figure></li>
</ul>
```

- Show a small preview (`view/…`) and link the original.
- Use `wb-tiles--big` when the pictures are wide (banners, screenshots, illustrations over 1000px).
- Write a real `alt`; the caption is the file's name in words.

## Component: Table
Tables are for rows of like things with the same columns: builds, docs, runs.

```html
<div class="wb-table-wrap"><table class="wb-table">
  <thead><tr><th scope="col">Date</th><th scope="col">Commit</th></tr></thead>
  <tbody><tr><td class="wb-mono">2026-09-26</td><td class="wb-mono">a312cea</td></tr></tbody>
</table></div>
```

- Always wrap in `wb-table-wrap` (it scrolls sideways on phones instead of the page).
- Headers use `scope="col"`. Hashes, dates and paths use `wb-mono`.
- Pictures don't belong in tables: use picture cards or tiles.

## Component: UpdateList
A list of short, dated updates, newest first.

```html
<ul class="wb-updates">
  <li class="wb-update">
    <span class="wb-update__when">26 Sep, 10:15</span>
    <a class="wb-update__where" href="/vefr/">VEFR</a>   <!-- optional -->
    <p>The gallery shows pictures right on the page now.</p>
  </li>
</ul>
```

- One plain sentence or two per update; say what changed for the reader.
- `wb-update__where` names the project when the list mixes projects.

## Component: EmptyState
What a section shows when it has nothing yet: what's missing, and how to add it.

```html
<div class="wb-empty">
  <strong>No art sets yet.</strong>
  Publish one with <span class="wb-mono">gallery art &lt;project&gt; &lt;folder&gt;</span>.
</div>
```

- The bold line says what's missing; the second line says the next step, with the exact command or button.
