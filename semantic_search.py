from py2neo import Graph
import os
from typing import List, Dict
import json
from dotenv import load_dotenv
import requests
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

# Ollama API endpoint
OLLAMA_API = "http://localhost:11434/api/embeddings"

# Connect to Neo4j
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def get_embedding(text: str) -> List[float]:
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

def find_similar_nodes(query: str, top_k: int = 5) -> List[Dict]:
    """Find similar nodes using vector similarity search"""
    print("Generating embedding for query...")
    query_embedding = get_embedding(query)
    if not query_embedding:
        print("Failed to generate embedding for query")
        return []
    
    print(f"Generated embedding of length: {len(query_embedding)}")
    print("Searching for similar nodes...")
    
    cypher_query = """
    MATCH (n:Node)
    WHERE n.embedding IS NOT NULL
    WITH n, gds.similarity.cosine(n.embedding, $embedding) AS score
    RETURN n.node_name, n.node_type, n.node_source, score
    ORDER BY score DESC
    LIMIT $top_k
    """
    
    try:
        results = graph.run(cypher_query, embedding=query_embedding, top_k=top_k).data()
        print(f"Found {len(results)} similar nodes")
        if len(results) == 0:
            print("No nodes found with embeddings. Please check if embeddings were properly generated.")
        return results
    except Exception as e:
        print(f"Error during similarity search: {e}")
        return []

def get_related_nodes(node_name: str, depth: int = 2) -> List[Dict]:
    """Get related nodes and their relationships up to a certain depth"""
    # Create a fresh connection for each query
    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    cypher_query = """
    MATCH (start:Node {node_name: $node_name})
    MATCH (start)-[r:RELATES_TO*1..2]-(related)
    RETURN start, r, related
    LIMIT 100
    """
    
    try:
        results = graph.run(cypher_query, node_name=node_name).data()
        return results
    except Exception as e:
        print(f"\nError querying related nodes for {node_name}: {e}")
        return []

def create_prompt_chain(query: str) -> str:
    """Create a prompt chain using Ollama"""
    # Step 1: Find similar nodes
    print("\nStarting similarity search...")
    similar_nodes = find_similar_nodes(query)
    
    if not similar_nodes:
        return "No similar nodes found in the knowledge graph. Please try a different query."
    
    # Step 2: Get related nodes for each similar node
    context = []
    print("\nGathering context from related nodes...")
    for node in tqdm(similar_nodes, desc="Processing nodes"):
        try:
            # Create a fresh connection for each node
            related = get_related_nodes(node['n.node_name'])
            if not related:
                continue
                
            # Process related nodes into a more readable format
            related_info = []
            for result in related:
                try:
                    related_info.append({
                        'start_node': result['start']['node_name'],
                        'end_node': result['related']['node_name'],
                        'relationships': [rel['relation'] for rel in result['r']]
                    })
                except Exception as e:
                    print(f"\nError processing result for {node['n.node_name']}: {e}")
                    continue
            
            context.append({
                'node': node['n.node_name'],
                'type': node['n.node_type'],
                'source': node['n.node_source'],
                'similarity': node['score'],
                'related': related_info
            })
        except Exception as e:
            print(f"\nError processing node {node['n.node_name']}: {e}")
            continue
    
    # Step 3: Create a prompt for Ollama
    print("Generating answer using Ollama...")
    prompt = f"""Based ONLY on the following knowledge graph context, please answer the question: {query}

Context:
{json.dumps(context, indent=2)}

Important instructions:
1. ONLY use information from the provided knowledge graph context
2. When referencing nodes, use the exact node names from the context
3. When referencing relationships, use the exact relationship types from the context
4. Format your response with:
   - Nodes in **bold** (e.g., **Node Name**)
   - Relationships in *italics* (e.g., *RELATES_TO*)
5. Do not make assumptions or use information outside the provided context
6. If the context doesn't contain enough information to fully answer the question, acknowledge this limitation

Please provide a comprehensive answer that:
1. Directly addresses the question using only the provided context
2. References specific nodes and relationships from the context
3. Explains the reasoning behind the answer
4. Acknowledges any limitations or uncertainties

Answer:"""
    
    # Step 4: Get response from Ollama
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "llama2",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based ONLY on knowledge graph data. Use the provided context to give accurate and well-reasoned answers. Always highlight nodes in bold and relationships in italics."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        print(f"Error getting response from Ollama: {e}")
        return "Sorry, I encountered an error while generating the response."

def main():
    while True:
        query = input("\nEnter your question (or 'quit' to exit): ")
        if query.lower() == 'quit':
            break
            
        try:
            answer = create_prompt_chain(query)
            print("\nAnswer:", answer)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main() 