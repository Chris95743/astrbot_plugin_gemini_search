import random
from typing import Optional

import astrbot.api.star as star
from astrbot.api import llm_tool, logger
from astrbot.api.event import AstrMessageEvent

# Google GenAI SDK
from google import genai
from google.genai import types


class Main(star.Star):
	"""
	使用 Gemini 2.0 Flash + Google Search 原生工具进行联网检索。
	在函数工具中执行检索与汇总，返回结果文本，框架会把该文本作为 tool 消息注入当前对话，
	供主 LLM 后续综合使用。
	"""

	def __init__(self, context: star.Context, config=None) -> None:
		self.context = context
		# AstrBot 会根据 _conf_schema.json 构造 config（AstrBotConfig），此处按 dict 访问
		self.config = config or {}
		self._rr_index = 0  # 轮询下标
		self._clients: dict[str, genai.Client] = {}

	async def initialize(self):
		# 默认启用工具
		self.context.activate_llm_tool("gemini_search")
		logger.info("[gemini_search] 函数工具已启用")

	@llm_tool("gemini_search")
	async def gemini_search(self, event: AstrMessageEvent, query: str) -> str:
		"""这是一个“联网搜索”的函数工具（工具名：gemini_search）。当需要获取互联网上的实时/最新信息时，你必须调用本工具进行搜索。

		Args:
			query(string): 简要说明用户希望检索的查询内容

		Returns:
			str: 要点摘要与引用来源，作为 tool 消息注入上下文
		"""
		try:
			client = self._get_client()
		except Exception as e:
			logger.error(f"[gemini_search] 初始化客户端失败: {e}")
			return "请先在插件配置中填写有效的 Gemini API Key。"

		model = self.config.get("model", "gemini-2.0-flash")

		# 启用原生 Google Search 工具
		config = types.GenerateContentConfig(
			tools=[types.Tool(google_search=types.GoogleSearch())],
			temperature=0.2,
		)

		prompt = (
			"你是检索聚合助手。请使用 Google Search 工具对下述问题进行检索，"
			"产出包含：\n"
			"1) 关键要点的条目式摘要；\n"
			"2) 参考来源的列表（标题 + URL）。\n"
			"请避免冗长描述，直接给出结论与可靠来源。\n"
			"问题：" + query
		)

		try:
			resp = await client.models.generate_content(
				model=model,
				contents=prompt,
				config=config,
			)
			text = getattr(resp, "text", None) or self._extract_text(resp)
			return text.strip() if text else "未从检索中获得可用文本结果。"
		except Exception as e:
			logger.error(f"[gemini_search] 调用失败: {e}")
			return f"检索失败：{e}"

	def _get_client(self):
		"""根据配置选择 API Key，并创建/复用异步 client。支持随机或轮询策略。"""
		keys = self.config.get("api_key", []) or []
		if not keys:
			raise RuntimeError("请在插件配置中填写至少一个 Google API Key。")

		use_random = bool(self.config.get("random_api_key_selection", False))
		if use_random:
			key = random.choice(keys)
		else:
			key = keys[self._rr_index % len(keys)]
			self._rr_index += 1

		if key in self._clients:
			return self._clients[key]

		api_base = self.config.get(
			"api_base_url", "https://generativelanguage.googleapis.com"
		)
		if api_base.endswith("/"):
			api_base = api_base[:-1]

		http_options = types.HttpOptions(
			base_url=api_base,
		)
		client = genai.Client(api_key=key, http_options=http_options).aio
		self._clients[key] = client
		return client

	@staticmethod
	def _extract_text(resp) -> Optional[str]:
		"""兼容性提取：把 candidates/parts 文本拼起来。"""
		try:
			if not resp or not getattr(resp, "candidates", None):
				return None
			parts = []
			for c in resp.candidates:
				content = getattr(c, "content", None)
				if not content or not getattr(content, "parts", None):
					continue
				for p in content.parts:
					t = getattr(p, "text", None)
					if t:
						parts.append(t)
			return "\n".join(parts) if parts else None
		except Exception:
			return None



