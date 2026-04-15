import sys, os

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.ingestion.extractor import extract_kg

story = """青竹悟

青竹峰上，小弟子阿禾终日打坐练气，却总因心浮气躁无法凝聚灵力，屡屡被师父罚去后山守竹。

一日暴雨，阿禾见一株嫩竹被狂风弯折，眼看就要断裂，便冒雨用竹片为其支撑。此后数日，他每日照料，看着嫩竹在风雨中慢慢挺直，即便再遇狂风，也能柔韧应对，不折不屈。

阿禾忽然顿悟，师父说的“静气守心”，从不是枯坐苦熬，而是如青竹般，于喧嚣中沉心，于困境中坚韧。他回到石坛打坐，摒弃杂念，回想嫩竹生长之态，灵力竟缓缓凝聚，周身泛起淡淡的青芒。

雨过天晴，师父立于坛边，望着周身萦绕竹影灵力的阿禾，微微颔首。阿禾起身行礼，终于懂了修炼的真谛——心向澄澈，方能致远，如竹般守拙，方能成器。夕阳洒在青竹峰上，师徒二人的身影与竹影相融，岁月安然。"""

kg = extract_kg(story, max_retries=3)
print("KG result:", kg)
