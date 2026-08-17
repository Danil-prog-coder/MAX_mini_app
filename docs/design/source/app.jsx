const VUZY = ['Северный политехнический','Приморский федеральный','Городской университет экономики','Институт прикладных наук'];
const GROUPS = ['ИС-231','ИС-232','ПМ-211','ПД-204'];

const MENU = [
  { id: 'test',    n: '01', t: 'Профориентационный тест' },
  { id: 'ege',     n: '02', t: 'Подбор вуза по баллам ЕГЭ' },
  { id: 'track',   n: '03', t: 'Трекер конкурсных списков', badge: '+52' },
  { id: 'sched',   n: '04', t: 'Расписание и дедлайны', needStudent: true },
  { id: 'ask',     n: '05', t: 'Спроси у старшекурсника' },
  { id: 'rating',  n: '06', t: 'Рейтинг активности' },
  { id: 'food',    n: '07', t: 'Где покушать?', needStudent: true },
  { id: 'support', n: '08', t: 'Поддержка / Предложить улучшение' }
];

const RULER = [10,16,10,22,10,16,10,26,16,10,22,10,16,10];

const MONTHS = [
  { m: 'ИЮНЬ', g: 'ИЮНЯ', y: 2026, days: 30, first: 1 },
  { m: 'ИЮЛЬ', g: 'ИЮЛЯ', y: 2026, days: 31, first: 3 },
  { m: 'АВГУСТ', g: 'АВГУСТА', y: 2026, days: 31, first: 6 }
];
const WD = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];

const EV_ABIT = {
  '1-3': [{ t: 'Документы поданы', s: 'Северный политехнический · комплект принят' }],
  '1-7': [{ t: 'Баллы ЕГЭ загружены', s: 'сумма 248 · 4 предмета' }],
  '1-13': [
    { t: 'Приём документов идёт', s: 'Северный политехнический · осталось 12 дней' },
    { t: 'Вы поднялись на 64 место', s: 'вчера были 116-м · проходной 78' }
  ],
  '1-15': [{ t: 'Обновление конкурсных списков', s: 'Северный политехнический · 09:00' }],
  '1-18': [{ t: 'День открытых дверей онлайн', s: 'Приморский федеральный · 17:00' }],
  '1-20': [{ t: 'Последний день приёма', s: 'Городской университет экономики' }],
  '1-25': [{ t: 'Приём документов закрывается', s: 'Северный политехнический и ещё 2 вуза' }],
  '1-29': [{ t: 'Приказы о зачислении', s: 'публикация на сайтах вузов' }],
  '2-1': [{ t: 'Заселение в общежитие', s: 'по спискам зачисленных' }],
  '0-28': [{ t: 'Старт приёма документов', s: 'все отслеживаемые вузы' }]
};

const EV_STUD = {
  '1-13': [
    { t: '4 пары · с 09:00', s: 'Базы данных, дискретная математика, интерфейсы, английский' },
    { t: 'Курсовая по базам данных', s: 'через 3 дня · напомню за сутки' }
  ],
  '1-14': [{ t: '3 пары · с 10:40', s: 'ауд. 118, 405, 207' }],
  '1-16': [{ t: 'Курсовая по базам данных', s: 'сдать до 18:00 · ауд. 312' }],
  '1-22': [{ t: 'Отчёт по практике', s: 'личный дедлайн' }],
  '1-9': [{ t: '4 пары · с 09:00', s: 'обычная неделя' }],
  '1-10': [{ t: '2 пары · с 12:20', s: 'короткий день' }],
  '2-1': [{ t: 'Начало семестра', s: 'расписание обновится автоматически' }]
};

const QUESTIONS = [
  { q: 'Что из этого вам ближе в свободный вечер?', a: ['Разобрать, как что-то устроено внутри', 'Придумать и нарисовать своё', 'Поговорить с людьми и что-то организовать'] },
  { q: 'Какая задача не бесит даже на третий час?', a: ['Найти ошибку в длинной цепочке', 'Собрать красивое из разрозненного', 'Договориться, кто что делает'] },
  { q: 'Что вам чаще говорят друзья?', a: ['«Ты объяснишь понятнее преподавателя»', '«У тебя вкус, глянь»', '«Без тебя бы не собрались»'] },
  { q: 'Как выглядит хороший результат работы?', a: ['Всё работает и не падает', 'На это приятно смотреть', 'Люди довольны и вернулись'] },
  { q: 'Что выберете на олимпиаде?', a: ['Задача с числами и логикой', 'Задача на конструкцию и форму', 'Кейс про людей и решения'] },
  { q: 'Какая учебная нагрузка кажется нормальной?', a: ['Много математики, зато понятно', 'Много практики и проектов', 'Много общения и защиты работ'] },
  { q: 'Где вам комфортнее работать?', a: ['Один, в наушниках', 'В мастерской или студии', 'В команде, вслух'] },
  { q: 'Что важнее в будущей работе?', a: ['Понятный рост и стабильность', 'Свобода делать по-своему', 'Влияние на людей и процессы'] },
  { q: 'Как относитесь к рутине?', a: ['Спокойно, если она ведёт к результату', 'Плохо, нужна новизна', 'Нормально, если рутина общая'] },
  { q: 'Последний вопрос: что скорее откроете первым?', a: ['Документацию', 'Референсы и примеры', 'Чат с коллегами'] }
];

const EGE_SUBJ = ['Русский язык','Математика','Информатика','Физика','Обществознание','Биология','История','Химия'];

