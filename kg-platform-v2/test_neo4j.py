import sys, os

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.core.config import get_settings

settings = get_settings()
print("Settings loaded:", settings.NEO4J_URI, settings.NEO4J_USER)
from neo4j import GraphDatabase

try:
    driver = GraphDatabase.driver(
        settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )
    with driver.session() as session:
        result = session.run("RETURN 1 AS test")
        print("Neo4j connection test result:", result.single()["test"])
except Exception as e:
    print("Neo4j connection failed:", e)
