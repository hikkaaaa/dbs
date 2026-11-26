"""Reading form fields and turning errors into clear messages."""

from datetime import date, datetime, time, timezone

from sqlalchemy.exc import DataError, IntegrityError


class FormError(Exception):
    """A rule was broken. The message is shown to the user."""


# Every save is wrapped in "try ... except SAVE_ERRORS".
SAVE_ERRORS = (FormError, IntegrityError, DataError)


# ---------- Reading form fields ----------

def required(form, name, label):
    value = form.get(name, "").strip()
    if not value:
        raise FormError(f"{label} is required.")
    return value


def optional(form, name):
    """An empty field is saved as NULL."""
    return form.get(name, "").strip() or None


def to_int(value, label):
    try:
        return int(value)
    except ValueError:
        raise FormError(f"{label} must be a whole number.")


def required_int(form, name, label):
    return to_int(required(form, name, label), label)


def required_date(form, name, label):
    try:
        return date.fromisoformat(required(form, name, label))
    except ValueError:
        raise FormError(f"{label} is not a valid date.")


def required_time(form, name, label):
    try:
        return time.fromisoformat(required(form, name, label))
    except ValueError:
        raise FormError(f"{label} is not a valid time.")


def required_utc_datetime(form, name, label):
    try:
        value = datetime.fromisoformat(required(form, name, label))
    except ValueError:
        raise FormError(f"{label} is not a valid date and time.")
    return value.replace(tzinfo=timezone.utc)


def lines(form, name, label):
    """Read a text box with one item per line. At least one item is needed."""
    items = [line.strip() for line in form.get(name, "").splitlines()]
    items = list(dict.fromkeys(item for item in items if item))  # drop blanks and repeats
    if not items:
        raise FormError(f"Enter at least one {label}.")
    return items


# ---------- Error messages ----------

# The keys are constraint names from 01_schema.sql.
CONSTRAINT_MESSAGES = {
    "uq_app_user_email": "Another user already has this email.",
    "uq_paper_author_position": "Two authors cannot have the same position.",
    "uq_paper_one_corresponding": "A paper can have only one corresponding author.",
    "uq_review_paper_reviewer": "This reviewer has already reviewed this paper.",
    "paper_version_pkey": "This paper already has a version with that number.",
    "paper_version_version_no_check": "Version number must be 1 or more.",
    "paper_author_author_position_check": "Author position must be 1 or more.",
    "reviewer_years_experience_check": "Years of experience cannot be negative.",
    "review_overall_score_check": "Score must be from 1 to 5.",
    "review_recommendation_check": "Recommendation must be accept or reject.",
    "ck_paper_status": "Invalid paper status.",
    "ck_session_times": "End time must be later than start time.",
    "fk_session_chair_pool": "The chair must be in this conference's reviewer pool.",
}


def error_message(error):
    """Turn any of the SAVE_ERRORS into a message for the user."""
    if isinstance(error, FormError):
        return str(error)
    if isinstance(error, DataError):
        return "One of the values is invalid or too large."

    constraint = error.orig.diag.constraint_name
    return CONSTRAINT_MESSAGES.get(constraint, f"The database rejected this change ({constraint}).")
