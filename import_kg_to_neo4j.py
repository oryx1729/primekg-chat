import csv
from py2neo import Graph, Node, Relationship

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

# Connect to Neo4j
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Function to create or get a node
def get_or_create_node(tx, label, properties):
    # Replace '/' with '_' in the label to avoid Cypher syntax errors
    safe_label = label.replace('/', '_')
    query = (
        f"MERGE (n:`{safe_label}` {{id: $id}}) "
        "ON CREATE SET n += $properties "
        "ON MATCH SET n += $properties "
        "RETURN n"
    )
    result = tx.run(query, id=properties['id'], properties=properties)
    record = result.data()
    if record:
        return record[0]['n']
    return None

# Read and import CSV data
csv_file = "dataverse_files/kg.csv"

BATCH_SIZE = 1000
batch = []

# Count total rows in CSV file
with open(csv_file, "r", encoding="utf-8") as file:
    total_rows = sum(1 for _ in file) - 1  # Subtract 1 to account for header

with open(csv_file, "r", encoding="utf-8") as file:
    csv_reader = csv.DictReader(file)
    
    for row_number, row in enumerate(csv_reader, start=1):
        batch.append(row)
        
        if len(batch) >= BATCH_SIZE or row_number == total_rows:
            tx = graph.begin()
            try:
                for batch_row in batch:
                    source_node = get_or_create_node(tx, batch_row["x_type"], {
                        "id": batch_row["x_id"],
                        "name": batch_row["x_name"],
                        "source": batch_row["x_source"]
                    })

                    target_node = get_or_create_node(tx, batch_row["y_type"], {
                        "id": batch_row["y_id"],
                        "name": batch_row["y_name"],
                        "source": batch_row["y_source"]
                    })

                    if source_node and target_node:
                        relationship = Relationship(source_node, batch_row["relation"], target_node)
                        tx.create(relationship)
                
                graph.commit(tx)
            except Exception as e:
                graph.rollback(tx)
                print(f"Error processing batch: {e}")

            print(f"Processed {row_number} rows out of {total_rows}")
            batch = []

print("Data import completed successfully!")
print(f"Total rows processed: {row_number}")
