import unittest
from pathlib import Path


class TestSchemaEditorHTML(unittest.TestCase):
    def test_li_draggable_false(self):
        # Load the HTML file content
        html_path = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "frontend"
            / "graph_editor.html"
        )
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Verify that list items are set to non-draggable
        self.assertIn("li.draggable = false", content)

    def test_new_entity_button_exists(self):
        html_path = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "frontend"
            / "graph_editor.html"
        )
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('<button onclick="createEntity()">+ 新建实体</button>', content)


if __name__ == "__main__":
    unittest.main()
