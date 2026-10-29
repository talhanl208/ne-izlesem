/* Ne İzlesem? — arayüz davranışları ve animasyonlar (kütüphanesiz) */
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function retrigger(el, cls) {
    el.classList.remove(cls);
    void el.offsetWidth; // animasyonu yeniden başlat
    el.classList.add(cls);
  }
  function markCurtain() {
    try { sessionStorage.setItem("ni-perde", "1"); } catch (_) { /* gizli sekme */ }
  }

  /* ------------------------------------------------ perde + geri sayım */
  const loading = $("#loading");
  const messages = [
    "Film arşivi taranıyor…",
    "Temalar eşleştiriliyor…",
    "IMDb puanlarına bakılıyor…",
    "İzleyici yorumları okunuyor…",
    "Pusula Puanı hesaplanıyor…",
    "Biletler basılıyor…",
  ];
  let msgTimer = null;
  let numTimer = null;

  function showLoading() {
    markCurtain();
    if (!loading || !loading.hidden) return;
    const text = $(".loading-text", loading);
    const num = $(".leader-num", loading);
    let i = 0;
    let n = 3;
    text.textContent = messages[0];
    num.textContent = "3";
    loading.hidden = false;
    clearInterval(msgTimer);
    clearInterval(numTimer);
    numTimer = setInterval(() => {
      n = n === 1 ? 3 : n - 1;
      num.textContent = String(n);
      retrigger(num, "tick");
    }, 1000);
    msgTimer = setInterval(() => {
      i = (i + 1) % messages.length;
      text.textContent = messages[i];
      retrigger(text, "swap");
    }, 1700);
  }
  function hideLoading() {
    if (loading) loading.hidden = true;
    clearInterval(msgTimer);
    clearInterval(numTimer);
  }

  // Geri tuşuyla dönülünce her şey eski haline gelsin
  window.addEventListener("pageshow", (e) => {
    hideLoading();
    if (e.persisted) {
      try { sessionStorage.removeItem("ni-perde"); } catch (_) { /* yok say */ }
      const t = $("#ticket");
      if (t) t.classList.remove("is-torn");
      going = false;
    }
  });

  $$("a[data-loading]").forEach((a) => a.addEventListener("click", (e) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    showLoading();
  }));
  $$("[data-reload]").forEach((b) => b.addEventListener("click", () => { showLoading(); location.reload(); }));

  /* ------------------------------------------------ afiş yüklenemezse */
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

  /* ------------------------------------------------ sıralama değişince gönder */
  $$("select[data-autosubmit]").forEach((s) => s.addEventListener("change", () => {
    showLoading();
    setTimeout(() => s.form.submit(), reduceMotion ? 0 : 350);
  }));

  /* ------------------------------------------------ fragman (tıklayınca yüklenir) */
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

  /* ------------------------------------------------ Pusula Puanı sayacı */
  const curtainDelay = document.documentElement.classList.contains("with-curtain") ? 1300 : 450;
  $$("[data-count]").forEach((el) => {
    const target = parseFloat(el.dataset.count);
    if (Number.isNaN(target) || reduceMotion) return;
    const duration = 1400;
    const start = performance.now() + curtainDelay;
    el.textContent = "0,0";
    function frame(now) {
      const t = Math.min(1, Math.max(0, (now - start) / duration));
      const eased = 1 - Math.pow(1 - t, 4);
      el.textContent = (target * eased).toFixed(1).replace(".", ",");
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  });

  /* ================================================ arama formu (ana sayfa) */
  const form = $("#finder");
  let going = false;
  if (!form) return;

  const ticket = $("#ticket");
  const ticketSel = $("#ticket-sel");
  const ticketCount = $("#ticket-count");
  const emptyText = ticketSel ? ticketSel.textContent : "";
  const STATE_TEXT = { 0: "seçili değil", 1: "olsun", 2: "olmasın" };
  let shown = new Set();

  function chipsFor(kind, key) {
    return $$(`.chip[data-kind="${kind}"]`).filter((c) => c.dataset.key === String(key));
  }

  function setState(chip, state, animate = true) {
    chipsFor(chip.dataset.kind, chip.dataset.key).forEach((c) => {
      c.dataset.state = String(state);
      c.setAttribute("aria-pressed", state ? "true" : "false");
      c.setAttribute("aria-label", `${c.dataset.label}: ${STATE_TEXT[state]}`);
      if (animate && !reduceMotion) retrigger(c, "pop-in");
    });
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
      const span = el("span", cls + (!initial && !shown.has(item.id) ? " t-new" : ""), item.label);
      return span;
    };
    const wanted = s.kwIn.map((i) => make(i, "t-in"))
      .concat(s.gIn.map((i) => make(i, "t-genre")))
      .concat(s.prov.map((i) => make(i, "t-genre")));
    const unwanted = s.kwOut.concat(s.gOut).map((i) => make(i, "t-out"));

    const total = wanted.length + unwanted.length;
    if (ticketCount) {
      const before = ticketCount.textContent;
      ticketCount.textContent = total ? String(total) : "";
      if (!initial && before !== ticketCount.textContent && total) retrigger(ticketCount, "bump");
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
    // boş seçimleri adres çubuğuna taşımayalım
    $$("select", form).forEach((sel) => { sel.disabled = !sel.value; });
    setTimeout(() => $$("select", form).forEach((sel) => { sel.disabled = false; }), 0);
  }

  /* Gönder: önce bilet koçanı kopar, perde kapanır, sonra arama başlar */
  form.addEventListener("submit", (e) => {
    buildHidden();
    if (going || reduceMotion) { showLoading(); return; }
    e.preventDefault();
    going = true;
    const submitter = e.submitter;
    if (ticket) ticket.classList.add("is-torn");
    setTimeout(showLoading, 280);
    setTimeout(() => {
      if (form.requestSubmit) {
        form.requestSubmit(submitter && submitter.form === form ? submitter : undefined);
      } else {
        if (submitter && submitter.formAction) form.action = submitter.formAction;
        form.submit();
      }
    }, 780);
  });

  /* ------------------------------------------------ sekmeler */
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

  /* ------------------------------------------------ ruh hali */
  const moods = $$(".mood", form);
  function clearMood() { moods.forEach((m) => m.setAttribute("aria-pressed", "false")); }
  function resetAll(animate) {
    $$(".chip", form).forEach((c) => { if (c.dataset.state !== "0") setState(c, 0, animate); });
    $$("select", form).forEach((s) => { s.value = ""; });
    const gem = $('input[name="cevher"]', form);
    if (gem) gem.checked = false;
    clearMood();
  }
  moods.forEach((m) => {
    m.setAttribute("aria-pressed", "false");
    m.addEventListener("click", () => {
      const data = JSON.parse(m.dataset.mood);
      resetAll(false);
      const steps = [];
      data.include.forEach((k) => { const c = chipsFor("kw", k)[0]; if (c) steps.push([c, 1]); });
      data.genres.forEach((g) => { const c = chipsFor("genre", g)[0]; if (c) steps.push([c, 1]); });
      data.xgenres.forEach((g) => { const c = chipsFor("genre", g)[0]; if (c) steps.push([c, 2]); });
      steps.forEach(([c, st], idx) => {
        if (reduceMotion) setState(c, st, false);
        else setTimeout(() => { setState(c, st); updateTicket(); }, 70 * idx);
      });
      const puan = $("#sel-puan");
      if (puan && data.puan) puan.value = data.puan;
      m.setAttribute("aria-pressed", "true");
      if (!reduceMotion) retrigger(m, "pop-in");
      updateTicket();
    });
  });
  const reset = $("#reset");
  if (reset) reset.addEventListener("click", () => { resetAll(false); updateTicket(); });

  /* ------------------------------------------------ serbest tema araması */
  const input = $("#kw-input");
  const list = $("#kw-suggest");
  const custom = $("#custom-chips");
  let debounce = null;
  let lastQuery = "";

  function closeList() { list.hidden = true; list.textContent = ""; }

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
    list.textContent = "";
    if (!items.length) list.appendChild(el("div", "empty-row", "Eşleşen tema bulunamadı. İngilizce yazmayı dene."));
    items.forEach((item) => {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "option");
      b.append(el("span", "", item.label), el("small", "", item.source === "katalog" ? "hazır tema" : "TMDB etiketi"));
      b.addEventListener("click", () => addTerm(item));
      list.appendChild(b);
    });
    list.hidden = false;
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
    // Alttaki bilet öneri listesini kapatmasın diye kutuyu ekranın ortasına getir
    input.addEventListener("focus", () => input.scrollIntoView({ block: "center", behavior: reduceMotion ? "auto" : "smooth" }));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeList();
      if (e.key === "ArrowDown") { const first = $("button", list); if (first) { e.preventDefault(); first.focus(); } }
      if (e.key === "Enter") { e.preventDefault(); const first = $("button", list); if (first) first.click(); }
    });
    list.addEventListener("keydown", (e) => {
      const btns = $$("button", list);
      const i = btns.indexOf(document.activeElement);
      if (e.key === "ArrowDown" && i < btns.length - 1) { e.preventDefault(); btns[i + 1].focus(); }
      if (e.key === "ArrowUp") { e.preventDefault(); (i > 0 ? btns[i - 1] : input).focus(); }
      if (e.key === "Escape") { closeList(); input.focus(); }
    });
    document.addEventListener("click", (e) => { if (!e.target.closest(".kw-field")) closeList(); });
  }

  updateTicket(true);
})();
