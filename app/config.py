import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App configuration
MAX_DOC_SIZE = 50 * 1024 * 1024  # 50MB

# Directory configuration
TEMP_DIR = Path(os.getenv('TEMP_DIR', Path.home() / '.document_qa' / 'faiss_indices'))
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Azure OpenAI configuration
OPENAI_CONFIG = {
    'api_type': 'azure',
    'api_key': os.getenv('OPENAI_API_KEY', '###YOUR_KEY##'),
    'api_base': os.getenv('OPENAI_API_BASE', '####YOUR_URI###'),
    'api_version': os.getenv('OPENAI_API_VERSION', '2024-08-01-preview'),
    'deployment_name': os.getenv('OPENAI_DEPLOYMENT_NAME', 'gpt-35-turbo')
}

# Text splitting configuration
TEXT_SPLITTER_CONFIG = {
    'chunk_size': 500,
    'chunk_overlap': 50,
    'separators': ["\n\n", "\n", ". ", " ", ""]
}

# Embeddings configuration
EMBEDDINGS_MODEL = {
    'name': "sentence-transformers/all-MiniLM-L6-v2",
    'device': 'cpu'
}