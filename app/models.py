from flask_login import UserMixin
from app import db
from app import login_manager
import enum

@login_manager.user_loader
def load_user(id):
    return User.query.get(id)

class UserType(enum.Enum):
    ADMIN = "admin"
    UC = "unit_coordinator"
    GUEST = "guest"

#user class
class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)  
    userType = db.Column(db.Enum(UserType), nullable=False)  
    password_hash = db.Column("password_hash", db.String(256), nullable=False)

class Unit(db.Model):
    __tablename__ = "unit"
    id = db.Column(db.Integer, primary_key=True)
    unitcode = db.Column(db.String(8), unique=True, nullable=False)  
    unitname = db.Column(db.String(64), nullable=False)  
    level = db.Column(db.Integer, nullable=False)
    creditpoints = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(512), nullable=True)
