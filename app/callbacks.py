from dash import Input, Output, State, ctx
from dash import html, dcc
from dash.exceptions import PreventUpdate
import json
import base64
import docx2txt
import io
from datetime import datetime
from services.document_processor import DocumentProcessor
from services.vector_store import VectorStoreService
from services.llm_service import LLMService
from utils.visualization import DocumentVisualizer
from utils.text_helpers import TextProcessor
from app import config

MAX_DOC_SIZE = 50 * 1024 * 1024

# Initialize global variables
original_document_content = None
global_images = []
global_tables = []
DocProc = DocumentProcessor()

def parse_contents(contents, filename):
    """Parse uploaded file contents"""
    try:
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        if len(decoded) > MAX_DOC_SIZE:
            raise Exception("File too large (max 50MB)")

        if filename.lower().endswith('.pdf'):
            content = DocProc._extract_text_with_layout(decoded)
            images = DocProc._extract_images(decoded)
            tables = DocProc._extract_tables(decoded)
            plain_text = "\n".join(
                " ".join(span["text"] for spans in page for span in spans)
                for page in content
            )
            return content, images, tables, plain_text

        elif filename.lower().endswith(('.txt', '.md')):
            content = decoded.decode("utf-8")
            return content, [], [], content

        elif filename.lower().endswith('.docx'):
            content = docx2txt.process(io.BytesIO(decoded))
            return content, [], [], content

        else:
            raise Exception("Unsupported file type")

    except Exception as e:
        raise Exception(f"Error in parse_contents: {str(e)}")

def register_callbacks(app):
    """Register all application callbacks"""

    @app.callback(
        [Output("document-viewer", "children"),
         Output("vectorstore-state", "data"),
         Output("chunk-mapping-state", "data"),
         Output("chat-history", "children"),
         Output("upload-document", "contents")],
        [Input("upload-document", "contents")],
        [State("upload-document", "filename"),
         State("chat-history", "children")]
    )
    def handle_document_upload(contents, filename, existing_chat_history):
        if not contents:
            raise PreventUpdate

        try:
            global original_document_content, global_images, global_tables

            content, images, tables, plain_text = parse_contents(contents, filename)
            original_document_content = content
            global_images = images or []
            global_tables = tables or []

            vect_serv = VectorStoreService()
            session_id, chunk_mapping = vect_serv.create_vectorstore_and_mapping(plain_text)

            doc_viz = DocumentVisualizer()
            doc_viewer_content = doc_viz.create_highlighted_content(
                content, 
                chunk_mapping, 
                [], 
                "", 
                images=global_images, 
                tables=global_tables
            )

            chat_history = existing_chat_history or []
            chat_history.append(html.P("Document processed successfully"))

            return doc_viewer_content, session_id, json.dumps(chunk_mapping), chat_history, None

        except Exception as e:
            chat_history = existing_chat_history or []
            chat_history.append(html.P(f"Error: {str(e)}"))
            return None, None, None, chat_history, None

    @app.callback(
        [Output("document-name", "children"),
         Output("document-name-chat", "children")],
        [Input("upload-document", "filename")]
    )
    def update_document_names(filename):
        if not filename:
            raise PreventUpdate

        main_display = html.Div([
            html.I(className="fas fa-file me-2"),
            f"Current file: {filename}"
        ], style={"display": "flex", "align-items": "center"})

        chat_display = f"Current file: {filename}"
        return main_display, chat_display

    @app.callback(
        [Output("chat-history", "children", allow_duplicate=True),
         Output("document-viewer", "children", allow_duplicate=True),
         Output("query-input", "value")],
        [Input("submit-btn", "n_clicks"),
         Input("query-input", "n_submit")],
        [State("query-input", "value"),
         State("document-viewer", "children"),
         State("chat-history", "children"),
         State("vectorstore-state", "data"),
         State("chunk-mapping-state", "data")],
        prevent_initial_call=True
    )
    def handle_query(n_clicks, n_submit, query, current_doc_view, chat_history, vectorstore_state, chunk_mapping_state):
        if not query:
            raise PreventUpdate

        if not vectorstore_state or not chunk_mapping_state:
            chat_history.append(html.P("Please upload a document first"))
            return chat_history, current_doc_view, query

        try:
            vect_serv = VectorStoreService()
            llm_serv = LLMService(*list(config.OPENAI_CONFIG.values())[1:])

            vectorstore, metadata = vect_serv.load_vectorstore(vectorstore_state)
            chunk_mapping = json.loads(chunk_mapping_state)

            relevant_chunk_ids, context, all_chunks = vect_serv.get_relevant_chunks(vectorstore, query)
            assistant_reply = llm_serv.get_response(context, query)

            doc_viz = DocumentVisualizer()
            doc_viewer_content = doc_viz.create_highlighted_content(
                original_document_content,
                chunk_mapping,
                relevant_chunk_ids[:2],
                assistant_reply,
                images=global_images,
                tables=global_tables
            )

            chat_history.extend([
                html.P(f"User: {query}"),
                html.P(f"Assistant: {assistant_reply}"),
                html.Hr()
            ])
            return chat_history, doc_viewer_content, ""

        except Exception as e:
            chat_history.append(html.P(f"Error: {str(e)}"))
            return chat_history, current_doc_view, query

    # Scroll to highlighted section
    app.clientside_callback(
        """
        function(mostRelevantId) {
            if (!mostRelevantId) return; // Exit if no relevant ID
            
            // Select the element with the given ID
            const highlightedElement = document.getElementById(mostRelevantId);
            if (highlightedElement) {
                highlightedElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        }
        """,
        Output("scroll-trigger", "children"),
        [Input("most-relevant-highlight", "value")],  # Trigger when the relevant ID changes
        prevent_initial_call=True
    )