const VUZ_DATA = [
  { v: 'Институт прикладных наук', p: 'Программная инженерия', pass: 222, budget: 95, price: 145, dorm: 'Есть', date: '25 июля' },
  { v: 'Северный политехнический', p: 'Информационные системы и технологии', pass: 236, budget: 120, price: 168, dorm: 'Есть', date: '25 июля' },
  { v: 'Приморский федеральный', p: 'Прикладная информатика', pass: 251, budget: 75, price: 194, dorm: 'Есть', date: '25 июля' },
  { v: 'Городской университет экономики', p: 'Бизнес-информатика', pass: 264, budget: 40, price: 212, dorm: 'Нет', date: '20 июля' }
];

const SUPPORT = {
  'Что-то не работает': [
    'Поймали, спасибо. Передал команде — обычно чиним в течение дня, о результате напишу сюда же.',
    'Записал в очередь на исправление. Если знаете, как повторить ошибку, допишите — это ускорит.',
    'Спасибо, это важно. Такие сообщения смотрят каждый день, ответ придёт от «Поддержки».',
    'Уже у разработчиков. Если поломка мешает прямо сейчас — напишите ещё раз, поднимем приоритет.',
    'Принято. Проверим на своей стороне и вернёмся с ответом, даже если причина окажется не в боте.'
  ],
  'Есть идея по улучшению': [
    'Отличная мысль, спасибо. Идеи собираем в общий список и раз в неделю разбираем с командой.',
    'Записал. Если идею поддержат другие пользователи — она поднимется в приоритете.',
    'Спасибо, что не прошли мимо. Ответим, когда решим, берём ли в ближайшую версию.',
    'Передал главе проекта. Часть таких предложений уже стала разделами бота.',
    'Идея принята. Иногда отвечаем не сразу, но читаем каждое сообщение целиком.'
  ],
  'Другой вопрос': [
    'Спасибо за сообщение — оно ушло команде, ответ придёт сюда от имени «Поддержки».',
    'Приняли. Постараемся ответить в течение суток.',
    'Записал ваш вопрос. Если он срочный — напишите ещё раз, так он поднимется в очереди.',
    'Спасибо, разберёмся. Ответ придёт в этот же чат.',
    'Получили. Иногда на такие вопросы отвечает лично глава проекта.'
  ]
};

class Component extends DCLogic {
  get base() { return this._b || (this._b = document.querySelector('[data-app]')); }
  el(s) { return this.base && this.base.querySelector(s); }
  all(s) { return this.base ? Array.from(this.base.querySelectorAll(s)) : []; }

  componentDidMount() {
    this.status = 'Абитуриент';
    this.vuz = 'Северный политехнический';
    this.group = null;
    this.stack = ['menu'];
    this.points = 540;
    this.tracked = [{ v: 'Северный политехнический', p: 'Информационные системы и технологии', date: '25 июля', pos: 64, prev: 116, pass: 78 }];
    this.egeSel = [];
    this.egeScore = {};
    this.egeTotal = 0;
    this.qi = 0;
    this.mi = 1;
    this.today = 13;
    this.paintCal();
    this.paintMenu();
    this.syncProfile();
  }

  events(mi, d) {
    const src = this.status === 'Студент' ? EV_STUD : EV_ABIT;
    return src[mi + '-' + d] || [];
  }

  paintCal() {
    const mi = this.mi == null ? 1 : this.mi;
    const M = MONTHS[mi];
    const grid = this.el('[data-cal-grid]');
    if (!grid) return;
    const mo = this.el('[data-cal-month]'), yr = this.el('[data-cal-year]');
    if (mo) mo.textContent = M.m;
    if (yr) yr.textContent = M.y;
    grid.innerHTML = '';
    for (let i = 1; i < M.first; i++) {
      const sp = document.createElement('span');
      grid.appendChild(sp);
    }
    for (let d = 1; d <= M.days; d++) {
      const ev = this.events(mi, d).length;
      const today = mi === 1 && d === this.today;
      const past = mi === 0 || (mi === 1 && d < this.today);
      const b = document.createElement('button');
      b.setAttribute('data-cal-dot', d);
      b.style.cssText = 'width:34px;height:34px;padding:0;border-radius:999px;cursor:pointer;transition:transform .2s cubic-bezier(.3,1.4,.4,1);animation:nvPop .34s cubic-bezier(.25,1.4,.45,1) ' + (d * 12) + 'ms both;' +
        (today ? 'border:0;background:var(--color-accent)'
          : ev ? 'border:0;background:var(--color-text)'
          : past ? 'border:0;background:var(--color-neutral-300)'
          : 'border:1.5px solid var(--color-neutral-400);background:transparent');
      b.onmouseenter = () => b.style.transform = 'scale(1.16)';
      b.onmouseleave = () => b.style.transform = 'none';
      b.onclick = () => this.openDay(mi, d);
      grid.appendChild(b);
    }
    const sel = this.selDay && this.selMi === mi ? this.selDay : (mi === 1 ? this.today : 1);
    this.setCalHead(mi, sel);
  }

  setCalHead(mi, d) {
    const M = MONTHS[mi];
    const dayEl = this.el('[data-cal-day]'), wdEl = this.el('[data-cal-wd]');
    if (dayEl) dayEl.textContent = d;
    if (wdEl) wdEl.textContent = WD[(M.first - 1 + d - 1) % 7];
  }

