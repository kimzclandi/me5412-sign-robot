'use strict';
(() => {
  const el = id => document.getElementById(id);
  let data = null, frame = 0, playing = false, origin = 0, busy = false, animation = null;
  const reasons = {no_exact_alias: '输入未在三类完整短语中登记。新文字不能自动变成已学会的新手语。',
    negated_or_declining: '这句话包含否定或拒绝含义，未生成动作。',
    multiple_or_compound_intents: '这句话包含额外含义，未生成部分动作。',
    clinical_content_out_of_scope: '当前模型没有学习这些医疗表达。'};
  function pause() { playing = false; if (animation !== null) cancelAnimationFrame(animation); animation = null; el('learn-play').textContent = '播放生成轨迹'; }
  function clear() { pause(); data = null; el('learn-result').classList.add('hidden'); }
  function canvas(id, height) {
    const node = el(id), ratio = window.devicePixelRatio || 1;
    const width = Math.max(240, node.clientWidth);
    node.width = Math.round(width * ratio); node.height = Math.round(height * ratio);
    const ctx = node.getContext('2d'); ctx.scale(ratio, ratio);
    ctx.clearRect(0, 0, width, height); return {ctx, width, height};
  }
  function pose() {
    if (!data) return;
    const {ctx, width, height} = canvas('learn-pose', 340);
    const points = data.kinematics.positions_m[frame], names = data.kinematics.body_names;
    ctx.fillStyle = '#edf4f4'; ctx.fillRect(0, 0, width, height);
    for (let view = 0; view < 2; view++) {
      const bounds = data._bounds[view], half = width / 2;
      const scale = Math.min((half - 34) / (bounds.maxx - bounds.minx), (height - 65) / (bounds.maxz - bounds.minz));
      const project = p => [half * (view + 0.5) + ((view ? p[0] : -p[1]) - (bounds.minx + bounds.maxx) / 2) * scale,
        42 + (bounds.maxz - p[2]) * scale];
      ctx.fillStyle = '#536b75'; ctx.font = '12px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText(window.ProjectI18n.t(view ? '右侧 · 前后位移' : '正面 · 左右位移'), half * (view + .5), 23);
      for (const [a, b] of data.kinematics.edges) {
        const p = project(points[a]), q = project(points[b]);
        ctx.strokeStyle = /^(right|R_)/.test(names[b]) ? '#087f83' : /^(left|L_)/.test(names[b]) ? '#4878a5' : '#95aab0';
        ctx.lineWidth = /thumb|index|middle|ring|pinky/.test(names[b]) ? 2 : 5;
        ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(...p); ctx.lineTo(...q); ctx.stroke();
      }
      for (const p of points) { const q = project(p); ctx.beginPath(); ctx.arc(...q, 2.5, 0, Math.PI * 2); ctx.fillStyle = '#173c46'; ctx.fill(); }
    }
    ctx.strokeStyle = '#cbdede'; ctx.beginPath(); ctx.moveTo(width / 2, 36); ctx.lineTo(width / 2, height - 20); ctx.stroke();
  }
  function chart() {
    if (!data) return;
    const {ctx, width, height} = canvas('learn-chart', 190);
    const j = Number(el('learn-joint').value), values = data.positions_rad.map(row => row[j]);
    const low = Math.min(...values) - .08, high = Math.max(...values) + .08;
    const x = t => 48 + t / data.duration_s * (width - 65), y = q => 22 + (high - q) / (high - low) * (height - 55);
    ctx.strokeStyle = '#dce5e6'; ctx.font = '11px sans-serif'; ctx.fillStyle = '#647980'; ctx.textAlign = 'right';
    for (let k = 0; k < 3; k++) { const q = low + (high - low) * k / 2; ctx.beginPath(); ctx.moveTo(48, y(q)); ctx.lineTo(width - 17, y(q)); ctx.stroke(); ctx.fillText(q.toFixed(2), 41, y(q) + 4); }
    ctx.fillText('rad', 41, 13); ctx.textAlign = 'left'; ctx.fillText('0 s', 48, height - 8); ctx.textAlign = 'right'; ctx.fillText(`${data.duration_s.toFixed(2)} s`, width - 17, height - 8);
    ctx.strokeStyle = '#087f83'; ctx.lineWidth = 2; ctx.beginPath(); values.forEach((q, i) => i ? ctx.lineTo(x(data.timestamps_s[i]), y(q)) : ctx.moveTo(x(data.timestamps_s[i]), y(q))); ctx.stroke();
    ctx.strokeStyle = '#b37a2b'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x(data.timestamps_s[frame]), 18); ctx.lineTo(x(data.timestamps_s[frame]), height - 29); ctx.stroke();
  }
  function draw() { if (!data) return; el('learn-frame').value = frame; el('learn-time').textContent = `${data.timestamps_s[frame].toFixed(2)} s · ${frame + 1} / ${data.timestamps_s.length} 帧`; pose(); chart(); }
  function tick(now) {
    if (!playing || !data) return;
    const time = (now - origin) / 1000;
    while (frame + 1 < data.timestamps_s.length && data.timestamps_s[frame + 1] <= time) frame++;
    draw(); if (time >= data.duration_s) pause(); else animation = requestAnimationFrame(tick);
  }
  function show(result) {
    if (!result.accepted || !result.kinematics) {
      el('learn-status').textContent = reasons[result.reason_code] || `本次未生成可播放候选：${result.reason_code || (result.rejection_reasons || []).join('，') || result.status}`;
      return;
    }
    data = result; frame = 0;
    data._bounds = [0, 1].map(view => {
      const all = data.kinematics.positions_m.flat();
      const xs = all.map(p => view ? p[0] : -p[1]), zs = all.map(p => p[2]);
      return {minx: Math.min(...xs) - .04, maxx: Math.max(...xs) + .04, minz: Math.min(...zs) - .025, maxz: Math.max(...zs) + .025};
    });
    el('learn-result').classList.remove('hidden'); el('learn-frame').max = data.timestamps_s.length - 1;
    el('learn-identity').textContent = `“${data.conditioning_text}” · ${data.duration_s.toFixed(2)} s`;
    el('learn-status').textContent = `本次生成 ${data.timestamps_s.length} 帧 × ${data.joint_names.length} 个关节坐标，工程阈值检查通过。ASL 语义与可理解性仍未验证。`;
    const select = el('learn-joint'); select.replaceChildren();
    data.joint_names.forEach((name, i) => { if (/^(right_|left_|R_|L_)/.test(name) && !/hip|knee|ankle/.test(name)) { const option = document.createElement('option'); option.value = i; option.textContent = name; select.append(option); }});
    select.value = data.joint_names.indexOf('right_elbow_joint');
    const m = data.metrics;
    el('learn-metrics').textContent = `限位误差 ${m.joint_limit_violation_rad.toFixed(6)} rad · 耦合误差 ${m.max_mimic_error_rad.toFixed(6)} rad · 超过 1 mm 的接触穿透 ${m.penetrating_contact_events_below_minus_1mm} 次。检测到的最大穿透 ${(m.maximum_reported_penetration_m * 1000).toFixed(3)} mm；最大角度限位修正 ${m.max_projection_rad.toFixed(6)} rad。`;
    const {positions_rad, timestamps_s, joint_names, kinematics, _bounds, ...summary} = data;
    el('learn-details').textContent = JSON.stringify(summary, null, 2); draw();
  }
  el('learn-generate').onclick = async () => {
    if (busy) return; busy = true; clear();
    const controls = [el('learn-generate'), el('learn-text'), el('learn-duration'), ...document.querySelectorAll('[data-learn-example]')]; controls.forEach(c => c.disabled = true);
    el('learn-status').textContent = '正在运行本地模型并逐帧检查…首次请求包含文字模型加载时间。';
    try {
      const response = await fetch('/api/learning/generate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: el('learn-text').value, duration_scale: Number(el('learn-duration').value)})});
      const result = await response.json(); if (!response.ok) throw new Error(result.message || result.error); show(result);
    } catch (e) { el('learn-status').textContent = `生成未完成：${e.message}`; }
    finally { busy = false; controls.forEach(c => c.disabled = false); }
  };
  el('learn-text').oninput = el('learn-duration').onchange = () => { clear(); el('learn-status').textContent = '输入已更改，请重新生成。'; };
  document.querySelectorAll('[data-learn-example]').forEach(button => button.onclick = () => { el('learn-text').value = button.dataset.learnExample; el('learn-text').oninput(); });
  el('learn-frame').oninput = () => { pause(); frame = Number(el('learn-frame').value); draw(); };
  el('learn-joint').onchange = chart;
  el('learn-play').onclick = () => { if (!data) return; if (playing) return pause(); if (frame === data.timestamps_s.length - 1) frame = 0; playing = true; origin = performance.now() - data.timestamps_s[frame] * 1000; el('learn-play').textContent = '暂停'; animation = requestAnimationFrame(tick); };
  el('learn-download').onclick = () => { if (!data) return; const {_bounds, ...output} = data; const url = URL.createObjectURL(new Blob([JSON.stringify(output)], {type: 'application/json'})); const a = document.createElement('a'); a.href = url; a.download = `learned-${data.action_id}-${data.duration_s}s.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); };
  window.addEventListener('project:tabchange', event => { if (event.detail.id !== 'learning') pause(); else requestAnimationFrame(draw); });
  window.addEventListener('resize', draw);
  window.addEventListener('project:languagechange', draw);
  fetch('/api/learning').then(r => { if (!r.ok) throw new Error('模型实验不可用'); return r.json(); }).then(s => {
    el('learn-corpus').textContent = s.corpus.annotation_rows.toLocaleString();
    if (!busy && !data) el('learn-status').textContent = s.accepted && s.checkpoint_hash_verified ? 'v1 模型已完成训练，权重校验通过。选择一句英文，运行一次真实推理。' : '模型实验未通过或权重校验不一致。';
  }).catch(e => { if (!busy && !data) el('learn-status').textContent = e.message; });
})();

