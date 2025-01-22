from datetime import datetime
import json
import shutil
from pathlib import Path
import tempfile
import uuid
import numpy as np
import faiss
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'}
)

# Text splitting configuration
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""]
)

class VectorStoreService:
    def __init__(self):
        self.embeddings = embeddings
        self.text_splitter = text_splitter
        self.TEMP_DIR = Path(tempfile.gettempdir()) / "faiss_indices"
        self.TEMP_DIR.mkdir(exist_ok=True)

    def create_vectorstore_and_mapping(self, text):
        try:
            chunks = text_splitter.create_documents([text])
            if not chunks:
                raise ValueError("No valid text chunks created")

            MAX_CHUNKS = 1000
            if len(chunks) > MAX_CHUNKS:
                chunks = chunks[:MAX_CHUNKS]

            chunk_mapping = {}
            embeddings_list = []
            docstore = {} #Initialize docstore here
            index_to_docstore_id = {} #Initialize the mapping here

            for i, chunk in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                chunk_mapping[chunk_id] = chunk.page_content[:1000]
                chunk.metadata['chunk_id'] = chunk_id
                embeddings_list.append(embeddings.embed_query(chunk.page_content))
                docstore[chunk_id] = chunk #Use chunk_id as key
                index_to_docstore_id[i] = chunk_id #Map index i to the correct chunk_id

            embeddings_array = np.array(embeddings_list).astype("float32")
            d = embeddings_array.shape[1]

            index = faiss.IndexFlatL2(d)
            index.add(embeddings_array)

            vectorstore = FAISS(embeddings.embed_query, index, docstore, index_to_docstore_id)

            session_id = str(uuid.uuid4())
            session_dir = self.TEMP_DIR / session_id
            session_dir.mkdir(exist_ok=True)

            metadata = {"last_used": datetime.now().isoformat()}
            with open(session_dir / "metadata.json", "w") as f:
                json.dump(metadata, f)

            self.save_vectorstore(session_id, vectorstore)

            self.cleanup_old_indices()
            return session_id, chunk_mapping

        except Exception as e:
            raise ValueError(f"Error in vectorstore creation: {str(e)}")

    def save_vectorstore(self, session_id, vectorstore):
        """Save vectorstore to disk"""
        session_dir = self.TEMP_DIR / session_id
        index_path = session_dir / "index.bin"
        data_path = session_dir / "data.json"

        faiss.write_index(vectorstore.index, str(index_path))

        docstore_data = []
        for doc_id, doc in vectorstore.docstore.items():
            docstore_data.append({
                "doc_id": doc_id,
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            })

        data = {
            "docstore": docstore_data,
            "index_to_docstore_id": vectorstore.index_to_docstore_id
        }

        with open(data_path, "w") as f:
            json.dump(data, f, indent=4, default=str)

    def load_vectorstore(self, session_id):
        """Load vectorstore from disk"""
        try:
            session_dir = self.TEMP_DIR / session_id
            index_path = session_dir / "index.bin"
            data_path = session_dir / "data.json"
            metadata_file = session_dir / "metadata.json"

            if not data_path.exists() or not metadata_file.exists() or not index_path.exists():
                raise ValueError("Vector store files not found")

            with open(data_path, "r") as f:
                data = json.load(f)

            with open(metadata_file, "r+") as f:
                metadata = json.load(f)
                metadata["last_used"] = datetime.now().isoformat()
                f.seek(0)
                json.dump(metadata, f, indent=4)
                f.truncate()

            index = faiss.read_index(str(index_path))

            docstore = {}
            index_to_docstore_id = data.get("index_to_docstore_id",{}) #Get the index mapping, default to empty dict

            if not index_to_docstore_id:
                raise ValueError("index_to_docstore_id is missing from saved data")

            for doc_data in data["docstore"]:
                doc_id = doc_data.get("doc_id") #Get doc_id safely
                if not doc_id:
                    raise ValueError("doc_id is missing from saved doc data")
                docstore[doc_id] = Document(page_content=doc_data["page_content"], metadata=doc_data["metadata"])

            vectorstore = FAISS(embeddings.embed_query, index, docstore, index_to_docstore_id)
            return vectorstore, metadata

        except (FileNotFoundError, json.JSONDecodeError, RuntimeError, ValueError) as e:
            print(f"Error loading vectorstore: {type(e).__name__}: {str(e)}") #Print detailed error
            return None, None #Return None to indicate failure 

    def cleanup_old_indices(self):
        """Clean up indices older than 1 hour or marked for deletion"""
        now = datetime.now()
        for session_dir in self.TEMP_DIR.glob("*"):
            try:
                metadata_file = session_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                    last_used = datetime.fromisoformat(
                        metadata.get("last_used", now.isoformat())
                    )
                    delete_flag = metadata.get("delete", False)

                    if (now - last_used).total_seconds() > 3600 or delete_flag:
                        shutil.rmtree(session_dir)
                else:
                    shutil.rmtree(session_dir)
            except Exception as e:
                print(f"Error cleaning up {session_dir}: {e}")

    def get_relevant_chunks(self, vectorstore, query, k=5):
        """Retrieve k most relevant chunks and calculate relevance scores"""
        if not vectorstore:
            return [], "", []
        query_embedding = self.embeddings.embed_query(query)
        query_vector = np.array([query_embedding]).astype("float32")

        index = vectorstore.index
        D, I = index.search(query_vector, k)
        
        relevant_chunks = []
        for i, distance in zip(I[0], D[0]):
            if i != -1:
                try:
                    doc_id = vectorstore.index_to_docstore_id[str(i)]
                    doc = vectorstore.docstore[doc_id]
                    
                    similarity = np.exp(-distance)
                    
                    if similarity > 0.1:
                        relevant_chunks.append({
                            'chunk_id': doc.metadata.get('chunk_id'),
                            'content': doc.page_content,
                            'score': similarity
                        })
                except KeyError as e:
                    print(f"KeyError for index {i}: {e}")
                    continue
        
        relevant_chunks.sort(key=lambda x: x['score'], reverse=True)
        
        top_k = min(5, len(relevant_chunks))
        top_chunks = relevant_chunks[:top_k]
        
        context = "\n\n".join([chunk['content'] for chunk in top_chunks])
        chunk_ids = [chunk['chunk_id'] for chunk in top_chunks]
        
        return chunk_ids, context, relevant_chunks