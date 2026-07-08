from flask import Flask, redirect, session, url_for
from flask_wtf import CSRFProtect

from config import DevConfig
from models import db

csrf = CSRFProtect()


def create_app(config_class=DevConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    csrf.init_app(app)

    from routes.auth import auth_bp
    from routes.students import students_bp
    from routes.courses import courses_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(courses_bp)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        if session.get("student_id"):
            return redirect(url_for("students.dashboard"))
        return redirect(url_for("auth.login"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=5000, debug=app.config["DEBUG"])
