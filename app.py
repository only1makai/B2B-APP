from flask import Flask

from config import DevConfig
from models import db


def create_app(config_class=DevConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    # CSRF and blueprints arrive in later phases.
    @app.route("/")
    def hello():
        return "B2B — scaffold OK. Phases 3+ bring the real app."

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=5000, debug=app.config["DEBUG"])
