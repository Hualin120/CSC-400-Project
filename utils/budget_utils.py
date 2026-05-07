from collections import defaultdict
from calendar import month_name
from datetime import date
from sqlalchemy import extract, func

from models import db, Budget, Expense, AccountBook


def get_month_label(month: int) -> str:
    """Return the month name for a month number."""
    if 1 <= month <= 12:
        return month_name[month]
    return "Unknown"


def get_budgets(user_id, account_book_id, month, year):
    """
    Return all budgets for a specific user, account book, month, and year.
    """
    return (
        Budget.query
        .filter_by(
            user_id=user_id,
            account_book_id=account_book_id,
            month=month,
            year=year
        )
        .order_by(Budget.category.asc())
        .all()
    )


def calculate_spent_by_category(user_id, account_book_id, month, year):
    """
    Return a dictionary of expense totals by category for a specific
    user, account book, month, and year.
    Example:
        {
            "Food": 180.0,
            "Gas": 70.0
        }
    """
    rows = (
        db.session.query(
            Expense.category,
            func.coalesce(func.sum(Expense.amount), 0.0)
        )
        .filter(
            Expense.account_book_id == account_book_id,
            extract("month", Expense.date) == month,
            extract("year", Expense.date) == year
        )
        .group_by(Expense.category)
        .all()
    )

    spent_by_category = {}
    for category, total in rows:
        spent_by_category[category] = float(total or 0.0)

    return spent_by_category


def get_status_class(percentage_used):
    """
    Return a status class based on budget usage percentage.
    """
    if percentage_used > 100:
        return "danger"
    if percentage_used >= 80:
        return "warning"
    return "success"


def build_budget_progress(user_id, account_book_id, month, year):
    """
    Build detailed budget progress data for one account book and month/year.
    Returns a list of dictionaries ready for the template.
    """
    budgets = get_budgets(user_id, account_book_id, month, year)
    spent_by_category = calculate_spent_by_category(user_id, account_book_id, month, year)

    budget_progress = []

    for budget in budgets:
        spent = float(spent_by_category.get(budget.category, 0.0))
        remaining = float(budget.amount - spent)

        if budget.amount > 0:
            percentage_used = round((spent / budget.amount) * 100, 1)
        else:
            percentage_used = 0.0

        progress_width = min(percentage_used, 100)

        budget_progress.append({
            "id": budget.id,
            "category": budget.category,
            "budget_amount": float(budget.amount),
            "spent_amount": spent,
            "remaining_amount": remaining,
            "percentage_used": percentage_used,
            "progress_width": progress_width,
            "status_class": get_status_class(percentage_used),
            "month": budget.month,
            "year": budget.year,
            "month_label": get_month_label(budget.month),
            "account_book_id": budget.account_book_id,
        })

    return budget_progress


def get_budget_summary(user_id, account_book_id, month, year):
    """
    Return a summary for a single account book's budgets in a selected month/year.
    """
    budget_progress = build_budget_progress(user_id, account_book_id, month, year)

    total_budget = round(sum(item["budget_amount"] for item in budget_progress), 2)
    total_spent = round(sum(item["spent_amount"] for item in budget_progress), 2)
    total_remaining = round(total_budget - total_spent, 2)

    over_budget_count = sum(1 for item in budget_progress if item["percentage_used"] > 100)
    warning_count = sum(1 for item in budget_progress if 80 <= item["percentage_used"] <= 100)

    return {
        "total_budget": total_budget,
        "total_spent": total_spent,
        "total_remaining": total_remaining,
        "over_budget_count": over_budget_count,
        "warning_count": warning_count,
        "budget_count": len(budget_progress),
    }


def get_top_budget_warnings(user_id, account_book_id, month, year, limit=3):
    """
    Return the budget categories closest to or over the limit
    for one account book in a selected month/year.
    """
    budget_progress = build_budget_progress(user_id, account_book_id, month, year)

    sorted_items = sorted(
        budget_progress,
        key=lambda item: item["percentage_used"],
        reverse=True
    )

    return sorted_items[:limit]


def get_overall_budget_summary(user_id, month, year):
    """
    Return combined budget totals across all account books for one user
    in a selected month/year.
    """
    budgets = (
        Budget.query
        .filter_by(user_id=user_id, month=month, year=year)
        .all()
    )

    total_budget = round(sum(float(b.amount) for b in budgets), 2)

    total_spent_result = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0.0))
        .join(AccountBook, Expense.account_book_id == AccountBook.id)
        .filter(
            AccountBook.user_id == user_id,
            extract("month", Expense.date) == month,
            extract("year", Expense.date) == year
        )
        .scalar()
    )

    total_spent = round(float(total_spent_result or 0.0), 2)
    total_remaining = round(total_budget - total_spent, 2)

    return {
        "total_budget": total_budget,
        "total_spent": total_spent,
        "total_remaining": total_remaining,
        "budget_count": len(budgets),
    }


def get_overall_budget_warnings(user_id, month, year, limit=5):
    """
    Return top budget warnings across all account books.
    Each result includes the account book name.
    """
    budgets = (
        Budget.query
        .filter_by(user_id=user_id, month=month, year=year)
        .all()
    )

    warnings = []

    for budget in budgets:
        spent_result = (
            db.session.query(func.coalesce(func.sum(Expense.amount), 0.0))
            .filter(
                Expense.account_book_id == budget.account_book_id,
                Expense.category == budget.category,
                extract("month", Expense.date) == month,
                extract("year", Expense.date) == year
            )
            .scalar()
        )

        spent = float(spent_result or 0.0)
        remaining = float(budget.amount - spent)

        if budget.amount > 0:
            percentage_used = round((spent / budget.amount) * 100, 1)
        else:
            percentage_used = 0.0

        warnings.append({
            "budget_id": budget.id,
            "category": budget.category,
            "account_book_name": budget.account_book.bookname if budget.account_book else "Unknown",
            "budget_amount": float(budget.amount),
            "spent_amount": spent,
            "remaining_amount": remaining,
            "percentage_used": percentage_used,
            "status_class": get_status_class(percentage_used),
        })

    warnings.sort(key=lambda item: item["percentage_used"], reverse=True)
    return warnings[:limit]


def get_available_budget_years(user_id):
    """
    Return a list of years that have budgets for the user.
    Includes the current year even if there are no budgets yet.
    """
    current_year = date.today().year

    rows = (
        db.session.query(Budget.year)
        .filter(Budget.user_id == user_id)
        .distinct()
        .order_by(Budget.year.desc())
        .all()
    )

    years = [row[0] for row in rows]

    if current_year not in years:
        years.insert(0, current_year)

    return years


def get_user_account_books(user_id):
    """
    Return all account books for the user ordered by name.
    """
    return (
        AccountBook.query
        .filter_by(user_id=user_id)
        .order_by(AccountBook.bookname.asc())
        .all()
    )