# 第一组实施指南：英文句子转 ASL 词序（最小版）

Oct 26, 2026 · @patrick

第一组要做一个离线运行的转换模块：医护人员输入一句英文，它输出按 ASL 语序排好、每个词都在词表里的手语词序列，例如 `Where does it hurt?` → `YOU HURT WHERE`。词表和测试句已经写好，照这份指南做即可。

## 一、你们在演示里的位置

演示场景：聋人在医院看病，现场没有手语翻译。老师扮演医护人员输入英文，机器人把话打成手语。整条流程在一台 Mac 上离线运行：

1. 老师在网页输入 `Where does it hurt?`
2. **第一组**：本地大模型把它转成 `YOU HURT WHERE`，代码检查每个词都在词表里
3. 网页显示“机器人将打：YOU · HURT · WHERE”给老师确认
4. 第二组的词库按词取出轨迹，第三组把几段轨迹衔接成一句
5. MuJoCo 里的 G1 机器人打出整句

你们只负责第 2 步，输出到词名为止，不碰动作。

### 要交的 4 样东西

| # | 交付 | 位置 |
| --- | --- | --- |
| 1 | 词表（已写好，和第二组核对 gloss 名即可） | `data/vocab/hospital_v1.json` |
| 2 | 在演示 Mac 上离线运行的大模型，和启动说明 | `docs/local-llm.md` |
| 3 | 转换函数 `text_to_gloss(sentence)` | `src/sign_robot/gloss.py` |
| 4 | 20 条测试句（已写好）和一键检查脚本 | `data/gloss_eval/gloss_test.csv`、`scripts/check_gloss.py` |

词表和测试句的文件已经随本指南一起发给你们（`hospital_v1.json`、`gloss_test.csv`），放进仓库对应位置就行。在自己的分支上做，例如 `group1/text-to-gloss`，做完开 PR。

## 二、词表：35 个词

大模型只能输出这 35 个 gloss。“英文说法”是老师可能用到、应该对应到这个词的说法，写进提示词里。“动作来源”由第二组负责，列出来只是让你们知道哪些词已经有动作。

| gloss | 中文 | 英文说法 | 动作来源 |
| --- | --- | --- | --- |
| HELLO | 你好 | hello, hi, hey | Studio Galt（待转换） |
| PLEASE | 请 | please | Studio Galt（待转换） |
| THANK-YOU | 谢谢 | thank you, thanks | SignAvatars |
| SORRY | 对不起 | sorry, apologize, excuse me | SignAvatars |
| YES | 是 | yes, yeah, sure | SignAvatars |
| NO | 不 | no, nope | SignAvatars |
| YOU | 你 | you | Studio Galt（已转换） |
| YOUR | 你的 | your, yours | SignAvatars |
| ME | 我 | I, me, myself | SignAvatars |
| DEAF | 聋 | deaf | SignAvatars |
| DOCTOR | 医生 | doctor, physician, Dr | SignAvatars |
| NURSE | 护士 | nurse | SignAvatars |
| INTERPRETER | 翻译 | interpreter, sign language interpreter, translator | SignAvatars |
| APPOINTMENT | 预约 | appointment, booking, reservation | Studio Galt（待转换） |
| MEDICINE | 药 | medicine, medication, pills, tablets, drug | SignAvatars |
| STOMACH | 肚子 | stomach, belly, tummy | SignAvatars |
| HEADACHE | 头疼 | headache | SignAvatars |
| HAVE | 有 | have, has, got | SignAvatars |
| NEED | 需要 | need, must, have to, require | SignAvatars |
| WAIT | 等 | wait, hold on, one moment | SignAvatars |
| COME | 来 | come, coming, be here, arrive | Studio Galt（已转换） |
| HURT | 疼 | hurt, pain, ache, sore, painful | SignAvatars |
| BREATHE-DEEP | 深呼吸 | take a deep breath, breathe deeply, breathe in | Studio Galt（待转换） |
| BLOOD-DRAW | 抽血 | draw blood, blood test, blood sample | Studio Galt（待转换） |
| TAKE | 拿、服用 | take | Studio Galt（已转换） |
| UNDERSTAND | 明白 | understand, get it | SignAvatars |
| WRITE | 写 | write, write down, note down | SignAvatars |
| NOT | 不（否定） | not, don't, doesn't, didn't | SignAvatars |
| NOW | 现在 | now, right now, immediately | SignAvatars |
| SOON | 马上 | soon, shortly, in a minute, in a moment | SignAvatars |
| LATER | 稍后 | later, after a while | SignAvatars |
| TOMORROW | 明天 | tomorrow | SignAvatars |
| MORNING | 早上 | morning, in the morning | SignAvatars |
| NIGHT | 晚上 | night, evening, at night, bedtime | SignAvatars |
| WHERE | 哪里 | where | SignAvatars |

