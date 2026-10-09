'use strict';
(() => {
  const el = id => document.getElementById(id);
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
  const number = value => Number(value).toLocaleString('en-US');
  let project = null, flow = 'baseline', selectedNode = 0, evalGroup = 'supported', selectedStage = 0, selectedRole = 'A1', materialCategory = '全部';
  const flows = {
    baseline: [
      ['英文或短语', '完整含义作为请求', '共同入口', '输入一句英文，或选择已登记的短语。当前目录只有三个候选表达。', '英文 / 短语按钮', '一条完整请求', '1 · 6', 'demo'],
      ['检查与选择', '规则 + 文字理解', '先确认表达范围', '固定别名、MiniLM 或研究 LLM 选择合法 ID；否定、混合与库外内容可能被拒绝。', '输入文字', '候选 ID / 明确拒绝', '1 · 2', 'demo'],
      ['已有动作库', '3 条自编轨迹', '按编号载入已编写动作', '人工关键位姿经有界 IK 和插值形成动作。选择结果并不代表 ASL 含义已通过核验。', 'HELLO 等候选 ID', '时间戳 + 53 个坐标', '3 · 4', 'inspection'],
      ['候选预览', 'MuJoCo 离线渲染', '明确查看研究候选', '允许研究预览后播放预先生成的视频。视频来自运动学轨迹，不是执行器动力学仿真。', '已保存的关节轨迹', '正面 / 侧面视频', '3 · 6', 'inspection'],
      ['分层评价', '文字 / 几何 / 含义', '每一层有自己的判断', '文本选择与几何检查已有记录；机器人手语能否被理解仍需独立使用者评价。', '选择记录与动作', '指标 / 失败 / 未验证项', '5', 'evidence']
    ],
    learned: [
      ['文字与相位', 'MiniLM + 时间进度', '编码文字与动作进度', '先检查输入属于登记含义，再编码实际文字。相位 u = t / T 表示动作从开始到结束的进度。', '英文 + 时间相位 u', '384 维向量 + 40 相位基', '4', 'learning'],
      ['训练后权重', '一次 RBF 岭回归', '从三个自编示范拟合', '训练使用 367 帧，验证使用同轨迹 365 帧。本次训练的回归权重直接参与角度计算。', '文字与相位特征', '26 个主动上肢角度', '4', 'learning'],
      ['重建与检查', '限位 + 从动关系', '生成机器人的完整坐标', '其余 15 坐标保持准备姿势，12 个从动坐标按 mimic 公式重建。检查速度和现有碰撞几何。', '26 个主动角', '53 坐标 + 检查指标', '3 · 5', 'learning'],
      ['模型输出样例', '骨架 / 曲线 / JSON', '查看已保存的模型输出', '本地实验台支持实际推理和骨架检查；此分享版提供已保存模型输出的正面与侧面视频。', '本次预测的角度序列', '运动学骨架与关节曲线', '6', 'learning'],
      ['独立验证', '下一阶段的关键', '拟合之外还需要新证据', '延长时间与同轨迹低误差不等于新手语泛化。下一步需要独立动作监督和可理解性评价。', '新动作 / 独立评审', '泛化与含义复述记录', '3 · 5', 'data']
    ]
  };
  function jump(id) { window.navigateProject(id); }
  document.querySelectorAll('[data-jump]').forEach(button => button.addEventListener('click', () => jump(button.dataset.jump)));
  function renderFlow() {
    const list = el('flow-nodes'); list.replaceChildren();
    flows[flow].forEach((item, i) => {
      const button = node('button', undefined, `flow-node${i === selectedNode ? ' active' : ''}`); button.setAttribute('aria-pressed', String(i === selectedNode));
      button.append(node('span', `0${i + 1}`, 'node-number'), node('strong', item[0]), node('small', item[1]));
      button.onclick = () => { selectedNode = i; renderFlow(); }; list.append(button);
    });
    const item = flows[flow][selectedNode], detail = el('flow-detail'); detail.replaceChildren();
    const title = node('div'); title.append(node('h3', item[2]), node('p', item[3])); detail.append(title);
    [['输入', item[4]], ['输出', item[5]]].forEach(([label, text]) => { const dl = node('dl'); dl.append(node('dt', label), node('dd', text)); detail.append(dl); });
    const button = node('button', `${item[6]} 负责模块\n打开相关页面 →`, 'text-button'); button.onclick = () => jump(item[7]); detail.append(button);
    document.querySelectorAll('[data-flow]').forEach(b => { b.classList.toggle('selected', b.dataset.flow === flow); b.setAttribute('aria-pressed', String(b.dataset.flow === flow)); });
  }
  document.querySelectorAll('[data-flow]').forEach(button => button.onclick = () => { flow = button.dataset.flow; selectedNode = 0; renderFlow(); });
  const stages = [
    ['英文文本索引', '已接入', '文本已经可索引', '记录包含英文、源句子 ID 与起止时间。每行是标注记录，不等于一个独立手语词或可执行动作。', '1 / 3：核对来源、许可和完整含义，保留原始 train / val / test 划分。'],
    ['视频与人体姿态', '尚未接入', '需要真实的人体动作监督', '本轮没有下载实例视频或提取人体姿态；只有视频 ID 不能充当关节坐标。', '1 / 3：先选少量可使用的示范，记录视频、时间段、手部可见性和姿态质量。'],
    ['机器人配对轨迹', '尚未接入', '人体动作需要适配机器人', '人体比例、手指结构和可动关节不同。需要动作重定向、手型校准及逐帧约束检查。', '3：输出有来源的新版本机器人轨迹，检查限位、耦合、掌向、接触与缺失的表情。'],
    ['独立动作训练集', '待上游配对', '建立新示范上的训练与测试', '同一条视频或动作的相邻帧不能同时充当独立泛化证据。先定义数据划分，再训练新版本。', '4 / 5：冻结 v2 协议，按独立示范划分，保留所有失败并单独报告语言评价。']
  ];
  function renderStages() {
    el('data-stages').replaceChildren();
    stages.forEach((item, i) => {
      const button = node('button', undefined, `data-stage${i === 0 ? ' available' : ''}${i === selectedStage ? ' selected' : ''}`);
      button.setAttribute('aria-pressed', String(i === selectedStage)); button.append(node('span', item[0], 'stage-title'), node('strong', i === 0 ? number(project.corpus.metadata_rows) : '0'), node('small', item[1]));
      button.onclick = () => { selectedStage = i; renderStages(); }; el('data-stages').append(button);
    });
    const item = stages[selectedStage], first = node('div'), second = node('div'); first.append(node('h3', item[2]), node('p', item[3])); second.append(node('span', '下一份可验收交付'), node('p', item[4])); el('data-stage-detail').replaceChildren(first, second);
  }
  const colors = {correct_selection:'#558971',correct_rejection:'#558971',wrong_rejection:'#c6aa70',wrong_action_id:'#b76554',false_execution:'#b76554',error:'#6e7e92'};
  const statusNames = {correct_selection:'选对',correct_rejection:'正确拒绝',wrong_rejection:'误拒',wrong_action_id:'错误 ID',false_execution:'错误执行',error:'非法输出 / 错误'};
  function renderEvaluation() {
    const keys = evalGroup === 'supported' ? ['correct_selection','wrong_rejection','wrong_action_id','error'] : ['correct_rejection','false_execution','error'];
    const denominator = evalGroup === 'supported' ? project.evaluation.supported_cases : project.evaluation.out_of_scope_cases;
    const legend = el('comparison-legend'); legend.replaceChildren(); keys.forEach(key => { const label = node('span'), dot = node('i'); dot.style.background = colors[key]; label.append(dot, node('span', statusNames[key])); legend.append(label); });
    el('comparison-caption').textContent = `${evalGroup === 'supported' ? '支持输入' : '库外输入'} ${denominator} 条 · 同一批冻结样例、同一组公共规则`;
    const rows = el('comparison-bars'); rows.replaceChildren();
    for (const method of project.evaluation.methods) {
      const row = node('article', undefined, 'comparison-row'), label = node('div', undefined, 'comparison-label'); label.append(node('strong', method.label), node('span', `${method.accuracy.numerator} / ${method.accuracy.denominator} 总体正确`)); row.append(label);
      const track = node('div', undefined, 'comparison-track'); track.setAttribute('aria-hidden','true');
      const description = [];
      keys.forEach(key => { const count = method[evalGroup][key]; description.push(`${statusNames[key]} ${count}`); if (count > 0) { const segment = node('span', String(count)); segment.style.width = `${count / denominator * 100}%`; segment.style.background = colors[key]; segment.title = `${statusNames[key]} ${count} / ${denominator}`; track.append(segment); } });
      row.append(track, node('p', description.join(' · '), 'bar-description')); rows.append(row);
    }
    el('comparison-note').textContent = `标签为 agent 起草，尚未人审；结果只评价文字选择。本地 LLM ${project.evaluation.llm_http_cases} 题实际调用、${project.evaluation.shared_guard_cases} 题由公共规则处理，默认入口未启用。`;
    document.querySelectorAll('[data-eval]').forEach(b => { b.classList.toggle('selected', b.dataset.eval === evalGroup); b.setAttribute('aria-pressed', String(b.dataset.eval === evalGroup)); });
  }
  document.querySelectorAll('[data-eval]').forEach(button => button.onclick = () => { evalGroup = button.dataset.eval; if (project) renderEvaluation(); });
  const dependencies = {
    A1:['动作组可获得的示范与目录范围','语意匹配目录与开发文本'], A2:['十类目录与开发文本','合法 ID、拒绝状态与配置版本'], B1:['十类完整含义与实际示范','有来源的机器人训练轨迹'], B2:['有效训练轨迹与冻结协议','新版权重、生成接口与检查指标'], C1:['语言和动作的冻结版本','独立结果、完整服务与版本注册'], C2:['已集成且检查通过的版本','统一展示、汇报与模型版本备份']
  };
  function renderRoles() {
    const cards = el('role-cards'); cards.replaceChildren();
    for (const role of project.roles) {
      const button = node('button', undefined, `role-card${role.id === selectedRole ? ' selected' : ''}`); button.setAttribute('aria-pressed', String(role.id === selectedRole)); button.append(node('span', role.number || role.id, 'role-id'), node('strong', window.ProjectI18n.lang === 'en' ? role.role_en || role.role : role.role), node('p', window.ProjectI18n.lang === 'en' ? role.focus_en || role.focus : role.focus), node('small', '查看交接与下一步 →')); button.onclick = () => { selectedRole = role.id; renderRoles(); }; cards.append(button);
    }
    const role = project.roles.find(r => r.id === selectedRole), dep = dependencies[role.id];
    const intro = node('div'); intro.append(node('h3', `${role.number || role.id} · ${window.ProjectI18n.lang === 'en' ? role.role_en || role.role : role.role}`), node('p','建议责任位，待组内认领。'));
    const work = node('dl'); work.append(node('dt','下一步工作'), node('dd', window.ProjectI18n.lang === 'en' ? role.next_step_en || role.next_step : role.next_step));
    const handoff = node('dl'); handoff.append(node('dt','上游 → 下游'), node('dd', `${dep[0]} → ${dep[1]}`)); el('role-detail').replaceChildren(intro,work,handoff);
  }
  const fileType = mime => ({'application/pdf':'PDF','application/vnd.openxmlformats-officedocument.presentationml.presentation':'PPTX','application/json':'JSON','text/markdown':'MD','text/plain':'TXT'}[mime.split(';')[0]] || 'FILE');
  function renderMaterials() {
    const materials = project.materials.filter(m => m.category !== '生成样例' && (!m.language || m.language === window.ProjectI18n.lang));
    const filters = el('material-filters'); filters.replaceChildren(); ['全部',...new Set(materials.map(m=>m.category))].forEach(category => { const b = node('button',category,category === materialCategory ? 'selected' : ''); b.setAttribute('aria-pressed',String(category === materialCategory)); b.onclick = () => { materialCategory = category; renderMaterials(); }; filters.append(b); });
    const cards = el('material-cards'); cards.replaceChildren();
    for (const item of materials.filter(m => materialCategory === '全部' || m.category === materialCategory)) {
      const card = node('article',undefined,'material-card'), top = node('div',undefined,'file-type'); top.append(node('span', `${fileType(item.mime)} / ${item.category}`),node('span', item.bytes ? item.bytes > 1048576 ? `${(item.bytes / 1048576).toFixed(1)} MB` : `${Math.ceil(item.bytes / 1024)} KB` : '—'));
      card.append(top,node('h3',window.ProjectI18n.lang === 'en' ? item.title_en || item.title : item.title),node('p',window.ProjectI18n.lang === 'en' ? item.description_en || item.description : item.description));
      if (item.available) { const a = node('a', item.mime === 'application/pdf' ? '打开 PDF ↗' : '下载文件 ↓'); a.href = item.url; if (item.mime === 'application/pdf') { a.target = '_blank'; a.rel = 'noopener noreferrer'; } else a.setAttribute('download',''); card.append(a); }
      else card.append(node('span',`暂不可用：${item.unavailable_reason || '本地文件缺失'}`,'unavailable'));
      cards.append(card);
    }
  }
  function renderPreview() {
    if (!project) return;
    const video = el('resource-video'); video.pause(); video.removeAttribute('src'); video.load();
    const example = project.generated_previews.find(x => x.action_id === el('resource-action').value), view = example?.views[el('resource-view').value];
    el('resource-play').disabled = !view?.available; el('resource-download').classList.toggle('hidden',!view?.available);
    if (!view?.available) { video.removeAttribute('poster'); el('resource-preview-info').textContent = '当前视角资源不可用。'; return; }
    video.poster = view.poster_url; video.src = view.video_url; video.load();
    el('resource-download').href = view.video_url;
    el('resource-preview-info').textContent = `${example.action_id} · 原始时长 ${example.duration_s.toFixed(2)} s · ${example.frames} 帧。${example.action_id === 'PLEASE_WAIT' ? '当前仅 WAIT 词例参考。' : 'v1 已保存的模型输出。'}`;
  }
  el('resource-action').onchange = el('resource-view').onchange = renderPreview;
  el('resource-play').onclick = async () => { try { await el('resource-video').play(); } catch (_) { el('resource-preview-info').textContent = '视频未能播放，请刷新页面后重试。'; } };
  el('resource-video').addEventListener('error',() => { el('resource-preview-info').textContent = '视频资源未能载入，可尝试切换视角或稍后重试。'; });
  window.addEventListener('project:tabchange', event => { if (event.detail.id !== 'resources') el('resource-video').pause(); });
  renderFlow();
  async function initProject() {
    try {
      const response = await fetch('/data/project.json',{cache:'no-store'}); if (!response.ok) throw new Error(`项目记录不可用（HTTP ${response.status}）`); project = await response.json();
      el('stat-actions').textContent = `${project.metrics.supported_actions} 种`; el('stat-corpus').textContent = number(project.metrics.metadata_rows); el('data-demos').textContent = project.model.independent_demonstrations;
      renderStages(); renderEvaluation(); renderRoles(); renderMaterials(); renderPreview();
      const names = {train:'训练集',val:'验证集',test:'测试集'}, colors = ['#417f6b','#b9d291','#d7b87c'];
      project.corpus.splits.forEach((split,i) => { const bar = node('span'); bar.style.width = `${split.metadata_rows / project.corpus.metadata_rows * 100}%`; bar.title = `${names[split.name]} ${number(split.metadata_rows)} 条`; el('corpus-split-bar').append(bar); const row = node('div',undefined,'split-row'), label = node('span'), dot = node('i',undefined,'swatch'); dot.style.background = colors[i]; label.append(dot,node('span',names[split.name])); row.append(label,node('strong',`${number(split.metadata_rows)} 条`)); el('corpus-splits').append(row); });
      const source = node('a','How2Sign 官方项目 ↗'); source.href = project.corpus.source_url; source.target = '_blank'; source.rel = 'noopener noreferrer'; el('corpus-source').append(source,document.createTextNode(` · ${project.corpus.license}。保留原 split，未下载实例视频。`));
      const max = Math.ceil(Math.max(...project.model.heldout_metrics.map(m => m.rmse_rad)) * 1000) / 1000;
      project.model.heldout_metrics.forEach(m => { const row = node('div',undefined,'fit-row'), track = node('div',undefined,'fit-bar'), bar = node('span'); bar.style.width = `${m.rmse_rad / max * 100}%`; track.append(bar); row.append(node('span',m.action_id),track,node('strong',`${m.rmse_rad.toFixed(6)} rad`)); el('fit-metrics').append(row); });
      el('fit-metrics').append(node('p',`图宽对应 ${max.toFixed(3)} rad；冻结 RMSE 门槛为 0.035 rad。`,'microcopy'));
      const snapshot = project.evidence_snapshot; el('test-snapshot').replaceChildren(node('strong', String(snapshot.tests.tests)),node('small',' 项通过 · 历史快照'));
      const date = new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Singapore',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(snapshot.created_utc));
      el('test-snapshot-date').textContent = `${date}（新加坡时间）的冻结验收。该数值不是本次页面改动后的实时测试数。`;
      el('course-deadline').textContent = `简报截止日 ${project.course.deadline} · 展示 ${project.course.presentation_minutes.join('–')} 分钟`;
    } catch (error) { const box = el('project-load-error'); box.classList.remove('hidden'); box.textContent = `${error.message}。请刷新页面重试，未用示例数字替代真实记录。`; }
    el('connection-status').textContent = '小组分享版 · 2026-10-09';
  }
  window.addEventListener('project:languagechange', () => { if (project) { renderMaterials(); renderRoles(); } });
  initProject();
})();

