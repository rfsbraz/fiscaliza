import os
import sys
import logging
import traceback
from datetime import datetime

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from config.settings import FLASK_CONFIG
from database.models import db
from app.routes.core import core_bp
from app.routes.parties import parties_bp
from app.routes.deputies import deputies_bp
from app.routes.activity import activity_bp
from app.routes.parlamento import parlamento_bp
from app.routes.agenda import agenda_bp
from app.routes.health import health_bp
from app.routes.voting import voting_bp
from app.data.connection import init_app as init_data

# Configure logging with more detailed formatting for debugging
log_dir = os.path.join(parent_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)

# Create a custom formatter for console output with colors (if supported)
class ColoredConsoleFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output for better visibility"""
    
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    COLORS = {
        'DEBUG': CYAN,
        'INFO': GREEN,
        'WARNING': YELLOW,
        'ERROR': RED,
        'CRITICAL': RED + BOLD,
    }
    
    def format(self, record):
        # Add color to level name for console output
        if hasattr(record, 'exc_info') and record.exc_info:
            # For exceptions, use special formatting
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        else:
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        return super().format(record)

# Set up console handler with colored output
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredConsoleFormatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# Set up file handler without colors
file_handler = logging.FileHandler(os.path.join(log_dir, 'flask_server.log'))
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logging.basicConfig(
    level=logging.INFO,  # Reduced from DEBUG to INFO
    handlers=[file_handler, console_handler]
)

# Reduce boto3/botocore logging to WARNING level
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

app = Flask(__name__)
app.config.update(FLASK_CONFIG)

# Debug mode controlled by environment variable
app.debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

# Ativar CORS para permitir requests do frontend
CORS(app)

app.register_blueprint(core_bp, url_prefix='/api')
app.register_blueprint(parties_bp, url_prefix='/api')
app.register_blueprint(deputies_bp, url_prefix='/api')
app.register_blueprint(activity_bp, url_prefix='/api')
app.register_blueprint(parlamento_bp, url_prefix='/api')
app.register_blueprint(agenda_bp, url_prefix='/api')
app.register_blueprint(health_bp, url_prefix='/api')
app.register_blueprint(voting_bp, url_prefix='/api')

# Site data: the read-only DuckDB file built by `python -m fiscaliza_data sync`
init_data(app)

# Initialize database - defer actual connection until first use
try:
    db.init_app(app)
    print("Database initialization completed (no connection established yet)")
except Exception as e:
    print(f"Database initialization failed: {e}")
    # Continue without database - routes will handle connection errors

# Create a dedicated exception logger
exception_logger = logging.getLogger('flask.exceptions')
exception_logger.setLevel(logging.ERROR)

def log_exception(exc_type, exc_value, exc_traceback):
    """
    Log exception with full details to console and file
    """
    if app.debug:
        # Format the exception details
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        request_info = ""
        
        # Try to get request context if available
        try:
            if request:
                request_info = f"""
    Request Details:
    - URL: {request.url}
    - Method: {request.method}
    - IP: {request.remote_addr}
    - Headers: {dict(request.headers)}
    - Args: {dict(request.args)}
    - Form: {dict(request.form) if request.form else 'None'}
    - JSON: {request.get_json(silent=True)}"""
        except:
            pass
        
        # Format the full traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_lines)
        
        # Create the formatted error message
        error_message = f"""
{'='*80}
EXCEPTION CAUGHT IN FLASK APP
Time: {timestamp}
Exception Type: {exc_type.__name__}
Exception Value: {str(exc_value)}{request_info}

