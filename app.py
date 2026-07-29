"""
Lumé, smart care for your natural glow
Main Flask application.

Sprint 1: user registration, login, and skin profile.
This file sets up the app, the routes, and connects the pieces together.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import database  # our own module that handles the SQLite database

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
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        # Basic validation, done on the server side.
        if not email or not password:
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
        user_id = database.create_user(email, password_hash)

        # Log the new user in by saving their id in the session.
        session["user_id"] = user_id
        session["email"] = email
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
            "climate": request.form.get("climate", ""),
        }

        # Simple validation: skin type and climate are required.
        if not profile_data["skin_type"] or not profile_data["climate"]:
            flash("Skin type and climate are required.")
            existing = database.get_profile(user_id)
            return render_template("profile.html", profile=existing or profile_data)

        database.save_profile(user_id, profile_data)
        flash("Your profile has been saved.")
        return redirect(url_for("profile"))

    # GET: show the form, filled in if a profile already exists.
    existing = database.get_profile(user_id)
    return render_template("profile.html", profile=existing)


if __name__ == "__main__":
    # debug=True reloads the app automatically while developing.
    app.run(debug=True, port=5000)
