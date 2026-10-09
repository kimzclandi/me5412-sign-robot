# 可分享的网站展示版

在线访问：https://me5412-robot-signing-lab.kimzc0103.chatgpt.site

此目录保存 2026-10-09 已发布分享版的静态文件。对应独立部署源码提交为 `2687479cd60b3f37747f7d4ec33dffbb225716c9`；这里不包含 Sites 账号配置、写入凭据或部署状态。

从仓库根目录运行：

```bash
python3 -m http.server 5414 --bind 127.0.0.1 --directory website/dist
```

本地打开 http://127.0.0.1:5414。八个栏目支持流程查看、固定短语匹配、已保存的机器人视频、轨迹数据检查、分工、评价和汇报下载。MiniLM、LLM 和新的轨迹生成在主项目的 Python 实验台运行；此静态站不会进行新的模型推理。

`dist` 已通过本地资源引用与 JavaScript 语法检查，可用静态托管提供。网站当前独立发布；推送此 GitHub 仓库不会自动更新线上网站。不要上传 `.openai` 或 `.sites-runtime` 中的个人部署配置。

来源与使用范围见 [attribution.txt](dist/materials/attribution.txt)。
