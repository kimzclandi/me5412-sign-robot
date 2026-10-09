# 可分享的网站展示版

**中文** · [English](README.en.md)

已有线上版本：https://me5412-robot-signing-lab.kimzc0103.chatgpt.site

此目录保存双语静态展示源码。本轮未重新发布线上站点；站点重建暂缓，最终展示方式由集成稳定后的交付需要决定。原分享版部署提交为 `2687479cd60b3f37747f7d4ec33dffbb225716c9`，原地址保留原样。这里不包含 Sites 账号配置、写入凭据或部署状态。

从仓库根目录运行：

```bash
python3 -m http.server 5414 --bind 127.0.0.1 --directory website/dist
```

本地打开 http://127.0.0.1:5414。八个栏目支持流程查看、固定短语匹配、已保存的机器人视频、轨迹数据检查、分工、评价和汇报下载。MiniLM、LLM 和新的轨迹生成在主项目的 Python 实验台运行；此静态站不会进行新的模型推理。

网页顶部语言切换覆盖静态文字、动态结果、图表及无障碍标签；同一浏览器记住选择，`?lang=en` 可直接打开英文。说明下载提供成对中英版本，实验原始数据保持原样。

`dist` 已通过本地资源引用与 JavaScript 语法检查，可用静态托管提供。网站当前独立发布；推送此 GitHub 仓库不会自动更新线上网站。不要上传 `.openai` 或 `.sites-runtime` 中的个人部署配置。

来源与使用范围见 [attribution.txt](dist/materials/attribution.txt)。
