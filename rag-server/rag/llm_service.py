import os
import json

import requests
from dotenv import load_dotenv


load_dotenv()


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"


SYSTEM_PROMPT = """
你是一个基于用户文档回答问题的知识库助手。

回答必须严格遵守以下规则：

1. 只能依据提供的参考资料回答。
2. 不允许补充参考资料中不存在的事实。
3. 如果参考资料不足以回答问题，明确回答“根据当前文档无法确定”。
4. 回答关键事实时使用 [1]、[2] 等编号标注对应的资料来源。
5. 引用编号必须与提供的 [资料 1]、[资料 2] 等编号对应。
6. 不得编造文件名、页码、数据、人物或其他来源信息。
7. 如果多个资料能够共同支持一个结论，可以同时引用，例如 [1][2]。
8. 回答优先直接回应用户问题，避免复述无关资料。
""".strip()


class LLMService:
    """
    大语言模型生成服务。

    当前使用 DeepSeek Chat Completions API。
    LLM 仅负责根据 Retriever 提供的 Context 生成答案，
    不负责文档解析和检索。
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = (
            api_key
            or os.getenv("DEEPSEEK_API_KEY")
        )

        self.base_url = (
            base_url
            or os.getenv(
                "DEEPSEEK_BASE_URL",
                DEFAULT_BASE_URL,
            )
        ).rstrip("/")

        self.model = (
            model
            or os.getenv(
                "DEEPSEEK_MODEL",
                DEFAULT_MODEL,
            )
        )

    def generate(
        self,
        question: str,
        context: str,
    ) -> str:
        """
        根据检索出的 Context 回答用户问题。
        """

        question = question.strip()
        context = context.strip()

        if not question:
            raise ValueError("question 不能为空")

        if not context:
            return "根据当前文档无法确定。"

        if not self.api_key:
            raise ValueError(
                "未配置 DEEPSEEK_API_KEY"
            )

        user_prompt = self._build_user_prompt(
            question=question,
            context=context,
        )

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization":
                    f"Bearer {self.api_key}",
                "Content-Type":
                    "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                "thinking": {
                    "type": "disabled"
                },
                "max_tokens": 800,
                "stream": False,
            },
            timeout=60,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                "LLM 请求失败："
                f"{response.status_code} "
                f"{response.text}"
            ) from exc

        data = response.json()

        try:
            answer = (
                data["choices"][0]
                ["message"]["content"]
            )
        except (
            KeyError,
            IndexError,
            TypeError,
        ) as exc:
            raise RuntimeError(
                f"LLM 返回格式异常：{data}"
            ) from exc

        answer = answer.strip()

        if not answer:
            raise RuntimeError(
                "LLM 返回了空回答"
            )

        return answer

    def generate_stream(
            self,
            question: str,
            context: str,
    ):
        """
        根据检索出的 Context 流式生成回答。

        每次 yield 一个模型生成的文本片段。
        """

        question = question.strip()
        context = context.strip()

        if not question:
            raise ValueError(
                "question 不能为空"
            )

        if not context:
            yield "根据当前文档无法确定。"
            return

        if not self.api_key:
            raise ValueError(
                "未配置 DEEPSEEK_API_KEY"
            )

        user_prompt = self._build_user_prompt(
            question=question,
            context=context,
        )

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization":
                    f"Bearer {self.api_key}",
                "Content-Type":
                    "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                "thinking": {
                    "type": "disabled"
                },
                "max_tokens": 800,
                "stream": True,
            },
            stream=True,
            timeout=60,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                "LLM 流式请求失败："
                f"{response.status_code} "
                f"{response.text}"
            ) from exc

        for line in response.iter_lines(
                decode_unicode=True
        ):
            if not line:
                continue

            # DeepSeek 可能发送：
            # : keep-alive
            if line.startswith(":"):
                continue

            if not line.startswith("data:"):
                continue

            data_text = (
                line[len("data:"):]
                .strip()
            )

            if data_text == "[DONE]":
                break

            try:
                data = json.loads(
                    data_text
                )
            except json.JSONDecodeError:
                continue

            choices = data.get(
                "choices",
                []
            )

            if not choices:
                continue

            delta = (
                choices[0]
                .get("delta", {})
                .get("content")
            )

            if delta:
                yield delta

    @staticmethod
    def _build_user_prompt(
        question: str,
        context: str,
    ) -> str:
        return f"""
以下是从用户文档中检索出的参考资料：

{context}

用户问题：
{question}

请严格依据以上参考资料回答问题，并使用 [1]、[2] 等编号标注答案依据。
""".strip()
