/* 대회 레이더 — 화면 코드 (빌드 도구 없이 그대로 동작) */
(function () {
  'use strict';

  var TZ = 'Asia/Seoul';
  var CATS = {
    algo: { label: '알고리즘' },
    hack: { label: '해커톤' },
    contest: { label: '공모전' },
    ai: { label: 'CTF·AI' }
  };
  var CAT_KEYS = ['algo', 'hack', 'contest', 'ai'];
  var WD = ['일', '월', '화', '수', '목', '금', '토'];
  var PAGE = 60;

  var view = document.getElementById('view');
  var state = {
    data: null,
    error: null,
    filter: load('cr.filter', 'all'),
    query: '',
    limit: PAGE,
    calY: null,
    calM: null,
    calSel: null,
    scroll: {}
  };
  var saved = load('cr.saved', {});

  // ------------------------------------------------------------ storage
  function load(key, fallback) {
    try {
      var v = localStorage.getItem(key);
      return v == null ? fallback : JSON.parse(v);
    } catch (e) { return fallback; }
  }
  function store(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* 저장 못 해도 앱은 계속 동작 */ }
  }

  // ------------------------------------------------------------ helpers
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  function safeUrl(u) {
    return /^https?:\/\//i.test(u || '') ? u : '#';
  }
  var partsFmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23', weekday: 'short'
  });
  var DOW = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  function kst(d) {
    var o = {};
    partsFmt.formatToParts(d).forEach(function (p) { o[p.type] = p.value; });
    return { y: +o.year, m: +o.month, d: +o.day, hh: o.hour, mm: o.minute, dow: DOW[o.weekday] };
  }
  function key(y, m, d) {
    return y + '-' + String(m).padStart(2, '0') + '-' + String(d).padStart(2, '0');
  }
  function dayKey(d) { var p = kst(d); return key(p.y, p.m, p.d); }
  function keyNum(k) { var a = k.split('-'); return Date.UTC(+a[0], +a[1] - 1, +a[2]) / 86400000; }
  function daysFromToday(d) { return keyNum(dayKey(d)) - keyNum(dayKey(new Date())); }
  function dt(s) { return s ? new Date(s) : null; }
  function fmtDay(d) { var p = kst(d); return p.m + '.' + String(p.d).padStart(2, '0') + ' (' + WD[p.dow] + ')'; }
  function fmtDayTime(d) { var p = kst(d); return fmtDay(d) + ' ' + p.hh + ':' + p.mm; }
  function fmtWhen(c) { var d = dt(c.date); return c.allDay ? fmtDay(d) : fmtDayTime(d); }

  function status(c) {
    var now = Date.now();
    var start = dt(c.start), end = dt(c.end), date = dt(c.date);
    if (start && end && start <= now && now < end) return { text: '진행 중', cls: 'live', live: true };
    if ((end || date) < now) return { text: c.allDay ? '마감' : '종료', cls: '', over: true };
    var n = daysFromToday(date);
    if (n <= 0) return { text: 'D-day', cls: 'urgent', n: 0 };
    return { text: 'D-' + n, cls: n <= 3 ? 'urgent' : '', n: n };
  }

  function contests() { return (state.data && state.data.contests) || []; }
  function findContest(id) {
    var list = contests();
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return saved[id] || null;
  }
  function isSaved(id) { return !!saved[id]; }
  function toggleSaved(id) {
    if (saved[id]) delete saved[id];
    else { var c = findContest(id); if (c) saved[id] = c; }
    store('cr.saved', saved);
  }
  // 저장해 둔 대회 정보가 새로 수집된 정보로 바뀌었으면 갱신
  function refreshSaved() {
    var changed = false;
    contests().forEach(function (c) { if (saved[c.id]) { saved[c.id] = c; changed = true; } });
    if (changed) store('cr.saved', saved);
  }

  // ------------------------------------------------------------ icons
  var I = {
    radar: '<svg viewBox="0 0 28 28" aria-hidden="true"><circle cx="14" cy="14" r="11"/><circle cx="14" cy="14" r="6"/><path d="M14 14 22 6"/><circle cx="14" cy="14" r="1.5" fill="currentColor"/></svg>',
    search: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
    star: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9 6.8 19.6l1-5.8-4.3-4.1 5.9-.9z"/></svg>',
    back: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg>',
    prev: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg>',
    next: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>',
    out: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8"/></svg>',
    cal: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4M12 13v5M9.5 15.5h5"/></svg>',
    bell: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
    warn: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>',
    chev: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>'
  };

  // ------------------------------------------------------------ pieces
  function tagHtml(c) {
    var t = '<span class="tag ' + esc(c.cat) + '">' + esc((CATS[c.cat] || {}).label || c.cat) + '</span>';
    if (c.tag) t += '<span class="tag plain">' + esc(c.tag) + '</span>';
    return t;
  }
  function starBtn(c, extraCls) {
    var on = isSaved(c.id);
    return '<button class="star' + (extraCls ? ' ' + extraCls : '') + '" data-star="' + esc(c.id) + '" aria-pressed="' + on +
      '" aria-label="' + esc(c.title) + (on ? ' 관심 대회에서 빼기' : ' 관심 대회에 저장') + '">' + I.star + '</button>';
  }
  function card(c) {
    var s = status(c);
    return '<article class="card">' +
      '<a class="card-link" href="#/c/' + encodeURIComponent(c.id) + '">' +
        '<div class="card-meta">' + tagHtml(c) + '<span>' + esc(c.kind) + '</span></div>' +
        '<div class="card-title">' + esc(c.title) + '</div>' +
        '<div class="card-sub">' + esc(c.host) + ' · ' + esc(fmtWhen(c)) + '</div>' +
      '</a>' +
      '<div class="card-side"><span class="dday ' + s.cls + '">' + esc(s.text) + '</span>' + starBtn(c) + '</div>' +
    '</article>';
  }
  function updatedText() {
    if (!state.data || !state.data.updatedAt) return '';
    return '업데이트 ' + fmtDayTime(new Date(state.data.updatedAt));
  }
  function sourceWarnings() {
    if (!state.data) return '';
    var out = [];
    var age = (Date.now() - new Date(state.data.updatedAt)) / 3600000;
    if (age > 48) out.push('자동 업데이트가 ' + Math.floor(age / 24) + '일째 멈춰 있어요. GitHub Actions 실행 기록을 확인해 보세요.');
    var bad = Object.keys(state.data.sources || {}).filter(function (k) { return !state.data.sources[k].ok; });
    if (bad.length) out.push(bad.join(', ') + ' 정보를 이번에 못 가져와서 지난번 정보로 보여주고 있어요.');
    return out.map(function (t) {
      return '<div class="notice warn" role="status">' + I.warn + '<span>' + esc(t) + ' <a href="#/saved">자세히</a></span></div>';
    }).join('');
  }
  function reminder() {
    var soon = Object.keys(saved).map(function (k) { return saved[k]; }).filter(function (c) {
      var s = status(c);
      return !s.over && (s.live || s.n <= 3);
    });
    if (!soon.length) return '';
    soon.sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    var first = soon[0];
    var fs = status(first);
    var when = fs.live ? '지금 진행 중' : fs.n === 0 ? (first.allDay ? '오늘 접수 마감' : '오늘 시작') : fs.n + '일 남음';
    var link = '<a href="#/c/' + encodeURIComponent(first.id) + '">' + esc(first.title) + '</a>';
    var txt = soon.length === 1
      ? '관심 대회 알림 · ' + link + ' (' + when + ')'
      : '관심 대회 <a href="#/saved">' + soon.length + '개</a>가 3일 안에 있어요. 가장 가까운 건 ' + link + ' (' + when + ')';
    return '<div class="notice remind" role="status">' + I.bell + '<span>' + txt + '</span></div>';
  }

  // ------------------------------------------------------------ views
  function filtered() {
    var q = state.query.trim().toLowerCase();
    return contests().filter(function (c) {
      if (state.filter !== 'all' && c.cat !== state.filter) return false;
      if (status(c).over) return false;
      if (!q) return true;
      return (c.title + ' ' + c.host + ' ' + c.source + ' ' + (c.tag || '') + ' ' + ((CATS[c.cat] || {}).label || ''))
        .toLowerCase().indexOf(q) !== -1;
    });
  }

  function renderList() {
    var all = contests().filter(function (c) { return !status(c).over; });
    var counts = { all: all.length };
    CAT_KEYS.forEach(function (k) { counts[k] = all.filter(function (c) { return c.cat === k; }).length; });
    var chips = [['all', '전체']].concat(CAT_KEYS.map(function (k) { return [k, CATS[k].label]; })).map(function (p) {
      return '<button class="chip" data-filter="' + p[0] + '" aria-pressed="' + (state.filter === p[0]) + '">' +
        esc(p[1]) + ' <span class="n">' + counts[p[0]] + '</span></button>';
    }).join('');

    view.innerHTML =
      '<header class="top">' +
        '<div class="top-row"><h1 class="brand">' + I.radar + '대회 레이더</h1><span class="updated">' + esc(updatedText()) + '</span></div>' +
        '<label class="search">' + I.search + '<span class="sr">대회 검색</span>' +
          '<input id="q" type="search" placeholder="대회 이름, 주최, 사이트 검색" value="' + esc(state.query) + '" autocomplete="off"></label>' +
        '<div class="chips" role="group" aria-label="대회 종류">' + chips + '</div>' +
      '</header>' +
      '<section class="list" id="list" aria-live="polite"></section>';
    renderListItems();
  }

  function renderListItems() {
    var box = document.getElementById('list');
    if (!box) return;
    var items = filtered();
    var html = sourceWarnings() + reminder();
    if (!items.length) {
      html += '<div class="empty"><strong>' + (state.query ? '검색 결과가 없어요' : '예정된 대회가 없어요') + '</strong>' +
        (state.query ? '다른 단어로 검색하거나 종류를 "전체"로 바꿔 보세요.' : '내일 다시 확인해 보세요.') + '</div>';
      box.innerHTML = html;
      return;
    }
    var groups = [
      { name: '진행 중', test: function (s) { return s.live; } },
      { name: '오늘·내일', test: function (s) { return s.n <= 1; } },
      { name: '이번 주', test: function (s) { return s.n <= 7; } },
      { name: '다음 주', test: function (s) { return s.n <= 14; } },
      { name: '그 이후', test: function () { return true; } }
    ];
    var shown = items.slice(0, state.limit);
    var buckets = groups.map(function () { return []; });
    shown.forEach(function (c) {
      var s = status(c);
      for (var i = 0; i < groups.length; i++) if (groups[i].test(s)) { buckets[i].push(c); break; }
    });
    groups.forEach(function (g, i) {
      if (!buckets[i].length) return;
      html += '<h2 class="group-h"><span>' + g.name + '</span><span>' + buckets[i].length + '개</span></h2>';
      html += buckets[i].map(card).join('');
    });
    if (items.length > shown.length) {
      html += '<button class="more" data-more>' + (items.length - shown.length) + '개 더 보기</button>';
    }
    html += '<p class="foot-note">마감·대회 시간이 가까운 순서예요. 시간은 한국 시간 기준이에요.</p>';
    box.innerHTML = html;
  }

  function renderCalendar() {
    var today = kst(new Date());
    if (state.calY == null) { state.calY = today.y; state.calM = today.m; }
    if (!state.calSel) state.calSel = key(today.y, today.m, today.d);
    var y = state.calY, m = state.calM;
    var first = new Date(Date.UTC(y, m - 1, 1));
    var startDow = first.getUTCDay();
    var days = new Date(Date.UTC(y, m, 0)).getUTCDate();
    var todayKey = key(today.y, today.m, today.d);

    var byDay = {};
    contests().forEach(function (c) {
      var k = dayKey(dt(c.start || c.date));
      (byDay[k] = byDay[k] || []).push(c);
    });

    var cells = '';
    for (var b = 0; b < startDow; b++) cells += '<button class="day" disabled aria-hidden="true" tabindex="-1"></button>';
    for (var d = 1; d <= days; d++) {
      var k = key(y, m, d);
      var evs = byDay[k] || [];
      var dow = (startDow + d - 1) % 7;
      var cats = [];
      evs.forEach(function (c) { if (cats.indexOf(c.cat) === -1) cats.push(c.cat); });
      var cls = 'day' + (dow === 0 ? ' sun' : dow === 6 ? ' sat' : '') + (k === todayKey ? ' today' : '') + (k < todayKey ? ' past' : '');
      cells += '<button class="' + cls + '" data-day="' + k + '" aria-pressed="' + (k === state.calSel) +
        '" aria-label="' + m + '월 ' + d + '일, 일정 ' + evs.length + '개">' +
        '<span class="num">' + d + '</span><span class="dots">' +
        cats.slice(0, 4).map(function (c) { return '<i class="' + c + '"></i>'; }).join('') + '</span></button>';
    }

    var selEvents = (byDay[state.calSel] || []).slice().sort(function (a, b) { return (a.start || a.date) < (b.start || b.date) ? -1 : 1; });
    var sp = state.calSel.split('-');
    var selDate = new Date(Date.UTC(+sp[0], +sp[1] - 1, +sp[2], 3));
    var selLabel = (+sp[1]) + '월 ' + (+sp[2]) + '일 (' + WD[selDate.getUTCDay()] + ')' + (state.calSel === todayKey ? ' · 오늘' : '');

    view.innerHTML =
      '<section class="cal" aria-label="달력">' +
        '<div class="cal-head"><h1 class="page-title">' + y + '년 ' + m + '월</h1><div>' +
          '<button class="icon-btn" data-month="-1" aria-label="이전 달">' + I.prev + '</button>' +
          '<button class="icon-btn" data-month="0" aria-label="이번 달로">' + '<span style="font-size:13px;font-weight:600">오늘</span>' + '</button>' +
          '<button class="icon-btn" data-month="1" aria-label="다음 달">' + I.next + '</button></div></div>' +
        '<div class="cal-grid">' + WD.map(function (w, i) { return '<div class="cal-dow' + (i === 0 ? ' sun' : i === 6 ? ' sat' : '') + '">' + w + '</div>'; }).join('') + cells + '</div>' +
        '<div class="legend">' + CAT_KEYS.map(function (k) { return '<span><i style="background:var(--' + k + '-dot)"></i>' + CATS[k].label + '</span>'; }).join('') + '</div>' +
      '</section>' +
      '<section class="list"><h2 class="group-h"><span>' + esc(selLabel) + '</span><span>' + selEvents.length + '개</span></h2>' +
        (selEvents.length ? selEvents.map(card).join('') : '<p class="empty" style="padding:16px 4px;text-align:left">이 날은 일정이 없어요.</p>') +
        '<p class="foot-note">알고리즘·CTF는 대회 시작일, 공모전·해커톤은 접수 마감일에 표시돼요.</p>' +
      '</section>';
  }

  function feedUrl(name, webcal) {
    var u = new URL('feeds/' + name + '.ics', location.href).href;
    return webcal ? u.replace(/^https?:/, 'webcal:') : u;
  }

  function renderSaved() {
    var list = Object.keys(saved).map(function (k) { return saved[k]; });
    var upcoming = list.filter(function (c) { return !status(c).over; }).sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    var past = list.filter(function (c) { return status(c).over; }).sort(function (a, b) { return a.date > b.date ? -1 : 1; });

    var savedHtml = upcoming.length
      ? upcoming.map(card).join('')
      : '<div class="empty" style="padding:24px 8px"><strong>아직 저장한 대회가 없어요</strong>목록에서 ☆ 별표를 누르면 여기에 모여요.</div>';
    if (past.length) {
      savedHtml += '<h2 class="group-h"><span>끝난 대회</span><span>' + past.length + '개</span></h2>' + past.map(card).join('');
    }

    var feeds = [['all', '전체']].concat(CAT_KEYS.map(function (k) { return [k, CATS[k].label]; })).map(function (p) {
      return '<a class="row" href="' + esc(feedUrl(p[0], true)) + '"><span class="label">' + esc(p[1]) + ' 일정 구독</span><span class="go">애플·기본 캘린더' + I.chev + '</span></a>';
    }).join('');
    var gFeed = 'https://calendar.google.com/calendar/r?cid=' + encodeURIComponent(feedUrl('all', true));

    var src = state.data ? Object.keys(state.data.sources || {}).map(function (k) {
      var s = state.data.sources[k];
      var last = s.lastSuccess ? fmtDayTime(new Date(s.lastSuccess)) : '없음';
      return '<div class="row"><span class="label">' + esc(k) + '</span><span class="src-status">' +
        (s.ok ? s.count + '개 · 정상' : '<span class="bad">실패</span> · 마지막 성공 ' + esc(last)) + '</span></div>';
    }).join('') : '';

    view.innerHTML =
      '<header class="top"><div class="top-row"><h1 class="page-title">관심 대회</h1><span class="updated">' + upcoming.length + '개 예정</span></div></header>' +
      '<section class="section"><div class="list" style="padding:0">' + savedHtml + '</div></section>' +
      '<section class="section"><h2>마감 알림</h2>' +
        '<div class="panel">' +
          '<div class="row"><span class="label">' + I.bell + '앱 안에서 알려주기</span><span class="go">3일 이내</span></div>' +
          '<div class="row"><span class="label">' + I.cal + '폰 알림 받기</span><span class="go">대회 상세에서 설정</span></div>' +
        '</div>' +
        '<p class="hint">앱을 열면 3일 안에 있는 관심 대회를 맨 위에 보여줘요. 폰 알림을 받으려면 대회 상세 화면에서 "내 캘린더에 추가"를 누르세요. 3일 전과 하루 전에 캘린더 앱이 알려줘요.</p>' +
      '</section>' +
      '<section class="section"><h2>캘린더 구독</h2>' +
        '<div class="panel">' + feeds + '<a class="row" href="' + esc(gFeed) + '" target="_blank" rel="noopener"><span class="label">구글 캘린더에 전체 구독</span><span class="go">열기' + I.chev + '</span></a></div>' +
        '<p class="hint">구독하면 새 대회가 캘린더에 자동으로 들어와요. 대회가 많아서 캘린더가 복잡해질 수 있으니 관심 있는 종류만 구독하는 걸 추천해요.</p>' +
      '</section>' +
      '<section class="section" style="padding-bottom:16px"><h2>데이터 상태</h2>' +
        '<div class="panel">' + src + '</div>' +
        '<p class="hint">' + esc(updatedText()) + ' · 매일 오전 6시와 오후 6시에 자동으로 새로 모아요.</p>' +
      '</section>';
  }

  function renderDetail(id) {
    var c = findContest(id);
    if (!c) {
      view.innerHTML = '<div class="d-top"><a class="icon-btn" href="#/" aria-label="목록으로 돌아가기">' + I.back + '</a><span>대회 정보</span><span style="width:44px"></span></div>' +
        '<div class="empty"><strong>이 대회를 찾을 수 없어요</strong>이미 끝났거나 목록에서 빠진 대회예요. <a href="#/">목록으로</a></div>';
      return;
    }
    var s = status(c);
    var countText = s.live ? '지금 진행 중이에요' : s.over ? (c.allDay ? '접수가 마감됐어요' : '대회가 끝났어요')
      : (c.kind === '접수 마감' ? '접수 마감' : '대회 시작') + (s.n === 0 ? ' 오늘이에요' : '까지 ' + s.n + '일 남았어요');

    var facts = (c.meta || []).map(function (f) {
      var unknown = f.value === '원문 확인';
      return '<div class="fact"><span class="k">' + esc(f.label) + '</span><span class="v' + (unknown ? ' unknown' : '') + '">' + esc(f.value) + '</span></div>';
    }).join('');

    var tl;
    if (c.allDay) {
      tl = '<div class="tl"><span class="pt on ' + esc(c.cat) + '"></span><div class="txt"><strong>접수 마감</strong><span class="when">' + esc(fmtDay(dt(c.date))) + '</span></div></div>' +
        '<p style="font-size:13px;color:var(--muted)">대회·발표 일정은 원래 사이트에서 확인해 주세요.</p>';
    } else {
      tl = '<div class="tl"><span class="pt on ' + esc(c.cat) + '"></span><div class="txt"><strong>시작</strong><span class="when">' + esc(fmtDayTime(dt(c.start))) + '</span></div></div>' +
        '<div class="tl"><span class="pt"></span><div class="txt"><span>종료</span><span class="when">' + esc(fmtDayTime(dt(c.end))) + '</span></div></div>';
    }

    var inData = contests().some(function (x) { return x.id === c.id; });
    var g = googleUrl(c);
    var calLinks = '<div class="cal-links">' +
      (inData ? '<a class="btn" href="ics/' + encodeURIComponent(c.id) + '.ics">' + I.cal + '내 캘린더에 추가</a>' : '') +
      '<a class="btn" href="' + esc(g) + '" target="_blank" rel="noopener">' + I.cal + '구글 캘린더에 추가</a></div>' +
      (inData ? '<p style="font-size:13px;color:var(--muted)">"내 캘린더에 추가"는 3일 전·하루 전 알림이 함께 들어가요.</p>' : '');

    view.innerHTML =
      '<div class="d-top"><a class="icon-btn" href="#/" data-back aria-label="이전 화면으로">' + I.back + '</a><span>대회 정보</span><span style="width:44px"></span></div>' +
      '<section class="d-head">' +
        '<div class="card-meta">' + tagHtml(c) + '<span>' + esc(c.source) + '</span></div>' +
        '<h1>' + esc(c.title) + '</h1>' +
        '<div class="d-host">' + esc(c.host) + '</div>' +
        '<div class="d-count"><span class="dday ' + s.cls + '">' + esc(s.text) + '</span><span>' + esc(countText) + '</span></div>' +
      '</section>' +
      '<div class="d-body">' +
        (facts ? '<section class="box"><div class="facts">' + facts + '</div></section>' : '') +
        '<section class="box"><h2>일정</h2>' + tl + calLinks + '</section>' +
        (c.summary ? '<section class="box"><h2>소개</h2><p>' + esc(c.summary) + '</p></section>' : '') +
        '<p class="source-line">출처: ' + esc(c.source) + ' · ' + esc(updatedText()) + '</p>' +
      '</div>' +
      '<div class="d-foot"><div class="d-foot-in">' + starBtn(c) +
        '<a class="btn primary" href="' + esc(safeUrl(c.url)) + '" target="_blank" rel="noopener">원래 사이트에서 보기' + I.out + '</a>' +
      '</div></div>';
  }

  function googleUrl(c) {
    function z(d) { return d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, ''); }
    var dates;
    if (c.allDay) {
      var p = kst(dt(c.date));
      var a = Date.UTC(p.y, p.m - 1, p.d), b = a + 86400000;
      var f = function (t) { return new Date(t).toISOString().slice(0, 10).replace(/-/g, ''); };
      dates = f(a) + '/' + f(b);
    } else {
      dates = z(dt(c.start)) + '/' + z(dt(c.end || c.start));
    }
    var title = c.allDay ? '[' + c.kind + '] ' + c.title : c.title;
    return 'https://calendar.google.com/calendar/render?action=TEMPLATE&text=' + encodeURIComponent(title) +
      '&dates=' + dates + '&details=' + encodeURIComponent(c.host + '\n' + c.url) + '&ctz=' + TZ;
  }

  // ------------------------------------------------------------ router
  var lastRoute = '';
  function route() {
    var h = location.hash.replace(/^#/, '') || '/';
    var prev = lastRoute;
    if (prev) state.scroll[prev] = window.scrollY;
    lastRoute = h;
    var tab = h.indexOf('/calendar') === 0 ? 'calendar' : h.indexOf('/saved') === 0 ? 'saved' : h.indexOf('/c/') === 0 ? null : 'list';
    document.body.classList.toggle('detail', !tab);
    Array.prototype.forEach.call(document.querySelectorAll('.tabbar a'), function (a) {
      if (a.getAttribute('data-tab') === tab) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });

    if (state.error) {
      view.innerHTML = '<div class="empty"><strong>대회 정보를 불러오지 못했어요</strong>' + esc(state.error) +
        '<br><br><button class="more" data-retry>다시 시도</button></div>';
      return;
    }
    if (!state.data) return;

    if (!tab) { renderDetail(decodeURIComponent(h.slice(3))); document.title = '대회 정보 · 대회 레이더'; }
    else if (tab === 'calendar') { renderCalendar(); document.title = '캘린더 · 대회 레이더'; }
    else if (tab === 'saved') { renderSaved(); document.title = '관심 대회 · 대회 레이더'; }
    else { renderList(); document.title = '대회 레이더'; }

    var y = (tab === 'list' && state.scroll[h]) || 0;
    window.scrollTo(0, y);
  }

  // ------------------------------------------------------------ events
  view.addEventListener('click', function (e) {
    var t = e.target.closest('button, a');
    if (!t) return;
    if (t.hasAttribute('data-star')) {
      var id = t.getAttribute('data-star');
      toggleSaved(id);
      var on = isSaved(id);
      Array.prototype.forEach.call(view.querySelectorAll('[data-star]'), function (b) {
        if (b.getAttribute('data-star') !== id) return;
        b.setAttribute('aria-pressed', on);
        var c = findContest(id);
        b.setAttribute('aria-label', (c ? c.title : '') + (on ? ' 관심 대회에서 빼기' : ' 관심 대회에 저장'));
      });
      if (lastRoute.indexOf('/saved') === 0) renderSaved();
      return;
    }
    if (t.hasAttribute('data-filter')) {
      state.filter = t.getAttribute('data-filter');
      state.limit = PAGE;
      store('cr.filter', state.filter);
      Array.prototype.forEach.call(view.querySelectorAll('[data-filter]'), function (b) {
        b.setAttribute('aria-pressed', b === t);
      });
      renderListItems();
      return;
    }
    if (t.hasAttribute('data-more')) { state.limit += PAGE; renderListItems(); return; }
    if (t.hasAttribute('data-day')) { state.calSel = t.getAttribute('data-day'); renderCalendar(); return; }
    if (t.hasAttribute('data-month')) {
      var dir = +t.getAttribute('data-month');
      if (dir === 0) { var tk = kst(new Date()); state.calY = tk.y; state.calM = tk.m; state.calSel = key(tk.y, tk.m, tk.d); }
      else {
        state.calM += dir;
        if (state.calM < 1) { state.calM = 12; state.calY--; }
        if (state.calM > 12) { state.calM = 1; state.calY++; }
        state.calSel = key(state.calY, state.calM, 1);
      }
      renderCalendar();
      return;
    }
    // 뒤로 버튼: 상세 화면에 오기 전 화면(캘린더, 관심 등)으로 돌아간다. 없으면 목록으로.
    if (t.hasAttribute('data-back') && lastRouteBeforeDetail) {
      e.preventDefault();
      location.hash = lastRouteBeforeDetail;
      return;
    }
    if (t.hasAttribute('data-retry')) { state.error = null; view.innerHTML = '<p class="loading">다시 불러오는 중…</p>'; init(); }
  });

  var lastRouteBeforeDetail = '';
  window.addEventListener('hashchange', function () {
    if (lastRoute && lastRoute.indexOf('/c/') !== 0) lastRouteBeforeDetail = '#' + lastRoute;
    route();
  });

  var qTimer;
  view.addEventListener('input', function (e) {
    if (e.target.id !== 'q') return;
    state.query = e.target.value;
    state.limit = PAGE;
    clearTimeout(qTimer);
    qTimer = setTimeout(renderListItems, 120);
  });

  // ------------------------------------------------------------ start
  function init() {
    fetch('data/contests.json', { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error('서버 응답 ' + r.status); return r.json(); })
      .then(function (d) { state.data = d; refreshSaved(); route(); })
      .catch(function (e) { state.error = '인터넷 연결을 확인해 주세요. (' + e.message + ')'; route(); });
  }
  init();
})();
