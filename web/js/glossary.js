/* vefr/web/js/glossary.js: loads the real words the Library teaches.
 * The words themselves are data: web/library/glossary.json (one file for the
 * Library's tap-to-learn, Fróði's notes, and the Worlds room). See web/library/README.md.
 * VEFR_GLOSSARY_READY resolves once they're in; a failed load leaves an empty
 * glossary, so books still read, just without tappable words. */
window.VEFR_GLOSSARY = {};
window.VEFR_GLOSSARY_READY = fetch('/static/library/glossary.json')
  .then(function (r) { if (!r.ok) throw new Error('glossary ' + r.status); return r.json(); })
  .then(function (g) { window.VEFR_GLOSSARY = g; return g; })
  .catch(function () { return window.VEFR_GLOSSARY; });
