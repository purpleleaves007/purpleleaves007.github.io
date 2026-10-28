const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#navigation');
menuButton?.addEventListener('click', () => {
  const expanded = menuButton.getAttribute('aria-expanded') === 'true';
  menuButton.setAttribute('aria-expanded', String(!expanded));
  navigation.classList.toggle('is-open', !expanded);
});
navigation?.addEventListener('click', event => {
  if (event.target.closest('a')) {
    menuButton?.setAttribute('aria-expanded', 'false');
    navigation.classList.remove('is-open');
  }
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && menuButton?.getAttribute('aria-expanded') === 'true') {
    menuButton.setAttribute('aria-expanded', 'false');
    navigation.classList.remove('is-open');
    menuButton.focus();
  }
});
const search = document.querySelector('#record-search');
if (search) {
  const entries = [...document.querySelectorAll('[data-record]')];
  const buttons = [...document.querySelectorAll('[data-filter]')];
  const year = document.querySelector('#year-filter');
  const grade = document.querySelector('#grade-filter');
  const paperType = document.querySelector('#format-filter');
  const counter = document.querySelector('#result-count');
  const empty = document.querySelector('#empty-state');
  let activeType = 'all';
  const normalize = value => value.normalize('NFKD').toLowerCase().replace(/[\u0300-\u036f]/g, '');
  const searchTexts = new Map(entries.map(entry => [entry, normalize(entry.textContent)]));
  const apply = () => {
    const terms = normalize(search.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    for (const entry of entries) {
      const matchesType = activeType === 'all' || entry.dataset.kind === activeType;
      const matchesYear = !year || year.value === 'all' || (year.value === 'unspecified' ? !entry.dataset.year : entry.dataset.year === year.value);
      const matchesGrade = !grade || grade.value === 'all' || entry.dataset.grade === grade.value;
      const matchesFormat = !paperType || paperType.value === 'all' || entry.dataset.paperType === paperType.value;
      const matchesQuery = terms.every(term => searchTexts.get(entry).includes(term));
      entry.hidden = !(matchesType && matchesYear && matchesGrade && matchesFormat && matchesQuery);
      if (!entry.hidden) count++;
    }
    document.querySelectorAll('[data-record-group]').forEach(group => {
      group.hidden = ![...group.querySelectorAll('[data-record]')].some(entry => !entry.hidden);
    });
    counter.textContent = `Showing ${count} of ${entries.length} entries`;
    empty.hidden = count > 0;
  };
  const reset = () => {
    search.value = '';
    activeType = 'all';
    if (year) year.value = 'all';
    if (grade) grade.value = 'all';
    if (paperType) paperType.value = 'all';
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === 'all')));
    apply();
  };
  buttons.forEach(button => button.addEventListener('click', () => {
    activeType = button.dataset.filter;
    buttons.forEach(other => other.setAttribute('aria-pressed', String(other === button)));
    apply();
  }));
  search.addEventListener('input', apply);
  year?.addEventListener('change', apply);
  grade?.addEventListener('change', apply);
  paperType?.addEventListener('change', apply);
  document.querySelector('#reset-filters')?.addEventListener('click', reset);
  document.querySelector('[data-reset]')?.addEventListener('click', () => { reset(); search.focus(); });
  const initialQuery = new URLSearchParams(location.search).get('q');
  if (initialQuery) search.value = initialQuery;
  apply();
}

