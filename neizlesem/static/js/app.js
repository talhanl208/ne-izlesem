/* Ne İzlesem? — arayüz davranışları ve animasyonlar (kütüphanesiz) */
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  function retrigger(el, cls) {
    if (!el) return;
    el.classList.remove(cls);
    void el.offsetWidth; // animasyonu yeniden başlat
    el.classList.add(cls);
  }
  const store = {
    get(key, fallback) {
      try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (_) { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* gizli sekme vb. */ }
    },
  };

  /* ================================================ salonun ışıkları */
  const house = $("#loading");
  const houseText = house ? $(".house-text", house) : null;
  const messages = [
    "Salon kararıyor…",
    "Temalar eşleştiriliyor…",
    "Etiketler tek tek okunuyor…",
    "IMDb puanlarına bakılıyor…",
    "İzleyici yorumları okunuyor…",
    "Seçki hazırlanıyor…",
  ];
  let msgTimer = null;

  function showLoading() {
    try { sessionStorage.setItem("ni-isik", "1"); } catch (_) { /* yok say */ }
    if (!house || !house.hidden) return;
    let i = 0;
    houseText.textContent = messages[0];
    house.hidden = false;
    clearInterval(msgTimer);
    msgTimer = setInterval(() => {
      i = (i + 1) % messages.length;
      houseText.textContent = messages[i];
      retrigger(houseText, "swap");
    }, 1600);
  }
  function hideLoading() {
    if (house) house.hidden = true;
    clearInterval(msgTimer);
  }
  window.addEventListener("pageshow", (e) => {
    hideLoading();
    if (e.persisted) {
      try { sessionStorage.removeItem("ni-isik"); } catch (_) { /* yok say */ }
      going = false;
    }
  });

  document.addEventListener("click", (e) => {
    const a = e.target.closest("a[data-loading]");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    if (a.hasAttribute("data-shuffle")) {
      const url = new URL(a.href, location.href);
      url.searchParams.set("karistir", String(1 + Math.floor(Math.random() * 99998)));
      a.href = url.pathname + url.search;
    }
    showLoading();
  });
  $$("[data-reload]").forEach((b) => b.addEventListener("click", () => { showLoading(); location.reload(); }));

  /* ================================================ küçük yardımcılar */
  document.addEventListener("error", (e) => {
    const img = e.target;
    if (img.tagName !== "IMG") return;
    if (img.dataset.fallback !== undefined) {
      const span = document.createElement("span");
      span.className = "poster-fallback";
      span.textContent = img.dataset.fallback;
      img.replaceWith(span);
    } else {
      img.style.visibility = "hidden";
    }
  }, true);

  $$("select[data-autosubmit]").forEach((s) => s.addEventListener("change", () => {
    showLoading();
    setTimeout(() => s.form.submit(), reduceMotion ? 0 : 420);
  }));

  $$(".trailer[data-yt]").forEach((btn) => btn.addEventListener("click", () => {
    const key = btn.dataset.yt;
    if (!/^[A-Za-z0-9_-]{6,20}$/.test(key)) return;
    const iframe = document.createElement("iframe");
    iframe.src = "https://www.youtube-nocookie.com/embed/" + key + "?autoplay=1&rel=0";
    iframe.title = "Fragman";
    iframe.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    iframe.allowFullscreen = true;
    const wrap = Object.assign(document.createElement("div"), { className: "trailer" });
    wrap.appendChild(iframe);
    btn.replaceWith(wrap);
  }));

  // Pusula Puanı sıfırdan sayarak gelir
  const lightsDelay = document.documentElement.classList.contains("with-lights") ? 700 : 0;
  $$("[data-count]").forEach((el) => {
    const target = parseFloat(el.dataset.count);
    if (Number.isNaN(target) || reduceMotion) return;
    const duration = 1400;
    const start = performance.now() + 450 + lightsDelay;
    el.textContent = "0,0";
    (function frame(now) {
      const t = Math.min(1, Math.max(0, (now - start) / duration));
      const eased = 1 - Math.pow(1 - t, 4);
      el.textContent = (target * eased).toFixed(1).replace(".", ",");
      if (t < 1) requestAnimationFrame(frame);
    })(performance.now());
  });

  /* ================================================ sonuç kartları */
  const list = $("#results");
  if (list) setupResults(list);

  function setupResults(list) {
    const HIDDEN_KEY = "ni-gizli";
    let hidden = new Set(store.get(HIDDEN_KEY, []));
    let showHidden = false;
    const note = $("#hidden-note");
    const noteCount = $("#hidden-count");
    const toggle = $("#toggle-hidden");
    const moreBtn = $("[data-more]");
    const moreNote = $("#more-note");
    let loadingMore = false;
    let firstBatch = true;

    // Kartlar ekrana girdikçe sırayla gelir
    const io = "IntersectionObserver" in window && !reduceMotion
      ? new IntersectionObserver((entries) => {
        const base = firstBatch ? lightsDelay : 0;
        firstBatch = false;
        entries.filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
          .forEach((e, n) => {
            const li = e.target;
            li.style.setProperty("--d", (base + n * 90) + "ms");
            li.classList.remove("pre");
            li.classList.add("in");
            io.unobserve(li);
          });
      }, { rootMargin: "0px 0px -6% 0px" })
      : null;

    function setupCard(li) {
      if (io) { li.classList.add("pre"); io.observe(li); } else { li.classList.add("in"); }
      const id = Number(li.dataset.id);
      if (hidden.has(id)) markHidden(li, false);
      if (finePointer && !reduceMotion) {
        const card = $(".tc-card", li);
        const poster = $(".tc-poster", li);
        card.addEventListener("pointermove", (e) => {
          const r = card.getBoundingClientRect();
          const x = (e.clientX - r.left) / r.width;
          const y = (e.clientY - r.top) / r.height;
          card.style.setProperty("--mx", (x * 100).toFixed(1) + "%");
          card.style.setProperty("--my", (y * 100).toFixed(1) + "%");
          if (poster) {
            poster.style.setProperty("--ry", ((x - 0.3) * 14).toFixed(2) + "deg");
            poster.style.setProperty("--rx", ((0.5 - y) * 10).toFixed(2) + "deg");
          }
        });
        card.addEventListener("pointerleave", () => {
          if (poster) { poster.style.setProperty("--rx", "0deg"); poster.style.setProperty("--ry", "0deg"); }
        });
      }
    }

    function visibleCount() { return $$(".tc", list).filter((li) => !li.hidden).length; }

    function updateNote() {
      const n = $$(".tc", list).filter((li) => hidden.has(Number(li.dataset.id))).length;
      if (!note) return;
      note.hidden = n === 0;
      noteCount.textContent = n === 1 ? "1" : String(n);
      toggle.textContent = showHidden ? "Gizle" : "Göster";
    }

    function markHidden(li, animate) {
      if (showHidden) { li.classList.add("is-hidden"); return; }
      if (!animate || reduceMotion) { li.hidden = true; return; }
      const h = li.offsetHeight;
      li.classList.add("gone");
      li.animate(
        [{ height: h + "px", marginTop: "0px" }, { height: "0px", marginTop: "-20px" }],
        { duration: 420, delay: 180, easing: "cubic-bezier(0.65, 0, 0.35, 1)" }
      ).onfinish = () => { li.hidden = true; li.classList.remove("gone"); };
    }

    list.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-hide]");
      if (!btn) return;
      e.preventDefault();
      const li = btn.closest(".tc");
      const id = Number(li.dataset.id);
      if (hidden.has(id)) {
        hidden.delete(id);
        li.classList.remove("is-hidden");
        li.hidden = false;
      } else {
        hidden.add(id);
        markHidden(li, true);
      }
      store.set(HIDDEN_KEY, Array.from(hidden).slice(-600));
      updateNote();
      if (visibleCount() < 6) loadMore();
    });

    if (toggle) toggle.addEventListener("click", () => {
      showHidden = !showHidden;
      $$(".tc", list).forEach((li) => {
        if (!hidden.has(Number(li.dataset.id))) return;
        li.hidden = !showHidden;
        li.classList.toggle("is-hidden", showHidden);
      });
      updateNote();
    });

    async function loadMore() {
      if (!moreBtn || loadingMore || !moreBtn.dataset.more) return;
      loadingMore = true;
      moreBtn.classList.add("loading");
      moreBtn.textContent = "Seçki genişliyor…";
      try {
        const res = await fetch(moreBtn.dataset.more, { headers: { Accept: "application/json" } });
        if (!res.ok) throw new Error(String(res.status));
        const data = await res.json();
        const tpl = document.createElement("template");
        tpl.innerHTML = data.html;
        const fresh = $$(".tc", tpl.content);
        fresh.forEach((li) => list.appendChild(li));
        fresh.forEach(setupCard);
        if (data.next) {
          moreBtn.dataset.more = data.next;
          moreNote.textContent = Math.max(0, data.total - data.shown) + " uygun film daha var";
        } else {
          moreBtn.closest(".more").remove();
        }
        updateNote();
      } catch (_) {
        moreNote.textContent = "Daha fazlası yüklenemedi, birazdan tekrar dene.";
      } finally {
        loadingMore = false;
        if (document.body.contains(moreBtn)) {
          moreBtn.classList.remove("loading");
          moreBtn.textContent = "Daha fazla göster";
        }
      }
      if (visibleCount() < 6 && document.body.contains(moreBtn)) loadMore();
    }
    if (moreBtn) moreBtn.addEventListener("click", loadMore);

    $$(".tc", list).forEach(setupCard);
    updateNote();
    if (visibleCount() < 6) loadMore();
  }

  /* ================================================ arama formu (ana sayfa) */
  const form = $("#finder");
  let going = false;
  if (!form) return;

  const ticketSel = $("#ticket-sel");
  const ticketCount = $("#ticket-count");
  const emptyText = ticketSel ? ticketSel.textContent : "";
  const STATE_TEXT = { 0: "seçili değil", 1: "olsun", 2: "olmasın" };
  let shown = new Set();

  function chipsFor(kind, key) {
    return $$(`.chip[data-kind="${kind}"]`).filter((c) => c.dataset.key === String(key));
  }

  function flyToken(from) {
    if (reduceMotion || !ticketCount || !from || from.offsetParent === null || !from.animate) return;
    const a = from.getBoundingClientRect();
    const b = ticketCount.getBoundingClientRect();
    const t = document.createElement("span");
    t.className = "token";
    t.style.left = (a.left + a.width / 2 - 6) + "px";
    t.style.top = (a.top + a.height / 2 - 6) + "px";
    document.body.appendChild(t);
    const dx = b.left + b.width / 2 - (a.left + a.width / 2);
    const dy = b.top + b.height / 2 - (a.top + a.height / 2);
    const lift = Math.min(160, Math.abs(dy) * 0.35 + 60);
    t.animate([
      { transform: "translate(0, 0) scale(1)", opacity: 1 },
      { transform: `translate(${dx * 0.45}px, ${dy * 0.45 - lift}px) scale(1.25)`, opacity: 1, offset: 0.5 },
      { transform: `translate(${dx}px, ${dy}px) scale(0.35)`, opacity: 0.25 },
    ], { duration: 680, easing: "cubic-bezier(0.5, 0, 0.3, 1)" }).onfinish = () => {
      t.remove();
      retrigger(ticketCount, "bump");
    };
  }

  function setState(chip, state, opts = {}) {
    chipsFor(chip.dataset.kind, chip.dataset.key).forEach((c) => {
      c.dataset.state = String(state);
      c.setAttribute("aria-pressed", state ? "true" : "false");
      c.setAttribute("aria-label", `${c.dataset.label}: ${STATE_TEXT[state]}`);
    });
    if (state === 1 && opts.fly !== false) flyToken(chip);
  }

  function cycle(chip) {
    const two = chip.dataset.two === "1";
    const now = Number(chip.dataset.state || 0);
    setState(chip, two ? (now ? 0 : 1) : (now + 1) % 3);
    clearMood();
    updateTicket();
  }

  form.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (chip && form.contains(chip)) cycle(chip);
  });
  $$(".chip", form).forEach((c) => c.setAttribute("aria-label", `${c.dataset.label}: ${STATE_TEXT[c.dataset.state || 0]}`));

  function selection() {
    const seen = new Set();
    const out = { kwIn: [], kwOut: [], gIn: [], gOut: [], prov: [] };
    $$(".chip", form).forEach((c) => {
      const id = c.dataset.kind + ":" + c.dataset.key;
      const st = Number(c.dataset.state || 0);
      if (!st || seen.has(id)) return;
      seen.add(id);
      const item = { id: id + ":" + st, key: c.dataset.key, label: c.dataset.label };
      if (c.dataset.kind === "kw") (st === 1 ? out.kwIn : out.kwOut).push(item);
      else if (c.dataset.kind === "genre") (st === 1 ? out.gIn : out.gOut).push(item);
      else if (c.dataset.kind === "provider" && st === 1) out.prov.push(item);
    });
    return out;
  }

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function updateTicket(initial = false) {
    if (!ticketSel) return;
    const s = selection();
    const next = new Set();
    const make = (item, cls) => {
      next.add(item.id);
      return el("span", cls + (!initial && !shown.has(item.id) ? " t-new" : ""), item.label);
    };
    const wanted = s.kwIn.map((i) => make(i, "t-in"))
      .concat(s.gIn.map((i) => make(i, "t-genre")))
      .concat(s.prov.map((i) => make(i, "t-genre")));
    const unwanted = s.kwOut.concat(s.gOut).map((i) => make(i, "t-out"));
    const total = wanted.length + unwanted.length;
    if (ticketCount) {
      ticketCount.textContent = String(total);
      ticketCount.classList.toggle("zero", total === 0);
    }
    ticketSel.textContent = "";
    shown = next;
    if (!total) { ticketSel.textContent = emptyText; return; }
    wanted.forEach((p, idx) => {
      if (idx) ticketSel.append(el("span", "plus", "+"));
      ticketSel.append(p);
    });
    if (unwanted.length) {
      if (wanted.length) ticketSel.append(". ");
      unwanted.forEach((p, idx) => { if (idx) ticketSel.append(", "); ticketSel.append(p); });
      ticketSel.append(" olmasın");
    }
  }

  function buildHidden() {
    const box = $("#hidden-inputs");
    box.textContent = "";
    const s = selection();
    const add = (name, value) => box.appendChild(Object.assign(document.createElement("input"), { type: "hidden", name, value }));
    s.kwIn.forEach((i) => add("k", i.key));
    s.kwOut.forEach((i) => add("x", i.key));
    s.gIn.forEach((i) => add("g", i.key));
    s.gOut.forEach((i) => add("xg", i.key));
    s.prov.forEach((i) => add("p", i.key));
    // boş ve varsayılan seçimleri adres çubuğuna taşımayalım
    const quiet = $$("select", form).filter((sel) => !sel.value);
    const tarz = $('input[name="tarz"]:checked', form);
    if (tarz && tarz.value === "dengeli") quiet.push(...$$('input[name="tarz"]', form));
    quiet.forEach((x) => { x.disabled = true; });
    setTimeout(() => quiet.forEach((x) => { x.disabled = false; }), 0);
  }

  // Gönder: önce ışıklar kararır, sonra arama başlar
  form.addEventListener("submit", (e) => {
    buildHidden();
    if (going || reduceMotion) { showLoading(); return; }
    e.preventDefault();
    going = true;
    const submitter = e.submitter;
    showLoading();
    setTimeout(() => {
      if (form.requestSubmit) {
        form.requestSubmit(submitter && submitter.form === form ? submitter : undefined);
      } else {
        if (submitter && submitter.formAction) form.action = submitter.formAction;
        form.submit();
      }
    }, 650);
  });

  // Sekmeler
  const tabs = $$('[role="tab"]', form);
  function openTab(name) {
    tabs.forEach((t) => t.setAttribute("aria-selected", String(t.dataset.tab === name)));
    $$(".tab-panel", form).forEach((p) => { p.hidden = p.dataset.panel !== name; });
  }
  tabs.forEach((t) => t.addEventListener("click", () => openTab(t.dataset.tab)));
  form.addEventListener("keydown", (e) => {
    const i = tabs.indexOf(document.activeElement);
    if (i < 0 || !["ArrowRight", "ArrowLeft"].includes(e.key)) return;
    e.preventDefault();
    const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
    next.focus();
    openTab(next.dataset.tab);
  });

  // Öneri tarzı açıklaması
  const segDesc = $("#seg-desc");
  $$('input[name="tarz"]', form).forEach((r) => r.addEventListener("change", () => {
    if (!segDesc) return;
    segDesc.textContent = r.dataset.desc || "";
    retrigger(segDesc, "swap");
  }));

  // Ruh hali kartları
  const moods = $$(".mood", form);
  function clearMood() { moods.forEach((m) => m.setAttribute("aria-pressed", "false")); }
  function resetAll() {
    $$(".chip", form).forEach((c) => { if (c.dataset.state !== "0") setState(c, 0); });
    $$("select", form).forEach((s) => { s.value = ""; });
    const dengeli = $('input[name="tarz"][value="dengeli"]', form);
    if (dengeli) dengeli.checked = true;
    clearMood();
  }
  moods.forEach((m) => {
    m.setAttribute("aria-pressed", "false");
    m.addEventListener("click", () => {
      const data = JSON.parse(m.dataset.mood);
      $$(".chip", form).forEach((c) => { if (c.dataset.state !== "0") setState(c, 0); });
      clearMood();
      const steps = [];
      data.include.forEach((k) => { const c = chipsFor("kw", k)[0]; if (c) steps.push([c, 1]); });
      data.genres.forEach((g) => { const c = chipsFor("genre", g)[0]; if (c) steps.push([c, 1]); });
      data.xgenres.forEach((g) => { const c = chipsFor("genre", g)[0]; if (c) steps.push([c, 2]); });
      steps.forEach(([c, st], idx) => {
        if (reduceMotion) { setState(c, st, { fly: false }); return; }
        setTimeout(() => { setState(c, st); updateTicket(); }, 90 * idx);
      });
      m.setAttribute("aria-pressed", "true");
      retrigger(m, "pop");
      updateTicket();
    });
  });
  const reset = $("#reset");
  if (reset) reset.addEventListener("click", () => { resetAll(); updateTicket(); });

  // Serbest tema araması
  const input = $("#kw-input");
  const suggest = $("#kw-suggest");
  const custom = $("#custom-chips");
  let debounce = null;
  let lastQuery = "";

  function closeList() { suggest.hidden = true; suggest.textContent = ""; }

  function addTerm(item) {
    const existing = chipsFor("kw", item.key);
    if (existing.length) {
      const panel = existing[0].closest(".tab-panel");
      if (panel && panel.hidden) openTab(panel.dataset.panel);
      setState(existing[0], 1);
    } else {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip chip-custom";
      chip.dataset.kind = "kw";
      chip.dataset.key = item.key;
      chip.dataset.label = item.label;
      chip.append(el("span", "chip-label", item.label));
      custom.appendChild(chip);
      setState(chip, 1);
    }
    clearMood();
    updateTicket();
    input.value = "";
    closeList();
    input.focus({ preventScroll: true });
  }

  function render(items) {
    suggest.textContent = "";
    if (!items.length) suggest.appendChild(el("div", "empty-row", "Eşleşen tema bulunamadı. İngilizce yazmayı dene."));
    items.forEach((item) => {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "option");
      b.append(el("span", "", item.label), el("small", "", item.source === "katalog" ? "hazır tema" : "TMDB etiketi"));
      b.addEventListener("click", () => addTerm(item));
      suggest.appendChild(b);
    });
    suggest.hidden = false;
  }

  if (input) {
    input.addEventListener("input", () => {
      const q = input.value.trim();
      clearTimeout(debounce);
      if (q.length < 2) { closeList(); return; }
      debounce = setTimeout(async () => {
        lastQuery = q;
        try {
          const res = await fetch("/api/anahtar-kelime?q=" + encodeURIComponent(q), { headers: { Accept: "application/json" } });
          if (!res.ok) { closeList(); return; }
          const items = await res.json();
          if (q === lastQuery) render(items);
        } catch (_) { closeList(); }
      }, 250);
    });
    input.addEventListener("focus", () => input.scrollIntoView({ block: "center", behavior: reduceMotion ? "auto" : "smooth" }));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeList();
      if (e.key === "ArrowDown") { const first = $("button", suggest); if (first) { e.preventDefault(); first.focus(); } }
      if (e.key === "Enter") { e.preventDefault(); const first = $("button", suggest); if (first) first.click(); }
    });
    suggest.addEventListener("keydown", (e) => {
      const btns = $$("button", suggest);
      const i = btns.indexOf(document.activeElement);
      if (e.key === "ArrowDown" && i < btns.length - 1) { e.preventDefault(); btns[i + 1].focus(); }
      if (e.key === "ArrowUp") { e.preventDefault(); (i > 0 ? btns[i - 1] : input).focus(); }
      if (e.key === "Escape") { closeList(); input.focus(); }
    });
    document.addEventListener("click", (e) => { if (!e.target.closest(".kw-field")) closeList(); });
  }

  updateTicket(true);
})();
