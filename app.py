"""حساب و کتاب خانه — shared monthly household expenses."""
import os
import re
import secrets
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

import jdatetime
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func

import helpers
from models import CATEGORIES, CATEGORY_MAP, Expense, Household, User, db

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, instance_path=str(BASE_DIR / "instance"))
Path(app.instance_path).mkdir(exist_ok=True)


def _secret_key():
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    key_file = Path(app.instance_path) / "secret_key"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32))
    return key_file.read_text().strip()


_secure_cookies = os.environ.get("COOKIE_SECURE") == "1"
app.config.update(
    SECRET_KEY=_secret_key(),
    SQLALCHEMY_DATABASE_URI="sqlite:///" + Path(
        os.environ.get("HESAB_DB") or Path(app.instance_path) / "hesab.db"
    ).as_posix(),
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=_secure_cookies,
    REMEMBER_COOKIE_SECURE=_secure_cookies,
)

db.init_app(app)
CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "لطفاً اول وارد شوید."
login_manager.login_message_category = "info"

with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


app.jinja_env.filters["fa_num"] = helpers.fa_number
app.jinja_env.filters["fa_digits"] = helpers.fa_digits
app.jinja_env.filters["shamsi"] = helpers.format_shamsi


@app.context_processor
def inject_globals():
    return {"CATEGORIES": CATEGORIES, "MONTH_NAMES": helpers.MONTH_NAMES}


def household_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user.household_id is None:
            return redirect(url_for("setup"))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


