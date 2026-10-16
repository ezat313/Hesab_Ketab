import secrets
from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

CATEGORIES = [
    {"key": "food", "label": "خوراک", "color": "#e76f51"},
    {"key": "rent", "label": "کرایهٔ خانه", "color": "#264653"},
    {"key": "bills", "label": "برق، آب و گاز", "color": "#e9c46a"},
    {"key": "transport", "label": "ترانسپورت", "color": "#2a9d8f"},
    {"key": "health", "label": "صحت و دوا", "color": "#c1121f"},
    {"key": "education", "label": "تعلیم و مکتب", "color": "#457b9d"},
    {"key": "clothing", "label": "لباس", "color": "#9b5de5"},
    {"key": "other", "label": "متفرقه", "color": "#8d99ae"},
]
CATEGORY_MAP = {c["key"]: c for c in CATEGORIES}

# No 0/O or 1/I so codes are easy to read aloud and type.
INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _now():
    return datetime.now(timezone.utc)


class Household(db.Model):
    __tablename__ = "households"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    invite_code = db.Column(db.String(8), unique=True, nullable=False)
    monthly_budget = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    members = db.relationship("User", back_populates="household", order_by="User.id")

    @staticmethod
    def generate_invite_code():
        while True:
            code = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(8))
            if not db.session.query(Household.id).filter_by(invite_code=code).first():
                return code

    @property
    def invite_code_display(self):
        return f"{self.invite_code[:4]}-{self.invite_code[4:]}"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    household = db.relationship("Household", back_populates="members")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def can_edit(self, expense):
        """Members edit their own entries; the family admin can edit any."""
        return expense.household_id == self.household_id and (
            expense.user_id == self.id or self.is_admin
        )


class Expense(db.Model):
    __tablename__ = "expenses"
    __table_args__ = (db.Index("ix_expenses_household_date", "household_id", "spent_on"),)

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(20), nullable=False)
    spent_on = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(200), default="", nullable=False)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    user = db.relationship("User")

    @property
    def category_info(self):
        return CATEGORY_MAP.get(self.category, CATEGORY_MAP["other"])
