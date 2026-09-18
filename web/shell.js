/* vefr/web/shell.js — the room.
 *
 * Lightweight view routing for VEFR.
 * Screens are plain objects with init(), enter(), leave(), and el.
 * Shell handles nav, routing, and the chrome around them.
 *
 * No framework. No virtual DOM. Just the DOM, carefully.
 */

(function () {
  'use strict';

  var screens = {};
  var current = null;
  var currentId = null;

  /* ── Helpers ───────────────────────────────────────────── */

  function resolveEl(screen) {
    if (!screen) return null;
    if (typeof screen.el === 'function') return screen.el();
    return screen.el || null;
  }

  /* ── Registration ──────────────────────────────────────── */

  function register(id, screen) {
    screens[id] = screen;
  }

  /* ── Navigation ────────────────────────────────────────── */

  function navigate(id) {
    if (!screens[id]) {
      console.warn('[shell] unknown screen:', id);
      return;
    }
    if (currentId === id) return;

    // Leave current
    if (current && current.leave) {
      try { current.leave(); } catch (e) { console.error('[shell] leave error:', e); }
    }

    // Hide current
    var currentEl = resolveEl(current);
    if (currentEl) {
      currentEl.classList.remove('vefr-screen--active');
    }

    // Enter new
    currentId = id;
    current = screens[id];

    if (!current._initialized) {
      try { current.init(); } catch (e) { console.error('[shell] init error:', e); }
      current._initialized = true;
    }

    var newEl = resolveEl(current);
    if (newEl) {
      newEl.classList.add('vefr-screen--active');
    }

    if (current.enter) {
      try { current.enter(); } catch (e) { console.error('[shell] enter error:', e); }
    }

    // Update nav
    updateNav(id);

    // Remember
    try {
      localStorage.setItem('vefr-screen', id);
    } catch (e) { /* quota or private mode */ }

    // Update URL hash without triggering hashchange handler
    history.replaceState(null, '', '#' + id);
  }

  function updateNav(activeId) {
    var items = document.querySelectorAll('.vefr-nav-item');
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var isActive = item.dataset.screen === activeId;
      item.classList.toggle('vefr-nav-item--active', isActive);
      item.setAttribute('aria-current', isActive ? 'page' : 'false');
    }
  }

  /* ── Sidebar (mobile) ──────────────────────────────────── */

  function openSidebar() {
    var sidebar = document.querySelector('.vefr-sidebar');
    var backdrop = document.querySelector('.vefr-sidebar__backdrop');
    if (sidebar) sidebar.classList.add('vefr-sidebar--open');
    if (backdrop) backdrop.style.display = 'block';
  }

  function closeSidebar() {
    var sidebar = document.querySelector('.vefr-sidebar');
    var backdrop = document.querySelector('.vefr-sidebar__backdrop');
    if (sidebar) sidebar.classList.remove('vefr-sidebar--open');
    if (backdrop) backdrop.style.display = 'none';
  }

  /* ── Init ──────────────────────────────────────────────── */

  function init() {
    // Wire nav clicks
    var nav = document.querySelector('.vefr-sidebar__nav');
    if (nav) {
      nav.addEventListener('click', function (e) {
        var item = e.target.closest('.vefr-nav-item');
        if (!item) return;
        var id = item.dataset.screen;
        if (id) {
          navigate(id);
          closeSidebar();
        }
      });
    }

    // Mobile menu button
    var menuBtn = document.querySelector('.vefr-topbar__menu');
    if (menuBtn) {
      menuBtn.addEventListener('click', openSidebar);
    }

    // Backdrop close
    var backdrop = document.querySelector('.vefr-sidebar__backdrop');
    if (backdrop) {
      backdrop.addEventListener('click', closeSidebar);
    }

    // Keyboard: Escape closes sidebar
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeSidebar();
    });

    // Hash routing
    window.addEventListener('hashchange', function () {
      var id = location.hash.slice(1);
      if (id && screens[id]) navigate(id);
    });

    // Initial route: hash > localStorage > default
    var initial = location.hash.slice(1)
      || tryGetLocal('vefr-screen')
      || 'workshop';

    if (!screens[initial]) initial = 'workshop';
    navigate(initial);
  }

  function tryGetLocal(key) {
    try { return localStorage.getItem(key); }
    catch (e) { return null; }
  }

  /* ── Export ─────────────────────────────────────────────── */

  window.VEFR_SHELL = {
    register: register,
    navigate: navigate,
    openSidebar: openSidebar,
    closeSidebar: closeSidebar,
    init: init,
    current: function () { return currentId; }
  };
})();
