import pathway as pw
from pathway.stdlib.ml.index import KNNIndex
from pathway.xpacks.llm.embedders import OpenAIEmbedder
from src.ingestion_live import get_live_news_table # Switching to Live Ingestion
import os
from dotenv import load_dotenv

load_dotenv()

class VectorStoreServer:
    def __init__(self):
        # Use LIVE table
        self.news_table = get_live_news_table()

    def build_index(self):
        # 1. Prepare text for embedding
        enriched_table = self.news_table.select(
            text=pw.sql.concat(
                 "Topic: ", pw.this.topic, 
                 ". Location: ", pw.this.location, 
                 ". Summary: ", pw.this.summary
            ),
            *pw.this.without("text") 
        )

        # 2. Define Embedder (Real)
        embedder = OpenAIEmbedder(
            api_key=os.getenv("OPENAI_API_KEY", ""), 
            model="text-embedding-3-small", 
            cache_strategy=pw.udfs.DiskCache()
        )

        # 3. Create Real-Time Vector Index
        index = KNNIndex(
            enriched_table.text,
            enriched_table, 
            embedder=embedder,
            n_dimensions=1536
        )

        return index

def start_vector_server(host="0.0.0.0", port=8000):
    server = VectorStoreServer()
    index = server.build_index()
    
    pw.io.http.write_groups(
        index.query,
        host=host,
        port=port,
        format="json"
    )
    
    print(f"Vector Store Server running on {host}:{port}...")
    pw.run()

if __name__ == "__main__":
    start_vector_server()
