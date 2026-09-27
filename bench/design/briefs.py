"""Design cup briefs: one screen each, built with Workbench.

Each brief lists `require`: CSS selectors that must exist in the result;
a (selector, n) pair needs at least n (counts added 26 Sep, after a 230M model
passed by returning the guide's empty starter page).
"""
BRIEFS = [
    {"id": "gallery-project", "brief": "A project page for a dev gallery. Breadcrumb 'Gallery / VEFR'. Title 'VEFR', one primary button 'Play newest build'. A section 'Art' with four picture cards (titles: Sticker icons, Room vignettes, Bolt's moods, Rune pebbles; each with a meta line like '27 images · 26 Sep'; use images at art/1.webp to art/4.webp). A section 'Updates' with three dated updates.",
     "require": [".wb-topbar", ".wb-crumbs", "h1", ".wb-btn--primary", (".wb-cards .wb-card", 4), (".wb-updates .wb-update", 3)]},
    {"id": "builds-table", "brief": "A 'Builds' page listing five builds in a table with columns Date, Commit, Status, Play. The newest is live (a success tag with the word Live); others are 'Past'. Commits are 7-character hashes. Include a breadcrumb and a one-sentence lede.",
     "require": [".wb-topbar", "h1", ".wb-table-wrap table.wb-table", ("th[scope=col]", 4), ("table.wb-table tbody tr", 5), ".wb-tag--success"]},
    {"id": "settings", "brief": "A settings page for a local tool with three sections: 'Theme' (buttons Dark, Light, High contrast; Dark is selected), 'Storage' (a table of two folders and their sizes), and 'Danger zone' (a button 'Clear cache' with a warning tag explaining it can't be undone).",
     "require": [".wb-topbar", "h1", (".wb-h2", 3), (".wb-btn", 4), ("table.wb-table tbody tr", 2), ".wb-tag--warning, .wb-tag--danger"]},
    {"id": "art-set", "brief": "An art set page titled 'Sticker icons' showing twelve images in a tile grid (images art/icon-1.webp to art/icon-12.webp, each linking to its full-size file and captioned with a plain name like 'bell'). Include a breadcrumb and a lede saying how many images there are.",
     "require": [".wb-topbar", "h1", (".wb-tiles .wb-tile", 12), ("figcaption", 12)]},
    {"id": "empty-project", "brief": "A project page for a brand-new project called 'Cottage of the Breeze' that has nothing published yet: breadcrumb, title, and empty states for 'Art', 'Builds' and 'Updates', each saying what's missing and the exact next step.",
     "require": [".wb-topbar", "h1", (".wb-empty", 3)]},
]

# Harder briefs (added 2026-09-26): more parts, exact counts, and one repair
# job. `require` entries may be (selector, minimum_count).
BROKEN = """<!doctype html><html><head><title>Lab</title>
<style>.big{color:#c33;background:rgb(20,20,20)} button{height:24px}</style></head>
<body><div class="big">Lab builds</div>
<button onclick="go()">Play</button><button>Delete all</button>
<img src="art/1.webp"><table><tr><td>26 Sep</td><td>ok</td></tr><tr><td>25 Sep</td><td>failed</td></tr></table>
</body></html>"""

HARD_BRIEFS = [
    {"id": "hard-status-board", "hard": True,
     "brief": "A status board for a small studio. Breadcrumb 'Studio / Status'. Title 'Status', a lede, and one primary button 'Open newest build'. "
              "Section 'Builds': a table of exactly 8 builds (columns Date, Commit, Status); statuses mix Live (success tag), Failed (danger tag) and Past (plain tag), each tag with a word and a symbol. "
              "Section 'Projects': exactly 6 picture cards (one of them has no images yet, one has a single image). "
              "Section 'Updates': 5 dated updates. Section 'Reviews': an empty state saying nothing is waiting and what to do next.",
     "require": [".wb-topbar", ".wb-crumbs", "h1", ".wb-lede", (".wb-btn--primary", 1), ("table.wb-table tbody tr", 8),
                 ".wb-tag--success", ".wb-tag--danger", (".wb-cards .wb-card", 6), ".wb-mosaic--empty", ".wb-mosaic--one",
                 (".wb-updates .wb-update", 5), ".wb-empty"],
     "forbid_many": ".wb-btn--primary"},
    {"id": "hard-repair", "hard": True,
     "brief": "Rewrite this broken internal page with Workbench. Keep all its content (title 'Lab builds', a Play action, a Delete all action, the image, both table rows with a real header row). "
              "Remove every hand-written colour and style, make the image accessible, show 'ok' and 'failed' as status tags with words, and make Delete all a normal (not primary) button.\n\n" + BROKEN,
     "require": [".wb-topbar", "h1", "table.wb-table", "th[scope=col]", ("table.wb-table tbody tr", 2), ".wb-tag--success", ".wb-tag--danger", "img[alt]", ".wb-btn"],
     "forbid_many": ".wb-btn--primary"},
    {"id": "hard-art-library", "hard": True,
     "brief": "An art library page titled 'VEFR art'. Breadcrumb, lede with the total image count, and a count label beside the title. "
              "Exactly 9 picture cards (titles of your choosing, each with a meta line with image count and date; two cards have a single image, one has none yet). "
              "Below, a section 'Wide art' with a big tile grid of 4 images (art/wide-1.webp to art/wide-4.webp), each captioned and linking to its full file.",
     "require": [".wb-topbar", ".wb-crumbs", "h1", ".wb-lede", ".wb-count", (".wb-cards .wb-card", 9), (".wb-card__meta", 9),
                 ".wb-mosaic--one", ".wb-mosaic--empty", ".wb-tiles--big", (".wb-tiles .wb-tile", 4), ("figcaption", 4)]},
]
