// Deterministic UI regression checks. Uses the real application source with a
// small DOM/history/media double; browser rendering remains a separate check.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const outputDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(outputDir, '../..');
const source = fs.readFileSync(path.join(root, 'web/app.js'), 'utf8');
const html = fs.readFileSync(path.join(root, 'web/index.html'), 'utf8');
const startupMarker = 'async function init(){';
assert.equal(source.split(startupMarker).length, 2, 'Application startup marker must remain unique');
const exercisedSource = source.split(startupMarker)[0];
const pages = [...html.matchAll(/<section id="([^"]+)" class="tab-panel(?: hidden)?">/g)].map(m => m[1]);
assert.equal(pages.length, 8);

function browser(hash = '#learning', code = exercisedSource) {
  const nodes = new Map(), listeners = new Map(), pending = [], events = [];
  const historyEntries = [hash];
  let historyIndex = 0;
  const context = {console, Promise, Number, Object};
  function node(id) {
    if (nodes.has(id)) return nodes.get(id);
    const classes = new Set(), attributes = new Map();
    const el = {
      id, value: 'Thank you', checked: true, textContent: '', style: {}, dataset: {},
      firstChild: {textContent: ''}, paused: true, playCalls: 0, pauseCalls: 0,
      classList: {
        toggle(name, force) { const add = force === undefined ? !classes.has(name) : force; add ? classes.add(name) : classes.delete(name); return add; },
        contains(name) { return classes.has(name); },
      },
      setAttribute(name, value) { attributes.set(name, value); },
      removeAttribute(name) { attributes.delete(name); if (name === 'src') delete this.src; },
      getAttribute(name) { return attributes.get(name); },
      addEventListener() {},
      querySelector(selector) { return node(`${id} ${selector}`); },
      focus() { context.document.activeElement = this; },
      scrollIntoView(options) { this.scrolled = options; },
      pause() { this.paused = true; this.pauseCalls++; },
      load() {},
      play() { this.paused = false; this.playCalls++; return Promise.resolve(); },
      closest(selector) { assert.equal(selector, '.tab-panel'); return node(this.panelId); },
    };
    nodes.set(id, el);
    return el;
  }
  const panels = pages.map(id => node(id));
  const tabs = pages.map(id => { const tab = node(`tab-${id}`); tab.dataset.tab = id; return tab; });
  const videos = [['video', 'demo'], ['inspect-video', 'inspection'], ['resource-video', 'resources']].map(([id, panelId]) => { const video = node(id); video.panelId = panelId; return video; });
  context.document = {
    activeElement: null,
    getElementById: node,
    querySelector(selector) { assert.equal(selector, '.skip-link'); return node('skip-link'); },
    querySelectorAll(selector) {
      if (selector === '.tab') return tabs;
      if (selector === '.tab-panel') return panels;
      if (selector === 'video') return videos;
      if (selector === '.method' || selector === '[data-example]') return [];
      throw new Error(`Unmodelled selector: ${selector}`);
    },
  };
  context.location = {hash};
  context.CustomEvent = class { constructor(type, options) { this.type = type; this.detail = options.detail; } };
  context.window = {
    addEventListener(type, callback) { if (!listeners.has(type)) listeners.set(type, []); listeners.get(type).push(callback); },
    dispatchEvent(event) { events.push({type: event.type, detail: event.detail}); for (const callback of listeners.get(event.type) || []) callback(event); },
    scrollTo(options) { context.window.lastScroll = options; },
  };
  context.history = {
    pushState(_state, _title, nextHash) { historyEntries.splice(historyIndex + 1); historyEntries.push(nextHash); historyIndex++; context.location.hash = nextHash; },
    back() {
      if (historyIndex === 0) return;
      historyIndex--; context.location.hash = historyEntries[historyIndex];
      context.window.dispatchEvent({type: 'popstate'});
      context.window.dispatchEvent({type: 'hashchange'});
    },
  };
  context.fetch = (endpoint, options) => new Promise(resolve => pending.push({endpoint, options, resolve}));
  vm.createContext(context);
  vm.runInContext(code, context, {filename: 'web/app.js [before network startup]'});
  function selected(expected) {
    assert.deepEqual(panels.filter(p => !p.classList.contains('hidden')).map(p => p.id), [expected]);
    assert.deepEqual(tabs.filter(t => t.classList.contains('active')).map(t => t.dataset.tab), [expected]);
    assert.deepEqual(tabs.filter(t => t.getAttribute('aria-current') === 'page').map(t => t.dataset.tab), [expected]);
  }
  return {context, node, pending, events, selected, historyEntries,
    run: expression => vm.runInContext(expression, context),
    navigate: id => context.window.navigateProject(id)};
}

const checks = [];
async function check(name, execute) { const details = await execute(); checks.push({name, passed: true, ...(details || {})}); }
const result = {selection: {action_id: 'THANK_YOU', status: 'execute', latency_ms: 20}, execution: {state: 'ready', preview_url: '/media/THANK_YOU.mp4'}};
function resolveResult(b, value = result) { assert.equal(b.pending.length, 1); b.pending.shift().resolve({ok: true, json: async () => value}); }

