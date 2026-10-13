"""Todoist label tools."""

import logging
from typing import Annotated, Optional

from pydantic import Field

from plugvan.todoist import client
from plugvan.todoist.limits import (
    MAX_COLOR_LENGTH,
    MAX_LABEL_NAME_LENGTH,
)
from plugvan.todoist.resolvers import (
    Ambiguous,
    LookupFailed,
    NotFound,
    _get_all_labels,
    ambiguous_message,
    resolve_label,
)

logger = logging.getLogger("todoist_mcp")


def list_labels() -> str:
    """Lists all user labels in Todoist (DEMO: deliberate description change to show CI turning red)."""
    try:
        api = client.get_api_client()
        labels = _get_all_labels(api)

        if not labels:
            return "ℹ️ Todoist hesabınızda herhangi bir etiket bulunamadı."

        lines = [f"🏷️ Mevcut Etiketler (Toplam: {len(labels)}):", ""]
        for idx, label in enumerate(labels, start=1):
            is_fav = " ⭐" if getattr(label, "is_favorite", False) else ""
            color_info = f", Renk: {label.color}" if getattr(label, "color", None) else ""
            lines.append(f"{idx}. [{label.id}] @{label.name}{is_fav}{color_info}")

        return "\n".join(lines).strip()
    except Exception as e:
        logger.error(
            "Failed to list labels from Todoist (error_type=%s)",
            type(e).__name__,
            exc_info=False,
        )
        return "❌ Failed to list labels from Todoist. Check server logs for details."


def create_label(
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_LABEL_NAME_LENGTH,
            description="The name of the new label (required, e.g. 'work', 'focus').",
        ),
    ],
    color: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_COLOR_LENGTH,
            description="Color name for the label icon (e.g. 'berry_red', 'mint_green', 'teal', optional).",
        ),
    ] = None,
) -> str:
    """Creates a new label in Todoist.

    Args:
        name: Name of the label (must not be empty, max 60 chars).
        color: Optional color name (e.g. 'berry_red', 'sky_blue', 'mint_green').
    """
    clean_name = name.strip().lstrip("@") if isinstance(name, str) else ""
    if not clean_name:
        return "❌ Invalid input: Label name cannot be empty or whitespace."
    if len(clean_name) > MAX_LABEL_NAME_LENGTH:
        return f"❌ Invalid input: Label name exceeds maximum length of {MAX_LABEL_NAME_LENGTH} characters."

    clean_color = color.strip().lower() if isinstance(color, str) else None
    if clean_color and len(clean_color) > MAX_COLOR_LENGTH:
        return f"❌ Invalid input: Color name exceeds maximum length of {MAX_COLOR_LENGTH} characters."

    try:
        api = client.get_api_client()
        kwargs = {}
        if clean_color:
            kwargs["color"] = clean_color

        label = api.add_label(name=clean_name, **kwargs)

        color_str = f"\n• Renk: {label.color}" if getattr(label, "color", None) else ""

        return (
            f"✅ Etiket başarıyla oluşturuldu!\n"
            f"• ID: {label.id}\n"
            f"• İsim: @{label.name}"
            f"{color_str}"
        )
    except Exception as e:
        logger.error(
            "Failed to create label in Todoist (name=%s, error_type=%s)",
            clean_name,
            type(e).__name__,
            exc_info=False,
        )
        return f"❌ Failed to create label '@{clean_name}' in Todoist. Check server logs for details."


