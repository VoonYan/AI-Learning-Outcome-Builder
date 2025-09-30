from flask_login import UserMixin
from app import db
from app import login_manager
import enum
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

@login_manager.user_loader
def load_user(id):
    return User.query.get(id)

# usertype enum, potentially not needed but is useful for implementing more user types as we have in the development process
class UserType(enum.Enum):
    ADMIN = "admin"
    UC = "unit_coordinator"

class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)  
    userType = db.Column(db.Enum(UserType), nullable=False)  
    password_hash = db.Column("password_hash", db.String(256), nullable=False)

    units = db.relationship("Unit", backref="owner", lazy=True)  

    @property
    def role(self):
        return self.userType

class Unit(db.Model):
    __tablename__ = "unit"
    id = db.Column(db.Integer, primary_key=True)
    unitcode = db.Column(db.String(8), unique=True, nullable=False)  
    unitname = db.Column(db.String(64), nullable=False)  
    level = db.Column(db.Integer, nullable=False, default=1)
    creditpoints = db.Column(db.Integer, nullable=False, default=6)
    description = db.Column(db.String(512), nullable=True)
    creatorid = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE", name='fk_unit_creatorid'), nullable=False)

    learning_outcomes = db.relationship(
        "LearningOutcome",
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="LearningOutcome.position.asc()"
    )



class LearningOutcome(db.Model):
    __tablename__ = "learning_outcomes"

    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey("unit.id", ondelete="CASCADE"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    assessment = db.Column(db.String(255), nullable=True)
    position = db.Column(db.Integer, nullable=False, default=0)

    unit = db.relationship("Unit", back_populates="learning_outcomes",foreign_keys=[unit_id],)