Full Traceback:
{tb_text}
{'='*80}
"""
        
        # Log to console with color
        console_output = f"\033[91m{error_message}\033[0m"  # Red color for console
        print(console_output, file=sys.stderr)
        
        # Also log using Flask's logger (without color for file)
        app.logger.error(error_message)
        exception_logger.error(error_message)

# Install custom exception hook for uncaught exceptions
sys.excepthook = log_exception

# Before request handler to log all incoming requests in debug mode
@app.before_request
def log_request_info():
    if app.debug:
        app.logger.debug('Headers: %s', request.headers)
        app.logger.debug('Body: %s', request.get_data())

# After request handler to log response status
@app.after_request
def log_response_info(response):
    if app.debug and response.status_code >= 400:
        app.logger.warning(f'Response Status: {response.status_code} for {request.url}')
    return response

# Enhanced error handlers
@app.errorhandler(404)
def not_found_error(error):
    if app.debug:
        app.logger.warning(f'404 Not Found: {request.url}')
    return jsonify({'error': 'Not found', 'url': request.url}), 404

@app.errorhandler(500)
def internal_error(error):
    # Log the full exception details
    log_exception(type(error), error, sys.exc_info()[2])
    
    # Return JSON response
    response = {
        'error': 'Internal server error',
        'message': str(error),
        'type': type(error).__name__
    }
    
    # In debug mode, include more details
    if app.debug:
        response['traceback'] = traceback.format_exc().split('\n')
        response['request_url'] = request.url
        response['request_method'] = request.method
    
    return jsonify(response), 500

@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Handle HTTP exceptions (like 400, 401, 403, etc.)"""
    if app.debug:
        app.logger.warning(f'HTTP Exception {e.code}: {e.description} for {request.url}')
    
    response = {
        'error': e.name,
        'message': e.description,
        'code': e.code
    }
    
    if app.debug:
        response['request_url'] = request.url
        response['request_method'] = request.method
    
    return jsonify(response), e.code

@app.errorhandler(Exception)
def handle_exception(e):
    """Catch-all handler for any unhandled exceptions"""
    # Log the full exception details
    log_exception(type(e), e, sys.exc_info()[2])
    
    # If it's an HTTP exception, pass it through
    if isinstance(e, HTTPException):
        return handle_http_exception(e)
    
    # For all other exceptions, return 500
    response = {
        'error': 'Unhandled exception',
        'message': str(e),
        'type': type(e).__name__
    }
    
    # In debug mode, include full traceback
    if app.debug:
        response['traceback'] = traceback.format_exc().split('\n')
        response['request_url'] = request.url if request else 'No request context'
        response['request_method'] = request.method if request else 'No request context'
    
    return jsonify(response), 500

# Não criar tabelas pois já existem na base de dados importada
# with app.app_context():
#     db.create_all()


@app.route('/')
def api_root():
    """API root endpoint - no frontend serving"""
    return jsonify({
        "service": "parliament-backend",
        "version": "1.0.0",
        "message": "Parliament Transparency Platform API",
        "endpoints": {
            "health": "/api/health",
            "deputies": "/api/deputies",
            "parties": "/api/parties", 
            "agenda": "/api/agenda"
        },
        "frontend": "https://fiscaliza.pt"
    })


if __name__ == '__main__':
    # Enable detailed error pages and debugging
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['DEBUG'] = True
    app.config['TRAP_HTTP_EXCEPTIONS'] = True  # Trap HTTP exceptions for custom handling
    
    # Set Flask's logger to DEBUG level
    app.logger.setLevel(logging.DEBUG)
    
    # Also set werkzeug logger to see request details
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    
    # Print startup message with configuration
    print("\n" + "="*80)
    print("Starting Flask server with ENHANCED error logging")
    print("="*80)
    print(f"Debug Mode: {app.debug}")
    print(f"Log Level: {logging.getLevelName(app.logger.level)}")
    print(f"Log Directory: {log_dir}")
    print(f"Exception Propagation: {app.config.get('PROPAGATE_EXCEPTIONS')}")
    print(f"HTTP Exception Trapping: {app.config.get('TRAP_HTTP_EXCEPTIONS')}")
    print("="*80)
    print("All 500 errors will be logged with:")
    print("  - Full traceback")
    print("  - Request details (URL, method, headers, body)")
    print("  - Colored console output for better visibility")
    print("  - Timestamp and exception type")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=True)