  openDay(mi, d) {
    this.selMi = mi; this.selDay = d;
    this.setCalHead(mi, d);
    const M = MONTHS[mi];
    const ev = this.events(mi, d);
    const title = d + ' ' + M.g + ' · ' + WD[(M.first - 1 + d - 1) % 7].toUpperCase();
    let html = '';
    if (!ev.length) {
      html = '<div style="flex:none;padding:22px 24px;border:1.5px solid var(--color-neutral-400);border-radius:30px">' +
        '<div style="font-family:var(--font-heading);font-size:30px;letter-spacing:-.03em">Ничего не запланировано</div>' +
        '<div style="margin-top:8px;font-size:14px;color:var(--color-neutral-700);text-wrap:pretty">' +
        (this.status === 'Студент' ? 'Ни пар, ни дедлайнов. Можно добавить свой дедлайн в разделе «Расписание».' : 'Ни одного события приёмной кампании в отслеживаемых вузах.') + '</div></div>';
    } else {
      ev.forEach((e, i) => {
        const dark = i === 0;
        html += '<div style="flex:none;padding:20px 22px;border-radius:30px;' + (dark ? 'background:var(--color-text);color:var(--color-neutral-200)' : 'border:1.5px solid var(--color-neutral-400)') + '">' +
          '<div style="font-family:var(--font-heading);font-size:22px;line-height:1.15;letter-spacing:-.025em">' + e.t + '</div>' +
          '<div style="margin-top:6px;font-size:13px;line-height:1.45;color:' + (dark ? 'var(--color-neutral-400)' : 'var(--color-neutral-700)') + ';text-wrap:pretty">' + e.s + '</div></div>';
      });
    }
    this.openSheetHTML(title.toUpperCase(), html);
  }

  shiftMonth(dir) {
    const next = (this.mi == null ? 1 : this.mi) + dir;
    if (next < 0 || next > MONTHS.length - 1) return;
    this.mi = next;
    this.selDay = null;
    this.paintCal();
  }

  paintRuler() {
    const r = this.el('[data-ruler]');
    if (!r || r.children.length) return;
    RULER.forEach((h, i) => {
      const s = document.createElement('span');
      const hot = i === 7;
      s.style.cssText = 'display:block;width:' + (hot ? 4 : 3) + 'px;height:' + h + 'px;border-radius:999px;background:' + (hot ? 'var(--color-accent)' : 'rgba(238,231,219,.2)');
      r.appendChild(s);
    });
  }

  paintMenu() {
    const box = this.el('[data-menu]');
    if (!box) return;
    box.innerHTML = '';
    MENU.forEach(m => {
      const locked = m.needStudent && this.status !== 'Студент';
      const b = document.createElement('button');
      b.setAttribute('data-go', m.id);
      b.style.cssText = 'display:flex;align-items:center;gap:14px;width:100%;padding:16px 18px;border:1.5px solid var(--color-neutral-400);border-radius:26px;background:transparent;cursor:pointer;text-align:left;font-family:var(--font-body);font-size:15px;color:var(--color-text)';
      b.onmouseenter = () => b.style.background = 'rgba(32,30,29,.06)';
      b.onmouseleave = () => b.style.background = 'transparent';
      b.onclick = () => this.show(m.id);
      b.innerHTML = '<span style="display:flex;align-items:center;justify-content:center;width:30px;height:30px;flex:none;border-radius:999px;background:' + (locked ? 'var(--color-neutral-400)' : 'var(--color-text)') + ';color:' + (locked ? 'var(--color-neutral-600)' : 'var(--color-neutral-200)') + ';font-family:var(--font-heading);font-size:13px">' + m.n + '</span>' +
        '<span style="flex:1">' + m.t + (locked ? '<span style="display:block;margin-top:3px;font-size:10px;font-weight:700;letter-spacing:.16em;color:var(--color-neutral-500)">НУЖЕН СТАТУС СТУДЕНТА</span>' : '') + '</span>' +
        (m.badge && !locked ? '<span style="padding:6px 11px;border-radius:999px;background:var(--color-accent);font-size:10px;font-weight:700;letter-spacing:.1em">' + m.badge + '</span>' : '') +
        '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#201e1d" stroke-width="2.75" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"></path></svg>';
      box.appendChild(b);
    });
  }

  syncProfile() {
    const isStud = this.status === 'Студент';
    const pill = this.el('[data-pill="status"]');
    if (pill) pill.textContent = this.status.toUpperCase();
    this.all('[data-status]').forEach(b => {
      const on = b.getAttribute('data-status') === this.status;
      b.style.background = on ? 'var(--color-text)' : 'transparent';
      b.style.color = on ? 'var(--color-neutral-200)' : 'var(--color-text)';
      b.style.border = on ? '1.5px solid var(--color-text)' : '1.5px solid var(--color-neutral-400)';
    });
    const gr = this.el('[data-row="group"]');
    if (gr) gr.style.display = isStud ? 'flex' : 'none';
    const gv = this.el('[data-field="group"]');
    if (gv) gv.textContent = this.group || 'Не указана';
    const vv = this.el('[data-field="vuz"]');
    if (vv) vv.textContent = this.vuz || 'Не указан';
    const ver = this.el('[data-verify]');
    if (ver) ver.style.display = isStud ? 'flex' : 'none';
    const hint = this.el('[data-cal-hint]');
    if (hint) hint.textContent = isStud
      ? 'Нажмите на день — пары и дедлайны этого дня'
      : 'Нажмите на день — события приёмной кампании';
    if (this.mi != null) this.paintCal();
    this.paintMenu();
  }

  setStatus(e) {
    const s = e.currentTarget.getAttribute('data-status');
    if (s === this.status) return;
    const wasStud = this.status === 'Студент';
    this.status = s;
    if (s === 'Студент' && !this.group) this.group = 'ИС-231';
    this.syncProfile();
    const t = this.el('[data-toast="profile"]');
    if (t) {
      t.style.display = 'block';
      t.style.animation = 'none'; void t.offsetWidth; t.style.animation = 'nvIn .4s ease both';
      t.textContent = s === 'Студент'
        ? 'Статус изменён на «Студент» — открылись «Расписание и дедлайны» и «Где покушать».'
        : wasStud ? 'Статус изменён на «' + s + '» — «Расписание» и «Где покушать» скрыты, данные сохранены.'
        : 'Статус изменён на «' + s + '». Доступны тест, подбор вуза и трекер.';
    }
  }

