// Editable local course report. Run with the bundled Node runtime.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RUNTIME = process.env.RUNTIME_ROOT ?? '/Users/yukaiyan/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES ??= path.join(RUNTIME, 'node/node_modules');
const SKILL = process.env.PRESENTATIONS_SKILL_DIR ?? '/Users/yukaiyan/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations';
const { Presentation, PresentationFile } = await import(pathToFileURL(path.join(process.env.RUNTIME_NODE_MODULES, '@oai/artifact-tool/dist/artifact_tool.mjs')));
const { resolvePresentationFont, applyPresentationChartFont, finalizePresentation } = await import(pathToFileURL(path.join(SKILL, 'container_tools/artifact_tool_utils.mjs')));
const revision = process.argv[2] ?? 'v1';
if(!/^v\d+$/.test(revision)) throw new Error('Revision must be v followed by an integer');
const upgraded = Number(revision.slice(1)) >= 4;
const slideCount = upgraded ? 14 : 12;
const tableOwners = upgraded ? [7,9,11,12,13] : [7,9,11];
const OUT = path.join(ROOT, upgraded ? `deliverables/course-report-${revision}` : 'deliverables/course-report-v1');
const BUILD = path.join(ROOT, 'deliverables/.build');
await fs.mkdir(path.join(OUT, 'previews'), {recursive:true});
await fs.mkdir(BUILD, {recursive:true});
const font = resolvePresentationFont();
const p = Presentation.create({ slideSize:{width:1280,height:720} });
const C={ink:'#142A32', teal:'#007D78', muted:'#4B666B', soft:'#EDF5F3', amber:'#A9620D', dark:'#0D1723', white:'#FFFFFF'};
const notes=[];
function text(s,t,x,y,w,h,size=27,color=C.ink,bold=false,align='left') {
 const q=s.shapes.add({geometry:'textbox',name:t.slice(0,45),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 q.text=t; q.text.style={typeface:font,fontSize:size,color,bold,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:'square',insets:0}; return q;
}
function slide(title, idx) {
 const s=p.slides.add();s.background.fill=C.white;
 text(s,title,64,50,1140,65,44,C.ink,true);
 text(s,'ME5412  /  Research prototype',64,678,700,22,16,C.muted);
 text(s,String(idx).padStart(2,'0'),1160,675,56,25,18,C.teal,true,'right');
 return s;
}
async function pic(s,relative,x,y,w,h) {
 const imagePath=path.join(ROOT,relative); const b=await fs.readFile(imagePath);
 s.images.add({blob:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),contentType:relative.endsWith('.jpg')?'image/jpeg':'image/png',alt:relative,fit:'contain',position:{left:x,top:y,width:w,height:h}});
}
function note(s,idx,title,sec,script,sources,check) {
 const n=`第 ${idx} 页：${title}\n建议 ${sec} 秒。\n\n${script}\n\n本页讲述检查：${check}\n\n来源与证据：\n${sources.join('\n')}`;
 s.speakerNotes.text=n;
 notes.push({slide:idx,title,seconds:sec,script,check,sources});
}
function table(s,values,x,y,w,h,widths,size=23) {
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
 t.borders.assign({fill:'#D8E5E2',width:1,style:'solid'});
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({textStyle:{typeface:font,fontSize:size,color:C.ink},margins:{left:14,right:14,top:11,bottom:9},anchor:'center'});
 t.cells.block({row:0,column:0,rowCount:1,columnCount:values[0].length}).assign({fill:C.teal,textStyle:{typeface:font,fontSize:size,bold:true,color:C.white}});
 for(let r=1;r<values.length;r++) t.cells.block({row:r,column:0,rowCount:1,columnCount:values[0].length}).fill=r%2?C.soft:C.white;
 return t;
}
const result='results/evaluation/test-20261008T142047221403Z';
const frozen = JSON.parse(await fs.readFile(path.join(ROOT,result,'summary.json'),'utf8'));
const expected = {exact:[38,8,22,0,0,0],embedding:[47,17,13,0,0,0],llm:[48,20,7,1,2,2]};
const keys=['accuracy','supported_correct_selection_rate','supported_wrong_rejection_rate','supported_wrong_execution_rate','unsupported_false_execution_rate','runtime_error_rate'];
for (const [method,values] of Object.entries(expected)) {
 const m=frozen.methods[method].metrics;
 if(m.n!==60||m.n_supported!==30||m.n_unsupported!==30||keys.some((k,i)=>m[k].numerator!==values[i])) throw new Error('Frozen evidence differs from slide claims: '+method);
}
const sources={robot:'https://github.com/unitreerobotics/unitree_ros/tree/5994d4faef0a9cadd3287f8de0199a67eeb2a259/robots/g1_description',thank:'https://www.lifeprint.com/asl101/pages-signs/t/thankyou.htm',thankVideo:'https://www.youtube.com/watch?v=2W0BDFUjsG0',wait:'https://www.lifeprint.com/asl101/pages-signs/w/wait.htm',waitVideo:'https://www.youtube.com/watch?v=YfwgS9ZsBVw',mini:'https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41'};
const learnedReport = upgraded ? JSON.parse(await fs.readFile(path.join(ROOT,'results/motion_learning/v1/report.json'),'utf8')) : null;
const learnedModel = upgraded ? JSON.parse(await fs.readFile(path.join(ROOT,'results/motion_learning/v1/model.json'),'utf8')) : null;
const corpus = upgraded ? JSON.parse(await fs.readFile(path.join(ROOT,'data/corpus_index/how2sign_realigned_v1/download_manifest.json'),'utf8')) : null;
if(upgraded && (learnedModel.independent_demonstrations!==3 || learnedModel.train_frames!==367 || learnedModel.validation_frames!==365 || !learnedReport.fit_accepted || !learnedReport.engineering_accepted || learnedReport.asl_reviewed || learnedReport.default_enabled || corpus.aggregate_counts.annotation_rows!==35263 || corpus.aggregate_counts.locally_available_motion_targets!==0)) throw new Error('Upgrade evidence does not match slide claims');

// 1. Cover
{
 const s=p.slides.add();s.background.fill=C.dark;
 text(s,'ME5412 Robotics for Healthcare',64,58,1100,34,25,'#73D3C5');
 text(s,'Text to\nrobot signing',64,180,590,172,65,C.white,true);
 text(s,upgraded ? 'Finite expressions and a learned\ntrajectory prototype' : 'A bounded ASL expression study',64,389,535,110,30,'#D4E5E8');
 text(s,'Simulation prototype  /  8 October 2026',64,598,570,34,22,'#A3B9C0');
 await pic(s,'results/inspection/HELLO/0efe9b20010d496e/front.png',666,152,562,422);
 text(s,'Candidate motion. ASL comprehensibility unreviewed.',680,596,538,53,20,'#EDC17E');
 note(s,1,'研究问题与原型范围',35,'我们的题目是有限表达的文字选择与机器人手语候选表达。输入一句英文或选择短语，系统选择一个明确编号，再预览对应的机器人动作。我们目前只研究三个候选，全部处于语言可理解性待验证状态。今天汇报两条主线：文字能否选对编号，以及机器人是否能在自身形态约束下呈现参考动作。',[sources.robot,'README.md','data/catalog.json'],'不要说成任意英文翻译，也不要说已经服务医院。');
}
// 2. Problem and design scope
{
 const s=slide('Problem and project scope',2);
 text(s,'Proposed setting',64,155,570,37,27,C.teal,true);
 text(s,'Brief service interactions at a care reception desk.',64,208,567,103,37,C.ink,true);
 text(s,'The project tests expression selection and robot motion. It has no clinical outcome evidence.',64,343,547,104,27,C.muted);
 text(s,'Design alternatives',695,155,516,37,27,C.teal,true);
 text(s,'Text display: no robot motion\nHuman signing: reference for meaning\nRobot candidate: repeatable motion to inspect',695,211,510,171,27,C.ink);
 text(s,'Current vocabulary',695,428,480,34,24,C.teal,true);
 text(s,'HELLO\nTHANK_YOU\nPLEASE_WAIT',695,472,490,125,31,C.ink,true);
 text(s,'PLEASE_WAIT currently approximates the WAIT word example.',64,573,572,70,24,C.amber);
 note(s,2,'场景、现有选择与收敛',60,'我们把应用设想放在接待处的简短服务互动，但这只是未来场景假设。文字显示、人类手语和机器人表达解决的环节不同；本项目选择可重复的机器人动作，便于检查形态和动作路径。现阶段词汇表只有 HELLO、THANK_YOU 和 PLEASE_WAIT 三个编号。最后一个编号为了接口兼容保留，但动作来源只支持 WAIT 词例，不能称为完整礼貌请求。ASL 也不等于新加坡本地 SgSL，未来本地部署还需要重新确认语言需求。',['docs/实施路线.md','docs/source-review.md','data/catalog.json','https://sadeaf.org.sg/sgsl-course/'],'能否清楚说明当前研究目标与设想应用之间的距离？');
}
// 3. Architecture. Flat editable process, with no decorative panels.
{
 const s=slide(upgraded ? 'Default demonstration architecture' : 'System architecture',3);
 const rows=[['01','English input or phrase button','One complete meaning'],['02','Shared guard and selector','execute / clarify / unsupported / error'],['03','Action ID contract','HELLO / THANK_YOU / PLEASE_WAIT'],['04','Independent preview permission','Unreviewed motion blocked by default'],['05','MuJoCo trajectory and video','Named joints and timestamped positions']];
 rows.forEach((r,i)=>{let y=156+i*91;text(s,r[0],64,y,70,54,39,C.teal,true);text(s,r[1],162,y,544,46,30,C.ink,true);text(s,r[2],741,y+3,461,63,23,C.muted)});
 text(s,'The selector returns an ID. It never generates joint commands.',164,627,1030,34,25,C.teal,true);
 note(s,3,'公共接口与错误隔离',65,'这个系统有两条独立验收线。语言模块先经过公共拒绝检查，再由固定匹配、句向量或本地模型决定编号。它输出的 status 只有四类，非 execute 状态不能携带动作。编号选中后，还要通过独立候选预览许可，默认阻止未评审动作。网页现场运行文字选择，但播放的是事先用真实 MuJoCo 逐帧渲染的 MP4，不能称为浏览器实时物理仿真。分开模块后，误选与动作几何错误可以分别定位。',['contracts/interfaces.json','src/sign_robot/pipeline.py','src/sign_robot/server.py','src/sign_robot/language.py'],'语言失败与动作失败分别在哪个接口被发现？');
}
// 4. Model
{
 const s=slide('Robot model and control boundary',4);
 await pic(s,'results/inspection/THANK_YOU/6096df4086863be6/front_start.png',650,161,571,428);
 text(s,'Unitree G1 + Inspire DFQ',64,158,553,74,35,C.teal,true);
 text(s,'53 scalar joint coordinates\n12 retained mimic relations\n0 actuators in this scene',64,267,535,143,30,C.ink);
 text(s,'Fixed base with kinematic qpos replay. Coupled fingers limit independent handshape control.',64,451,523,116,27,C.muted);
 text(s,'Dynamics and ASL comprehension remain untested.',64,612,1110,35,25,C.amber);
 note(s,4,'模型自由度与控制边界',65,'机器人模型来自 Unitree 官方仓库，固定到具体提交并保存逐文件哈希。这里的 53 是标量关节坐标数，包含从动关节，不能说成 53 个独立电机。我们保留 12 条 mimic 耦合。当前场景的执行器数是零，直接回放 qpos，因此验收的是运动学几何，不是控制器跟踪、力矩可行性或真实机器人安全。手指缺少独立并指能力，头部和面部也没有表达，这些限制影响动作的语言真实性。',[sources.robot,'assets/robot/model_info.json','assets/robot/upstream_manifest.json','motions/THANK_YOU.json'],'如果有人问这是不是实时控制，应答运动学回放，并说明未做哪些动力学检查。');
}
// 5. Video calibration
{
 const s=slide('Video references guide qualitative calibration',5);
 const pics=['right_side_start.png','right_side_middle.png','right_side_end.png'];
 const labels=['Near lower-face proxy','Forward and slightly down','Final palm faces up'];
 for(let i=0;i<3;i++){await pic(s,`results/inspection/THANK_YOU/6096df4086863be6/${pics[i]}`,64+i*392,158,368,276);text(s,labels[i],64+i*392,451,368,65,25,C.ink,true)}
 text(s,'ASLU video observations: 0.916 s, 1.116 s and 1.516 s',64,553,1135,36,26,C.teal,true);
 text(s,'Human video provides qualitative references. Robot keyframes use manual engineering targets.',64,607,1128,47,23,C.muted);
 note(s,5,'公开视频如何指导校准',75,'A1 实际播放了 ASLU 的 THANK YOU 和 WAIT 视频，并用浏览器暂停逐帧观察。THANK YOU 的关键顺序是近唇起手、掌面向自身、向前略下、最后掌向上。这里展示的是我们自己的机器人渲染，下面的秒数对应来源视频的观察时刻，并不是机器人截图的同一时间，也不是精确人体三维标注。机器人仍有脸部间隙，手指间距不同且缺少微笑。视频对照帮助修正明显偏差，但不能直接得出毫米级真人重定向误差或可理解性通过。',[sources.thank,sources.thankVideo,'docs/video-calibration.md','results/previews/THANK_YOU_calibration.json'],'指明视频时间与机器人时间属于不同时间轴。');
}
// 6. Motion method
{
 const s=slide('Motion construction and checks',6);
 text(s,'Manual wrist targets',64,157,564,41,31,C.teal,true);
 text(s,'Bounded inverse kinematics fits position and orientation while limiting posture change.',64,215,556,104,27,C.ink);
 text(s,'q(u) = (1 − s) q₀ + s q₁\ns(u) = 3u² − 2u³',64,352,557,105,34,C.ink,true);
 text(s,'u is normalized segment time.\nZero endpoint velocity does not ensure continuous acceleration.',64,487,552,112,25,C.muted);
 await pic(s,'results/inspection/PLEASE_WAIT/cfec47d9ad243fd9/front.png',669,166,545,409);
 text(s,'WAIT remains a coupled-finger approximation.',673,590,540,54,24,C.amber);
 note(s,6,'逆运动学、插值与轨迹验收',75,'输入是人工指定的手腕位置、朝向和时刻，输出是按关节命名的 positions[T,53]。有界数值 IK 同时考虑位置、旋转、与前一姿态的变化和部分距离惩罚。相邻关键帧使用三次 smoothstep，段端速度为零，但加速度连续性并没有保证。THANK YOU 加入 12 个中间位姿，避免仅插值两端关节角造成指尖向上绕行。我们检查全帧关节限位、速度、耦合和上游已有碰撞几何。已有几何没有深于 1 毫米的穿透，不等于完整安全证明。右图 WAIT 还有耦合手指与完整请求表达缺口。',['scripts/build_motions.py','tests/test_motion.py','motions/THANK_YOU.json','motions/PLEASE_WAIT.json','docs/实施路线.md',sources.wait,sources.waitVideo],'要能解释为何小 IK 残差不能证明手语正确。');
}
// 7. Selector methods
{
 const s=slide('Three selectors share one interface',7);
 table(s,[['Method','Mechanism','Main limitation'],['Exact matching','Full registered phrase\nafter shared guard','Limited paraphrase coverage'],['MiniLM','Local 384-dimensional\nsentence embeddings','Thresholds can reject\nvalid paraphrases'],['Local LLM','Strict five-label output\nfrom existing Q8 checkpoint','Wrong choices and\ninvalid labels observed']],64,165,1152,342,[245,460,447],25);
 text(s,'All methods return the same allowed ID or a non-execution status.',64,552,1146,43,29,C.teal,true);
 text(s,'Default demo: exact or MiniLM. LLM remains disabled after its development gate failed.',64,615,1143,45,24,C.amber);
 note(s,7,'方法对比与共享控制条件',65,'固定匹配只接受登记的完整短语。MiniLM 用本地真实的 384 维句向量，根据相似度和候选差值决定选择或拒绝。LLM 使用已有本地 Q8 检查点，严格要求整个回答等于五种标签之一，程序再封装统一接口。三个方法前面都使用同一套公共拒绝规则，所以报告的是方法加规则的系统行为。LLM 最早要求 JSON 时三个开发正例全失败；一次协议修复后格式三条合法但只选对两条，没有达到开发启用门槛，因此只进入研究对照，默认继续关闭。',[sources.mini,'config/embedding.json','config/llm_local_provenance.json','config/llm_local_feasibility_v1.json','config/llm_local_feasibility_v2_label.json','src/sign_robot/llm.py'],'不要把共享 guard 的成功全部归功于模型。');
}
// 8. Native editable chart with complete literal values.
{
 const s=slide('Frozen text evaluation',8);
 text(s,'60 cases: 30 supported and 30 out of scope',64,146,1141,40,28,C.teal,true);
 const chart=s.charts.add('bar',{position:{left:64,top:218,width:758,height:386},categories:['Exact + guard','MiniLM + guard','LLM + guard'],series:[{name:'Correct behavior / 60',values:[38,47,48],fill:C.teal}],barOptions:{direction:'column',grouping:'clustered',gapWidth:110},hasLegend:false,xAxis:{visible:true,textStyle:{fontSize:22,fill:C.ink},line:{fill:'#A8BFBE',width:1}},yAxis:{visible:true,min:0,max:60,majorUnit:15,title:{text:'Cases',textStyle:{fontSize:20,fill:C.muted}},textStyle:{fontSize:20,fill:C.muted},numberFormatCode:'0',majorGridlines:{fill:'#DCE8E6',width:1}},dataLabels:{showValue:true,position:'outEnd',textStyle:{fontSize:26,bold:true,fill:C.ink}},chartFill:C.white,plotAreaFill:C.white});
 applyPresentationChartFont(chart,{fontFamily:font});
 text(s,'18 development cases',873,233,342,80,31,C.ink,true);
 text(s,'Test frozen before evaluation',873,337,335,100,30,C.ink,true);
 text(s,'Agent-drafted labels\nHuman review pending',873,468,332,89,26,C.amber);
 text(s,'Correct behavior includes correct rejection. This metric does not measure ASL comprehension.',64,626,1145,43,23,C.muted);
 note(s,8,'评价协议与总体结果',75,'最终集包含 60 条输入，支持与库外各 30 条；另外有 18 条开发题。我们在运行前冻结测试哈希，并保存全部原始返回。标签由 agent 起草、尚未人审，所以只能称探索性结果。整体行为准确率将支持输入选对和库外正确拒绝合并：固定匹配 38 条，MiniLM 47 条，LLM 48 条。error 算错误，不把运行异常当成功拒绝。三个方法的分母一致，但总分隐藏错误类型，需要看下一页。它只测英文到 ID，不测动作是否可理解。',[`${result}/summary.json`,`${result}/raw.jsonl`,'data/source_manifest.json','docs/source-review.md'],'如果全部拒绝，支持部分会怎样计分？');
}
// 9. Failure profile
{
 const s=slide('The LLM score includes incorrect execution',9);
 table(s,[['Outcome','Exact','MiniLM','Local LLM'],['Supported input selected correctly','8 / 30','17 / 30','20 / 30'],['Wrong ID on supported input','0 / 30','0 / 30','1 / 30'],['Execution on out-of-scope input','0 / 30','0 / 30','2 / 30'],['Invalid output / runtime error','0 / 60','0 / 60','2 / 60']],64,158,1152,351,[580,184,184,204],24);
 text(s,'35 actual LLM calls',64,552,555,45,31,C.teal,true);
 text(s,'25 cases ended in the shared guard',638,552,579,45,27,C.ink);
 text(s,'The LLM remains disabled by default. Small-sample zero counts do not establish zero risk.',64,614,1145,50,24,C.amber);
 note(s,9,'负结果与默认选择',75,'LLM 的总体分数略高，但支持输入里有一条选错编号，两个非法输出，并把两条库外请求执行成动作。MiniLM 仍有 13 条支持输入被错误拒绝，不能说效果已经很好。LLM 的 60 条里只有 35 条真的请求模型，25 条由 guard 截断，实际 HTTP 子集的正确行为是 25/35，guard 是 23/25。这是经过筛选的条件子集，不能当成模型总体独立准确率。我们保留全部失败，未按最终题调提示词，默认继续用 exact 或 MiniLM。',[`${result}/summary.json`,`${result}/raw.jsonl`,`${result}/counterexamples.jsonl`,'config/llm.json','config/llm_experimental.json'],'为什么总准确率更高还不足以启用该方法？');
}
// 10. Demonstration
{
 const s=slide('Demonstration and failure behavior',10);
 text(s,'1   “Thank you.”',64,160,720,51,33,C.ink,true);
 text(s,'Exact match selects THANK_YOU. Preview stays blocked.',112,222,651,66,25,C.muted);
 text(s,'2   Explicit candidate preview',64,327,740,48,32,C.ink,true);
 text(s,'Research permission enables the pre-rendered motion.',112,388,645,67,25,C.muted);
 text(s,'3   A mixed or negated request',64,493,740,49,32,C.ink,true);
 text(s,'The system rejects the input and clears the old video.',112,553,637,69,25,C.muted);
 await pic(s,'results/ui/demo-detail.jpg',830,151,386,486);
 text(s,'Local startup: run_demo.command',64,634,700,32,22,C.teal,true);
 note(s,10,'现场演示顺序',upgraded?60:80,`${upgraded?'这一页留 60 秒做现场演示。':'这一页留 80 秒做现场演示。'}演示前先双击 run_demo.command，确认本机 5412 页面可以打开。先输入 Thank you，展示选中编号但默认阻止候选动作。再勾选研究预览，看到真实 MuJoCo 预渲染视频。接着输入 Many thanks 用 MiniLM 选择同一表达。最后输入 I do not want to wait 或 Please wait and take two pills，观察拒绝与清除上一动作。断网时模型和 MP4 已在本机即可做这两种方法的备份演示，LLM 默认不可用。网页的视频不是实时物理控制。`,['README.md','results/ui/demo-detail.jpg','tests/test_pipeline.py','tests/test_server.py'],'失败输入后屏幕是否仍残留上一条动作？');
}
// 11-12. Actual learning experiment and corpus acquisition, only in revision >= 4.
if(upgraded) {
 const s=slide('Learning trajectories from text and phase',11);
 text(s,'Frozen MiniLM (384) + Gaussian phase RBFs (40)',64,148,1149,42,30,C.teal,true);
 text(s,'Ridge regression fits 26 active joint coordinates.\nLimit projection and mimic reconstruction return 53 coordinates.',64,212,1140,76,27,C.ink);
 const rows=[['Candidate','Odd-frame RMSE','Max error']];
 for(const id of ['HELLO','THANK_YOU','PLEASE_WAIT']) {
  const m=learnedReport.fit[id].validation_indices;
  rows.push([id,m.active_rmse_rad.toFixed(6)+' rad',m.active_max_error_rad.toFixed(6)+' rad']);
 }
 table(s,rows,64,331,670,246,[218,239,213],23);
 text(s,'3 authored demonstrations',791,328,415,74,30,C.ink,true);
 text(s,'367 even frames for fitting\n365 odd frames for validation',791,423,419,90,25,C.muted);
 text(s,'Same-demonstration interpolation only',791,537,418,79,27,C.amber,true);
 text(s,'Fit and sampled geometry gates passed. Default route unchanged. ASL review pending.',64,625,1150,42,23,C.muted);
 note(s,11,'实际训练的小型轨迹模型',75,'这里报告已经完成的一次真实拟合，而不是未来计划。训练资料只有三条 agent 编写的轨迹，共 732 个高度相关的帧。367 个偶数帧拟合，365 个奇数帧验证，仍来自相同三条示范。冻结 MiniLM 把文字变成 384 维向量，加常数后与 40 个高斯相位基做张量积，用闭式岭回归拟合 26 个主动上肢坐标。W 形状为 385×40×26。剩余 15 个坐标保持 neutral，12 个 mimic 从动坐标按约束重建，因此输出 53 个关节坐标。它是学习型 RBF ridge 回归，不是深度生成模型。推理加载拟合权重，在新时间点重算，而不读取旧轨迹文件。表中误差在明确限位投影后计算；原预测小幅越界没有隐藏，六条主轨迹最大投影约 0.001978 rad，低于冻结 0.02 rad 门槛。三条原时长和三条加长百分之二十时长通过冻结几何门槛，但只检验已知示范内部的时间插值。没有新词、独立表演或 ASL 理解证据，默认旧演示保持不变。',['results/motion_learning/v1/report.json','results/motion_learning/v1/model.json','config/motion_learning_v1.json','docs/学习型轨迹模型.md'],'为什么 732 帧不能写成 732 条独立示范？');
}
if(upgraded) {
 const s=slide('How2Sign text records and missing motion targets',12);
 text(s,'35,263 metadata rows acquired and hashed',64,149,1141,47,34,C.teal,true);
 table(s,[['Official split','Annotation rows'],['Train',corpus.files.train.counts.annotation_rows.toLocaleString('en-US')],['Validation',corpus.files.val.counts.annotation_rows.toLocaleString('en-US')],['Test',corpus.files.test.counts.annotation_rows.toLocaleString('en-US')],['Total',corpus.aggregate_counts.annotation_rows.toLocaleString('en-US')]],64,238,545,326,[275,270],27);
 text(s,'Available locally',678,239,527,42,29,C.ink,true);
 text(s,'English text, sentence IDs\nand aligned timestamps',678,302,526,85,29,C.muted);
 text(s,'New video / pose / robot\nsupervision: 0',678,427,521,100,34,C.amber,true);
 text(s,'Next step: permitted motion targets, robot retargeting and independent demonstration splits.',64,618,1150,56,24,C.muted);
 note(s,12,'语料接入与升级缺口',60,'数据侧实际下载并校验 How2Sign 的三个重对齐文本文件，分别有 31165、1741 和 2357 条标注行，总计 35263 行。索引包含英文句子、ID 和对齐时间戳；行数与唯一句子 ID 数不同，唯一源句 ID 是 34438。我们没有新增视频、人体姿态或机器人动作监督，因此这三万多条没有进入上一页的轨迹模型训练。How2Sign 来源按 CC BY-NC 4.0 保留归属、原始字节和派生修改说明。下一步真正需要的监督是许可清楚的人体动作，再把手腕、指尖、掌向与身体关系重定向到机器人。验证也要按完整示范或适当 signer 隔离。下载更多文本或同一动作增加采样帧，不能替代独立动作数据。',['data/corpus_index/how2sign_realigned_v1/download_manifest.json','docs/语料规模与模型升级.md','https://how2sign.github.io/','https://github.com/how2sign/how2sign.github.io/tree/f85816c184662406bd8e0f338863b7c243763129','https://creativecommons.org/licenses/by-nc/4.0/'],'这 35,263 条里有哪些内容可以直接作为机器人关节监督？');
}
// 11 or 13. Ownership and remaining work
{
 const s=slide('Six owners and remaining work',upgraded?13:11);
 table(s,[['Owner','Current artifact','Next acceptance check'],['A1  Sources',upgraded?'Video notes and text index':'Video observations',upgraded?'Permitted motion targets and meaning review':'Full request reference and meaning review'],['A2  Motion',upgraded?'Trajectories and fitted RBF model':'Three candidate trajectories',upgraded?'Independent demonstrations and retargeting':'Handshape and view-by-view inspection'],['B1  Matching','Exact and local embeddings','New reviewed development data'],['B2  LLM','Reproducible negative result','New protocol before prompt changes'],['C1  Evaluation','Frozen cases and raw outputs','Independent labels and new test set'],['C2  Integration','Local demo and report','Second-computer reproduction']],64,154,1152,431,[211,394,547],22);
 text(s,'26–30 Oct: rehearsal materials.  31 Oct–2 Nov: final rehearsal.  3 Nov: slides due.',64,616,1144,48,24,C.teal,true);
 note(s,upgraded?13:11,'六人如何接手',upgraded?40:60,'分工按数据和接口而不是代码量划分。A1 确认来源支持什么含义，A2 实现受约束轨迹。B1 和 B2 只看开发集，把冻结版本交给 C1 评价。C2 汇总界面、跨电脑复现与演示。每人可以有一个 agent，但 agent 写出文件不等于同学掌握方法，大家都要能解释自己的输入输出和失败。建议 10 月底形成完整演示与备份，11 月 2 日前冻结提交版。课程原简报截止为 11 月 3 日，最终提交方式应按 Canvas 最新通知核对。',['docs/six-person-handoff.md','docs/实施路线.md','Course briefing, slide 4: submission of slides on November 3, 2026'],'下一次验收要看到什么文件或行为，不能只汇报“在做”。');
}
// 12 or 14. Conclusion
{
 const s=slide('Conclusions and open questions',upgraded?14:12);
 text(s,'Working engineering prototype',64,162,1089,54,37,C.teal,true);
 text(s,upgraded?'The default selector and candidate motion pipeline remain available.\nA fitted text–phase model now reproduces three authored trajectories.':'Finite ID selection and inspectable robot motion run locally.\nThe shared interface separates language errors from motion errors.',64,238,1124,101,29,C.ink);
 text(s,'Open language question',64,381,1087,53,37,C.teal,true);
 text(s,upgraded?'Three demonstrations support temporal interpolation evidence.\nNew-sign generalization and ASL comprehension remain untested.':'Video-informed geometry remains a candidate.\nASL comprehension and complete WAIT requests need further evidence.',64,454,1121,104,29,C.ink);
 text(s,upgraded?'Next evidence: real motion targets, independent demonstrations and meaning assessment.':'Next evidence: reviewed text labels, independent reproduction and meaning assessment.',64,614,1138,50,25,C.muted);
 note(s,upgraded?14:12,'闭环与问答',40,upgraded?'我们已经把项目从固定候选回放推进到一次真实学习实验：原有选择器保留，RBF ridge 将三条已有轨迹拟合为文字和相位函数，How2Sign 文本索引也已经实际接入。证据范围仍然清楚：旧 60 题测文字编号选择，新奇数帧验证测同示范时间插值，三万多元数据没有提供新增动作监督。下一步应获得许可明确的真实动作目标，并按独立示范划分，再测试 ASL 使用者能否理解。不能把低拟合误差说成掌握通用手语。':'回到开头的问题，我们已经完成可运行的有限编号选择和真实机器人运动学预览，并用统一协议记录了三种文字方法的差异。这个原型使错误可追踪，但当前证据还没有闭合语言可理解性。下一步优先补人工标签、另一台电脑复现，以及 ASL 使用者无字幕复述；如果无法找到使用者，就保留“视频参考的候选动作”这个结论。请大家在问答中把文本准确率、轨迹几何、真实控制与语言理解四类证据分开。',['README.md','results/acceptance.json','docs/source-review.md','docs/video-calibration.md',...(upgraded?['results/motion_learning/v1/report.json','data/corpus_index/how2sign_realigned_v1/download_manifest.json']:[])],'不要用“测试通过”回答语言理解或临床效果问题。');
}

await fs.writeFile(path.join(OUT,'speaker-notes.zh-CN.txt'),notes.map(n=>`第 ${n.slide} 页  ${n.title}（${n.seconds} 秒）\n\n${n.script}\n\n讲述检查：${n.check}\n来源：\n${n.sources.map(s=>'  '+s).join('\n')}`).join('\n\n────────────────────────────────\n\n'),'utf8');
await fs.writeFile(path.join(BUILD,'notes.json'),JSON.stringify(notes,null,2));
await fs.writeFile(path.join(BUILD,'font-policy.json'),JSON.stringify({basis:'design',families:[font]},null,2));
const provenance={revision,font,createdAt:new Date().toISOString(),frozenSummary:result+'/summary.json',sources:{}};
for(const f of [result+'/summary.json',result+'/raw.jsonl','scripts/build_course_slides.mjs','docs/source-review.md','docs/video-calibration.md',...(upgraded?['results/motion_learning/v1/report.json','results/motion_learning/v1/model.json','data/corpus_index/how2sign_realigned_v1/download_manifest.json']:[])]) provenance.sources[f]=createHash('sha256').update(await fs.readFile(path.join(ROOT,f))).digest('hex');
await fs.writeFile(path.join(BUILD,`provenance-${revision}.json`),JSON.stringify(provenance,null,2));
for (const [i,s] of p.slides.items.entries()) {
 const name=`slide-${String(i+1).padStart(2,'0')}`;
 const blob=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(OUT,'previews',name+'.png'),new Uint8Array(await blob.arrayBuffer()));
 const layout=await s.export({format:'layout'}); await fs.writeFile(path.join(BUILD,name+'.layout.json'),await layout.text());
 console.log('Rendered',i+1);
}
try {
 const pdf=await p.export({format:'pdf'});
 await fs.writeFile(path.join(OUT,`ME5412_Text_to_Robot_Signing_${revision}.pdf`),new Uint8Array(await pdf.arrayBuffer()));
} catch(error) {
 await fs.writeFile(path.join(BUILD,`pdf-export-${revision}.error.txt`),String(error.stack));
 const r=spawnSync(path.join(RUNTIME,'python/bin/python3'),[path.join(ROOT,'scripts/build_course_slides.py'),revision],{cwd:ROOT,encoding:'utf8'});
 if(r.status!==0) throw new Error('Static PDF fallback failed: '+r.stderr);
 console.log('Native PDF export unavailable; created a static PDF from reviewed slide PNGs.');
}
const candidate=path.join(BUILD,`candidate-${revision}.pptx`);await (await PresentationFile.exportPptx(p)).save(candidate);
const final=path.join(OUT,`ME5412_Text_to_Robot_Signing_${revision}.pptx`);
const report=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:final,pythonExecutable:path.join(RUNTIME,'python/bin/python3'),integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--cover-role','cover',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:slideCount,requiredNativeTableOwnerSlides:tableOwners,requiredNativeChartOwnerSlides:[8],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(BUILD,`validation-${revision}.json`)});
await fs.copyFile(path.join(BUILD,`validation-${revision}.json`),path.join(OUT,`validation-${revision}.json`));
await fs.copyFile(path.join(BUILD,`provenance-${revision}.json`),path.join(OUT,`provenance-${revision}.json`));
console.log(JSON.stringify({final,report,totalSeconds:notes.reduce((a,n)=>a+n.seconds,0)}));
