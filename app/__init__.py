import logging

from flask import Flask
from flask.logging import create_logger
from flask_admin import Admin
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from app.common.auth.MyAdminIndexView import MyAdminIndexView
from config import FlaskConfig, ApeksConfig as Apeks

db = SQLAlchemy()
login = LoginManager()
login.login_view = "auth.login"
admin = Admin()


def check_tokens() -> bool:
    """Проверяем переменные окружения."""
    required_env = {
        "SECRET_KEY": FlaskConfig.SECRET_KEY,
        "APEKS_URL": Apeks.URL,
        "APEKS_TOKEN": Apeks.TOKEN,
    }
    missing_env = []
    for key in required_env:
        if not required_env[key]:
            missing_env.append(key)
    if not missing_env:
        return True
    else:
        logging.critical(
            "Отсутствуют необходимые переменные окружения: " f'{", ".join(missing_env)}'
        )
        return False


def create_app(config_class=FlaskConfig):

    app = Flask(__name__)
    app.config.from_object(config_class)

    if not check_tokens():
        raise SystemExit("Программа принудительно остановлена.")

    db.init_app(app)
    login.init_app(app)
    admin.init_app(app, index_view=MyAdminIndexView())
    create_logger(app)

    from app.auth import bp as login_bp
    app.register_blueprint(login_bp)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.schedule import bp as schedule_bp
    app.register_blueprint(schedule_bp)

    from app.load import bp as load_bp
    app.register_blueprint(load_bp)

    from app.plans import bp as plans_bp
    app.register_blueprint(plans_bp, url_prefix="/plans")

    from app.programs import bp as programs_bp
    app.register_blueprint(programs_bp, url_prefix="/programs")

    from app.library import bp as library_bp
    app.register_blueprint(library_bp)

    return app