# ---------- Auth ----------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _safe_next(url):
    if not url or not url.startswith("/") or url.startswith(("//", "/\\")):
        return url_for("dashboard")
    parts = urlsplit(url)
    return url if not parts.scheme and not parts.netloc else url_for("dashboard")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = request.form
    if request.method == "POST":
        name = form.get("name", "").strip()
        email = form.get("email", "").strip().lower()
        password = form.get("password", "")

        error = None
        if not name:
            error = "نام خود را بنویسید."
        elif not EMAIL_RE.match(email):
            error = "ایمیل درست نیست."
        elif len(password) < 8:
            error = "رمز عبور باید حداقل ۸ حرف باشد."
        elif password != form.get("password2", ""):
            error = "رمز عبور و تکرار آن یکی نیست."
        elif User.query.filter_by(email=email).first():
            error = "با این ایمیل قبلاً حساب ساخته شده است."

        if error:
            flash(error, "error")
        else:
            user = User(name=name[:80], email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            return redirect(url_for("setup"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = request.form
    if request.method == "POST":
        email = form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(form.get("password", "")):
            login_user(user, remember=True)
            return redirect(_safe_next(request.args.get("next")))
        flash("ایمیل یا رمز عبور اشتباه است.", "error")

    return render_template("login.html", form=form)


@app.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/setup", methods=["GET", "POST"])
@login_required
def setup():
    """Create a new family (and become its admin) or join one with an invite code."""
    if current_user.household_id is not None:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            name = request.form.get("household_name", "").strip()
            if not name:
                flash("نام خانواده را بنویسید.", "error")
            else:
                household = Household(name=name[:100], invite_code=Household.generate_invite_code())
                db.session.add(household)
                db.session.flush()
                current_user.household_id = household.id
                current_user.is_admin = True
                db.session.commit()
                flash("خانواده ساخته شد. کد دعوت را به اعضای خانواده بدهید.", "success")
                return redirect(url_for("family"))
        elif action == "join":
            code = helpers.normalize_invite_code(request.form.get("code"))
            household = Household.query.filter_by(invite_code=code).first() if code else None
            if household is None:
                flash("کد دعوت درست نیست.", "error")
            else:
                current_user.household_id = household.id
                current_user.is_admin = False
                db.session.commit()
                flash(f"به خانوادهٔ «{household.name}» خوش آمدید.", "success")
                return redirect(url_for("dashboard"))

    return render_template("setup.html")


# ---------- Expenses ----------

def _year_options(selected):
    this_year = helpers.today_shamsi().year
    years = set(range(this_year - 3, this_year + 2))
    years.add(selected)
    return sorted(years, reverse=True)


def _read_expense_form(form):
    """Validate the expense form. Returns (fields, None) or (None, error message)."""
    amount = helpers.parse_amount(form.get("amount"))
    if not amount or amount <= 0:
        return None, "مبلغ را درست بنویسید."
    if amount > 1_000_000_000:
        return None, "مبلغ خیلی زیاد است."

    category = form.get("category")
    if category not in CATEGORY_MAP:
        return None, "کتگوری را انتخاب کنید."

    try:
        year = int(helpers.to_ascii_digits(form.get("year")))
        month = int(helpers.to_ascii_digits(form.get("month")))
        day = int(helpers.to_ascii_digits(form.get("day")))
        spent_on = jdatetime.date(year, month, day).togregorian()
    except (TypeError, ValueError):
        return None, "این تاریخ وجود ندارد. روز و ماه را دوباره ببینید."

    note = form.get("note", "").strip()[:200]
    return {"amount": amount, "category": category, "spent_on": spent_on, "note": note}, None


def _editable_expense(expense_id):
    expense = db.session.get(Expense, expense_id)
    if expense is None or expense.household_id != current_user.household_id:
        abort(404)
    if not current_user.can_edit(expense):
        abort(403)
    return expense


def _month_total(household_id, year, month):
    start, end = helpers.month_bounds(year, month)
    return db.session.scalar(
        db.select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.household_id == household_id,
            Expense.spent_on >= start,
            Expense.spent_on < end,
        )
    )


@app.route("/")
@login_required
@household_required
def dashboard():
    today = helpers.today_shamsi()
    year = request.args.get("y", type=int) or today.year
    month = request.args.get("m", type=int) or today.month
    if not (1 <= month <= 12 and 1300 <= year <= 1500):
        year, month = today.year, today.month

    household = current_user.household
    start, end = helpers.month_bounds(year, month)
    expenses = db.session.scalars(
        db.select(Expense)
        .where(
            Expense.household_id == household.id,
            Expense.spent_on >= start,
            Expense.spent_on < end,
        )
        .order_by(Expense.spent_on.desc(), Expense.id.desc())
    ).all()

    total = sum(e.amount for e in expenses)
    by_category = {c["key"]: 0 for c in CATEGORIES}
    daily = [0] * (end - start).days
    for e in expenses:
        by_category[e.category_info["key"]] += e.amount
        daily[(e.spent_on - start).days] += e.amount

    chart_data = {
        "categories": [
            {"label": c["label"], "color": c["color"], "value": by_category[c["key"]]}
            for c in CATEGORIES
            if by_category[c["key"]]
        ],
        "daily": daily,
        "dayLabels": [helpers.fa_digits(d) for d in range(1, len(daily) + 1)],
    }

    prev_year, prev_month = helpers.shift_month(year, month, -1)
    next_year, next_month = helpers.shift_month(year, month, 1)
    is_current = (year, month) == (today.year, today.month)

    budget = household.monthly_budget
    budget_pct = min(100, round(total * 100 / budget)) if budget else 0

    # New entries default to today, or to the first day when viewing another month.
    default_date = today if is_current else jdatetime.date(year, month, 1)
    form_values = {
        "amount": "",
        "category": "food",
        "year": default_date.year,
        "month": default_date.month,
        "day": default_date.day,
        "note": "",
    }

    return render_template(
        "dashboard.html",
        household=household,
        expenses=expenses,
        total=total,
        chart_data=chart_data,
        title=helpers.month_title(year, month),
        prev={"y": prev_year, "m": prev_month},
        next={"y": next_year, "m": next_month},
        prev_title=helpers.month_title(prev_year, prev_month),
        prev_total=_month_total(household.id, prev_year, prev_month),
        is_current=is_current,
        budget=budget,
        budget_pct=budget_pct,
        form_values=form_values,
        years=_year_options(default_date.year),
        view={"y": year, "m": month},
    )


@app.post("/expenses")
@login_required
@household_required
def add_expense():
    data, error = _read_expense_form(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for(
            "dashboard",
            y=request.form.get("view_y", type=int),
            m=request.form.get("view_m", type=int),
        ))

    db.session.add(Expense(household_id=current_user.household_id, user_id=current_user.id, **data))
    db.session.commit()
    flash("مصرف ثبت شد.", "success")
    j = helpers.to_shamsi(data["spent_on"])
    return redirect(url_for("dashboard", y=j.year, m=j.month))


@app.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
@household_required
def edit_expense(expense_id):
    expense = _editable_expense(expense_id)

    if request.method == "POST":
        data, error = _read_expense_form(request.form)
        if error:
            flash(error, "error")
        else:
            for field, value in data.items():
                setattr(expense, field, value)
            db.session.commit()
            flash("تغییرات ذخیره شد.", "success")
            j = helpers.to_shamsi(expense.spent_on)
            return redirect(url_for("dashboard", y=j.year, m=j.month))

    j = helpers.to_shamsi(expense.spent_on)
    values = {
        "amount": expense.amount,
        "category": expense.category,
        "year": j.year,
        "month": j.month,
        "day": j.day,
        "note": expense.note,
    }
    return render_template(
        "edit_expense.html", expense=expense, values=values, years=_year_options(j.year)
    )


@app.post("/expenses/<int:expense_id>/delete")
@login_required
@household_required
def delete_expense(expense_id):
    expense = _editable_expense(expense_id)
    j = helpers.to_shamsi(expense.spent_on)
    db.session.delete(expense)
    db.session.commit()
    flash("مصرف حذف شد.", "success")
    return redirect(url_for("dashboard", y=j.year, m=j.month))


# ---------- Family ----------

@app.route("/family")
@login_required
@household_required
def family():
    return render_template("family.html", household=current_user.household)


@app.post("/family/budget")
@login_required
@household_required
@admin_required
def set_budget():
    raw = request.form.get("budget", "").strip()
    budget = helpers.parse_amount(raw) if raw else None
    if raw and not budget:
        flash("بودجه را درست بنویسید.", "error")
    else:
        current_user.household.monthly_budget = budget
        db.session.commit()
        flash("بودجهٔ ماهانه ذخیره شد." if budget else "بودجه برداشته شد.", "success")
    return redirect(url_for("family"))


@app.post("/family/invite-code")
@login_required
@household_required
@admin_required
def regenerate_invite_code():
    current_user.household.invite_code = Household.generate_invite_code()
    db.session.commit()
    flash("کد دعوت جدید ساخته شد. کد قبلی دیگر کار نمی‌کند.", "success")
    return redirect(url_for("family"))


@app.post("/family/members/<int:user_id>/remove")
@login_required
@household_required
@admin_required
def remove_member(user_id):
    member = db.session.get(User, user_id)
    if member is None or member.household_id != current_user.household_id:
        abort(404)
    if member.id == current_user.id:
        abort(400)
    member.household_id = None
    member.is_admin = False
    db.session.commit()
    flash(f"«{member.name}» از خانواده حذف شد.", "success")
    return redirect(url_for("family"))


@app.post("/family/leave")
@login_required
@household_required
def leave_family():
    if current_user.is_admin:
        abort(400)
    current_user.household_id = None
    db.session.commit()
    flash("شما از خانواده خارج شدید.", "info")
    return redirect(url_for("setup"))


if __name__ == "__main__":
    # Port 5000 is reserved by Windows on this machine, so use 8000.
    app.run(debug=True, port=8000)
