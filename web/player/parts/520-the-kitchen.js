// ---- the kitchen (cooking ruleset v0) ----
// The morning is pack-authored; the engine only resolves it.
// Orders arrive as the customer's voice (the ticket's note) -
// reading them is the game. Resolution is set equality,
// deterministic, model-free. No timers: tickets wait.
var KITCHEN_KEY = 'vefr-packaged-kitchen';
function kitchenJournal() {
  return store.getJSON(KITCHEN_KEY, []);
}
function kitchenLog(entry) {
  var j = kitchenJournal();
  entry.at = new Date().toISOString();
  j.push(entry);
  store.setJSON(KITCHEN_KEY, j);
  return entry;
}
function initKitchen() {
  var act = (VEFR_WORLD.acts && VEFR_WORLD.acts[0]) || {};
  var K = act.cooking || {};
  var pantry = K.pantry || [];
  var tickets = K.tickets || [];
  var morningLen = K.morning_length || tickets.length;
  var headlines = K.headlines || [];
  var resolved = {};
  var wrapper = [];
  var resolvedCount = 0;
  var vol = 1;
  var morningStart = kitchenJournal().length;

  // The town stays asleep during a cooking morning.
  document.querySelectorAll(
    '#phase, #play > section.controls, #feed, #hud-hp, #encounter-prompt,'
    + ' #town-canvas, #near, #poi, #dpad, #npc-box, #verb-row, #combat-log,'
    + ' #combat-live, #play > h2, #play > p.status'
  ).forEach(function (el) { el.hidden = true; });
  document.getElementById('kitchen').hidden = false;
  document.getElementById('k-open').textContent =
    K.opening || 'the grill wakes before the world does.';

  function labels(ids) {
    return ids.map(function (id) {
      var item = pantry.filter(function (p) { return p.id === id; })[0];
      return item ? item.label : id;
    });
  }
  function sameSet(a, b) {
    return a.slice().sort().join('\u0000') === b.slice().sort().join('\u0000');
  }
  function nextTicket() {
    for (var i = 0; i < tickets.length; i++) {
      if (!resolved[tickets[i].id]) return tickets[i];
    }
    return null;
  }
  function line(t) { document.getElementById('k-line').textContent = t; }

  function renderRail() {
    var box = document.getElementById('k-tickets');
    box.innerHTML = '';
    tickets.forEach(function (t) {
      var card = document.createElement('article');
      card.className = 'card' + (resolved[t.id] ? ' done' : '');
      var who = document.createElement('p');
      who.className = 'speaker';
      who.textContent = t.customer;
      var voice = document.createElement('p');
      voice.className = 'order-voice';
      voice.textContent = '\u201c' + t.note + '\u201d';
      card.appendChild(who); card.appendChild(voice);
      if (resolved[t.id]) {
        var ep = document.createElement('p');
        ep.className = 'epitaph';
        ep.textContent = resolved[t.id].epitaph;
        card.appendChild(ep);
      }
      box.appendChild(card);
    });
  }
  function renderPantry() {
    var box = document.getElementById('k-pantry');
    box.innerHTML = '';
    pantry.forEach(function (p) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = p.label;
      b.dataset.pid = p.id;
      b.setAttribute('aria-pressed', wrapper.indexOf(p.id) > -1 ? 'true' : 'false');
      box.appendChild(b);
    });
  }
  function renderWrap() {
    document.getElementById('k-wrap').textContent = wrapper.length
      ? labels(wrapper).join(' + ')
      : 'an empty wrapper, waiting.';
  }
  function renderAll() { renderRail(); renderPantry(); renderWrap(); }

  function showHeadlines(msg) {
    document.getElementById('k-serve').hidden = true;
    document.getElementById('k-undo').hidden = true;
    document.getElementById('k-aside').hidden = true;
    document.getElementById('k-pantry').hidden = true;
    var box = document.getElementById('k-headline-list');
    box.innerHTML = '';
    headlines.forEach(function (h) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = h;
      b.addEventListener('click', function () {
        kitchenLog({ kind: 'headline_printed', headline: h, vol: vol });
        renderPage(h);
      });
      box.appendChild(b);
    });
    document.getElementById('k-headlines').hidden = false;
    line(msg || 'the morning is over. the paper wants a front page.');
  }

  function renderPage(headline) {
    var entries = kitchenJournal().slice(morningStart);
    var items = entries.map(function (e) {
      if (e.kind === 'ticket_served') {
        return e.customer + ' was fed: ' + labels(e.order).join(', ') + '.';
      }
      if (e.kind === 'ticket_corrected') {
        return e.customer + ' got something else (' + labels(e.order).join(', ')
          + '). they ate it anyway.';
      }
      if (e.kind === 'ticket_set_aside') {
        return 'a ticket for ' + e.customer + ' waited behind the glass.';
      }
      return null;
    }).filter(function (x) { return x; });
    var page = document.getElementById('k-page');
    page.innerHTML = '';
    var mast = document.createElement('p');
    mast.className = 'masthead';
    mast.textContent = 'the morning page \u00b7 vol. ' + vol + ' no. 1';
    var h3 = document.createElement('h3');
    h3.textContent = headline;
    var by = document.createElement('p');
    by.className = 'byline';
    by.textContent = K.byline || ('by ' + (VEFR_WORLD.title || 'the truck'));
    var ul = document.createElement('ul');
    items.forEach(function (t) {
      var li = document.createElement('li');
      li.textContent = t;
      ul.appendChild(li);
    });
    page.appendChild(mast); page.appendChild(h3); page.appendChild(by);
    page.appendChild(ul);
    if (VEFR_WORLD.creed) {
      var cr = document.createElement('p');
      cr.className = 'creed';
      cr.textContent = VEFR_WORLD.creed;
      page.appendChild(cr);
    }
    var more = document.createElement('p');
    more.className = 'byline';
    more.textContent = 'more mornings soon.';
    page.appendChild(more);
    document.getElementById('k-headlines').hidden = true;
    page.hidden = false;
    document.getElementById('k-again').hidden = false;
    page.focus();
  }

  document.getElementById('k-pantry').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-pid]');
    if (!b) return;
    var id = b.dataset.pid;
    var at = wrapper.indexOf(id);
    if (at > -1) wrapper.splice(at, 1); else wrapper.push(id);
    renderPantry(); renderWrap();
  });
  document.getElementById('k-undo').addEventListener('click', function () {
    if (!wrapper.length) { line('nothing to take back.'); return; }
    wrapper.pop();
    renderPantry(); renderWrap();
  });
  document.getElementById('k-serve').addEventListener('click', function () {
    var t = nextTicket();
    if (!t) return;
    if (!wrapper.length) { line('the wrapper is empty. the customer waits.'); return; }
    var ok = sameSet(wrapper, t.order);
    resolved[t.id] = {
      ok: ok,
      epitaph: ok ? 'fed \u00b7 ' + t.customer : 'fed, mostly \u00b7 ' + t.customer
    };
    kitchenLog(ok
      ? { kind: 'ticket_served', customer: t.customer, ticket: t.id, order: wrapper.slice() }
      : { kind: 'ticket_corrected', customer: t.customer, ticket: t.id, order: wrapper.slice() });
    wrapper = [];
    resolvedCount += 1;
    var beat1 = ok
      ? (t.thanks || 'they eat it slow, like the morning is theirs.')
      : (t.kind_line || 'they eat it anyway. something is off and so is the morning; both are true.');
    if (resolvedCount >= morningLen) {
      renderAll();
      showHeadlines(beat1 + ' \u00b7 the morning is over; the paper wants a front page.');
    } else { renderAll(); line(beat1); }
  });
  document.getElementById('k-aside').addEventListener('click', function () {
    var t = nextTicket();
    if (!t) return;
    resolved[t.id] = { ok: null, epitaph: 'waiting \u00b7 ' + t.customer };
    kitchenLog({ kind: 'ticket_set_aside', customer: t.customer, ticket: t.id });
    resolvedCount += 1;
    var beat2 = 'the ticket goes back behind the glass. no one hurries.';
    if (resolvedCount >= morningLen) {
      renderAll();
      showHeadlines(beat2 + ' \u00b7 the morning is over; the paper wants a front page.');
    } else { renderAll(); line(beat2); }
  });
  document.getElementById('k-sleep').addEventListener('click', function () {
    vol += 1;
    resolved = {};
    wrapper = [];
    resolvedCount = 0;
    morningStart = kitchenJournal().length;
    document.getElementById('k-page').hidden = true;
    document.getElementById('k-again').hidden = true;
    document.getElementById('k-serve').hidden = false;
    document.getElementById('k-undo').hidden = false;
    document.getElementById('k-aside').hidden = false;
    document.getElementById('k-pantry').hidden = false;
    renderAll();
    line('the grill sleeps. the grill wakes.');
  });

  renderAll();
  line('read what they say. wrap what they mean.');
}

