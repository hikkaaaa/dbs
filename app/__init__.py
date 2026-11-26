"""Creates the Flask web application."""

import os

from flask import Flask, redirect, url_for

from . import papers, reviews, sessions, users


def create_app():
    app = Flask(__name__)

    # Flask needs a secret key to show one-time (flash) messages.
    app.secret_key = os.environ.get("SECRET_KEY", "local-development-key")

    # Each file below holds the pages for one kind of record.
    app.register_blueprint(users.bp)
    app.register_blueprint(papers.bp)
    app.register_blueprint(reviews.bp)
    app.register_blueprint(sessions.bp)

    @app.route("/")
    def home():
        return redirect(url_for("papers.list_papers"))

    return app