await check('main_target_supports_programmatic_focus', () => {
  assert.match(html, /<main\b[^>]*\bid="main-content"[^>]*\btabindex="-1"/);
});
await check('initial_learning_deep_link_selects_one_panel', () => {
  const b = browser(); b.selected('learning'); assert.equal(b.context.location.hash, '#learning');
  assert.equal(b.historyEntries.length, 1); return {visible_panel: 'learning'};
});
await check('skip_link_preserves_page_and_focuses_main', () => {
  const b = browser(); let prevented = false;
  b.node('skip-link').onclick({preventDefault() { prevented = true; }});
  assert.equal(prevented, true); b.selected('learning'); assert.equal(b.context.location.hash, '#learning');
  assert.equal(b.context.document.activeElement.id, 'main-content');
  assert.equal(b.node('main-content').scrolled.block, 'start'); assert.equal(b.historyEntries.length, 1);
  return {hash: b.context.location.hash, focused_element: 'main-content'};
});
await check('all_eight_routes_have_exactly_one_visible_active_panel', () => {
  const b = browser();
  for (const id of pages) { b.navigate(id); b.selected(id); assert.equal(b.context.location.hash, `#${id}`); }
  return {routes: pages};
});
await check('back_restores_previous_panel_without_new_history', () => {
  const b = browser(); b.navigate('inspection'); b.navigate('resources');
  b.context.history.back(); b.selected('inspection');
  b.context.history.back(); b.selected('learning'); assert.equal(b.historyEntries.length, 3);
  return {history: b.historyEntries, restored_panel: 'learning'};
});
await check('direct_hash_event_selects_page_without_pushing_history', () => {
  const b = browser(); b.context.location.hash = '#team'; b.context.window.dispatchEvent({type: 'hashchange'});
  b.selected('team'); assert.equal(b.historyEntries.length, 1);
});
await check('unknown_route_falls_back_to_overview', () => { const b = browser('#unknown'); b.selected('overview'); });
await check('navigation_pauses_every_off_page_video', () => {
  const b = browser('#demo');
  for (const id of ['video', 'inspect-video', 'resource-video']) b.node(id).paused = false;
  b.navigate('resources'); assert.equal(b.node('video').paused, true); assert.equal(b.node('inspect-video').paused, true);
  assert.equal(b.node('resource-video').paused, false);
});
await check('delayed_selection_does_not_play_after_leaving_demo', async () => {
  const b = browser('#demo'); const request = b.run("submit('/api/select',{text:'Thank you',method:'embedding'})");
  b.navigate('resources'); resolveResult(b); await request;
  b.selected('resources'); assert.equal(b.node('video').paused, true); assert.equal(b.node('video').playCalls, 0);
  assert.equal(b.node('video').src, result.execution.preview_url);
  b.navigate('demo'); b.selected('demo'); assert.equal(b.node('video').paused, true);
  return {response_saved: true, hidden_video_paused: true, returning_to_demo_autoplays: false};
});
await check('selection_still_plays_when_demo_remains_visible', async () => {
  const b = browser('#demo'); const request = b.run("submit('/api/select',{text:'Thank you',method:'exact'})");
  resolveResult(b); await request;
  assert.equal(b.node('video').paused, false); assert.equal(b.node('video').playCalls, 1);
});
await check('rejected_input_clears_previous_media_source', async () => {
  const b = browser('#demo'); b.node('video').src = '/media/HELLO.mp4';
  const request = b.run("submit('/api/select',{text:'unsupported input',method:'exact'})");
  resolveResult(b, {selection: {status: 'unsupported', reason_code: 'unsupported', latency_ms: 1}, execution: {state: 'not_executed'}});
  await request; assert.equal(b.node('video').src, undefined); assert.equal(b.node('video').paused, true);
});
await check('negative_control_detects_original_hidden_playback_bug', async () => {
  const regression = exercisedSource.replace("if(!$('demo').classList.contains('hidden'))video.play()", 'video.play()');
  assert.notEqual(regression, exercisedSource);
  const b = browser('#demo', regression); const request = b.run("submit('/api/select',{text:'Thank you',method:'embedding'})");
  b.navigate('resources'); resolveResult(b); await request;
  assert.equal(b.node('video').paused, false); assert.equal(b.node('video').playCalls, 1);
  return {mutated_only_in_memory: true, original_failure_reproduced: true};
});

const report = {
  schema_version: 1,
  created_utc: new Date().toISOString(),
  method: 'Real app.js navigation and response handlers evaluated in Node VM with deterministic DOM, history, fetch and media doubles.',
  source_sha256: Object.fromEntries([['web/app.js', source], ['web/index.html', html]].map(([name, text]) => [name, crypto.createHash('sha256').update(text).digest('hex')])),
  tests: checks.length, failures: 0, checks,
  limitations: ['No real browser layout, media decoding, native focus behaviour or network tested here.', 'History event ordering is explicitly simulated; actual browser navigation is validated separately.', 'Only app.js before asynchronous startup is evaluated. Model, inference, inspection charts and frozen results are unchanged.'],
};
fs.writeFileSync(path.join(outputDir, 'navigation-regression.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({tests: report.tests, failures: report.failures, report: path.relative(root, path.join(outputDir, 'navigation-regression.json'))}));
