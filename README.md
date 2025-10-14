Gemini Search 函数工具

概述
- 通过 Google Generative AI SDK 调用 Gemini 2.0 Flash，并启用原生 Google Search 工具进行联网搜索。
- 将检索后的“要点摘要 + 引用来源（标题+URL）”作为工具输出，注入到 AstrBot 对话中，供主模型继续整合与回答。

配置
- 在插件配置页填写：
	- api_key: 支持多个 Google API Key
	- api_base_url: 可选，默认 https://generativelanguage.googleapis.com
	- model: 默认为 gemini-2.0-flash
	- random_api_key_selection: 是否随机选择 Key（否则按轮询）

使用
- 启动 AstrBot 后，工具会自动启用（名称：gemini_search）。
- 当当前模型具备函数调用能力时，Agent 会在需要联网检索时自动调用该工具。
- 也可以在 Prompt 中显式引导模型调用 gemini_search 来获取检索摘要与来源列表。

注意
- 需要为项目安装 google-genai 依赖（推荐按仓库指引使用 uv 安装）。
