from flask_login import LoginManager

from app.db.auth_models import AnonymousUser

login_manager = LoginManager()
login_manager.anonymous_user = AnonymousUser
