"""
Liberty Charity Foundation
Flask marketing site. Static content, one dynamic route (contact form to email).
"""

import os
import re
import smtplib
import logging
from email.message import EmailMessage
from datetime import datetime, timezone

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, abort
)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    SITE_NAME="Liberty Charity Foundation",
    CONTACT_EMAIL=os.environ.get("CONTACT_EMAIL", "info@libertycharityfoundation.org"),
    SMTP_HOST=os.environ.get("SMTP_HOST", ""),
    SMTP_PORT=int(os.environ.get("SMTP_PORT", "587")),
    SMTP_USER=os.environ.get("SMTP_USER", ""),
    SMTP_PASS=os.environ.get("SMTP_PASS", ""),
    MAIL_FROM=os.environ.get("MAIL_FROM", ""),
)

logging.basicConfig(level=logging.INFO)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")

NAV = [
    ("home", "Home", "/"),
    ("about", "About", "/about"),
    ("work", "Our work", "/our-work"),
    ("contact", "Contact", "/contact"),
]

# The four-stage framework. Order carries meaning, so it is data, not decoration.
STAGES = [
    {"n": 1, "key": "survival",    "name": "Survival",
     "line": "Daily needs consume every hour. Nothing can be planned."},
    {"n": 2, "key": "stability",   "name": "Stability",
     "line": "Food is reliable. Families can attend school and work."},
    {"n": 3, "key": "selfsuff",    "name": "Self-sufficiency",
     "line": "Land produces. The community feeds itself and generates value."},
    {"n": 4, "key": "liberty",     "name": "Liberty",
     "line": "Capital, choice, and agency. Independence that lasts."},
]

PROGRAMS = [
    {
        "name": "Food resources",
        "layer": "The survival and dignity layer",
        "outcome": "Immediate stability",
        "points": [
            "Addresses urgent hunger and nutrition gaps",
            "Stabilizes families so they can participate in education and work",
            "Creates the baseline security needed for growth",
        ],
        "close": "Liberty here means no one is trapped in survival mode.",
    },
    {
        "name": "Land cultivation",
        "layer": "The foundation layer",
        "outcome": "Economic independence",
        "points": [
            "Turns unused or underutilized land into productive assets",
            "Builds food security and local farming capacity",
            "Creates long-term self-sufficiency instead of dependency",
        ],
        "close": "Liberty begins when a community can feed itself and generate value from its own land.",
    },
    {
        "name": "Microfinancing",
        "layer": "The mobility layer",
        "outcome": "Access to opportunity",
        "points": [
            "Gives individuals capital to start or grow small businesses",
            "Supports entrepreneurship where traditional banking does not reach",
            "Converts potential into action",
        ],
        "close": "Liberty means people are not locked out of opportunity by a lack of access to credit.",
    },
]

PROJECTS = [
    {
        "slug": "uganda",
        "country": "Uganda",
        "stage": 2,
        "stage_name": "Stability",
        "programs": ["Food resources"],
        "photo": "uganda",
        "alt": "Schoolchildren leaning out of a classroom window, smiling",
        "summary": "Our work in Uganda begins where every community has to begin: food. "
                   "Consistent food resources remove the daily uncertainty that keeps "
                   "families in survival mode and keeps children out of school.",
        "detail": [
            "Food support directed to families and schoolchildren",
            "Focus on consistency, so households can plan beyond the week",
            "Groundwork for the cultivation phase that follows",
        ],
        "next": "Next: moving from reliable food to land that produces it.",
    },
    {
        "slug": "cameroon",
        "country": "Cameroon",
        "stage": 3,
        "stage_name": "Self-sufficiency",
        "programs": ["Food resources", "Land cultivation", "Microfinancing"],
        "photo": "cameroon",
        "alt": "A village road in Cameroon under an open sky",
        "summary": "Cameroon is where the full model is taking shape. Food support is in "
                   "place, land cultivation is underway, and microfinancing is beginning "
                   "to put capital in the hands of people who have never had access to it.",
        "detail": [
            "Food resources sustaining households today",
            "Land cultivation turning idle ground into a working asset",
            "Microfinancing opening credit to small business owners",
        ],
        "next": "Next: capital circulating locally, without outside dependency.",
    },
]


