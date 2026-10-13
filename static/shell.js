/* Channel Builder shell: group menus, about popover, theme toggle, global search. */
(function () {
  var root = document.documentElement;
  function $(s, c) { return (c || document).querySelector(s); }
  function $$(s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); }

  // ---- bottom-bar group menus (phones) ----
  function closeGroups(except) {
    $$('#nav .grp.open').forEach(function (g) {
      if (g !== except) { g.classList.remove('open'); $('.grp-toggle', g).setAttribute('aria-expanded', 'false'); }
    });
  }
  $$('#nav .grp-toggle').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var g = btn.parentNode, open = !g.classList.contains('open');
      closeGroups(g);
      g.classList.toggle('open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });

  // ---- about popover ----
  var about = $('#aboutBtn'), pop = $('#aboutPop');
  about.addEventListener('click', function (e) {
    e.stopPropagation();
    pop.hidden = !pop.hidden;
    about.setAttribute('aria-expanded', pop.hidden ? 'false' : 'true');
  });
  pop.addEventListener('click', function (e) { e.stopPropagation(); });

  // ---- theme ----
  $('#themeBtn').addEventListener('click', function () {
    var cur = root.getAttribute('data-theme') ||
      (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    var next = cur === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('cb-theme', next); } catch (e) {}
  });

  // ---- global search ----
  var bar = $('.appbar'), input = $('#gsearch'), list = $('#gresults'), sbtn = $('#searchBtn');
  var results = [], sel = -1, timer = null, seq = 0;
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]; }); }
  function mark(text, q) {
    var t = esc(text), i = text.toLowerCase().indexOf(q.toLowerCase());
    if (i < 0) return t;
    return esc(text.slice(0, i)) + '<mark>' + esc(text.slice(i, i + q.length)) + '</mark>' + esc(text.slice(i + q.length));
  }
  function closeSearch() {
    list.hidden = true; input.setAttribute('aria-expanded', 'false'); sel = -1;
    if (bar.classList.contains('searching')) bar.classList.remove('searching');
  }
  function render(q) {
    if (!results.length) {
      list.innerHTML = '<li class="r-none" role="presentation">No matches for “' + esc(q) + '”.</li>';
    } else {
      list.innerHTML = results.map(function (r, i) {
        return '<li role="option" id="gr' + i + '" data-i="' + i + '" aria-selected="false"><div class="r-top"><b>' + mark(r.title, q) +
          '</b><span class="r-tab">' + esc(r.tab) + '</span></div>' + (r.snip ? '<div class="r-snip">' + mark(r.snip, q) + '</div>' : '') + '</li>';
      }).join('');
    }
    list.hidden = false; input.setAttribute('aria-expanded', 'true'); sel = -1;
  }
  function choose(i) { if (results[i]) window.location.href = results[i].href; }
  function setSel(i) {
    var items = $$('li[role=option]', list);
    if (!items.length) return;
    sel = (i + items.length) % items.length;
    items.forEach(function (li, k) { li.setAttribute('aria-selected', k === sel ? 'true' : 'false'); });
    input.setAttribute('aria-activedescendant', items[sel].id);
    items[sel].scrollIntoView({ block: 'nearest' });
  }
  input.addEventListener('input', function () {
    clearTimeout(timer);
    var q = input.value.trim();
    if (q.length < 2) { list.hidden = true; return; }
    timer = setTimeout(function () {
      var mine = ++seq;
      fetch('/api/search?q=' + encodeURIComponent(q))
        .then(function (r) { return r.json(); })
        .then(function (j) { if (mine === seq) { results = j.results || []; render(q); } })
        .catch(function () {});
    }, 140);
  });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSel(sel + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSel(sel - 1); }
    else if (e.key === 'Enter') { e.preventDefault(); choose(sel >= 0 ? sel : 0); }
    else if (e.key === 'Escape') { closeSearch(); input.blur(); }
  });
  list.addEventListener('click', function (e) {
    var li = e.target.closest ? e.target.closest('li[data-i]') : null;
    if (li) choose(+li.getAttribute('data-i'));
  });
  list.addEventListener('click', function (e) { e.stopPropagation(); });
  sbtn.addEventListener('click', function (e) {
    e.stopPropagation(); bar.classList.add('searching'); input.focus();
  });

  // ---- global dismiss ----
  document.addEventListener('click', function (e) {
    closeGroups(null);
    if (!pop.hidden) { pop.hidden = true; about.setAttribute('aria-expanded', 'false'); }
    if (!list.hidden && e.target !== input) closeSearch();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeGroups(null); pop.hidden = true; about.setAttribute('aria-expanded', 'false'); }
    if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test((document.activeElement || {}).tagName || '')) {
      e.preventDefault(); bar.classList.add('searching'); input.focus();
    }
  });
})();
