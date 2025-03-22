from py2neo import Graph

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

# Connect to Neo4j
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def create_vector_index():
    # Drop existing index if it exists
    drop_query = """
    DROP INDEX node_embedding_index IF EXISTS
    """
    
    # Create vector index
    create_query = """
    CREATE VECTOR INDEX node_embedding_index IF NOT EXISTS
    FOR (n:Node)
    ON (n.embedding)
    OPTIONS {
        indexConfig: {
            `vector.dimensions`: 384,
            `vector.similarity_function`: 'cosine'
        }
    }
    """
    
    try:
        print("Dropping existing index if present...")
        graph.run(drop_query)
        
        print("Creating vector index...")
        graph.run(create_query)
        
        print("Vector index created successfully!")
    except Exception as e:
        print(f"Error creating vector index: {e}")

if __name__ == "__main__":
    create_vector_index() 