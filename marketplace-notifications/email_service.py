"""
Email service for marketplace alert notifications.

Uses the Mailgun HTTP API to deliver alert emails. Credentials and the
sending domain are configured via environment variables (see README).
"""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv


def send_marketplace_alert_email(
    recipient_email: str, all_results: dict[str, list[dict]]
) -> None:
    """Build and send the marketplace alert email for the given results.

    :param recipient_email: Address that should receive the alert.
    :param all_results: Mapping of search query to its list of listings.
    :raises requests.HTTPError: If the Mailgun API returns a non-2xx response.
    """
    total = sum(len(listings) for listings in all_results.values())
    if total == 0:
        print("No listings found across all searches. Skipping email.")
        return

    body = _build_email_body(all_results)
    _send_email(
        recipients=[recipient_email],
        subject="New Facebook Marketplace Listings",
        body=body,
    )
    print(f"Email sent with {total} total listings.")


def _build_email_body(all_results: dict[str, list[dict]]) -> str:
    """Render the HTML body for a marketplace alert email.

    :param all_results: Mapping of search query to its list of listings.
    :return: Fully rendered HTML document as a string.
    """
    html_parts = ["<html><body>"]
    for search_query, listings in all_results.items():
        html_parts.append(f"<h2>{search_query} — {len(listings)} listings</h2>")
        for listing in listings:
            location = listing.get("location", "")
            loc_str = f" ({location})" if location else ""
            title = listing["details"][0] if listing.get("details") else ""
            images = listing.get("images", [])
            imgs_html = "".join(
                f"<img src='{src}' alt='{title}' "
                f"style='width:120px;height:120px;object-fit:cover;"
                f"border-radius:8px;margin-right:4px;'>"
                for src in images
            )
            html_parts.append(
                f"<div style='margin-bottom:16px;'>"
                f"<a href='{listing['url']}' style='text-decoration:none;color:inherit;'>"
                f"<div style='font-size:16px;'><strong>{title}</strong></div>"
                f"<div style='margin-top:6px;'>{listing['price']}{loc_str}</div>"
                f"<div style='margin-top:6px;'>{imgs_html}</div>"
                f"</a></div>"
            )
    html_parts.append("</body></html>")
    return "".join(html_parts)


def _send_email(recipients: list[str], subject: str, body: str) -> None:
    """POST an HTML email to the Mailgun messages endpoint.

    :param recipients: List of recipient email addresses.
    :param subject: Email subject line.
    :param body: Rendered HTML email body.
    :raises RuntimeError: If required Mailgun env vars are missing.
    :raises requests.HTTPError: If the Mailgun API returns a non-2xx response.
    """
    load_dotenv()

    if not _get_bool_env("EMAIL_NOTIFICATIONS_ENABLED", default=True):
        print("EMAIL_NOTIFICATIONS_ENABLED is false. Skipping email send.")
        return

    # The following env vars must be set after you create your Mailgun account.
    # See README for setup instructions.
    mailgun_api_key = os.getenv("MAILGUN_API_KEY")
    mailgun_domain = os.getenv("MAILGUN_DOMAIN")
    mailgun_from_address = os.getenv("MAILGUN_FROM_ADDRESS")

    if not mailgun_api_key or not mailgun_domain or not mailgun_from_address:
        raise RuntimeError(
            "Mailgun is not configured. Set MAILGUN_API_KEY, MAILGUN_DOMAIN, "
            "and MAILGUN_FROM_ADDRESS in your .env file."
        )

    data = {
        "from": mailgun_from_address,
        "to": recipients,
        "subject": subject,
        "html": body,
    }

    response = requests.post(
        f"https://api.mailgun.net/v3/{mailgun_domain}/messages",
        auth=("api", mailgun_api_key),
        data=data,
        timeout=10,
    )
    response.raise_for_status()


def _get_bool_env(variable_name: str, default: bool) -> bool:
    """Read a boolean-valued environment variable.

    :param variable_name: Name of the environment variable.
    :param default: Value to return when the variable is unset or unparseable.
    :return: Parsed boolean, or default.
    """
    value = os.getenv(variable_name)
    if value is None:
        return default
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return default
