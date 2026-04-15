import pytest
from app.graph.neo4j_client import Neo4jClient


@pytest.fixture(scope="module")
def neo():
    client = Neo4jClient()
    # 清空已有数据（fallback 模式下）
    client.run("MATCH (n) DETACH DELETE n")
    # 创建示例节点和关系
    client.run("""
        CREATE (a:Entity {name: 'A'})
        CREATE (b:Entity {name: 'B'})
        CREATE (c:Entity {name: 'C'})
        CREATE (a)-[:REL]->(b)
        CREATE (b)-[:REL]->(c)
    """)
    return client


def test_variable_path_one_hop(neo):
    """单跳路径应返回 A -> B 的节点和关系"""
    res = neo.variable_path_query(start_name="A", min_hops=1, max_hops=1)
    node_names = [n["name"] for n in res[0]["path"]]
    assert set(node_names) == {"A", "B"}
    assert len(res[0]["relations"]) == 1


def test_variable_path_two_hop(neo):
    """两跳路径应返回 A -> B -> C"""
    res = neo.variable_path_query(start_name="A", min_hops=2, max_hops=2)
    node_names = [n for n in res[0]["path"]]
    # 在 fallback 实现中 path 为节点名列表
    assert set(node_names) == {"A", "B", "C"}
    assert len(res[0]["relations"]) == 2