def update_label(
    label_name_or_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_LABEL_NAME_LENGTH,
            description="The Todoist Label ID or Name to update (required).",
        ),
    ],
    new_name: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_LABEL_NAME_LENGTH,
            description="New name for the label (optional).",
        ),
    ] = None,
    color: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=MAX_COLOR_LENGTH,
            description="New color name for the label (e.g. 'berry_red', 'teal', optional).",
        ),
    ] = None,
) -> str:
    """Updates an existing Todoist label's name or color.

    Args:
        label_name_or_id: Name or ID of the label to update (required).
        new_name: New name for the label.
        color: New color name for the label.
    """
    clean_identifier = str(label_name_or_id).strip().lstrip("@") if label_name_or_id is not None else ""
    if not clean_identifier:
        return "❌ Invalid input: Label identifier cannot be empty or whitespace."
    if len(clean_identifier) > MAX_LABEL_NAME_LENGTH:
        return f"❌ Invalid input: Label identifier exceeds maximum length of {MAX_LABEL_NAME_LENGTH} characters."

    clean_new_name = new_name.strip().lstrip("@") if isinstance(new_name, str) else None
    if clean_new_name is not None and len(clean_new_name) > MAX_LABEL_NAME_LENGTH:
        return f"❌ Invalid input: New label name exceeds maximum length of {MAX_LABEL_NAME_LENGTH} characters."

    clean_color = color.strip().lower() if isinstance(color, str) else None
    if clean_color and len(clean_color) > MAX_COLOR_LENGTH:
        return f"❌ Invalid input: Color name exceeds maximum length of {MAX_COLOR_LENGTH} characters."

    if clean_new_name is None and clean_color is None:
        return "⚠️ Güncellenecek hiçbir alan belirtilmedi. Lütfen new_name veya color parametresi girin."

    failure_message = f"❌ Failed to update label '@{clean_identifier}' in Todoist. Check server logs for details."
    try:
        api = client.get_api_client()
        resolved = resolve_label(api, clean_identifier)

        if isinstance(resolved, LookupFailed):
            return failure_message
        if isinstance(resolved, Ambiguous):
            return ambiguous_message(resolved, "etiket", shown_query=f"@{clean_identifier}")
        if isinstance(resolved, NotFound):
            return f"⚠️ Güncellenecek etiket bulunamadı: '@{clean_identifier}'."
        label_id = resolved.id

        kwargs = {}
        updated_fields = []
        if clean_new_name is not None:
            kwargs["name"] = clean_new_name
            updated_fields.append(f"İsim: '@{clean_new_name}'")
        if clean_color is not None:
            kwargs["color"] = clean_color
            updated_fields.append(f"Renk: '{clean_color}'")

        api.update_label(label_id=label_id, **kwargs)

        changes_summary = "\n".join([f"• {field}" for field in updated_fields])
        return (
            f"✅ Etiket başarıyla güncellendi (ID: {label_id})!\n"
            f"Yapılan değişiklikler:\n"
            f"{changes_summary}"
        )
    except Exception as e:
        logger.error(
            "Failed to update label in Todoist (identifier=%s, error_type=%s)",
            clean_identifier,
            type(e).__name__,
            exc_info=False,
        )
        return failure_message


def delete_label(
    label_name_or_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_LABEL_NAME_LENGTH,
            description="The Todoist Label ID or Name to delete (required).",
        ),
    ],
) -> str:
    """Deletes a label from Todoist by either its ID or label name.

    Args:
        label_name_or_id: The ID or name of the label to delete.
    """
    clean_identifier = str(label_name_or_id).strip().lstrip("@") if label_name_or_id is not None else ""
    if not clean_identifier:
        return "❌ Invalid input: Label identifier cannot be empty or whitespace."
    if len(clean_identifier) > MAX_LABEL_NAME_LENGTH:
        return f"❌ Invalid input: Label identifier exceeds maximum length of {MAX_LABEL_NAME_LENGTH} characters."

    failure_message = f"❌ Failed to delete label '@{clean_identifier}' in Todoist. Check server logs for details."
    try:
        api = client.get_api_client()
        resolved = resolve_label(api, clean_identifier)

        if isinstance(resolved, LookupFailed):
            return failure_message
        if isinstance(resolved, Ambiguous):
            return ambiguous_message(resolved, "etiket", shown_query=f"@{clean_identifier}")
        if isinstance(resolved, NotFound):
            return f"⚠️ Silinecek etiket bulunamadı: '@{clean_identifier}'."
        label_id, label_name = resolved.id, resolved.name

        success = api.delete_label(label_id=label_id)
        display_name = f"'@{label_name}' (ID: {label_id})" if label_name else f"ID: {label_id}"

        if success:
            return f"🗑️ Etiket başarıyla silindi: {display_name}."
        else:
            return f"⚠️ Etiket silinemedi: {display_name}."
    except Exception as e:
        logger.error(
            "Failed to delete label in Todoist (identifier=%s, error_type=%s)",
            clean_identifier,
            type(e).__name__,
            exc_info=False,
        )
        return failure_message