// Scholar author metrics use a successful daily snapshot, never a browser scrape.
const scholarSection = document.querySelector('[data-scholar-url]');
if (scholarSection) {
  const expectedScholarId = 'mz4NUCAAAAAJ';
  const validateSnapshot = raw => {
    if (!raw || raw.scholar_id !== expectedScholarId) throw new Error('Unexpected Scholar profile');
    for (const key of ['citedby', 'hindex', 'i10index']) {
      if (!Number.isSafeInteger(raw[key]) || raw[key] < 0) throw new Error('Invalid citation metric');
    }
    let timestamp = raw.updated_at || raw.updated;
    if (typeof timestamp !== 'string') throw new Error('Missing snapshot timestamp');
    timestamp = timestamp.replace(' ', 'T').replace(/(\.\d{3})\d+/, '$1');
    if (!/(Z|[+-]\d{2}:\d{2})$/.test(timestamp)) timestamp += 'Z';
    const updated = new Date(timestamp);
    if (!Number.isFinite(updated.getTime())) throw new Error('Invalid snapshot date');
    const annual = Object.entries(raw.cites_per_year || {}).map(([year, value]) => {
      if (!/^(19|20)\d{2}$/.test(year) || !Number.isSafeInteger(value) || value < 0) {
        throw new Error('Invalid annual citation data');
      }
      return [Number(year), value];
    }).sort((a, b) => a[0] - b[0]);
    if (!annual.length) throw new Error('No annual citation data');
    return { ...raw, updated, annual };
  };
  let currentSnapshot;
  const number = new Intl.NumberFormat('en-US');
  const renderSnapshot = data => {
    currentSnapshot = data;
    document.querySelector('#scholar-total').textContent = number.format(data.citedby);
    document.querySelector('#scholar-hindex').textContent = number.format(data.hindex);
    document.querySelector('#scholar-i10index').textContent = number.format(data.i10index);
    const updatedDate = new Intl.DateTimeFormat('en-GB', {
      day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Shanghai',
    }).format(data.updated);
    document.querySelector('#scholar-sync').textContent = `Last synced ${updatedDate}`;
    const stale = Date.now() - data.updated.getTime() > 7 * 24 * 60 * 60 * 1000;
    const status = document.querySelector('#scholar-status');
    status.textContent = stale ? 'Older snapshot · check Scholar' : 'Google Scholar snapshot';
    status.classList.toggle('is-stale', stale);
    const scale = Math.max(100, Math.ceil(Math.max(...data.annual.map(([, value]) => value)) / 100) * 100);
    const ticks = scholarSection.querySelectorAll('.chart-axis span');
    [scale, scale / 2, 0].forEach((value, i) => { ticks[i].textContent = number.format(value); });
    const lastYear = data.annual.at(-1)[0];
    const thisYear = new Date().getFullYear();
    document.querySelector('#scholar-ytd').textContent = lastYear === thisYear ? `${thisYear} · year to date` : `Through ${lastYear}`;
    const bars = document.querySelector('#citation-bars');
    const description = document.querySelector('#citation-detail');
    const showYear = (year, value, button) => {
      bars.querySelectorAll('button').forEach(other => other.setAttribute('aria-pressed', String(other === button)));
      description.textContent = `${year} · ${number.format(value)} citations${year === thisYear ? ' · year to date' : ''}`;
    };
    const fragment = document.createDocumentFragment();
    data.annual.forEach(([year, value]) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `citation-column${year === thisYear ? ' is-current' : ''}`;
      button.dataset.citationYear = String(year);
      button.dataset.citationCount = String(value);
      button.setAttribute('aria-pressed', String(year === lastYear));
      button.setAttribute('aria-label', `${year}: ${number.format(value)} citations${year === thisYear ? ' (year to date)' : ''}`);
      button.style.setProperty('--value-height', `${value / scale * 100}%`);
      const label = document.createElement('span');
      label.className = 'bar-value';
      label.textContent = number.format(value);
      const bar = document.createElement('span');
      bar.className = 'citation-bar';
      bar.style.height = `${value / scale * 100}%`;
      const yearLabel = document.createElement('span');
      yearLabel.className = 'bar-year';
      yearLabel.textContent = String(year);
      button.append(label, bar, yearLabel);
      button.addEventListener('click', () => showYear(year, value, button));
      fragment.append(button);
    });
    bars.replaceChildren(fragment);
    const [year, value] = data.annual.at(-1);
    showYear(year, value, bars.lastElementChild);
  };
  try {
    renderSnapshot(validateSnapshot(JSON.parse(document.querySelector('#scholar-snapshot').textContent)));
  } catch {
    document.querySelector('#scholar-status').textContent = 'Citation data unavailable';
  }
  const refreshSnapshot = async () => {
    for (const source of [scholarSection.dataset.scholarUrl, scholarSection.dataset.scholarFallback]) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 6000);
      try {
        const response = await fetch(source, { signal: controller.signal, cache: 'no-cache', credentials: 'omit' });
        if (!response.ok) throw new Error('Snapshot is unavailable');
        const incoming = validateSnapshot(await response.json());
        // Never replace a newer successful local snapshot with an older remote cache.
        if (!currentSnapshot || incoming.updated > currentSnapshot.updated) renderSnapshot(incoming);
        return;
      } catch {
        // Keep the last successful snapshot visible, with its actual date.
      } finally {
        clearTimeout(timeout);
      }
    }
  };
  refreshSnapshot();
}

// Annual journal metadata is fetched once by GitHub; visitors read the cached JSON.
const journalTags = [...document.querySelectorAll('[data-journal-key]')];
if (journalTags.length) {
  const journalMetrics = new Map();
  const acceptJournalSnapshot = snapshot => {
    if (!snapshot || typeof snapshot.journals !== 'object') return;
    for (const [key, raw] of Object.entries(snapshot.journals)) {
      if (!raw || !Number.isFinite(raw.jif) || raw.jif < 0 || raw.jif >= 1000) continue;
      if (!Number.isInteger(raw.metric_year) || raw.metric_year < 2000 || raw.metric_year > new Date().getFullYear() - 1) continue;
      const old = journalMetrics.get(key);
      if (old && old.metric_year > raw.metric_year) continue;
      journalMetrics.set(key, raw);
    }
    for (const element of journalTags) {
      const metric = journalMetrics.get(element.dataset.journalKey);
      if (!metric) continue;
      let value = element.querySelector('[data-jif-value]');
      if (!value) {
        value = document.createElement('span');
        value.className = 'tag tag-neutral';
        value.dataset.jifValue = '';
        element.append(value);
      }
      value.textContent = `IF ${metric.jif.toFixed(1)} · ${metric.metric_year}`;
      let quartile = element.querySelector('[data-jif-quartile]');
      if (!quartile) {
        quartile = document.createElement('span');
        quartile.className = 'tag tag-neutral';
        quartile.dataset.jifQuartile = '';
        element.append(quartile);
      }
      quartile.hidden = !/^Q[1-4]$/.test(metric.quartile || '');
      quartile.textContent = quartile.hidden ? '' : metric.quartile;
    }
  };
  try {
    acceptJournalSnapshot(JSON.parse(document.querySelector('#journal-metrics-snapshot').textContent));
  } catch {
    // Static year-labelled values remain available without a network connection.
  }
  (async () => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);
    try {
      const response = await fetch('https://raw.githubusercontent.com/purpleleaves007/purpleleaves007.github.io/google-scholar-stats/journal_metrics.json', {
        signal: controller.signal, cache: 'no-cache', credentials: 'omit',
      });
      if (response.ok) acceptJournalSnapshot(await response.json());
    } catch {
      // Keep the previous verified year and value on publisher or network failure.
    } finally {
      clearTimeout(timeout);
    }
  })();
}
