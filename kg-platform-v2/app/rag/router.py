"""LLM Router for GraphRAG.

Determines whether a user's natural‑language query should be answered by:
* **graph**   – pure Neo4j structural lookup
* **vector**  – pure semantic Milvus search
* **hybrid**  – combination of both (default)

The router uses the same LLM abstraction (`app.core.llm.LLM`) that powers other
components.  It sends a clearly‑structured prompt (see PRD section *graphrag_router*)
and expects a JSON response of the form::

    {"graph": true/false, "vector": true/false}

If parsing fails or the LLM is unavailable, the router falls back to the
*hybrid* mode (both flags true) and logs a warning.
"""

import json
from typing import Dict

from ..core.llm import LLM
from ..core.logger import get_logger

_logger = get_logger(__name__)

# Prompt taken from the product requirements (PRD) – it asks the model to decide
# which retrieval modality is needed for the given question.
_ROUTER_PROMPT = """
你是查询路由器。

判断问题需要：
1. 图数据库查询（graph）
2. 向量检索（vector）
3. 或两者结合（hybrid）

**示例**（请参考以下示例来决定返回的 JSON）:

示例 1（纯图查询）:
问题: "请展示张三所在部门的所有上级部门。"
期望返回: {"graph": true, "vector": false}

示例 2（纯向量检索）:
问题: "与以下句子最相似的三段文字是什么？\n‘企业知识图谱可以帮助结构化管理信息’"
期望返回: {"graph": false, "vector": true}

示例 3（混合查询）:
问题: "张三在A公司的职位是什么？并给出该职位的相似岗位描述。"
期望返回: {"graph": true, "vector": true}

输出JSON：
{
  "graph": true/false,
  "vector": true/false
}

问题：
{question}
"""


class LLMRouter:
    """Encapsulates the routing logic.

    The public method :meth:`route` returns a dict with boolean flags ``graph``
    and ``vector``.  ``hybrid`` is simply ``graph and vector`` – callers can
    decide whether to treat the case ``graph=False, vector=False`` as an error.
    """

    def __init__(self):
        self.llm = LLM()

    def _call_llm(self, question: str) -> str:
        prompt = _ROUTER_PROMPT.format(question=question)
        return self.llm.chat(prompt)

    def _parse_response(self, raw: str) -> Dict[str, bool]:
        data = self.llm._parse_response(raw)
        if not data:
            return {"graph": True, "vector": True}
        graph = bool(data.get("graph", True))
        vector = bool(data.get("vector", True))
        return {"graph": graph, "vector": vector}

    def route(self, question: str) -> Dict[str, bool]:
        """Return routing decision for *question*.

        The result always contains the keys ``graph`` and ``vector``.
        """
        try:
            raw = self._call_llm(question)
            return self._parse_response(raw)
        except Exception as e:
            _logger.error(f"LLMRouter unexpected error: {e}")
            return {"graph": True, "vector": True}
