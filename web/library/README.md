# web/library/: the studio's own shelf

The studio handbook as Library books: how games are made, one stage at a
time. Same format as a pack's `library/*.md` (see `src/vefr/library.py`).
These belong to the studio, not to any world, and ship with `web/`.

## House rules the tests check

- A **bold phrase with no end punctuation** names something on screen (a button, a
  room, a setting), so it must exist in the studio. Emphasis and definitions end in
  `.` or `:` (`**Try it.**`, `**Keep:**`).
- An *italic* word is a real-world term: it becomes tappable, so it needs an entry in
  `web/js/glossary.js`.
- Every book's front matter names a `source:` (the file where the truth lives), and
  that file must exist.