词表文件 `hospital_v1.json` 里每个词长这样：

```json
{"gloss": "HURT", "category": "verb", "source": "signavatars", "motion_ready": false, "english": ["hurt", "pain", "ache", "sore", "painful"]}
```

- `motion_ready`：第二组把这个词的轨迹做好后改成 `true`。开发和测试时用全部 35 个词；演示时只允许输出 `motion_ready` 为 `true` 的词，用一个参数切换。
- 想增删词或改 gloss 名，先和第二组商量，两边名字必须一致。

## 三、实现步骤

### 第 1 步：在演示 Mac 上跑起本地大模型

- 模型：7B 级、指令微调过的模型，例如 Qwen2.5-7B-Instruct 的 4-bit 量化版（大约 5 GB）。
- 运行方式二选一：`mlx_lm.server`（Apple 芯片最快）或 llama.cpp 的 `llama-server`。两者都能在本机开一个 OpenAI 兼容的接口，例如 `http://127.0.0.1:5413/v1/chat/completions`。
- 仓库里 `src/sign_robot/llm.py` 已经写好了只连本机接口的请求代码，可以直接复用或参考。
- 在演示用的那台 Mac 上实测：内存够不够、一句话要几秒。把安装、下载、启动命令和实测结果写进 `docs/local-llm.md`，保证别人照着能跑起来。

### 第 2 步：提示词

下面是模板，`{VOCAB}` 由代码从 `hospital_v1.json` 生成，每行一个词，如 `HURT: hurt, pain, ache, sore, painful`。可以改措辞，但规则和例子要保留。

```
You are an American Sign Language (ASL) interpreter in a hospital. A hearing medical worker types an English sentence; you convert it into a sequence of ASL glosses for a robot to sign to a Deaf patient.

You may ONLY use these glosses (gloss: English words it covers):
{VOCAB}

Rules:
1. Translate the meaning, not word by word. Use a listed gloss when the English word is a synonym.
2. Drop words ASL does not sign: a, an, the, is, are, am, be, do, does, did, will, would, can, could, to, it, this, that, of, at, in, on, for, and.
3. Put time words (NOW, SOON, LATER, TOMORROW, MORNING, NIGHT) at the start.
4. Put the topic first, then the comment. Example: MEDICINE, MORNING NIGHT TAKE.
5. Put question words (WHERE) at the end.
6. Put NOT after the verb: ME UNDERSTAND NOT.
7. Say pronouns explicitly (YOU, ME, YOUR).
8. If a meaning that matters cannot be expressed with the listed glosses (for example X-ray, insurance, a form, an exact time or number, an allergy), do not guess: return unsupported and list those words in "unknown".

Return ONLY one JSON object, no other text:
{"status": "ok" or "unsupported", "glosses": [...], "question": true or false, "dropped": [...], "unknown": [...]}

Examples:
Input: Where does it hurt?
Output: {"status": "ok", "glosses": ["YOU", "HURT", "WHERE"], "question": true, "dropped": ["does", "it"], "unknown": []}

Input: Take this medicine in the morning and at night.
Output: {"status": "ok", "glosses": ["MEDICINE", "MORNING", "NIGHT", "TAKE"], "question": false, "dropped": ["this", "in", "the", "and", "at"], "unknown": []}

Input: The nurse will draw your blood now.
Output: {"status": "ok", "glosses": ["NOW", "NURSE", "BLOOD-DRAW"], "question": false, "dropped": ["the", "will", "your"], "unknown": []}

Input: Sorry, I don't understand.
Output: {"status": "ok", "glosses": ["SORRY", "ME", "UNDERSTAND", "NOT"], "question": false, "dropped": [], "unknown": []}

Input: Do you need an X-ray?
Output: {"status": "unsupported", "glosses": [], "question": true, "dropped": [], "unknown": ["X-ray"]}
```

注意：例子里的句子不要和第四节的测试句重复太多，否则测试会虚高。上面 5 个例子里有 3 个和对话脚本相同，可以换成你们自己造的句子。

### 第 3 步：`text_to_gloss` 函数

```python
def text_to_gloss(sentence: str, demo_only: bool = False) -> dict:
    # 1. 空输入或超过 200 字符 -> {"status": "unsupported", ...}
    # 2. 读取词表；demo_only=True 时只保留 motion_ready 的词
    # 3. 用词表填好提示词，请求本地模型（temperature=0，超时 15 秒）
    # 4. 校验模型输出（见下表），任何一项不过就返回 {"status": "error", "reason": ...}
    # 5. 返回结果，加上 "latency_ms"
```

校验规则（不能只信模型）：

