from flask import Flask

from config import DevConfig


def create_app(config_class=DevConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Phase 1 scaffold: models, CSRF, and blueprints arrive in later phases.
    @app.route("/")
    def hello():
        return "B2B — scaffold OK. Phases 2+ bring the real app."

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=5000, debug=app.config["DEBUG"])
