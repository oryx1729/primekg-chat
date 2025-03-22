from py2neo import Graph
import requests
import json
from tqdm import tqdm
import time

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

# Ollama API endpoint
OLLAMA_API = "http://localhost:11434/api/embeddings"

# Connect to Neo4j
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def get_embedding(text):
    """Get embedding for a text using Ollama API"""
    try:
        response = requests.post(
            OLLAMA_API,
            json={
                "model": "twine/mxbai-embed-xsmall-v1",
                "prompt": text
            }
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        print(f"Error getting embedding for text: {text}")
        print(f"Error: {e}")
        return None

def process_nodes():
    # Get all nodes that don't have embeddings yet
    query = """
    MATCH (n:Node)
    WHERE n.embedding IS NULL
    RETURN n.node_index, n.node_name
    """
    
    nodes = graph.run(query).data()
    
    print(f"Found {len(nodes)} nodes without embeddings")
    
    # Process nodes in batches
    batch_size = 100
    for i in tqdm(range(0, len(nodes), batch_size)):
        batch = nodes[i:i + batch_size]
        
        # Generate embeddings for the batch
        for node in batch:
            embedding = get_embedding(node['n.node_name'])
            if embedding:
                # Store the embedding in Neo4j
                update_query = """
                MATCH (n:Node {node_index: $node_index})
                SET n.embedding = $embedding
                """
                graph.run(update_query, node_index=node['n.node_index'], embedding=embedding)
        
        # Small delay to avoid overwhelming the Ollama API
        time.sleep(0.1)

if __name__ == "__main__":
    process_nodes()
    print("Embedding generation completed.") 