| 检查 | 不通过时 |
| --- | --- |
| 输出能解析成 JSON，字段齐全 | `error`，原因 `invalid_json` |
| `status` 只能是 `ok` 或 `unsupported` | `error` |
| `ok` 时 `glosses` 非空，每个词都在当前词表里 | `error`，原因 `unknown_gloss` |
| `ok` 时词数不超过 10 | `error` |
| `unsupported` 时 `glosses` 为空 | `error` |
| 模型连不上或超时 | `error`，原因 `llm_unavailable` |

不自动重试，也不从模型的文字里硬抽词。`error` 和 `unsupported` 时界面不播放任何动作。

## 四、测试句、检查脚本和验收

### 20 条测试句（`gloss_test.csv`）

参考答案里用 `|` 分隔的是多种都算对的语序。

| id | 类型 | 英文 | 参考答案 | 问句 |
| --- | --- | --- | --- | --- |
| s1 | 脚本原句 | Hello, do you have an appointment? | HELLO YOU APPOINTMENT HAVE | 是 |
| s2 | 脚本原句 | Do you need an interpreter? | YOU NEED INTERPRETER | 是 |
| s3 | 脚本原句 | Please wait, the doctor will come soon. | PLEASE WAIT DOCTOR COME SOON | 否 |
| s4 | 脚本原句 | Where does it hurt? | YOU HURT WHERE | 是 |
| s5 | 脚本原句 | Take a deep breath. | BREATHE-DEEP | 否 |
| s6 | 脚本原句 | The nurse will draw your blood now. | NOW NURSE BLOOD-DRAW | 否 |
| s7 | 脚本原句 | Take this medicine in the morning and at night. | MEDICINE MORNING NIGHT TAKE | 否 |
| s8 | 脚本原句 | Do you understand? | YOU UNDERSTAND | 是 |
| s9 | 脚本原句 | Thank you. | THANK-YOU | 否 |
| p1 | 换说法 | Where is the pain? | YOU HURT WHERE \| HURT WHERE | 是 |
| p2 | 换说法 | Hi, have you booked an appointment? | HELLO YOU APPOINTMENT HAVE | 是 |
| p3 | 换说法 | The doctor will be here shortly, please wait. | DOCTOR COME SOON PLEASE WAIT \| PLEASE WAIT DOCTOR COME SOON | 否 |
| p4 | 换说法 | Is an interpreter needed? | YOU NEED INTERPRETER \| INTERPRETER NEED | 是 |
| p5 | 换说法 | Take your pills every morning and every night. | MEDICINE MORNING NIGHT TAKE \| MORNING NIGHT MEDICINE TAKE | 否 |
| p6 | 换说法 | Sorry, I don't understand. Can you write it down? | SORRY ME UNDERSTAND NOT PLEASE WRITE \| SORRY ME UNDERSTAND NOT YOU WRITE | 是 |
| o1 | 库外 | Do you need an X-ray? | 拒绝 | 是 |
| o2 | 库外 | Please show me your insurance card. | 拒绝 | 否 |
| o3 | 库外 | Your appointment is at 3:30 pm. | 拒绝 | 否 |
| o4 | 库外 | Are you allergic to penicillin? | 拒绝 | 是 |
| o5 | 库外 | Please fill in this form. | 拒绝 | 否 |

这份参考答案是按第三节的规则写的，没有经过懂 ASL 的人审核。组里如果有人懂 ASL 或能找到懂的人，请先让他们看一遍，可以增加合理语序。

### 检查脚本 `scripts/check_gloss.py`

- 逐条读 `gloss_test.csv`，调用 `text_to_gloss`。
- 判定对错：
  - 应拒绝的句子：`status` 是 `unsupported` 算对。
  - 其余句子：`status` 是 `ok`，并且 `glosses` 用空格连起来后和任一参考答案完全一致。
  - `question` 单独记录，不影响对错。
- 每条打印：id、对或错、模型输出、参考答案、耗时。最后打印三类各对了几条、最慢一条的耗时。
- 结果存到 `results/gloss_check/<时间>.json`，不覆盖之前的结果。

### 验收标准

- [ ] 脚本原句 9/9 正确
- [ ] 库外句 5/5 被拒绝
- [ ] 换说法 6 条：如实报告对了几条，错的逐条说明原因
- [ ] 任何情况下都不输出词表外的词（校验代码保证）
- [ ] 断开本地模型时返回 `error`，不崩溃
- [ ] 在演示 Mac 上实测每句耗时，写进 `docs/local-llm.md`
- [ ] 以上代码和文件在 `group1/text-to-gloss` 分支开 PR

换说法对不上时，先改提示词里的规则和例子，不要把测试句原样抄进例子里。做完这一版，第三组就能接上界面和动作模块。时间够的话，再按[完整版任务说明](https://claude.ai/artifact/ANMMFw1CUpbiAj5mr2nYrX)补规则基线对比和独立测试集。
