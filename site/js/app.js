/* Book of Bangers — vanilla JS frontend
 *
 * Loads three JSON files (top_rt, top_likes, top_qt), renders a paginated feed
 * of tweet cards, supports year + search filtering, and persists two display
 * toggles (reading mode + links visibility) to localStorage.
 */

(function () {
  "use strict";

  // ---------------------------------------------------------------- config
  const PAGE_SIZE = 100;
  const METRIC_FILES = {
    rt:    "data/top_rt.json",
    likes: "data/top_likes.json",
    qt:    "data/top_qt.json",
  };
  const METRIC_FIELD = {
    rt:    "retweet_count",
    likes: "favorite_count",
    qt:    "qt_count",
  };
  const METRIC_LABEL = {
    rt:    "retweets",
    likes: "likes",
    qt:    "quote-tweets",
  };

  // ---------------------------------------------------------------- state
  const state = {
    metric: "rt",
    year: "all",
    search: "",
    visible: PAGE_SIZE,
    cache: {},          // {metric: {primary: [...], byId: Map}}
    loading: new Set(),
  };

  // ---------------------------------------------------------------- DOM
  const $feed       = document.getElementById("feed");
  const $count      = document.getElementById("count");
  const $year       = document.getElementById("year-select");
  const $search     = document.getElementById("search");
  const $loadMore   = document.getElementById("load-more");
  const $modeBtn    = document.getElementById("toggle-mode");
  const $linksBtn   = document.getElementById("toggle-links");
  const $aboutDlg   = document.getElementById("about-dialog");

  // ---------------------------------------------------------------- init

  initToggles();
  bindControls();
  loadMetric(state.metric).then(render);

  // ---------------------------------------------------------------- toggles

  function initToggles() {
    const reading = localStorage.getItem("bob.readingMode") === "1";
    const linksOff = localStorage.getItem("bob.linksOff") === "1";
    setMode(reading);
    setLinks(!linksOff);
  }

  function setMode(reading) {
    document.body.classList.toggle("reading-mode", reading);
    $modeBtn.setAttribute("aria-pressed", reading ? "true" : "false");
    $modeBtn.setAttribute("data-tip", reading
      ? "Social mode: show avatars, names and dates"
      : "Reading mode: hide avatars, names and dates");
    localStorage.setItem("bob.readingMode", reading ? "1" : "0");
  }

  function setLinks(on) {
    document.body.classList.toggle("no-links", !on);
    $linksBtn.setAttribute("aria-pressed", on ? "true" : "false");
    $linksBtn.setAttribute("data-tip", on
      ? "Hide links to x.com"
      : "Show links to x.com");
    localStorage.setItem("bob.linksOff", on ? "0" : "1");
  }

  // ---------------------------------------------------------------- bindings

  function bindControls() {
    document.querySelectorAll(".metric-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const m = btn.dataset.metric;
        if (m === state.metric) return;
        state.metric = m;
        state.visible = PAGE_SIZE;
        document.querySelectorAll(".metric-btn").forEach(b =>
          b.setAttribute("aria-selected", b.dataset.metric === m ? "true" : "false")
        );
        loadMetric(m).then(() => {
          rebuildYearOptions();
          render();
          window.scrollTo({ top: 0, behavior: "instant" });
        });
      });
      // initial state
      if (btn.dataset.metric === state.metric) btn.setAttribute("aria-selected", "true");
    });

    $year.addEventListener("change", () => {
      state.year = $year.value;
      state.visible = PAGE_SIZE;
      render();
    });

    let searchTimer = null;
    $search.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.search = $search.value.trim().toLowerCase();
        state.visible = PAGE_SIZE;
        render();
      }, 200);
    });

    $loadMore.addEventListener("click", () => {
      state.visible += PAGE_SIZE;
      render({ preserveScroll: true });
    });

    $modeBtn.addEventListener("click", () => {
      const next = !document.body.classList.contains("reading-mode");
      setMode(next);
    });
    $linksBtn.addEventListener("click", () => {
      const next = document.body.classList.contains("no-links"); // currently off → turn on
      setLinks(next);
    });

    // About dialog
    const open = e => { e.preventDefault(); if (typeof $aboutDlg.showModal === "function") $aboutDlg.showModal(); else $aboutDlg.setAttribute("open", ""); };
    document.getElementById("about-link")?.addEventListener("click", open);
    document.getElementById("about-link-2")?.addEventListener("click", open);
    $aboutDlg.querySelector("[data-close-about]")?.addEventListener("click", () => $aboutDlg.close());
    $aboutDlg.addEventListener("click", e => {
      const r = $aboutDlg.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) {
        $aboutDlg.close();
      }
    });
  }

  // ---------------------------------------------------------------- data loading

  async function loadMetric(metric) {
    if (state.cache[metric]) return state.cache[metric];
    if (state.loading.has(metric)) {
      // wait until the in-flight request is cached
      return new Promise(res => {
        const t = setInterval(() => {
          if (state.cache[metric]) { clearInterval(t); res(state.cache[metric]); }
        }, 50);
      });
    }
    state.loading.add(metric);
    try {
      const r = await fetch(METRIC_FILES[metric]);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const primary = [];
      const byId = new Map();
      for (const t of data) {
        byId.set(t.tweet_id, t);
        if (!t.is_context) primary.push(t);
      }
      // primary is already in rank order by metric — keep it that way
      state.cache[metric] = { primary, byId };
      rebuildYearOptions();
      return state.cache[metric];
    } catch (e) {
      console.error("failed to load", metric, e);
      $feed.innerHTML = `<p class="placeholder">Couldn't load the data file. Run <code>build.py</code> first.</p>`;
      throw e;
    } finally {
      state.loading.delete(metric);
    }
  }

  function rebuildYearOptions() {
    const c = state.cache[state.metric];
    if (!c) return;
    const years = new Set();
    for (const t of c.primary) if (t.year) years.add(t.year);
    const sorted = [...years].sort((a, b) => b - a);
    const current = state.year;
    $year.innerHTML = `<option value="all">All time</option>` +
      sorted.map(y => `<option value="${y}">${y}</option>`).join("");
    if (current !== "all" && sorted.includes(Number(current))) {
      $year.value = current;
    } else {
      state.year = "all";
      $year.value = "all";
    }
  }

  // ---------------------------------------------------------------- filtering

  function getFiltered() {
    const c = state.cache[state.metric];
    if (!c) return [];
    let arr = c.primary;
    if (state.year !== "all") {
      const y = Number(state.year);
      arr = arr.filter(t => t.year === y);
    }
    if (state.search) {
      const q = state.search;
      // Usernames in the data are stored without an "@" prefix. If the user
      // typed "@handle" we strip the @ for username matching but keep the
      // original `q` for full_text matching (so "@user" still matches mentions).
      const qHandle = q.replace(/^@+/, "");
      arr = arr.filter(t =>
        (t.full_text && t.full_text.toLowerCase().includes(q)) ||
        (t.username && t.username.toLowerCase().includes(qHandle)) ||
        (t.account_display_name && t.account_display_name.toLowerCase().includes(q))
      );
    }
    return arr;
  }

  // ---------------------------------------------------------------- render

  function render(opts = {}) {
    const c = state.cache[state.metric];
    if (!c) return;
    const filtered = getFiltered();
    const slice = filtered.slice(0, state.visible);

    const scrollY = window.scrollY;

    if (slice.length === 0) {
      $feed.innerHTML = `<p class="placeholder">Nothing matches that filter. Try a different year or search term.</p>`;
      $count.textContent = `0 tweets`;
      $loadMore.hidden = true;
      $feed.removeAttribute("aria-busy");
      return;
    }

    const frag = document.createDocumentFragment();
    slice.forEach((t, i) => frag.appendChild(renderCard(t, i + 1, c.byId)));
    $feed.replaceChildren(frag);
    $feed.removeAttribute("aria-busy");

    const fmt = n => n.toLocaleString("en-GB");
    $count.textContent = `Showing ${fmt(slice.length)} of ${fmt(filtered.length)}`;

    if (slice.length < filtered.length) {
      $loadMore.hidden = false;
      const remaining = filtered.length - slice.length;
      const next = Math.min(PAGE_SIZE, remaining);
      const seen = slice.length;
      $loadMore.textContent = seen === PAGE_SIZE
        ? `You've seen the top ${fmt(seen)} — load the next ${fmt(next)}?`
        : `Load ${fmt(next)} more (${fmt(remaining)} to go)`;
    } else {
      $loadMore.hidden = true;
    }

    if (opts.preserveScroll) window.scrollTo({ top: scrollY, behavior: "instant" });
  }

  // ---------------------------------------------------------------- card

  function renderCard(t, rank, byId) {
    const card = document.createElement("article");
    card.className = "card";
    card.dataset.tweetId = t.tweet_id;

    // rank label
    const rankEl = document.createElement("div");
    rankEl.className = "rank";
    rankEl.textContent = `№ ${rank.toLocaleString("en-GB")}`;
    card.appendChild(rankEl);

    // open-on-x link
    const xLink = document.createElement("a");
    xLink.className = "open-x x-link";
    xLink.href = xUrl(t.username, t.tweet_id);
    xLink.target = "_blank";
    xLink.rel = "noopener";
    xLink.textContent = "open on x ↗";
    card.appendChild(xLink);

    // avatar
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    if (t.avatar_media_url) {
      const img = document.createElement("img");
      img.loading = "lazy";
      img.alt = "";
      img.referrerPolicy = "no-referrer";
      img.src = t.avatar_media_url;
      img.onerror = () => { avatar.replaceChildren(initialOf(t)); };
      avatar.appendChild(img);
    } else {
      avatar.appendChild(initialOf(t));
    }
    card.appendChild(avatar);

    // right column: meta, body, media, metrics
    const meta = document.createElement("div");
    meta.className = "meta";
    const dn = document.createElement("span");
    dn.className = "display-name";
    dn.textContent = t.account_display_name || t.username || "";
    const handle = document.createElement("span");
    handle.className = "handle";
    handle.textContent = "@" + (t.username || "");
    const date = document.createElement("span");
    date.className = "date";
    date.textContent = formatDate(t.created_at);
    meta.append(dn, handle, date);
    card.appendChild(meta);

    // reply context
    appendReplyContext(card, t, byId);

    // body
    const body = document.createElement("div");
    body.className = "body";
    body.appendChild(renderText(t.full_text || "", t.url_expansions, t.media_tcos));
    card.appendChild(body);

    // media
    const media = t.media || [];
    if (media.length) {
      card.appendChild(renderMedia(media));
    }

    // quoted tweet
    appendQuoted(card, t, byId);

    // metrics
    card.appendChild(renderMetrics(t));

    return card;
  }

  function initialOf(t) {
    const ch = ((t.account_display_name || t.username || "?")[0] || "?").toUpperCase();
    const span = document.createElement("span");
    span.textContent = ch;
    return span;
  }

  // -------------------------------------------------------- reply context

  function appendReplyContext(card, t, byId) {
    if (!t.reply_to_tweet_id) return;

    // Walk up to 3 ancestors that we have in cache
    const chain = [];
    let cur = byId.get(t.reply_to_tweet_id);
    let depth = 1;
    while (cur && depth <= 3) {
      chain.push({ tweet: cur, depth });
      if (!cur.reply_to_tweet_id) break;
      cur = byId.get(cur.reply_to_tweet_id);
      depth++;
    }

    if (chain.length === 0) {
      // immediate parent unavailable
      const label = document.createElement("div");
      label.className = "reply-label";
      const replyToUser = t.reply_to_username ? "@" + t.reply_to_username : "an earlier tweet";
      const link = document.createElement("a");
      link.className = "x-link";
      link.href = xUrl(t.reply_to_username, t.reply_to_tweet_id);
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = `Replying to ${replyToUser} ↗`;
      const plain = document.createElement("span");
      plain.className = "x-link-text";
      plain.textContent = `Replying to ${replyToUser}`;
      plain.style.display = "none";
      label.append(link, plain);
      // hide whichever doesn't apply via CSS .no-links rules — but plain needs to show then
      // Simpler: just always render plain when no-links is on
      label.classList.add("with-fallback");
      card.appendChild(label);
      return;
    }

    // We have ancestors — figure out if the chain bottoms out at a real root or not
    const stack = document.createElement("div");
    stack.className = "context-stack";

    // If the highest ancestor we have *also* has a reply_to_tweet_id we couldn't find,
    // show an "Earlier in thread" hint at the very top.
    const top = chain[chain.length - 1].tweet;
    if (top.reply_to_tweet_id) {
      const link = document.createElement("a");
      link.className = "thread-link x-link thread-link-x";
      link.href = xUrl(top.reply_to_username, top.reply_to_tweet_id);
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "Earlier in thread →";
      const plain = document.createElement("span");
      plain.className = "thread-link x-link-text";
      plain.textContent = "Earlier in thread…";
      plain.style.display = "none";
      stack.append(link, plain);
    }

    // Render ancestors top-down (oldest at top)
    chain.slice().reverse().forEach(({ tweet, depth }) => {
      const ctx = document.createElement("div");
      ctx.className = `context-tweet depth-${depth}`;
      const m = document.createElement("div");
      m.className = "ctx-meta";
      const dn = document.createElement("span");
      dn.className = "display-name";
      dn.textContent = tweet.account_display_name || tweet.username || "";
      const handle = document.createElement("span");
      handle.className = "handle";
      handle.textContent = " @" + (tweet.username || "");
      m.append(dn, handle);
      ctx.appendChild(m);
      const b = document.createElement("div");
      b.className = "ctx-body";
      b.appendChild(renderText(tweet.full_text || "", tweet.url_expansions, tweet.media_tcos));
      ctx.appendChild(b);
      const ctxM = tweet.media || [];
      if (ctxM.length) {
        const ctxMedia = renderMedia(ctxM);
        ctxMedia.classList.add("ctx-media");
        ctx.appendChild(ctxMedia);
      }
      stack.appendChild(ctx);
    });

    card.appendChild(stack);
  }

  // -------------------------------------------------------- quoted tweet

  function appendQuoted(card, t, byId) {
    if (!t.quoted_tweet_id) return;
    const quoted = byId.get(t.quoted_tweet_id);

    const block = document.createElement("aside");
    block.className = "quoted-block";

    if (quoted) {
      const m = document.createElement("div");
      m.className = "ctx-meta";
      const dn = document.createElement("span");
      dn.className = "display-name";
      dn.textContent = quoted.account_display_name || quoted.username || "";
      const handle = document.createElement("span");
      handle.textContent = " @" + (quoted.username || "");
      m.append(dn, handle);
      block.appendChild(m);
      const b = document.createElement("div");
      b.className = "ctx-body";
      b.appendChild(renderText(quoted.full_text || "", quoted.url_expansions, quoted.media_tcos));
      block.appendChild(b);
      const qm = quoted.media || [];
      if (qm.length) {
        const qme = renderMedia(qm);
        qme.classList.add("ctx-media");
        block.appendChild(qme);
      }
    } else {
      const label = document.createElement("div");
      label.className = "quoted-fallback";
      const link = document.createElement("a");
      link.className = "x-link";
      link.href = `https://x.com/i/status/${t.quoted_tweet_id}`;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "Quoting a tweet ↗";
      const plain = document.createElement("span");
      plain.className = "x-link-text";
      plain.textContent = "Quoting a tweet";
      plain.style.display = "none";
      label.append(link, plain);
      block.appendChild(label);
    }
    card.appendChild(block);
  }

  // -------------------------------------------------------- metrics row

  function renderMetrics(t) {
    const row = document.createElement("div");
    row.className = "metrics";
    const items = [
      { key: "likes", glyph: "♥", label: "likes",        n: t.favorite_count },
      { key: "rt",    glyph: "↻", label: "retweets",     n: t.retweet_count },
      { key: "qt",    glyph: "❝", label: "quote-tweets", n: t.qt_count },
    ];
    for (const it of items) {
      const span = document.createElement("span");
      span.className = "metric" + (it.key === state.metric ? " is-rank-metric" : "");
      const g = document.createElement("span");
      g.className = "glyph";
      g.textContent = it.glyph;
      const v = document.createElement("span");
      v.textContent = (it.n || 0).toLocaleString("en-GB") + " " + it.label;
      span.append(g, v);
      row.appendChild(span);
    }
    return row;
  }

  // -------------------------------------------------------- media

  /** Render an array of media items: {type: 'photo'|'video'|'gif', url?, poster?}.
   *
   * IMPORTANT: video.twimg.com (and pbs.twimg.com to a lesser extent) returns
   * 403 if the Referer header points anywhere other than twitter.com /
   * x.com — the standard hotlink-protection pattern. We therefore set
   * `referrerPolicy="no-referrer"` on every twimg element so the browser sends
   * no Referer at all. (Setting a fake referrer in JS doesn't work; browsers
   * strip cross-origin overrides.)
   *
   * Photos: <img>. Videos with a playable url: <video controls playsinline
   * preload=none referrerpolicy=no-referrer> with a poster. Videos with only
   * a poster (no resolvable mp4): show poster as <img>.
   *
   * Error handling: broken IMAGES self-remove silently (and an empty wrapper
   * removes itself with them). Broken VIDEOS keep their poster visible —
   * removing a video on a transient playback error would make the tweet
   * appear empty after the user clicks play, which is much worse than just
   * leaving a non-playing thumbnail. */
  function renderMedia(items) {
    const wrap = document.createElement("div");
    wrap.className = "media media-" + Math.min(items.length, 4);
    const removeImg = el => {
      el.remove();
      if (!wrap.children.length) wrap.remove();
    };

    items.slice(0, 4).forEach(m => {
      let el;
      if ((m.type === "video" || m.type === "gif") && m.url) {
        el = document.createElement("video");
        el.src = m.url;
        if (m.poster) el.poster = m.poster;
        el.controls = m.type === "video";
        el.playsInline = true;
        el.preload = "none";
        el.referrerPolicy = "no-referrer";
        if (m.type === "gif") {
          el.loop = true;
          el.muted = true;
          el.autoplay = true;
        }
        // Don't auto-remove on error — keep the poster visible.
      } else if ((m.type === "video" || m.type === "gif") && m.poster) {
        // No playable mp4 — fall back to poster image so something renders.
        el = document.createElement("img");
        el.loading = "lazy";
        el.alt = "";
        el.referrerPolicy = "no-referrer";
        el.src = m.poster;
        el.classList.add("video-poster-only");
        el.onerror = () => removeImg(el);
      } else if (m.url) {
        el = document.createElement("img");
        el.loading = "lazy";
        el.alt = "";
        el.referrerPolicy = "no-referrer";
        el.src = m.url;
        el.onerror = () => removeImg(el);
      } else {
        return; // nothing to render
      }
      wrap.appendChild(el);
    });
    return wrap;
  }

  // -------------------------------------------------------- text rendering

  /** Decode HTML entities like &amp; &gt; &#39; via a textarea trick.
   * Cached element to avoid GC churn — one shared decoder is fine, we never
   * read its DOM, only its textContent value. */
  const _decoder = document.createElement("textarea");
  function htmlDecode(s) {
    if (!s) return "";
    _decoder.innerHTML = s;
    return _decoder.value;
  }

  /** Escape a string for use in a RegExp. */
  function escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Match http(s):// URLs in tweet text. Stops at whitespace and basic terminators.
  const URL_RE = /(https?:\/\/[^\s<>"]+)/g;

  /** Render tweet body:
   *   1. HTML-decode entities
   *   2. Strip any t.co URLs that point to the tweet's own attached media
   *      (passed in via mediaTcos) — these are the auto-appended "view image"
   *      shortlinks; they're redundant when the media renders inline.
   *   3. Linkify remaining URLs. If a URL appears in urlExpansions, replace
   *      its href with the expanded destination and its visible text with the
   *      friendlier display_url. */
  function renderText(text, urlExpansions, mediaTcos) {
    text = htmlDecode(text || "");

    // Strip media-bearing t.co URLs anywhere in the text (with surrounding
    // whitespace collapsed to a single space, then trimmed).
    const tcos = (mediaTcos || []).filter(Boolean);
    if (tcos.length) {
      const re = new RegExp("\\s*(?:" + tcos.map(escapeRe).join("|") + ")\\s*", "g");
      text = text.replace(re, " ").replace(/[ \t]+\n/g, "\n").replace(/[ \t]{2,}/g, " ").trim();
    }

    const expMap = new Map();
    for (const e of urlExpansions || []) {
      if (e && e.url) expMap.set(e.url, e);
    }

    const frag = document.createDocumentFragment();
    let last = 0;
    text.replace(URL_RE, (match, _u, idx) => {
      if (idx > last) frag.appendChild(document.createTextNode(text.slice(last, idx)));

      const exp = expMap.get(match);
      const href = exp ? exp.expanded_url : match;
      const display = exp ? exp.display_url : displayUrl(match);

      const a = document.createElement("a");
      a.className = "x-link";
      a.href = href;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = display;

      const plain = document.createElement("span");
      plain.className = "x-link-text";
      plain.textContent = display;
      plain.style.display = "none";

      const wrap = document.createElement("span");
      wrap.appendChild(a);
      wrap.appendChild(plain);
      frag.appendChild(wrap);

      last = idx + match.length;
      return match;
    });
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    return frag;
  }

  function displayUrl(u) {
    try {
      const x = new URL(u);
      const host = x.hostname.replace(/^www\./, "");
      const path = x.pathname.length > 1 ? x.pathname : "";
      let s = host + path;
      if (s.length > 50) s = s.slice(0, 47) + "…";
      return s;
    } catch (e) {
      return u;
    }
  }

  // -------------------------------------------------------- helpers

  function xUrl(username, id) {
    return `https://x.com/${username || "i"}/status/${id}`;
  }

  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return "";
    // British English: 4 May 2026
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return `${d.getUTCDate()} ${months[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  }

  // -------------------------------------------------------- handle .no-links for plain spans
  // The default markup renders both <a> and a hidden plain span. CSS hides one or the other.
  // For the "plain" span to *show* when links are off, we use a stylesheet rule via :is().
  // Add it dynamically since we want the toggle to be cheap.
  const styleEl = document.createElement("style");
  styleEl.textContent = `
    body.no-links .x-link-text { display: inline !important; }
    body:not(.no-links) .x-link-text { display: none !important; }
  `;
  document.head.appendChild(styleEl);

})();