@app.context_processor
def inject_globals():
    return {
        "nav": NAV,
        "site_name": app.config["SITE_NAME"],
        "contact_email": app.config["CONTACT_EMAIL"],
        "year": datetime.now(timezone.utc).year,
    }


@app.route("/")
def home():
    return render_template(
        "index.html", page="home",
        stages=STAGES, programs=PROGRAMS, projects=PROJECTS,
    )


@app.route("/about", strict_slashes=False)
def about():
    return render_template("about.html", page="about", stages=STAGES)


@app.route("/our-work", strict_slashes=False)
@app.route("/work", strict_slashes=False)
@app.route("/ourwork", strict_slashes=False)
def work():
    return render_template(
        "work.html", page="work",
        programs=PROGRAMS, projects=PROJECTS, stages=STAGES,
    )


@app.route("/contact", methods=["GET", "POST"], strict_slashes=False)
def contact():
    form = {"name": "", "email": "", "organization": "", "topic": "", "message": ""}

    if request.method == "POST":
        # Honeypot. Real people leave it empty.
        if request.form.get("website", "").strip():
            return redirect(url_for("contact_thanks"))

        for field in form:
            form[field] = request.form.get(field, "").strip()

        errors = []
        if not form["name"]:
            errors.append("Add your name so we know who we are replying to.")
        if not EMAIL_RE.match(form["email"]):
            errors.append("Enter an email address we can reply to.")
        if len(form["message"]) < 10:
            errors.append("Tell us a little more in the message field.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("contact.html", page="contact", form=form), 400

        try:
            send_contact_email(form)
        except Exception:
            app.logger.exception("Contact email failed to send")
            flash(
                "The message did not send. Email us directly at "
                f"{app.config['CONTACT_EMAIL']} and we will pick it up from there.",
                "error",
            )
            return render_template("contact.html", page="contact", form=form), 500

        return redirect(url_for("contact_thanks"))

    return render_template("contact.html", page="contact", form=form)


@app.route("/contact/thank-you", strict_slashes=False)
def contact_thanks():
    return render_template("thanks.html", page="contact")


def send_contact_email(form):
    """Send the submission to the foundation inbox. No database by design."""
    host = app.config["SMTP_HOST"]
    if not host:
        # Local development without SMTP configured: log instead of failing silently.
        app.logger.info("SMTP not configured. Submission: %s", form)
        return

    msg = EmailMessage()
    msg["Subject"] = f"Website enquiry: {form['name']}"
    msg["From"] = app.config["MAIL_FROM"] or app.config["SMTP_USER"]
    msg["To"] = app.config["CONTACT_EMAIL"]
    msg["Reply-To"] = form["email"]
    msg.set_content(
        "New message from the Liberty Charity Foundation website.\n\n"
        f"Name:         {form['name']}\n"
        f"Email:        {form['email']}\n"
        f"Organization: {form['organization'] or '-'}\n"
        f"Topic:        {form['topic'] or '-'}\n\n"
        f"Message:\n{form['message']}\n"
    )

    with smtplib.SMTP(host, app.config["SMTP_PORT"], timeout=20) as smtp:
        smtp.starttls()
        if app.config["SMTP_USER"]:
            smtp.login(app.config["SMTP_USER"], app.config["SMTP_PASS"])
        smtp.send_message(msg)


@app.route("/healthz")
def healthz():
    """Confirms Flask is serving and lists the routes it knows about."""
    routes = sorted(
        str(r.rule) for r in app.url_map.iter_rules()
        if r.endpoint != "static"
    )
    return {"status": "ok", "routes": routes}, 200


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html", page=""), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
