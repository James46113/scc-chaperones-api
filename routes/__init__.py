from .auth import auth_bp
from .chaperones import chaperones_bp
from .events import events_bp
from .templates import templates_bp
from .chaperone_slots import chaperone_slots_bp
from .template_chaperone_slots import template_slots_bp
from .notifications import notifications_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(chaperones_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(chaperone_slots_bp)
    app.register_blueprint(template_slots_bp)
    app.register_blueprint(notifications_bp)