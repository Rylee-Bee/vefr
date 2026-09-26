/* vefr/web/js/chronicle.js: how the Chronicle reads the journal.
 *
 * The journal holds several kinds of entry, and each keeps its words
 * in a different field (a rumor's `whisper`, an npc's `line`, a
 * letter's `letter`, an action's `verb`). The Chronicle shows every
 * kind in words, and folds a run of actions in one phase into a single
 * line so fifty clicks read as one entry. Pure functions, no DOM.
 */
(function (root) {
  'use strict';

  function line(e) {
    switch (e.kind) {
      case 'rumor': return { kind: 'A whisper', who: e.speaker || '', text: e.whisper || '' };
      case 'npc_line': return { kind: 'A line', who: e.speaker || '', text: e.line || '' };
      case 'stefna_letter': return { kind: 'A letter', who: '', text: e.letter || '' };
      case 'combat_action':
        return { kind: 'An action', who: '', text: 'You chose to ' + (e.verb || 'act') + (e.target ? ' → ' + e.target : '') + '.' };
      default:
        return { kind: 'A moment', who: e.speaker || '',
          text: e.text || e.content || e.event || e.whisper || e.line || e.letter || '' };
    }
  }

  function fold(entries) {
    var out = [];
    entries.forEach(function (e, idx) {
      var last = out[out.length - 1];
      if (e.kind === 'combat_action' && last && last.kind === 'combat_action' && last.phase === e.phase) {
        last.count += 1;
        last.verbs[e.verb] = (last.verbs[e.verb] || 0) + 1;
        last.at = e.at;
        return;
      }
      var run = { kind: e.kind, phase: e.phase, at: e.at, count: 1, verbs: {}, entry: e, index: idx };
      if (e.kind === 'combat_action') run.verbs[e.verb] = 1;
      out.push(run);
    });
    return out;
  }

  function actions(run) {
    var verbs = Object.keys(run.verbs).map(function (v) {
      return v + (run.verbs[v] > 1 ? ' ×' + run.verbs[v] : '');
    });
    return { kind: run.count > 1 ? run.count + ' actions' : 'An action', who: '',
      text: (run.phase ? 'At ' + run.phase + ': ' : '') + verbs.join(', ') + '.' };
  }

  root.VEFR_CHRONICLE = { line: line, fold: fold, actions: actions };
})(typeof window !== 'undefined' ? window : globalThis);
