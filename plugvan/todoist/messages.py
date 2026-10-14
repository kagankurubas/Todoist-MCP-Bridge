"""User-facing tool messages: one catalog per output language, looked up by key.

Templates use str.format named placeholders. A key that is missing in the selected language
raises MissingMessageError; tools re-raise it before their generic `except Exception` handler,
so a missing translation is never turned into a generic failure message.
"""

from plugvan.todoist.language import current_language


class MissingMessageError(Exception):
    """A message key has no entry in the selected language's catalog."""


CATALOGS: dict[str, dict[str, str]] = {
    "en": {},
    "tr": {
        # Shared: name resolution
        "ambiguous.project": "⚠️ '{query}' için birden fazla proje bulundu; lütfen proje ID'sini kullanın:",
        "ambiguous.section": "⚠️ '{query}' için birden fazla bölüm bulundu; lütfen bölüm ID'sini kullanın:",
        "ambiguous.label": "⚠️ '{query}' için birden fazla etiket bulundu; lütfen etiket ID'sini kullanın:",
        "inbox.display_name": "Gelen Kutusu",
        "inbox.marker": " [Gelen Kutusu]",
        "project.not_found": "⚠️ Belirtilen proje bulunamadı: '{name}'.",
        "section.not_found": "⚠️ Belirtilen bölüm bulunamadı: '{name}'.",
        # Shared: input validation
        "invalid.task_id_empty": "❌ Invalid input: Task ID cannot be empty or whitespace.",
        "invalid.task_id_too_long": "❌ Invalid input: Task ID exceeds maximum length of {limit} characters.",
        "invalid.task_content_empty": "❌ Invalid input: Task content cannot be empty or whitespace.",
        "invalid.task_content_too_long": "❌ Invalid input: Task content exceeds maximum length of {limit} characters.",
        "invalid.task_description_too_long": "❌ Invalid input: Task description exceeds maximum length of {limit} characters.",
        "invalid.project_name_too_long": "❌ Invalid input: Project name exceeds maximum length of {limit} characters.",
        "invalid.due_string_too_long": "❌ Invalid input: Due date string exceeds maximum length of {limit} characters.",
        "invalid.priority": "❌ Invalid input: Priority must be an integer between 1 (Normal) and 4 (Urgent).",
        "invalid.labels_not_list": "❌ Invalid input: Labels must be a list of strings.",
        "invalid.section_identifier_too_long": "❌ Invalid input: Section identifier exceeds maximum length of {limit} characters.",
        "invalid.parent_task_id_too_long": "❌ Invalid input: Parent task ID exceeds maximum length of {limit} characters.",
        "invalid.deadline_date_format": "❌ Invalid input: deadline_date must be in YYYY-MM-DD format (received: '{value}').",
        "invalid.filter_query_empty": "❌ Invalid input: Filter query cannot be empty or whitespace.",
        "invalid.filter_query_too_long": "❌ Invalid input: Filter query exceeds maximum length of {limit} characters.",
        # Tasks
        "task.deadline_plan_restricted": "❌ Deadline özelliği Todoist Free/Beginner planında desteklenmiyor — Pro veya Business plan gerekiyor (403 Forbidden).",
        "task.create_failed": "❌ Todoist task creation failed. Check server logs for details.",
        "task.due_not_specified": "Belirtilmedi",
        "task.created.section_line": "\n• Bölüm: {name} (ID: {id})",
        "task.created.labels_line": "\n• Etiketler: {labels}",
        "task.created.deadline_line": "\n• Son Teslim Tarihi (Deadline): {date}",
        "task.created": (
            "✅ Görev başarıyla oluşturuldu!\n"
            "• ID: {id}\n"
            "• Başlık: {content}\n"
            "• Proje: {project}"
            "{section_line}\n"
            "• Öncelik: p{priority}\n"
            "• Tarih / Tekrar: {due}"
            "{deadline_line}"
            "{labels_line}\n"
            "• URL: {url}"
        ),
        "task.list.empty": "ℹ️ '{query}' filtresine uygun açık görev bulunamadı.",
        "task.priority.4": "🔴 p4 (Çok Acil)",
        "task.priority.3": "🟠 p3 (Yüksek)",
        "task.priority.2": "🔵 p2 (Orta)",
        "task.priority.1": "⚪ p1 (Normal)",
        "task.list.header": "📋 Açık Görevler (Filtre: '{query}', Toplam: {count}):",
        "task.list.no_due": "Tarih yok",
        "task.list.priority_line": "   • Öncelik: {priority}",
        "task.list.due_line": "   • Tarih: {due}",
        "task.list.description_line": "   • Açıklama: {description}",
        "task.list_failed": "❌ Failed to retrieve tasks from Todoist. Check server logs for details.",
        "task.detail.not_set": "Belirlenmedi",
        "task.detail.none": "Yok",
        "task.detail.no_parent": "Yok (üst seviye görev)",
        "task.detail": (
            "📄 Görev Detayları (ID: {id})\n"
            "• Başlık: {content}\n"
            "• Açıklama: {description}\n"
            "• Proje ID: {project_id}\n"
            "• Bölüm ID: {section}\n"
            "• Üst Görev ID (parent_id): {parent}\n"
            "• Öncelik: p{priority}\n"
            "• Tarih / Tekrar: {due}\n"
            "• Etiketler: {labels}\n"
            "• URL: {url}"
        ),
        "task.get_failed": "❌ Failed to retrieve task from Todoist (ID: {id}). Check server logs for details.",
        "task.completed": "✅ Görev başarıyla tamamlandı (ID: {id}).",
        "task.complete_unconfirmed": "⚠️ Görev tamamlanamadı veya zaten tamamlanmış olabilir (ID: {id}).",
        "task.complete_failed": "❌ Failed to complete task in Todoist (ID: {id}). Check server logs for details.",
        "task.reopened": "🔄 Görev başarıyla yeniden açıldı (ID: {id}).",
        "task.reopen_unconfirmed": "⚠️ Görev yeniden açılamadı veya zaten açık olabilir (ID: {id}).",
        "task.reopen_failed": "❌ Failed to reopen task in Todoist (ID: {id}). Check server logs for details.",
        "task.update.no_fields": "⚠️ Güncellenecek hiçbir alan belirtilmedi. Lütfen en az bir parametre (content, description, project_name, due_string, priority, labels, section_name_or_id, parent_id, deadline_date) girin.",
        "task.update_failed": "❌ Failed to update task in Todoist (ID: {id}). Check server logs for details.",
        "task.update.target_project_not_found": "⚠️ Hedef proje bulunamadı: '{name}'.",
        "task.update.target_section_not_found": "⚠️ Hedef bölüm bulunamadı: '{name}'.",
        "task.update.change.content": "Başlık: '{value}'",
        "task.update.change.description": "Açıklama: '{value}'",
        "task.update.change.due": "Tarih: '{value}'",
        "task.update.change.priority": "Öncelik: p{value}",
        "task.update.change.labels": "Etiketler: {value}",
        "task.update.change.labels_cleared": "Temizlendi",
        "task.update.change.deadline": "Son Teslim Tarihi (Deadline): '{value}'",
        "task.update.change.project": "Hedef Proje: '{name}' (ID: {id})",
        "task.update.change.section": "Hedef Bölüm: '{name}' (ID: {id})",
        "task.update.change.parent": "Üst Görev (parent_id): '{id}'",
        "task.update.change.parent_removed": "Üst Görev: Kaldırıldı (görev üst seviyeye taşındı)",
        "task.updated": "✅ Görev başarıyla güncellendi (ID: {id})!\nYapılan değişiklikler:\n{changes}",
        "task.deleted": "🗑️ Görev kalıcı olarak silindi (ID: {id}).",
        "task.delete_unconfirmed": "⚠️ Görev silinemedi (ID: {id}). Görev zaten silinmiş veya bulunamıyor olabilir.",
        "task.delete_failed": "❌ Failed to delete task in Todoist (ID: {id}). Check server logs for details.",
    },
}


def message(key: str, **params) -> str:
    """Returns the message `key` in the selected output language, formatted with `params`."""
    language = current_language()
    template = CATALOGS.get(language, {}).get(key)
    if template is None:
        raise MissingMessageError(f"No '{key}' message for language '{language}'")
    return template.format(**params)