  verify() {
    const box = this.el('[data-verify]'), btn = this.el('[data-verify-btn]');
    if (!box || !btn) return;
    box.style.border = '1.5px solid var(--color-accent)';
    box.firstElementChild.textContent = 'Учебная почта подтверждена — вы можете отвечать на вопросы';
    btn.outerHTML = '<span style="flex:none;padding:10px 16px;border-radius:999px;background:var(--color-accent);font-size:10px;font-weight:700;letter-spacing:.14em">ГОТОВО</span>';
  }

  get onEnter() {
    return {
      test: () => this.startTest(),
      ege: () => this.paintEge(),
      'ege-res': () => this.paintEgeRes(),
      track: () => this.paintTrack(),
      'track-det': () => this.paintTrackDet(),
      rating: () => this.paintRating(),
      food: () => this.paintFood(),
      sched: () => this.paintSched(),
      ask: () => this.paintAsk()
    };
  }

  paintGate(id) {
    const k = this.el('[data-gate-kicker]'), t = this.el('[data-gate-text]');
    if (k) k.textContent = id === 'food' ? 'ГДЕ ПОКУШАТЬ' : 'РАСПИСАНИЕ И ДЕДЛАЙНЫ';
    if (t) t.textContent = id === 'food'
      ? 'Точки питания подбираются рядом с вашим вузом. Укажите в профиле статус «Студент» и вуз — и раздел откроется.'
      : 'Этот раздел собирает расписание вашей группы. Укажите в профиле статус «Студент» и вуз — и он откроется.';
  }

  show(id) {
    if ((id === 'sched' || id === 'food') && this.status !== 'Студент') { this.paintGate(id); id = 'gate'; }
    const target = this.el('[data-scr="' + id + '"]') ? id : 'menu';
    this.all('[data-scr]').forEach(s => s.style.display = s.getAttribute('data-scr') === target ? 'block' : 'none');
    const cur = this.el('[data-scr="' + target + '"]');
    if (cur) { cur.scrollTop = 0; cur.style.animation = 'none'; void cur.offsetWidth; cur.style.animation = 'nvIn .34s cubic-bezier(.3,1,.4,1) both'; }
    if (target === 'menu') this.stack = ['menu'];
    else if (this.stack[this.stack.length - 1] !== target) this.stack.push(target);
    this.all('[data-tab]').forEach(b => {
      const on = b.getAttribute('data-tab') === (target === 'profile' ? 'profile' : 'menu');
      if (b.getAttribute('data-tab') === 'profile') {
        b.style.background = on ? 'var(--color-text)' : 'transparent';
        b.style.color = on ? 'var(--color-neutral-200)' : 'var(--color-text)';
        b.style.border = on ? '1.5px solid var(--color-text)' : '1.5px solid var(--color-neutral-400)';
      }
    });
    if (this.onEnter && this.onEnter[target]) this.onEnter[target]();
  }

  back() {
    this.stack.pop();
    const prev = this.stack.pop() || 'menu';
    this.show(prev);
  }

  openSheet(title, items, onPick) {
    const b = this.el('[data-backdrop]'), s = this.el('[data-sheet]'), t = this.el('[data-sheet-title]'), body = this.el('[data-sheet-body]');
    if (!b || !s || !body) return;
    t.textContent = title;
    body.innerHTML = '';
    items.forEach(it => {
      const btn = document.createElement('button');
      btn.style.cssText = 'flex:none;padding:16px 20px;border:1.5px solid var(--color-neutral-400);border-radius:24px;background:transparent;cursor:pointer;text-align:left;font-family:var(--font-body);font-size:15px;color:var(--color-text)';
      btn.onmouseenter = () => btn.style.background = 'rgba(32,30,29,.06)';
      btn.onmouseleave = () => btn.style.background = 'transparent';
      btn.textContent = it;
      btn.onclick = () => { this.closeSheet(); onPick(it); };
      body.appendChild(btn);
    });
    b.style.display = 'block';
    s.style.transform = 'translateY(0)';
  }

  closeSheet() {
    const b = this.el('[data-backdrop]'), s = this.el('[data-sheet]');
    if (b) b.style.display = 'none';
    if (s) s.style.transform = 'translateY(101%)';
  }

  openPicker(e) {
    const what = e.currentTarget.getAttribute('data-pick');
    if (what === 'vuz') this.openSheet('ВЫБЕРИТЕ ВУЗ', VUZY, v => { this.vuz = v; this.syncProfile(); });
    else this.openSheet('ВЫБЕРИТЕ ГРУППУ', GROUPS, g => { this.group = g; this.syncProfile(); });
  }

  startTest() {
    this.qi = 0;
    this.paintQuestion();
  }

