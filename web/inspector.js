'use strict';
(() => {
  const el = id => document.getElementById(id);
  const video = el('inspect-video');
  let motion = null, entry = null, frame = 0, sequence = 0, mediaReady = false;
  const message = text => { el('inspect-status').textContent = text; };
  function clear() {
    sequence += 1;
    motion = null; entry = null; frame = 0; mediaReady = false;
    video.pause(); video.onloadedmetadata = null; video.removeAttribute('src'); video.load();
    el('inspect-content').classList.add('hidden');
  }
  async function getJSON(url) {
    const response = await fetch(url, {cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.error || '数据不可用');
    return data;
  }
  function displayedFrame(time) {
    return Math.max(0, Math.min(motion.timestamps_s.length-1, Math.floor(time*motion.provenance.fps+1e-6)));
  }
  function frameMediaTime(index) {
    // Seek inside the encoded frame interval, avoiding rounded JSON boundaries.
    return (index+0.5)/motion.provenance.fps;
  }
  function drawChart(id, series, color, title, unit, limits) {
    const canvas = el(id), width = Math.max(260, canvas.clientWidth), height = 178;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = width * ratio; canvas.height = height * ratio;
    const context = canvas.getContext('2d'); context.scale(ratio, ratio);
    const pad = {left:54,right:18,top:27,bottom:27};
    const values = limits ? series.concat(limits) : series;
    let low = Math.min(...values), high = Math.max(...values);
    const range = Math.max(high-low, 0.1); low -= range*.1; high += range*.1;
    const first = motion.timestamps_s[0], last = motion.timestamps_s.at(-1);
    const x = t => pad.left+(t-first)/(last-first)*(width-pad.left-pad.right);
    const y = v => pad.top+(high-v)/(high-low)*(height-pad.top-pad.bottom);
    context.fillStyle='#647980'; context.font='11px -apple-system,sans-serif'; context.fillText(`${title} (${unit})`,8,14);
    context.font='10px -apple-system,sans-serif';
    for(let tick=0;tick<=3;tick++){
      const value=low+(high-low)*tick/3, heightY=y(value);
      context.strokeStyle='#e5ebed'; context.beginPath(); context.moveTo(pad.left,heightY); context.lineTo(width-pad.right,heightY); context.stroke();
      context.fillStyle='#647980'; context.textAlign='right'; context.fillText(value.toFixed(2),pad.left-7,heightY+3);
    }
    context.textAlign='center';
    for(let tick=0;tick<=4;tick++){
      const time=first+(last-first)*tick/4;
      context.fillText(`${time.toFixed(1)} s`,x(time),height-7);
    }
    if(limits){
      context.setLineDash([4,4]);context.strokeStyle='#b68544';
      for(const limit of limits){context.beginPath();context.moveTo(pad.left,y(limit));context.lineTo(width-pad.right,y(limit));context.stroke();}
      context.setLineDash([]);
    }
    context.strokeStyle=color;context.lineWidth=1.8;context.beginPath();
    series.forEach((value,index)=>{index?context.lineTo(x(motion.timestamps_s[index]),y(value)):context.moveTo(x(motion.timestamps_s[index]),y(value));});context.stroke();
    context.strokeStyle='#17303a';context.lineWidth=1;context.beginPath();context.moveTo(x(motion.timestamps_s[frame]),pad.top);context.lineTo(x(motion.timestamps_s[frame]),height-pad.bottom);context.stroke();
    context.fillStyle=color;context.beginPath();context.arc(x(motion.timestamps_s[frame]),y(series[frame]),3.5,0,2*Math.PI);context.fill();
  }
  function updateReadouts() {
    if(!motion) return;
    const name=el('inspect-joint').value, column=motion.joint_names.indexOf(name);
    if(column<0)return;
    el('inspect-frame').value=String(frame);
    const time=motion.timestamps_s[frame];
    el('inspect-time').textContent=`${time.toFixed(2)} s · ${frame+1} / ${motion.timestamps_s.length} 帧`;
    const phase=(motion.phase_intervals||[]).find(p=>time>=p.start_s && time<p.end_s) || motion.phase_intervals?.at(-1);
    el('inspect-phase').textContent=`阶段：${phase?.label_zh || phase?.name || '未标注'}；曲线对应当前视频帧的轨迹时刻。`;
    const angle=motion.positions_rad[frame][column], speed=motion.velocities_rad_s[frame][column];
    el('inspect-angle').textContent=`${angle.toFixed(3)} rad / ${(angle*180/Math.PI).toFixed(1)}°`;
    el('inspect-velocity').textContent=`${speed.toFixed(3)} rad/s`;
    drawChart('inspect-position-chart',motion.positions_rad.map(row=>row[column]),'#087f83','位置','rad',motion.joint_limits_rad[column]);
    drawChart('inspect-velocity-chart',motion.velocities_rad_s.map(row=>row[column]),'#b77b33','速度','rad/s');
    const linked=(motion.mimic_couplings||[]).filter(rule=>rule.parent===name || rule.child===name);
    el('inspect-coupling').textContent=linked.length ? '手指耦合：'+linked.map(rule=>`${rule.child} = ${rule.multiplier} × ${rule.parent} + ${rule.offset}`).join('；') : '该关节没有登记的 mimic 从动关系。53 个坐标包含从动关节，不代表 53 个独立驱动。';
  }
  function selectGroup() {
    if(!motion)return;
    const select=el('inspect-joint'); select.replaceChildren();
    for(const name of motion.joint_groups[el('inspect-group').value]||[]){
      const option=document.createElement('option');option.value=name;option.textContent=name;select.append(option);
    }
    updateReadouts();
  }
  function setView() {
    if(!motion || !entry)return;
    const selected=entry.views[el('inspect-view').value];
    if(!selected){message('该视角尚未生成。');return;}
    const ticket=sequence;video.pause();mediaReady=false;
    video.onloadedmetadata=()=>{
      if(ticket!==sequence || !motion)return;
      video.currentTime=Math.min(frameMediaTime(frame),video.duration);
      video.playbackRate=Number(el('inspect-speed').value);mediaReady=true;updateReadouts();
    };
    video.poster=selected.poster_url;video.src=selected.video_url;video.load();
    message(`${motion.action_id} 已载入。可播放、逐帧查看或切换关节；所有动作仍为未评审候选。`);
  }
  el('inspect-load').onclick=async()=>{
    clear(); const ticket=sequence, action=el('inspect-action').value;
    message('正在读取轨迹与视角清单…');el('inspect-load').disabled=true;
    try{
      const available=await getJSON('/api/inspection');
      if(ticket!==sequence)return;
      const chosen=available.actions[action];
      if(!chosen)throw new Error('该表达的检查资料尚未生成，请稍后重试。');
      const data=await getJSON(chosen.telemetry_url);
      if(ticket!==sequence)return;
      if(data.action_id!==action || data.run_id!==chosen.run_id || data.trajectory_sha256!==chosen.trajectory_sha256)throw new Error('轨迹与视角记录不一致，已停止加载。');
      motion=data;entry=chosen;frame=0;
      el('inspect-frame').max=String(data.timestamps_s.length-1);
      el('inspect-content').classList.remove('hidden');
      el('inspect-view').value=chosen.views.front?'front':'right_side';
      el('inspect-provenance').textContent=JSON.stringify({action_id:data.action_id,trajectory_sha256:data.trajectory_sha256,run_id:chosen.run_id,units:data.units,validation:data.validation,provenance:data.provenance},null,2);
      selectGroup();setView();
    }catch(error){if(ticket===sequence){clear();message('未加载动作：'+error.message);}}
    finally{el('inspect-load').disabled=false;}
  };
  function seek(index){
    if(!motion)return;
    video.pause();frame=Math.max(0,Math.min(index,motion.timestamps_s.length-1));
    if(mediaReady)video.currentTime=frameMediaTime(frame);updateReadouts();
  }
  el('inspect-frame').oninput=()=>seek(Number(el('inspect-frame').value));
  el('inspect-prev').onclick=()=>seek(frame-1);
  el('inspect-next').onclick=()=>seek(frame+1);
  el('inspect-view').onchange=setView;
  el('inspect-speed').onchange=()=>{video.playbackRate=Number(el('inspect-speed').value);};
  el('inspect-group').onchange=selectGroup;
  el('inspect-joint').onchange=updateReadouts;
  el('inspect-action').onchange=()=>{clear();message('表达已改变。点击“打开候选轨迹”加载新的动作。');};
  video.addEventListener('timeupdate',()=>{if(motion && mediaReady){frame=displayedFrame(video.currentTime);updateReadouts();}});
  video.addEventListener('error',()=>{if(motion)message('视频未能载入。请检查本机资源，关节数据本身不表示视频播放成功。');});
  window.addEventListener('project:tabchange',event=>{
    if(event.detail.id!=='inspection')video.pause();
    if(event.detail.id==='inspection')updateReadouts();
  });
  window.addEventListener('resize',updateReadouts);
})();
