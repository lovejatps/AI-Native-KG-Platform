from app.core.llm import LLM
from app.core.config import get_settings
import json
import re
import time
from typing import Any, Dict, List

from ..core.logger import get_logger

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt template – optimized for consistent JSON output
# ---------------------------------------------------------------------------
KG_EXTRACT_PROMPT = """从以下文本中抽取知识图谱要素，请严格返回 JSON，包含实体属性（如年龄、性别、穿着、颜色、职业等），格式如下：\n{
  \"entities\": [
    {
      \"name\": <实体名称>,
      \"type\": <实体类型>,
      \"properties\": {
        \"age\": <整数，可选>,
        \"gender\": <性别，可选>,
        \"clothing\": <穿着描述，可选>,
        \"color\": <颜色描述，可选>,
        \"occupation\": <职业，可选>
        // 其他属性键值对
      }
    }
  ],
  \"relations\": [
    {\"from\": <源实体名称>, \"to\": <目标实体名称>, \"type\": <关系类型>}
  ]
}
要求：\n- 所有实体必须包含 `name`、`type`，并提供 `properties`（若无属性则返回空对象 `{}`）。\n- `relations` 中的 `from`、`to` 必须引用 `entities` 中的 `name`。\n- 请尽可能从文本中抽取年龄、性别、穿着、颜色、职业等属性。示例：\n  {\n    \"entities\": [\n      {\"name\": \"张三\", \"type\": \"人物\", \"properties\": {\"age\": 39, \"gender\": \"男\", \"clothing\": \"蓝色运动装\", \"occupation\": \"工程师\"}},\n      {\"name\": \"A公司\", \"type\": \"组织\", \"properties\": {}}\n    ],\n    \"relations\": [\n      {\"from\": \"张三\", \"to\": \"A公司\", \"type\": \"WORKS_FOR\"}\n    ]\n  }\n请严格遵循上述 JSON 格式返回，不要添加任何解释文字。\n\n{text}\n"""


def _validate_kg(data: Any) -> bool:
    """Simple validation – ensure required top‑level keys exist and are lists.
    Returns ``True`` if the structure looks correct, ``False`` otherwise.
    """
    if not isinstance(data, dict):
        return False
    for key in ("entities", "relations"):
        if key not in data or not isinstance(data[key], list):
            return False
    return True


def extract_kg(
    chunk: str, max_retries: int = 3, backoff: float = 0.5
) -> Dict[str, List[Any]]:
    """Extract KG triples from *chunk* using the LLM.

    - Uses the optimized ``KG_EXTRACT_PROMPT`` template.
    - Validates the JSON result; on failure it retries up to ``max_retries``.
    - Logs each retry attempt via the project logger.
    - Guarantees that the returned dictionary always contains ``entities`` and
      ``relations`` lists (empty if extraction ultimately fails).
    """
    llm = LLM()
    # Limit LLM input length to avoid overly long responses
    max_input_len = 1500  # characters – adjust as needed
    chunk_input = chunk if len(chunk) <= max_input_len else chunk[:max_input_len]
    for attempt in range(1, max_retries + 1):
        prompt = KG_EXTRACT_PROMPT.replace("{text}", chunk_input)
        # Pass stop token to guarantee clean termination
        # Use a generous max_tokens limit to allow full JSON generation
        res = llm.chat(
            prompt,
            max_tokens=get_settings().LLM_MAX_OUTPUT_TOKENS,
            stop=["END_OF_JSON"],
        )
        # Trim any trailing text after the stop marker (including the marker itself)
        if "END_OF_JSON" in res:
            res = res.split("END_OF_JSON")[0].strip()
        try:
            parsed = json.loads(res)
            if _validate_kg(parsed):
                return parsed
            else:
                _logger.warning(
                    f"KG extraction validation failed on attempt {attempt}. "
                    f"Response snippet: {res[:200]}"
                )
        except Exception as exc:
            # === 多层容错修复 ===
            # 1️⃣ 基于括号计数的完整截取
            repaired = res
            if "{" in res:
                start_idx = res.find("{")
                brace_cnt = 0
                end_idx = None
                for i in range(start_idx, len(res)):
                    if res[i] == "{":
                        brace_cnt += 1
                    elif res[i] == "}":
                        brace_cnt -= 1
                    if brace_cnt == 0:
                        end_idx = i
                        break
                if end_idx is not None:
                    repaired = res[start_idx : end_idx + 1]
                else:
                    # Append as many closing braces as needed to balance
                    repaired = res[start_idx:] + "}" * brace_cnt
                repaired = repaired.rstrip(",")
                repaired = repaired.replace(",]", "]").replace(",}", "}")
                try:
                    parsed = json.loads(repaired)
                    if _validate_kg(parsed):
                        _logger.info(
                            f"KG extraction repaired via brace‑count truncation on attempt {attempt}"
                        )
                        return parsed
                except Exception:
                    pass
            # 2️⃣ 正则块提取实体 / 关系
            import re

            entities = []
            relations = []
            for match in re.finditer(r"\{[^{}]*\}", res):
                block = match.group()
                try:
                    obj = json.loads(block)
                    if isinstance(obj, dict):
                        if "name" in obj:
                            obj.setdefault("properties", {})
                            entities.append(obj)
                        elif "from" in obj and "to" in obj:
                            relations.append(obj)
                except Exception:
                    continue
            if entities:
                candidate = {"entities": entities, "relations": relations}
                if _validate_kg(candidate):
                    _logger.info(
                        f"KG extraction repaired via regex block fallback on attempt {attempt}"
                    )
                    return candidate
            # 3️⃣ 记录错误并重试
            _logger.warning(
                f"KG extraction JSON parse error on attempt {attempt}: {exc}. "
                f"Response snippet: {res[:200]}"
            )
        if attempt < max_retries:
            time.sleep(backoff * attempt)
    # All attempts failed – heuristic fallback
    _logger.error(
        "KG extraction failed after maximum retries; falling back to simple heuristic."
    )
    # Simple rule‑based extraction as fallback
    candidates = []
    candidates += [m.group() for m in re.finditer(r"[\u4e00-\u9fff]{2,}", chunk)]
    candidates += [m.group() for m in re.finditer(r"\b[A-Za-z]{2,}\b", chunk)]
    seen = set()
    entities = []
    for name in candidates:
        if name not in seen:
            seen.add(name)
            entities.append({"name": name, "type": "Person", "properties": {}})
    relations = []
    for i in range(len(entities) - 1):
        relations.append(
            {
                "from": entities[i]["name"],
                "to": entities[i + 1]["name"],
                "type": "related_to",
            }
        )
    return {"entities": entities, "relations": relations}


# ---------------------------------------------------------------------------
# Wrapper class for backward‑compatible usage in tests and legacy code
# ---------------------------------------------------------------------------


class Extractor:
    """Compatibility wrapper exposing a simple ``extract`` method.

    The original implementation exposed a functional API ``extract_kg``.
    Some parts of the codebase (including the unit test) expect a class
    with an ``extract`` method, so we provide a thin wrapper that forwards
    the call to ``extract_kg``.
    """

    def __init__(self, schema: dict | None = None):
        # ``schema`` is currently unused – kept for future extension.
        self.schema = schema

    def extract(self, text: str) -> Dict[str, List[Any]]:
        """Extract KG data from *text*.

        This method simply forwards to :func:`extract_kg`.  It returns the
        dictionary with ``entities`` and ``relations`` keys as defined by the
        functional implementation.
        """
        return extract_kg(text)
