// Read-only local observations, never a model safety score.
import { drivingMetrics, milesText, trackingStatus } from '../tools/model_metrics.js';

export function topModelRows(models, mode = 'interventions', history = null, limit = 3) {
  if (mode === 'distance' && Array.isArray(history)) {
    return history.filter(m => typeof m?.key === 'string' && Number.isFinite(m.distanceMeters) && m.distanceMeters > 0)
      .slice().sort((a, b) => b.distanceMeters - a.distanceMeters || a.key.localeCompare(b.key))
      .slice(0, limit).map(m => ({id: m.key, name: m.name || m.key,
        total: `Recorded drive distance: ${milesText(m.distanceMeters)}`}));
  }
  if (mode === 'distance') {
    return (Array.isArray(models) ? models : []).filter(m => m?.stats?.available === true
      && Number.isFinite(m.stats.assistedMeters) && m.stats.assistedMeters > 0)
      .sort((a, b) => b.stats.assistedMeters - a.stats.assistedMeters || String(a.value).localeCompare(String(b.value)))
      .slice(0, limit).map(m => ({ id: m.value, name: m.label || m.value,
        total: `Total recorded assisted: ${milesText(m.stats.assistedMeters)}`, status: trackingStatus(m) }));
  }
  const key = mode === 'disengagements' ? 'disengagements' : 'interventions';
  const exposureKey = key === 'interventions' ? 'interventionMeters' : 'disengagementMeters';
  return (Array.isArray(models) ? models : []).filter(m => {
    const s = m?.stats;
    return s?.available === true && s.eventRatesComparable !== false && s.definitionStatus !== 'historical' && typeof s[exposureKey] === 'number' && Number.isFinite(s[exposureKey])
      && s[exposureKey] > 0 && Number.isSafeInteger(s[key]) && s[key] >= 0;
  }).map(m => ({
    id: m.value, name: m.label || m.value, events: m.stats[key], exposure: m.stats[exposureKey],
    ratio: m.stats[key] > 0 ? m.stats[exposureKey] / m.stats[key] : null,
    metric: drivingMetrics(m)[key === 'interventions' ? 1 : 2].value,
    sample: `Recorded sample: ${milesText(m.stats[exposureKey])}`,
    // Use only this catalogue identity's all-time assisted distance, not the
    // selected event's eligible exposure or a sum across names/revisions/pairs.
    total: `Total recorded assisted: ${milesText(m.stats.assistedMeters)}`,
    status: trackingStatus(m),
  })).sort((a, b) => {
    if (a.ratio === null || b.ratio === null) return a.ratio === b.ratio ? b.exposure - a.exposure : a.ratio === null ? 1 : -1;
    return b.ratio - a.ratio || b.exposure - a.exposure || String(a.id).localeCompare(String(b.id));
  }).slice(0, limit);
}

export class TopModels extends HTMLElement {
  static get observedAttributes() { return ['history-rows']; }
  attributeChangedCallback() { this.renderRows?.(); }
  connectedCallback() {
    this.selectApp?.unmount();
    this.style.display = 'block';
    this.style.padding = '0 0 12px';
    const generation = this.generation = (this.generation || 0) + 1;
    this.replaceChildren();
    const label = document.createElement('label');
    label.textContent = 'Sort By: ';
    const select = document.createElement('select');
    select.style.cssText = 'font:inherit;color:inherit;background:transparent;max-width:100%;padding:6px;border:1px solid currentColor;border-radius:8px';
    const distanceDefault = this.getAttribute('default-mode') === 'distance';
    const choices = [['interventions', 'Miles / intervention'], ['disengagements', 'Miles / disengagement']];
    if (distanceDefault) choices.unshift(['distance', 'Miles driven']);
    for (const [value, text] of choices) {
      const option = document.createElement('option'); option.value = value; option.textContent = text; select.append(option);
    }
    label.append(select); this.append(label);
    const note = document.createElement('p');
    note.style.cssText = 'font-size:0.8em;opacity:0.75;line-height:1.5';
    note.textContent = 'Highest recorded miles per event, not a safety ranking. Different routes, settings and sample sizes are not controlled. No-event samples follow measured averages; they are not infinite scores. Local tracked data only; paired runs may overlap. Event rankings use the current measurement definition; mixed, unknown and historical definitions are excluded.';
    this.append(note);
    const list = document.createElement('div'); list.className = 'top-models__list';
    if (this.hasAttribute('all-rows')) { list.tabIndex = 0; list.setAttribute('role', 'region'); list.setAttribute('aria-label', 'Ranked models'); }
    this.append(list);
    const render = () => {
      list.replaceChildren();
      note.hidden = select.value === 'distance';
      let history = null;
      if (this.hasAttribute('history-rows')) {
        try { history = JSON.parse(this.getAttribute('history-rows')); } catch { history = []; }
        if (!Array.isArray(history)) history = [];
      }
      const rows = topModelRows(this.models, select.value, history, this.hasAttribute('all-rows') ? Infinity : 3);
      if (!rows.length) { list.textContent = this.error || 'No recorded exposure for this metric yet.'; return; }
      for (const row of rows) {
        const article = document.createElement('article');
        article.style.cssText = 'padding:12px 0;border-top:1px solid currentColor;overflow-wrap:anywhere';
        const title = document.createElement('strong'); title.textContent = row.name; article.append(title);
        for (const text of [row.total, row.metric, row.sample, row.status].filter(Boolean)) {
          const line = document.createElement('div'); line.style.cssText = 'font-size:0.85em;margin-top:4px'; line.textContent = text; article.append(line);
        }
        list.append(article);
      }
    };
    this.renderRows = render;
    select.onchange = render;
    // New Galaxy owns its styled menu; Classic retains its native control.
    const vue = window.__galaxyVue;
    if (vue?.GalaxySelect && this.closest('#galaxy-app')) {
      const host = document.createElement('span');
      label.replaceChild(host, select);
      this.selectApp = vue.createApp({ render: () => vue.h(vue.GalaxySelect, {
        class: 'gx-field', 'aria-label': 'Sort By',
        onChange: event => { select.value = event.target.value; render(); },
      }, () => choices.map(([value, text]) => vue.h('option', { value }, text))) });
      this.selectApp.mount(host);
    }
    list.textContent = 'Loading recorded model statistics…';
    if (this.hasAttribute('history-rows')) render();
    this.controller = new AbortController();
    this.timeout = setTimeout(() => this.controller.abort(), 10000);
    fetch('/api/models/status', {cache: 'no-store', signal: this.controller.signal})
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => { if (generation !== this.generation || !this.isConnected) return; if (!Array.isArray(data.models)) throw new Error('Invalid model statistics'); this.models = data.models; this.error = ''; render(); })
      .catch(() => { if (generation !== this.generation || !this.isConnected) return; this.models = []; this.error = 'Recorded model statistics unavailable.'; render(); })
      .finally(() => { if (generation === this.generation) clearTimeout(this.timeout); });
  }
  disconnectedCallback() { this.selectApp?.unmount(); this.selectApp = null; this.renderRows = null; ++this.generation; clearTimeout(this.timeout); this.controller?.abort(); }
}
if (!customElements.get('top-models')) customElements.define('top-models', TopModels);
