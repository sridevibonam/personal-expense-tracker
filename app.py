
from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

DATABASE = "expenses.db"

ALLOWED_CATEGORIES = [
    "Food",
    "Travel",
    "Shopping",
    "Education",
    "Bills",
    "Other"
]


# Connect to the database
def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Create the expenses table
def create_table():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# Validate expense form data
def validate_expense(form):
    title = form.get("title", "").strip()
    amount_text = form.get("amount", "").strip()
    category = form.get("category", "").strip()
    date = form.get("date", "").strip()

    if not title:
        return None, "Expense name is required"

    if len(title) > 100:
        return None, "Expense name cannot exceed 100 characters"

    try:
        amount = float(amount_text)

        if not (amount > 0 and amount < float("inf")):
            return None, "Amount must be a valid positive number"

    except (ValueError, OverflowError):
        return None, "Please enter a valid amount"

    if category not in ALLOWED_CATEGORIES:
        return None, "Please select a valid category"

    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return None, "Please enter a valid date"

    expense_data = (title, amount, category, date)

    return expense_data, None


# Home page and add expense
@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":
        expense_data, error = validate_expense(request.form)

        if error:
            return f"""
            <h2>Invalid Expense Details</h2>
            <p>{error}</p>
            <a href="/">Go Back</a>
            """, 400

        conn = get_connection()

        conn.execute("""
            INSERT INTO expenses (title, amount, category, date)
            VALUES (?, ?, ?, ?)
        """, expense_data)

        conn.commit()
        conn.close()

        return redirect("/")

    # Fetch all expenses
    conn = get_connection()

    expenses = conn.execute("""
        SELECT * FROM expenses
        ORDER BY date DESC, id DESC
    """).fetchall()

    conn.close()

    # Calculate total spending
    total = sum(expense["amount"] for expense in expenses)

    # Calculate category-wise spending
    category_totals = {}

    for expense in expenses:
        category = expense["category"]
        amount = expense["amount"]

        category_totals[category] = (
            category_totals.get(category, 0) + amount
        )

    # Calculate monthly spending
    monthly_totals = {}

    for expense in expenses:
        month_key = expense["date"][:7]

        month_name = datetime.strptime(
            month_key, "%Y-%m"
        ).strftime("%B %Y")

        amount = expense["amount"]

        monthly_totals[month_name] = (
            monthly_totals.get(month_name, 0) + amount
        )

    # Sort months chronologically
    monthly_totals = dict(
        sorted(
            monthly_totals.items(),
            key=lambda item: datetime.strptime(
                item[0], "%B %Y"
            )
        )
    )

    # Display the home page
    return render_template(
        "index.html",
        expenses=expenses,
        total=total,
        category_totals=category_totals,
        monthly_totals=monthly_totals
    )


# Delete an expense
@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):

    conn = get_connection()

    conn.execute(
        "DELETE FROM expenses WHERE id = ?",
        (expense_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")


# Edit an existing expense
@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):

    conn = get_connection()

    # Find the expense
    expense = conn.execute(
        "SELECT * FROM expenses WHERE id = ?",
        (expense_id,)
    ).fetchone()

    if expense is None:
        conn.close()
        return "Expense not found", 404

    if request.method == "POST":

        expense_data, error = validate_expense(request.form)

        if error:
            conn.close()
            return f"""
            <h2>Invalid Expense Details</h2>
            <p>{error}</p>
            <a href="/">Go Back</a>
            """, 400

        title, amount, category, date = expense_data

        conn.execute("""
            UPDATE expenses
            SET title = ?, amount = ?, category = ?, date = ?
            WHERE id = ?
        """, (title, amount, category, date, expense_id))

        conn.commit()
        conn.close()

        return redirect("/")

    conn.close()

    return render_template(
        "edit.html",
        expense=expense
    )


# Run the application
if __name__ == "__main__":
    create_table()
    app.run(debug=True)