  paintQuestion() {
    const q = QUESTIONS[this.qi];
    const num = this.el('[data-q-num]'), txt = this.el('[data-q-text]'), opts = this.el('[data-q-opts]'), dots = this.el('[data-q-dots]');
    if (!q || !num) return;
    num.textContent = String(this.qi + 1).padStart(2, '0');
    txt.textContent = q.q;
    txt.style.animation = 'none'; void txt.offsetWidth; txt.style.animation = 'nvIn .3s ease both';
    dots.innerHTML = '';
    QUESTIONS.forEach((_, i) => {
      const d = document.createElement('span');
      d.style.cssText = 'display:block;flex:1;height:5px;border-radius:999px;background:' + (i < this.qi ? 'var(--color-text)' : i === this.qi ? 'var(--color-accent)' : 'var(--color-neutral-400)');
      dots.appendChild(d);
    });
    opts.innerHTML = '';
    q.a.forEach((a, i) => {
      const b = document.createElement('button');
      b.style.cssText = 'display:flex;align-items:center;gap:14px;width:100%;padding:17px 20px;border:1.5px solid var(--color-neutral-400);border-radius:26px;background:transparent;cursor:pointer;text-align:left;font-family:var(--font-body);font-size:15px;line-height:1.35;color:var(--color-text);animation:nvIn .3s ease ' + (i * 50) + 'ms both';
      b.onmouseenter = () => b.style.background = 'rgba(32,30,29,.06)';
      b.onmouseleave = () => b.style.background = 'transparent';
      b.textContent = a;
      b.onclick = () => {
        b.style.background = 'var(--color-accent)';
        b.style.border = '1.5px solid var(--color-accent)';
        setTimeout(() => {
          if (this.qi < QUESTIONS.length - 1) { this.qi++; this.paintQuestion(); }
          else this.show('test-res');
        }, 180);
      };
      opts.appendChild(b);
    });
  }

  saveTest() {
    this.testResult = 'Информационные системы · 86%';
    const f = this.el('[data-field="test"]');
    if (f) f.textContent = this.testResult;
    this.addPoints(50);
    const b = this.el('[data-save-test]');
    if (b) { b.textContent = 'Сохранено в профиль · +50 баллов'; b.style.background = 'var(--color-accent)'; b.style.color = 'var(--color-text)'; }
  }

  jobs() {
    this.openSheet('ВАКАНСИИ ПО ПРОФИЛЮ · ОТКРЫТЫЕ ДАННЫЕ', ['Junior-разработчик · 24 позиции', 'Аналитик данных · 18 позиций', 'Инженер техподдержки · 41 позиция', 'Тестировщик · 12 позиций'], () => {});
  }

  paintEge() {
    if (!this.egeSel) { this.egeSel = []; this.egeScore = {}; }
    const box = this.el('[data-ege-subj]');
    if (!box) return;
    box.innerHTML = '';
    EGE_SUBJ.forEach(s => {
      const on = this.egeSel.indexOf(s) > -1;
      const b = document.createElement('button');
      b.style.cssText = 'padding:12px 18px;border-radius:999px;border:1.5px solid ' + (on ? 'var(--color-text)' : 'var(--color-neutral-400)') + ';background:' + (on ? 'var(--color-text)' : 'transparent') + ';color:' + (on ? 'var(--color-neutral-200)' : 'var(--color-text)') + ';cursor:pointer;font-family:var(--font-body);font-size:14px';
      b.textContent = s;
      b.onclick = () => {
        const i = this.egeSel.indexOf(s);
        if (i > -1) { this.egeSel.splice(i, 1); delete this.egeScore[s]; } else this.egeSel.push(s);
        this.paintEge();
      };
      box.appendChild(b);
    });
    const rows = this.el('[data-ege-rows]');
    rows.innerHTML = '';
    this.egeSel.forEach(s => {
      const r = document.createElement('div');
      r.style.cssText = 'display:flex;align-items:center;gap:14px;padding:12px 14px 12px 20px;border:1.5px solid var(--color-neutral-400);border-radius:26px;animation:nvIn .3s ease both';
      const label = document.createElement('div');
      label.style.cssText = 'flex:1;min-width:0;font-size:15px';
      label.textContent = s;
      const inp = document.createElement('input');
      inp.type = 'number'; inp.min = 0; inp.max = 100; inp.placeholder = '0';
      inp.value = this.egeScore[s] != null ? this.egeScore[s] : '';
      inp.style.cssText = 'width:96px;flex:none;padding:12px 14px;border:1.5px solid var(--color-neutral-400);border-radius:999px;background:transparent;font-family:var(--font-heading);font-size:22px;letter-spacing:-.03em;text-align:center;color:var(--color-text)';
      const warn = document.createElement('div');
      warn.style.cssText = 'display:none;flex:none;font-size:11px;color:var(--color-accent-700)';
      inp.oninput = () => {
        const v = Number(inp.value);
        if (inp.value === '') { delete this.egeScore[s]; inp.style.borderColor = 'var(--color-neutral-400)'; }
        else if (isNaN(v) || v < 0 || v > 100) { inp.style.borderColor = 'var(--color-accent)'; warn.style.display = 'block'; warn.textContent = '0–100'; delete this.egeScore[s]; }
        else { this.egeScore[s] = v; inp.style.borderColor = 'var(--color-neutral-400)'; warn.style.display = 'none'; }
        this.egeSum();
      };
      r.appendChild(label); r.appendChild(warn); r.appendChild(inp);
      rows.appendChild(r);
    });
    this.egeSum();
  }

  egeSum() {
    const vals = this.egeSel ? this.egeSel.map(s => this.egeScore[s]).filter(v => typeof v === 'number') : [];
    const sum = vals.reduce((a, b) => a + b, 0);
    this.egeTotal = sum;
    const out = this.el('[data-ege-sum]');
    if (out) out.textContent = sum;
    const ready = this.egeSel.length >= 3 && vals.length === this.egeSel.length;
    const go = this.el('[data-ege-go]');
    if (go) {
      go.style.background = ready ? 'var(--color-text)' : 'var(--color-neutral-400)';
      go.style.color = ready ? 'var(--color-neutral-200)' : 'var(--color-neutral-600)';
      go.style.cursor = ready ? 'pointer' : 'not-allowed';
      go.textContent = ready ? 'Подобрать вузы' : 'Выберите минимум 3 предмета и введите баллы';
    }
    const hint = this.el('[data-ege-hint]');
    if (hint) hint.style.display = this.egeSel.length ? 'none' : 'block';
  }

