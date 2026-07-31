"""
Lumé, smart care for your natural glow
Main Flask application.

Sprint 1: user registration, login, and skin profile.
This file sets up the app, the routes, and connects the pieces together.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import json
from datetime import datetime
import database  # our own module that handles the SQLite database
import ai_service  # our own module that talks to the Claude API

app = Flask(__name__)
# The secret key is needed by Flask to keep user sessions secure
# In a real deployment this would be loaded from an environment variable.
app.secret_key = "lume-dev-secret-key-change-me"


# Make sure the database and its tables exist when the app starts.
database.init_db()


@app.route("/")
def home():
    """The landing page. If already logged in, go straight to the profile."""
    if "user_id" in session:
        return redirect(url_for("profile"))
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user with an email and a password."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        # Basic validation, done on the server side.
        if not name or not email or not password:
            flash("Please fill in every field.")
            return render_template("register.html")
        if password != confirm:
            flash("The two passwords do not match.")
            return render_template("register.html")
        if len(password) < 6:
            flash("Your password should be at least 6 characters.")
            return render_template("register.html")
        if database.get_user_by_email(email):
            flash("That email is already registered. Try logging in.")
            return render_template("register.html")

        # Store the password as a hash, never as plain text.
        password_hash = generate_password_hash(password, method="pbkdf2:sha256")
        user_id = database.create_user(name, email, password_hash)

        # Log the new user in by saving their details in the session.
        session["user_id"] = user_id
        session["email"] = email
        session["name"] = name
        flash(f"Welcome to Lumé, {name}. Let's care for your skin and bring out your glow.")
        return redirect(url_for("profile"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log an existing user in."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = database.get_user_by_email(email)
        # Check the user exists and the password matches the stored hash.
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            session["name"] = user["name"]
            return redirect(url_for("profile"))

        flash("Wrong email or password. Please try again.")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log the user out by clearing the session."""
    session.clear()
    return redirect(url_for("home"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    """Show and save the user's skin profile. Requires login."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        # Collect the profile fields from the form
        profile_data = {
            "skin_type": request.form.get("skin_type", ""),
            "age": request.form.get("age", ""),
            "concerns": request.form.get("concerns", ""),
            "sensitivities": request.form.get("sensitivities", ""),
            "allergies": request.form.get("allergies", ""),
            "climate": request.form.get("climate", ""),
        }

        # Server side validation: these fields are required.
        if (not profile_data["skin_type"] or not profile_data["climate"]
                or not profile_data["age"] or not profile_data["concerns"]):
            flash("Please fill in skin type, age, main concerns and climate.")
            existing = database.get_profile(user_id)
            return render_template("profile.html", profile=existing or profile_data)

        database.save_profile(user_id, profile_data)
        flash("Lovely. Now let's add what you already use.")
        return redirect(url_for("products"))

    # GET: show the form, filled in if a profile already exists.
    existing = database.get_profile(user_id)
    return render_template("profile.html", profile=existing)


# The list of product types the user can choose from.
# Keeping this here means the same list is used every time.
PRODUCT_TYPES = [
    "Cleanser",
    "Toner",
    "Serum",
    "Moisturiser",
    "Sunscreen",
    "Exfoliant",
    "Eye cream",
    "Face oil",
    "Mask",
]


@app.route("/products", methods=["GET", "POST"])
def products():
    """Show the user's products and let them add a new one. Requires login."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        product_type = request.form.get("type", "")

        # Both fields are required to add a product.
        if not name or not product_type:
            flash("Please enter a product name and choose a type.")
        else:
            database.add_product(user_id, name, product_type)
            flash("Product added.")
        return redirect(url_for("products"))

    # GET: show the form and the list of products the user already has.
    user_products = database.get_products(user_id)
    return render_template("products.html", products=user_products, types=PRODUCT_TYPES)


@app.route("/products/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    """Delete one of the user's products. Requires login."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    database.delete_product(product_id, user_id)
    flash("Product removed.")
    return redirect(url_for("products"))


@app.route("/routine", methods=["GET", "POST"])
def routine():
    """Generate and show the user's AI routine. Requires login."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        # The user clicked 'generate'. Gather their data.
        profile = database.get_profile(user_id)
        products = database.get_products(user_id)

        # A profile is needed for a useful routine.
        if not profile:
            flash("Please fill in your skin profile first.")
            return redirect(url_for("profile"))

        # Ask the AI for a routine.
        result = ai_service.generate_routine(profile, products)

        # If the AI failed or the reply could not be read, fail safely.
        if result is None:
            flash("Sorry, we could not build your routine right now. Please try again.")
            return redirect(url_for("routine"))

        # Save the routine as JSON text, with the date.
        database.save_routine(
            user_id,
            json.dumps(result),
            datetime.now().strftime("%d %b %Y"),
        )
        flash("Your routine is ready.")
        return redirect(url_for("routine"))

    # GET: show the latest saved routine, if there is one.
    saved = database.get_latest_routine(user_id)
    routine_data = None
    created_at = None
    if saved:
        routine_data = json.loads(saved["routine_json"])
        created_at = saved["created_at"]

    return render_template("routine.html", routine=routine_data, created_at=created_at)


@app.route("/history")
def history():
    """Show all the user's past routines. Requires login."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    saved = database.get_all_routines(user_id)

    # Turn each stored JSON string back into data the page can show.
    past = []
    for row in saved:
        past.append({
            "routine": json.loads(row["routine_json"]),
            "created_at": row["created_at"],
        })

    return render_template("history.html", past=past)


if __name__ == "__main__":
    # debug=True reloads the app automatically while developing.
    app.run(debug=True, port=5000)