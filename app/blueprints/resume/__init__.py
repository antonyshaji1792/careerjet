from flask import Blueprint

bp = Blueprint('resume', __name__, url_prefix='/resume', template_folder='templates')

from app.blueprints.resume import routes