  egeGo() {
    const vals = this.egeSel.map(s => this.egeScore[s]).filter(v => typeof v === 'number');
    if (this.egeSel.length < 3 || vals.length !== this.egeSel.length) return;
    this.show('ege-res');
  }

  chanceOf(pass) {
    const d = this.egeTotal - pass;
    if (d >= 8) return { k: 'high', label: 'ВЫСОКИЙ ШАНС', n: 3 };
    if (d >= -10) return { k: 'mid', label: 'ПОГРАНИЧНЫЙ', n: 2 };
    return { k: 'low', label: 'МАЛОВЕРОЯТНО', n: 1 };
  }

  dotsHTML(n, dark) {
    let h = '<span style="display:flex;gap:5px">';
    for (let i = 0; i < 3; i++) h += '<span style="display:block;width:9px;height:9px;border-radius:999px;background:' + (i < n ? 'var(--color-accent)' : (dark ? 'rgba(238,231,219,.25)' : 'var(--color-neutral-400)')) + '"></span>';
    return h + '</span>';
  }

  paintEgeRes() {
    const sum = this.el('[data-ege-res-sum]');
    if (sum) sum.textContent = this.egeTotal || 0;
    const list = this.el('[data-ege-list]');
    if (!list) return;
    list.innerHTML = '';
    VUZ_DATA.map(v => ({ v: v, c: this.chanceOf(v.pass) }))
      .sort((a, b) => b.c.n - a.c.n)
      .forEach((it, i) => {
        const b = document.createElement('button');
        const dark = it.c.k === 'high';
        b.style.cssText = 'display:block;width:100%;padding:20px 22px;border-radius:30px;text-align:left;cursor:pointer;font-family:var(--font-body);animation:nvIn .34s ease ' + (i * 60) + 'ms both;' +
          (dark ? 'border:0;background:var(--color-text);color:var(--color-neutral-200)' : 'border:1.5px solid var(--color-neutral-400);background:transparent;color:var(--color-text)');
        b.innerHTML = '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px">' +
          '<span style="font-size:10px;font-weight:700;letter-spacing:.18em;color:' + (dark ? 'var(--color-accent-300)' : 'var(--color-neutral-600)') + '">' + it.c.label + '</span>' + this.dotsHTML(it.c.n, dark) + '</div>' +
          '<div style="margin-top:6px;font-family:var(--font-heading);font-size:24px;line-height:1.1;letter-spacing:-.03em">' + it.v.v + '</div>' +
          '<div style="margin-top:6px;font-size:13px;color:' + (dark ? 'var(--color-neutral-400)' : 'var(--color-neutral-700)') + '">' + it.v.p + '</div>' +
          '<div style="margin-top:10px;font-size:12px;color:' + (dark ? 'var(--color-neutral-500)' : 'var(--color-neutral-600)') + '">проходной прошлого года — ' + it.v.pass + '</div>';
        b.onclick = () => { this.curVuz = it.v; this.curChance = it.c; this.show('vuz-card'); this.paintVuzCard(); };
        list.appendChild(b);
      });
  }

  paintVuzCard() {
    const v = this.curVuz || VUZ_DATA[0], c = this.curChance || { label: 'ВЫСОКИЙ ШАНС' };
    const set = (sel, val) => { const e = this.el(sel); if (e) e.textContent = val; };
    set('[data-vc-chance]', c.label);
    set('[data-vc-name]', v.v);
    set('[data-vc-prog]', v.p);
    set('[data-vc-budget]', v.budget);
    set('[data-vc-price]', v.price);
    set('[data-vc-dorm]', v.dorm);
    set('[data-vc-date]', v.date);
    const btn = this.el('[data-vc-track]');
    const already = this.tracked.some(t => t.v === v.v);
    if (btn) {
      btn.textContent = already ? 'Уже отслеживается' : 'Отслеживать этот вуз';
      btn.style.background = already ? 'transparent' : 'var(--color-accent)';
      btn.style.border = already ? '1.5px solid var(--color-neutral-400)' : '0';
    }
  }

  trackVuz() {
    const v = this.curVuz || VUZ_DATA[0];
    if (!this.tracked.some(t => t.v === v.v)) {
      this.tracked.push({ v: v.v, p: v.p, date: v.date, pos: null, prev: null, pass: 78 });
      const f = this.el('[data-field="tracked"]');
      if (f) f.textContent = this.tracked.length;
    }
    this.paintVuzCard();
    this.show('track');
  }

