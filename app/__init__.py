from app.models import User
from flask import Flask
from flask_pymongo import PyMongo
from flask_mail import Mail
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

mongo = PyMongo() # Initializes PyMongo
mail = Mail() # Initializes Mail
bcrypt = Bcrypt() # Initialize Bcrypt
login_manager = LoginManager() # Initialize LoginManager

# Create the flask app
def create_app():
    app = Flask(__name__)

    # Load Configurations
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['MONGO_URI'] = os.getenv('MONGO_URI')
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['STRIPE_PUBLIC_KEY'] = os.getenv('STRIPE_PUBLIC_KEY')
    app.config['STRIPE_SECRET_KEY'] = os.getenv('STRIPE_SECRET_KEY')

    # Initialize extensions
    mongo.init_app(app) # Initializes PyMongo with the flask app
    mail.init_app(app) # Initializes Mail with the flask app
    bcrypt.init_app(app)    # Initializes Bcrypt with the flask app
    login_manager.init_app(app)    # Initializes LoginManager with the flask app

    # Register blueprint or views
    from .views import bp as main_bp    # Import views to register routes
    from .admin import bp as admin_bp   # Import admin views to register routes
    app.register_blueprint(main_bp)    # Register the Blueprint
    app.register_blueprint(admin_bp)   # Register the Blueprint

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        user_dict = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if user_dict:
            return User(user_dict)
        return None

    return app