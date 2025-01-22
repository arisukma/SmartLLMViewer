from dash import html, dcc
import dash_bootstrap_components as dbc

def create_layout():
    """Create the application layout with enhanced styling"""
    
    # Custom styles
    SHADOW_STYLE = "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)"
    CARD_STYLE = {
        "border-radius": "8px",
        "box-shadow": SHADOW_STYLE,
        "background-color": "#ffffff",
        "height": "100%",
        "padding": "20px",
    }
    
    return dbc.Container(
        [
            # Header section with gradient background
            dbc.Row(
                dbc.Col(
                    html.Div(
                        [
                            html.H1(
                                "Document Q&A System",
                                className="display-4 mb-2 text-center text-primary",
                                style={"font-weight": "bold"}
                            ),
                            html.P(
                                "Upload a document and ask questions to get instant answers",
                                className="lead text-center text-muted mb-4"
                            ),
                        ],
                        style={
                            "padding": "2rem 0",
                            "background": "linear-gradient(120deg, #fdfbfb 0%, #ebedee 100%)",
                            "border-radius": "8px",
                            "margin-bottom": "2rem",
                            "box-shadow": SHADOW_STYLE,
                        }
                    ),
                    width=12,
                )
            ),
            
            # Main content
            dbc.Row(
                [
                    # Chat Section
                    dbc.Col(
                        dbc.Card(
                            [
                                # Upload button with status
                                html.Div(
                                    [
                                        dcc.Upload(
                                            id="upload-document",
                                            multiple=False,
                                            children=dbc.Button(
                                                [
                                                    html.I(className="fas fa-upload me-2"),
                                                    "Upload Document"
                                                ],
                                                color="primary",
                                                size="lg",
                                                className="w-100",
                                                style={"box-shadow": SHADOW_STYLE}
                                            ),
                                            className="mb-3"
                                        ),
                                        # File status indicator below upload button
                                        html.Div(
                                            id="document-name-chat",
                                            className="text-muted text-center small",
                                            style={"font-style": "italic"}
                                        )
                                    ],
                                    className="text-center mb-4"
                                ),
                                
                                # Chat history
                                html.Div(
                                    id="chat-history",
                                    style={
                                        "height": "500px",
                                        "overflow-y": "auto",
                                        "border": "1px solid #e9ecef",
                                        "padding": "20px",
                                        "margin-bottom": "20px",
                                        "border-radius": "8px",
                                        "background-color": "#f8f9fa"
                                    },
                                ),
                                
                                # Input group with keyboard event listener
                                html.Div([
                                    dbc.InputGroup(
                                        [
                                            dbc.Input(
                                                id="query-input",
                                                placeholder="Type your question here...",
                                                type="text",
                                                style={
                                                    "border-radius": "8px 0 0 8px",
                                                    "border": "2px solid #e9ecef",
                                                    "padding": "12px"
                                                },
                                                n_submit=0  # Enable Enter key submission
                                            ),
                                            dbc.Button(
                                                [
                                                    html.I(className="fas fa-paper-plane me-2"),
                                                    "Send"
                                                ],
                                                id="submit-btn",
                                                color="primary",
                                                style={
                                                    "border-radius": "0 8px 8px 0",
                                                    "box-shadow": SHADOW_STYLE
                                                }
                                            ),
                                        ],
                                        className="mb-3",
                                    )
                                ]),
                                
                                # Hidden components
                                dcc.Store(id='vectorstore-state'),
                                dcc.Store(id='chunk-mapping-state'),
                                html.Div(id="scroll-trigger"),
                                dcc.Location(id="scroll-location"),
                            ],
                            body=True,
                            style=CARD_STYLE
                        ),
                        md=6,
                        className="mb-4"
                    ),
                    
                    # Document Viewer Section
                    dbc.Col(
                        dbc.Card(
                            [
                                # Enhanced Document viewer header with file info
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.I(
                                                    className="fas fa-file-alt me-2",
                                                    style={"color": "#4a90e2"}
                                                ),
                                                html.H4(
                                                    "Document Viewer",
                                                    className="mb-0 text-primary"
                                                ),
                                            ],
                                            className="d-flex align-items-center"
                                        ),
                                        html.Div(
                                            id="document-name",
                                            className="mt-2 p-2",
                                            style={
                                                "font-style": "italic",
                                                "background-color": "#f8f9fa",
                                                "border-radius": "4px",
                                                "border": "1px solid #e9ecef",
                                                "padding": "0.5rem",
                                            }
                                        )
                                    ],
                                    className="mb-4"
                                ),
                                
                                # Document viewer content
                                html.Div(
                                    id="document-viewer",
                                    style={
                                        "height": "700px",
                                        "overflow-y": "auto",
                                        "border": "1px solid #e9ecef",
                                        "padding": "20px",
                                        "border-radius": "8px",
                                        "background-color": "#f8f9fa"
                                    },
                                ),
                            ],
                            body=True,
                            style=CARD_STYLE
                        ),
                        md=6,
                        className="mb-4"
                    ),
                ],
                className="g-4",
            ),
        ],
        fluid=True,
        className="py-4",
        style={"background-color": "#f0f2f5"}
    )