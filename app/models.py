"""
Database models for the AI Learning Outcome Builder application.

This module defines the SQLAlchemy models for users, units, and learning outcomes.
It includes the User model with role-based access control, Unit model for course units,
and LearningOutcome model for individual learning objectives.
"""

from flask_login import UserMixin
from app import db
from app import login_manager
import enum
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


@login_manager.user_loader
def load_user(id):
    """
    Flask-Login user loader callback.

    Args:
        id: User ID to load

    Returns:
        User object if found, None otherwise
    """
    return User.query.get(id)


class UserType(enum.Enum):
    """
    Enumeration for user roles in the system.

    ADMIN: Full system access, can manage all units and settings
    UC: Unit Coordinator, can create and manage their own units
    """
    ADMIN = "admin"
    UC = "unit_coordinator"


class User(UserMixin, db.Model):
    """
    User model for authentication and authorization.

    Attributes:
        id: Primary key
        username: Unique username for login
        userType: Role-based access level (ADMIN or UC)
        password_hash: Hashed password for security
        units: Relationship to owned units
    """
    __tablename__ = "user"

    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # User credentials
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column("password_hash", db.String(256), nullable=False)

    # User role for access control
    userType = db.Column(db.Enum(UserType), nullable=False)

    # Relationship to units created by this user
    units = db.relationship("Unit", backref="owner", lazy=True)

    @property
    def role(self):
        """
        Property to access user's role.

        Returns:
            UserType enum value
        """
        return self.userType


class Unit(db.Model):
    """
    Unit model representing a course/subject unit.

    Attributes:
        id: Primary key
        unitcode: Unique code for the unit (e.g., "CITS3001")
        unitname: Full name of the unit
        level: Academic level (1-6, representing year/complexity)
        creditpoints: Number of credit points (6, 12, or 24)
        description: Optional detailed description
        creatorid: Foreign key to User who created this unit
        learning_outcomes: Related learning outcomes for this unit
    """
    __tablename__ = "unit"

    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Unit identification
    unitcode = db.Column(db.String(8), unique=True, nullable=False)
    unitname = db.Column(db.String(64), nullable=False)

    # Academic details
    level = db.Column(db.Integer, nullable=False, default=1)
    creditpoints = db.Column(db.Integer, nullable=False, default=6)

    # Optional description
    description = db.Column(db.String(512), nullable=True)

    # Foreign key to user who created this unit
    creatorid = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE", name='fk_unit_creatorid'),
        nullable=False
    )

    # Relationship to learning outcomes
    # Cascade delete ensures outcomes are deleted when unit is deleted
    # Order by position ensures outcomes maintain their sequence
    learning_outcomes = db.relationship(
        "LearningOutcome",
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="LearningOutcome.position.asc()"
    )


class LearningOutcome(db.Model):
    """
    Learning Outcome model for individual learning objectives within a unit.

    Attributes:
        id: Primary key
        unit_id: Foreign key to parent unit
        description: The actual learning outcome text
        assessment: Optional assessment method for this outcome
        position: Order position within the unit (for maintaining sequence)
        unit: Relationship back to parent unit
    """
    __tablename__ = "learning_outcomes"

    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Foreign key to parent unit
    unit_id = db.Column(
        db.Integer,
        db.ForeignKey("unit.id", ondelete="CASCADE"),
        nullable=False
    )

    # Learning outcome content
    description = db.Column(db.Text, nullable=False)

    # Optional assessment method
    assessment = db.Column(db.String(255), nullable=True)

    # Position for ordering (0-based index)
    position = db.Column(db.Integer, nullable=False, default=0)

    # Relationship back to parent unit
    unit = db.relationship(
        "Unit",
        back_populates="learning_outcomes",
        foreign_keys=[unit_id]
    )