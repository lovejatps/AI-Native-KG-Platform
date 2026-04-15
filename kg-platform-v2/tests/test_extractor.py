# -*- coding: utf-8 -*-
"""
Simple unit test for the Extractor class.
It verifies that a short Chinese paragraph can be extracted into
structured entities using the LLM singleton.
"""

import json
import unittest

from app.ingestion.extractor import Extractor

# A tiny example paragraph – should yield at least one entity (e.g., a person)
SAMPLE_TEXT = """
阿禾在青竹峰上练气，遇到暴雨，用竹片支撑折断的竹子，最终领悟到静气守心的道理。
"""


class TestExtractor(unittest.TestCase):
    def setUp(self) -> None:
        # Use default schema (None) – the extractor will ask the LLM for JSON output.
        self.extractor = Extractor()

    def test_basic_extraction(self):
        result = self.extractor.extract(SAMPLE_TEXT)
        # ``extract`` 现在返回一个字典，包含 ``entities`` 与 ``relations`` 两个键。
        self.assertIsInstance(result, dict)
        self.assertIn("entities", result)
        self.assertIn("relations", result)
        entities = result["entities"]
        # 若抽取到实体，确保每个实体都是字典并拥有 ``type`` 与 ``name`` 键。
        if entities:
            for ent in entities:
                self.assertIsInstance(ent, dict)
                self.assertIn("type", ent)
                self.assertIn("name", ent)
                if "description" in ent:
                    self.assertIsInstance(ent["description"], str)
        # 为调试打印完整的抽取结果（不影响断言）
        print("\nExtracted result:", json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    unittest.main()
