from dash import Dash
import dash_bootstrap_components as dbc
from app.layout import create_layout
from app.callbacks import register_callbacks

def create_app():
    app = Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css'
        ],
        suppress_callback_exceptions=True,
        prevent_initial_callbacks=True
    )
    
    app.layout = create_layout()
    register_callbacks(app)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run_server(debug=True, dev_tools_hot_reload=False)