  paintTrack() {
    const list = this.el('[data-track-list]'), empty = this.el('[data-track-empty]'), cnt = this.el('[data-track-count]');
    if (!list) return;
    if (cnt) cnt.textContent = this.tracked.length;
    if (empty) empty.style.display = this.tracked.length ? 'none' : 'block';
    list.innerHTML = '';
    this.tracked.forEach((t, i) => {
      const b = document.createElement('button');
      const known = t.pos != null;
      b.style.cssText = 'display:flex;align-items:center;gap:14px;width:100%;padding:18px 20px;border-radius:28px;cursor:pointer;text-align:left;font-family:var(--font-body);animation:nvIn .3s ease ' + (i * 60) + 'ms both;' +
        (known ? 'border:0;background:var(--color-text);color:var(--color-neutral-200)' : 'border:1.5px solid var(--color-neutral-400);background:transparent;color:var(--color-text)');
      b.innerHTML = '<div style="flex:1;min-width:0">' +
        '<div style="font-size:10px;font-weight:700;letter-spacing:.18em;color:' + (known ? 'var(--color-accent-300)' : 'var(--color-neutral-600)') + '">' + (known ? 'ВАША ПОЗИЦИЯ' : 'ПОЗИЦИЯ НЕ УКАЗАНА') + '</div>' +
        '<div style="margin-top:3px;font-family:var(--font-heading);font-size:20px;letter-spacing:-.025em">' + t.v + '</div>' +
        '<div style="margin-top:4px;font-size:12px;color:' + (known ? 'var(--color-neutral-500)' : 'var(--color-neutral-600)') + '">приём до ' + t.date + '</div></div>' +
        (known ? '<span style="font-family:var(--font-heading);font-size:44px;letter-spacing:-.04em">' + t.pos + '</span>' : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#201e1d" stroke-width="2.75" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"></path></svg>');
      b.onclick = () => { this.curTrack = t; this.show('track-det'); };
      list.appendChild(b);
    });
  }

  paintTrackDet() {
    const t = this.curTrack || this.tracked[0];
    if (!t) return;
    const known = t.pos != null;
    const n = this.el('[data-td-name]'), k = this.el('[data-td-known]'), a = this.el('[data-td-ask]');
    if (n) n.textContent = t.v.toUpperCase();
    if (k) k.style.display = known ? 'block' : 'none';
    if (a) a.style.display = known ? 'none' : 'block';
    if (known) {
      const now = this.el('[data-td-now]'), d = this.el('[data-td-delta]'), note = this.el('[data-td-note]');
      if (now) now.textContent = t.pos;
      const up = t.prev != null ? t.prev - t.pos : 0;
      if (d) d.textContent = up > 0 ? 'на ' + up : 'без движения';
      if (note) note.textContent = (t.prev != null ? 'Вчера вы были ' + t.prev + '-м. ' : '') + 'Ориентировочный проходной — ' + t.pass + ' место, вы ' + (t.pos <= t.pass ? 'внутри' : 'ниже границы') + '.';
    } else {
      const inp = this.el('[data-td-input]');
      if (inp) inp.value = '';
    }
  }

  savePos() {
    const inp = this.el('[data-td-input]'), t = this.curTrack || this.tracked[0];
    const v = Number(inp && inp.value);
    if (!t || !v || v < 1) { if (inp) inp.style.borderColor = 'var(--color-accent)'; return; }
    t.prev = v;
    t.pos = Math.max(1, v - 52);
    this.paintTrackDet();
  }

  askPos() {
    const t = this.curTrack || this.tracked[0];
    if (!t) return;
    t.pos = null;
    this.paintTrackDet();
  }

  paintSched() {
    const g = this.el('[data-sched-group]');
    if (g) g.textContent = this.group || 'ГРУППА НЕ УКАЗАНА';
  }

  addDeadline() {
    this.openSheetHTML('НОВЫЙ ДЕДЛАЙН', '<input data-dl-name="1" placeholder="Название" style="flex:none;padding:18px 22px;border:1.5px solid var(--color-neutral-400);border-radius:999px;background:transparent;font-family:var(--font-body);font-size:16px;color:var(--color-text);box-sizing:border-box">' +
      '<div style="flex:none;margin-top:4px;font-size:10px;font-weight:700;letter-spacing:.18em;color:var(--color-neutral-600)">КОГДА</div>' +
      '<div data-dl-days="1" style="flex:none;display:flex;flex-wrap:wrap;gap:8px"></div>' +
      '<button data-dl-save="1" style="flex:none;margin-top:6px;padding:17px 10px;border:0;border-radius:999px;background:var(--color-text);color:var(--color-neutral-200);cursor:pointer;font-family:var(--font-body);font-size:14px">Добавить</button>');
    const days = this.el('[data-dl-days]');
    let picked = 3;
    const paint = () => {
      days.innerHTML = '';
      [1, 3, 7, 14, 30].forEach(d => {
        const b = document.createElement('button');
        const on = d === picked;
        b.style.cssText = 'padding:12px 18px;border-radius:999px;border:1.5px solid ' + (on ? 'var(--color-text)' : 'var(--color-neutral-400)') + ';background:' + (on ? 'var(--color-text)' : 'transparent') + ';color:' + (on ? 'var(--color-neutral-200)' : 'var(--color-text)') + ';cursor:pointer;font-family:var(--font-body);font-size:14px';
        b.textContent = 'через ' + d + (d === 1 ? ' день' : d < 5 ? ' дня' : ' дней');
        b.onclick = () => { picked = d; paint(); };
        days.appendChild(b);
      });
    };
    paint();
    const save = this.el('[data-dl-save]');
    save.onclick = () => {
      const name = (this.el('[data-dl-name]') || {}).value;
      if (!name) { this.el('[data-dl-name]').style.borderColor = 'var(--color-accent)'; return; }
      const list = this.el('[data-dl-list]');
      const row = document.createElement('div');
      row.style.cssText = 'display:flex;align-items:center;gap:14px;padding:16px 18px;border:1.5px solid var(--color-accent);border-radius:26px;animation:nvIn .34s ease both';
      row.innerHTML = '<span style="font-family:var(--font-heading);font-size:28px;letter-spacing:-.03em">' + picked + '</span>' +
        '<div style="flex:1;min-width:0"><div style="font-size:15px">' + name + '</div>' +
        '<div style="margin-top:2px;font-size:12px;color:var(--color-neutral-600)">напомню за сутки · личный дедлайн</div></div>';
      list.insertBefore(row, list.firstChild);
      this.closeSheet();
    };
  }

  paintAsk() {
    const v = this.el('[data-ask-vuz]');
    if (v) v.textContent = this.vuz || 'Не указан';
    if (!this.topic) this.topic = null;
  }

  pickTopic(e) {
    this.topic = e.currentTarget.getAttribute('data-topic');
    this.all('[data-topic]').forEach(b => {
      const on = b.getAttribute('data-topic') === this.topic;
      b.style.background = on ? 'var(--color-text)' : 'transparent';
      b.style.color = on ? 'var(--color-neutral-200)' : 'var(--color-text)';
      b.style.borderColor = on ? 'var(--color-text)' : 'var(--color-neutral-400)';
    });
  }

  sendQuestion() {
    const ta = this.el('[data-ask-text]');
    const text = ta && ta.value.trim();
    if (!text) { if (ta) ta.style.borderColor = 'var(--color-accent)'; return; }
    if (!this.topic) { this.topic = 'Поступление'; this.all('[data-topic]')[0].click(); }
    const box = this.el('[data-feed-new]'), t = this.el('[data-feed-new-text]');
    if (box && t) { box.style.display = 'block'; t.textContent = text; }
    ta.value = '';
    ta.style.borderColor = 'var(--color-neutral-400)';
    this.show('ask-feed');
  }

  like(e) {
    const btn = e.currentTarget, id = btn.getAttribute('data-like');
    this.liked = this.liked || {};
    const span = btn.querySelector('[data-like-n]');
    const n = Number(span.textContent);
    if (this.liked[id]) { this.liked[id] = false; span.textContent = n - 1; btn.style.background = 'transparent'; btn.style.borderColor = 'var(--color-neutral-400)'; }
    else { this.liked[id] = true; span.textContent = n + 1; btn.style.background = 'var(--color-accent)'; btn.style.borderColor = 'var(--color-accent)'; }
  }

  addPoints(n) {
    this.points += n;
    const p = this.el('[data-field="points"]'), r = this.el('[data-rt-points]');
    if (p) p.textContent = this.points;
    if (r) r.textContent = this.points;
  }

  paintRating() {
    const r = this.el('[data-rt-points]');
    if (r) r.textContent = this.points;
    const sub = this.el('[data-rt-sub]');
    if (sub) sub.textContent = this.points + ' баллов · до 6 места ' + Math.max(0, 600 - this.points);
  }

  checkin() {
    if (this.checkedIn) return;
    this.checkedIn = true;
    this.addPoints(10);
    this.paintRating();
    const b = this.el('[data-checkin]');
    if (b) { b.style.background = 'transparent'; b.style.border = '1.5px solid var(--color-neutral-400)'; b.lastElementChild.textContent = 'Чек-ин засчитан сегодня · +10'; }
  }

  spend(e) {
    const cost = Number(e.currentTarget.getAttribute('data-spend'));
    const btn = e.currentTarget;
    if (this.points < cost) { btn.style.borderColor = 'var(--color-accent)'; btn.firstElementChild.textContent = 'Не хватает баллов'; return; }
    this.addPoints(-cost);
    this.paintRating();
    btn.style.background = 'var(--color-accent)';
    btn.style.borderColor = 'var(--color-accent)';
    btn.firstElementChild.textContent = 'Активировано';
    btn.lastElementChild.textContent = '✓';
  }

  paintFood() {
    const s = this.el('[data-food-sub]');
    if (s) s.textContent = 'Рядом с корпусом · ' + (this.vuz || '');
  }

  pickSupport(e) {
    this.supType = e.currentTarget.getAttribute('data-sup');
    this.all('[data-sup]').forEach(b => {
      const on = b.getAttribute('data-sup') === this.supType;
      b.style.background = on ? 'var(--color-text)' : 'transparent';
      b.style.color = on ? 'var(--color-neutral-200)' : 'var(--color-text)';
      b.style.borderColor = on ? 'var(--color-text)' : 'var(--color-neutral-400)';
    });
  }

  sendSupport() {
    const ta = this.el('[data-sup-text]');
    const text = ta && ta.value.trim();
    if (!text) { if (ta) ta.style.borderColor = 'var(--color-accent)'; return; }
    if (!this.supType) { this.all('[data-sup]')[2].click(); }
    const pool = SUPPORT[this.supType] || SUPPORT['Другой вопрос'];
    const box = this.el('[data-sup-reply]'), t = this.el('[data-sup-reply-text]');
    if (box && t) {
      box.style.display = 'block';
      box.style.animation = 'none'; void box.offsetWidth; box.style.animation = 'nvIn .36s ease both';
      t.textContent = pool[Math.floor(Math.random() * pool.length)];
    }
    ta.value = '';
    ta.style.borderColor = 'var(--color-neutral-400)';
  }

  openSheetHTML(title, html) {
    const b = this.el('[data-backdrop]'), s = this.el('[data-sheet]'), t = this.el('[data-sheet-title]'), body = this.el('[data-sheet-body]');
    if (!b || !s || !body) return;
    t.textContent = title;
    body.innerHTML = html;
    b.style.display = 'block';
    s.style.transform = 'translateY(0)';
  }

  renderVals() {
    return {
      nav: (e) => this.show(e.currentTarget.getAttribute('data-go')),
      back: () => this.back(),
      setStatus: (e) => this.setStatus(e),
      openPicker: (e) => this.openPicker(e),
      closeSheet: () => this.closeSheet(),
      verify: () => this.verify(),
      saveTest: () => this.saveTest(),
      jobs: () => this.jobs(),
      egeGo: () => this.egeGo(),
      trackVuz: () => this.trackVuz(),
      savePos: () => this.savePos(),
      askPos: () => this.askPos(),
      addDeadline: () => this.addDeadline(),
      pickTopic: (e) => this.pickTopic(e),
      sendQuestion: () => this.sendQuestion(),
      like: (e) => this.like(e),
      checkin: () => this.checkin(),
      spend: (e) => this.spend(e),
      pickSupport: (e) => this.pickSupport(e),
      sendSupport: () => this.sendSupport(),
      prevMonth: () => this.shiftMonth(-1),
      nextMonth: () => this.shiftMonth(1)
    };
  }
}

</script>


</body></html>
