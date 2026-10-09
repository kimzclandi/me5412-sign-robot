'use strict';
let method='exact'; let catalog=[]; let busy=false;
const $=id=>document.getElementById(id);
const reasons={no_exact_alias:'未找到登记的完整短语，可尝试语义匹配或直接选择短语。',unsupported:'当前动作库不支持完整表达。',embedding_unavailable:'本地语义模型尚未准备好。',embedding_below_threshold:'语义匹配不足以确定完整含义，未执行动作。',embedding_ambiguous:'多个候选含义接近，请重新表述。',llm_unavailable:'未配置本地大模型服务。',negated_or_declining:'包含否定或拒绝含义，未执行候选动作。',multiple_or_compound_intents:'输入包含多个或额外含义，未执行部分匹配动作。',clinical_content_out_of_scope:'当前表达库不支持这些医疗内容。',qualified_wait_out_of_scope:'输入限定了等待条件，超出当前表达库。',waiting_role_mismatch:'输入中等待的主体与候选表达不同。',empty_input:'请输入一句英文或选择短语。',reported_or_metalinguistic:'输入在描述或引用话语，不能直接代替本人表达。'};
function showResult(result){
  const selection=result.selection, execution=result.execution;
  const titles={execute:'已选中候选表达',clarify:'需要重述',unsupported:'暂不支持',error:'方法当前不可用'};
  $('chosen').textContent=selection.action_id||'未执行';
  $('latency').textContent=Number.isFinite(selection.latency_ms)?`${selection.latency_ms.toFixed(1)} ms`:'—';
  $('result').className='result '+(execution.state==='ready'?'':selection.status==='error'?'error':'warning');
  $('result').querySelector('strong').textContent=execution.state==='ready'?'正在预览候选动作':titles[selection.status]||selection.status;
  $('result').querySelector('p').textContent=execution.message||reasons[selection.reason_code]||`原因：${selection.reason_code}。未触发机器人动作。`;
  const video=$('video');video.pause();
  if(execution.preview_url){video.style.display='block';$('empty-view').style.display='none';video.src=execution.preview_url;video.load();if(!$('demo').classList.contains('hidden'))video.play().catch(()=>{});}
  else{video.removeAttribute('src');video.load();video.style.display='none';$('empty-view').style.display='flex';$('empty-view').querySelector('strong').textContent=execution.state==='review_required'?'候选表达已选中':'本次未播放动作';$('empty-view').querySelector('p').textContent=execution.state==='review_required'?'勾选研究预览后，重新提交即可查看':'可修改输入或直接选择目录中的短语';}
}
async function submit(endpoint,payload){
  if(busy)return;busy=true;$('submit').disabled=true;$('submit').firstChild.textContent='正在选择… ';
  $('video').pause();$('video').style.display='none';$('empty-view').style.display='flex';$('empty-view').querySelector('strong').textContent='正在检查输入';$('empty-view').querySelector('p').textContent=method==='embedding'?'首次使用包含本地模型加载时间':'只会选择目录中支持的完整含义';$('chosen').textContent='—';$('latency').textContent='—';
  try{const res=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload,allow_candidate_preview:$('preview').checked})});const result=await res.json();if(!res.ok)throw new Error(result.message||result.error);showResult(result);}
  catch(error){$('result').className='result error';$('result').querySelector('strong').textContent='请求未完成';$('result').querySelector('p').textContent=error.message;$('empty-view').querySelector('strong').textContent='本次未播放动作';$('empty-view').querySelector('p').textContent='请求异常，请检查服务后重新提交';}
  finally{busy=false;$('submit').disabled=false;$('submit').firstChild.textContent='理解并选择动作 ';}
}
$('submit').onclick=()=>submit('/api/select',{text:$('text').value,method});
$('text').addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter')$('submit').click();});
document.querySelectorAll('.method').forEach(button=>button.onclick=()=>{method=button.dataset.method;document.querySelectorAll('.method').forEach(b=>b.classList.toggle('selected',b===button));});
document.querySelectorAll('[data-example]').forEach(button=>button.onclick=()=>{$('text').value=button.dataset.example;$('text').focus();});
const pages={overview:['项目总览','PROJECT AT A GLANCE','从文字到动作，看清每个环节的输入、输出与验证状态。'],demo:['交互演示','TEXT TO ACTION','输入完整含义，比较不同文字选择方法与候选动作。'],learning:['学习模型','LEARNED MOTION','用已经训练的模型，为当前请求生成并检查关节轨迹。'],inspection:['动作检查','MOTION INSPECTION','连接机器人画面、时间轴和关节数据，逐帧检查候选动作。'],data:['数据路线','FROM TEXT TO MOTION DATA','沿数据处理过程，区分已取得的记录与缺少的动作监督。'],evidence:['实验评价','EVIDENCE & LIMITS','分别查看文字选择、轨迹工程与语言可理解性。'],team:['六人协作','SIX OWNERS, ONE PROJECT','明确每个模块接收什么、交付什么、怎样验收。'],resources:['资料与汇报','PROJECT LIBRARY','查看演示样例，下载组内讨论和课程汇报材料。']};
window.navigateProject=(id,record=true)=>{
  if(!Object.hasOwn(pages,id))id='overview';
  document.querySelectorAll('.tab').forEach(b=>{const active=b.dataset.tab===id;b.classList.toggle('active',active);active?b.setAttribute('aria-current','page'):b.removeAttribute('aria-current');});
  document.querySelectorAll('.tab-panel').forEach(panel=>panel.classList.toggle('hidden',panel.id!==id));
  $('page-title').textContent=pages[id][0];$('page-eyebrow').textContent=pages[id][1];$('page-subtitle').textContent=pages[id][2];document.title=pages[id][0]+' · ME5412 机器人手语表达';
  document.querySelectorAll('video').forEach(video=>{if(video.closest('.tab-panel')?.id!==id)video.pause();});
  if(record&&location.hash!=='#'+id)history.pushState(null,'','#'+id);
  window.dispatchEvent(new CustomEvent('project:tabchange',{detail:{id}}));
  window.scrollTo({top:0,behavior:'instant'});
};
document.querySelectorAll('.tab').forEach(button=>button.onclick=()=>window.navigateProject(button.dataset.tab));
document.querySelector('.skip-link').onclick=event=>{event.preventDefault();$('main-content').focus({preventScroll:true});$('main-content').scrollIntoView({block:'start'});};
window.addEventListener('hashchange',()=>window.navigateProject(location.hash.slice(1),false));
window.addEventListener('popstate',()=>window.navigateProject(location.hash.slice(1),false));
window.navigateProject(location.hash.slice(1)||'overview',false);
async function init(){
  try{
    const status=await(await fetch('/api/status')).json();catalog=status.catalog;
    for(const action of catalog){
      const button=document.createElement('button');button.textContent=action.label_zh||action.action_id;button.onclick=()=>submit('/api/action',{action_id:action.action_id});$('phrase-buttons').append(button);
      const article=document.createElement('article');const h=document.createElement('h3');h.textContent=action.label_zh||action.action_id;article.append(h);
      const meaning=document.createElement('p');meaning.textContent=action.meaning_en;article.append(meaning);
      const meta=document.createElement('p');meta.textContent=`${action.action_id} · ${status.motions[action.action_id].preview?'候选轨迹已渲染':'轨迹制作中'}`;article.append(meta);
      const note=document.createElement('small');note.textContent=action.action_id==='PLEASE_WAIT'?'等待词例参考；完整请求表达尚未核验':'源动作参考已登记；机器人 ASL 可理解性未验证';article.append(note);
      for(const sourceId of action.source_ids||[]){const source=(status.sources||[]).find(s=>s.source_id===sourceId);if(source){const link=document.createElement('a');link.href=source.url;link.target='_blank';link.rel='noopener noreferrer';link.textContent=`查看 ${source.title} ↗`;link.style.display='block';link.style.marginTop='8px';article.append(link);}}
      $('catalog').append(article);
    }
    const evidence=await(await fetch('/api/evidence')).json();$('evidence-json').textContent=JSON.stringify(evidence,null,2);
    $('evidence-summary').textContent=evidence.summary_zh||'最终验收仍在进行，当前目录均为研究候选。';
    const names={exact:'固定匹配',embedding:'本地 MiniLM',llm:'本地 LLM · 研究对照'};
    for(const [key,item] of Object.entries(evidence.text_evaluation?.methods||{})){
      const row=document.createElement('tr');
      const fields=[names[key]||key,item.supported_correct,item.supported_wrong_rejection,item.unsupported_false_execution];
      for(const value of fields){const cell=document.createElement('td');cell.textContent=typeof value==='object'&&value!==null?`${value.numerator} / ${value.denominator}`:value||'未运行';row.append(cell);}
      $('evaluation-rows').append(row);
    }
  }catch(error){$('result').querySelector('strong').textContent='初始化未完成';$('result').querySelector('p').textContent=error.message;}
}
init();
