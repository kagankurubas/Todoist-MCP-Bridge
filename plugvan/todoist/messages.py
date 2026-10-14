"""User-facing tool messages: one catalog per output language, looked up by key.

Templates use str.format named placeholders. A key that is missing in the selected language
raises MissingMessageError; tools re-raise it before their generic `except Exception` handler,
so a missing translation is never turned into a generic failure message.
"""

from plugvan.todoist.language import current_language


class MissingMessageError(Exception):
    """A message key has no entry in the selected language's catalog."""


CATALOGS: dict[str, dict[str, str]] = {
    "en": {
        # Shared: name resolution
        "ambiguous.project": "⚠️ Multiple projects found for '{query}'; please use the project ID:",
        "ambiguous.section": "⚠️ Multiple sections found for '{query}'; please use the section ID:",
        "ambiguous.label": "⚠️ Multiple labels found for '{query}'; please use the label ID:",
        "inbox.display_name": "Inbox",
        "inbox.marker": " [Inbox]",
        "project.not_found": "⚠️ Project not found: '{name}'.",
        "section.not_found": "⚠️ Section not found: '{name}'.",
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
        "task.deadline_plan_restricted": "❌ The deadline feature is not available on the Todoist Free/Beginner plan — a Pro or Business plan is required (403 Forbidden).",
        "task.create_failed": "❌ Todoist task creation failed. Check server logs for details.",
        "task.due_not_specified": "Not specified",
        "task.created.section_line": "\n• Section: {name} (ID: {id})",
        "task.created.labels_line": "\n• Labels: {labels}",
        "task.created.deadline_line": "\n• Deadline: {date}",
        "task.created": (
            "✅ Task created successfully!\n"
            "• ID: {id}\n"
            "• Title: {content}\n"
            "• Project: {project}"
            "{section_line}\n"
            "• Priority: p{priority}\n"
            "• Due / Recurrence: {due}"
            "{deadline_line}"
            "{labels_line}\n"
            "• URL: {url}"
        ),
        "task.list.empty": "ℹ️ No open tasks match the filter '{query}'.",
        "task.priority.4": "🔴 p4 (Urgent)",
        "task.priority.3": "🟠 p3 (High)",
        "task.priority.2": "🔵 p2 (Medium)",
        "task.priority.1": "⚪ p1 (Normal)",
        "task.list.header": "📋 Open Tasks (Filter: '{query}', Total: {count}):",
        "task.list.no_due": "No due date",
        "task.list.priority_line": "   • Priority: {priority}",
        "task.list.due_line": "   • Due: {due}",
        "task.list.description_line": "   • Description: {description}",
        "task.list_failed": "❌ Failed to retrieve tasks from Todoist. Check server logs for details.",
        "task.detail.not_set": "Not set",
        "task.detail.none": "None",
        "task.detail.no_parent": "None (top-level task)",
        "task.detail": (
            "📄 Task Details (ID: {id})\n"
            "• Title: {content}\n"
            "• Description: {description}\n"
            "• Project ID: {project_id}\n"
            "• Section ID: {section}\n"
            "• Parent Task ID (parent_id): {parent}\n"
            "• Priority: p{priority}\n"
            "• Due / Recurrence: {due}\n"
            "• Labels: {labels}\n"
            "• URL: {url}"
        ),
        "task.get_failed": "❌ Failed to retrieve task from Todoist (ID: {id}). Check server logs for details.",
        "task.completed": "✅ Task completed successfully (ID: {id}).",
        "task.complete_unconfirmed": "⚠️ The task could not be completed, or it may already be completed (ID: {id}).",
        "task.complete_failed": "❌ Failed to complete task in Todoist (ID: {id}). Check server logs for details.",
        "task.reopened": "🔄 Task reopened successfully (ID: {id}).",
        "task.reopen_unconfirmed": "⚠️ The task could not be reopened, or it may already be open (ID: {id}).",
        "task.reopen_failed": "❌ Failed to reopen task in Todoist (ID: {id}). Check server logs for details.",
        "task.update.no_fields": "⚠️ No fields to update were specified. Please provide at least one parameter (content, description, project_name, due_string, priority, labels, section_name_or_id, parent_id, deadline_date).",
        "task.update_failed": "❌ Failed to update task in Todoist (ID: {id}). Check server logs for details.",
        "task.update.target_project_not_found": "⚠️ Target project not found: '{name}'.",
        "task.update.target_section_not_found": "⚠️ Target section not found: '{name}'.",
        "task.update.change.content": "Title: '{value}'",
        "task.update.change.description": "Description: '{value}'",
        "task.update.change.due": "Due: '{value}'",
        "task.update.change.priority": "Priority: p{value}",
        "task.update.change.labels": "Labels: {value}",
        "task.update.change.labels_cleared": "Cleared",
        "task.update.change.deadline": "Deadline: '{value}'",
        "task.update.change.project": "Target Project: '{name}' (ID: {id})",
        "task.update.change.section": "Target Section: '{name}' (ID: {id})",
        "task.update.change.parent": "Parent Task (parent_id): '{id}'",
        "task.update.change.parent_removed": "Parent Task: Removed (task moved to the top level)",
        "task.updated": "✅ Task updated successfully (ID: {id})!\nChanges made:\n{changes}",
        "task.deleted": "🗑️ Task permanently deleted (ID: {id}).",
        "task.delete_unconfirmed": "⚠️ The task could not be deleted (ID: {id}). It may already be deleted or not exist.",
        "task.delete_failed": "❌ Failed to delete task in Todoist (ID: {id}). Check server logs for details.",
        # Shared: target display in delete messages
        "display.named": "'{name}' (ID: {id})",
        "display.id_only": "ID: {id}",
        # Shared: input validation (projects)
        "invalid.project_id_empty": "❌ Invalid input: Project ID cannot be empty or whitespace.",
        "invalid.project_id_too_long": "❌ Invalid input: Project ID exceeds maximum length of {limit} characters.",
        "invalid.project_name_empty": "❌ Invalid input: Project name cannot be empty or whitespace.",
        "invalid.parent_project_identifier_too_long": "❌ Invalid input: Parent project identifier exceeds maximum length of {limit} characters.",
        "invalid.color_too_long": "❌ Invalid input: Color name exceeds maximum length of {limit} characters.",
        "invalid.project_identifier_empty": "❌ Invalid input: Project identifier cannot be empty or whitespace.",
        "invalid.project_identifier_too_long": "❌ Invalid input: Project identifier exceeds maximum length of {limit} characters.",
        "invalid.new_project_name_empty": "❌ Invalid input: New project name cannot be empty or whitespace.",
        "invalid.new_project_name_too_long": "❌ Invalid input: New project name exceeds maximum length of {limit} characters.",
        # Projects
        "project.list.empty": "ℹ️ No projects found in your Todoist account.",
        "project.list.header": "📁 Available Projects (Total: {count}):",
        "project.list.color_suffix": ", Color: {color}",
        "project.list.url_line": "{indent}• URL: {url}",
        "project.list_failed": "❌ Failed to list projects from Todoist. Check server logs for details.",
        "project.detail.none": "None",
        "project.detail.no_parent": "None (top-level project)",
        "project.detail.yes": "Yes",
        "project.detail.no": "No",
        "project.detail.not_set": "Not set",
        "project.detail": (
            "📁 Project Details (ID: {id})\n"
            "• Name: {name}\n"
            "• Color: {color}\n"
            "• Parent Project ID (parent_id): {parent}\n"
            "• Favorite: {favorite}\n"
            "• View Style: {view_style}\n"
            "• URL: {url}"
        ),
        "project.get_failed": "❌ Failed to retrieve project from Todoist (ID: {id}). Check server logs for details.",
        "project.create_failed": "❌ Failed to create project '{name}' in Todoist. Check server logs for details.",
        "project.parent_not_found": "⚠️ Parent project not found: '{name}'.",
        "project.created.parent_line": "\n• Parent Project: '{name}' (ID: {id})",
        "project.created.color_line": "\n• Color: {color}",
        "project.created.url_line": "\n• URL: {url}",
        "project.created": "✅ Project created successfully!\n• ID: {id}\n• Name: {name}{parent_line}{color_line}{url_line}",
        "project.update.no_fields": "⚠️ No fields to update were specified. Please provide the name or color parameter.",
        "project.update_failed": "❌ Failed to update project '{name}' in Todoist. Check server logs for details.",
        "project.update.not_found": "⚠️ Project to update not found: '{name}'.",
        "project.update.change.name": "Name: '{value}'",
        "project.update.change.color": "Color: '{value}'",
        "project.updated": "✅ Project updated successfully (ID: {id})!\nChanges made:\n{changes}",
        "project.delete_failed": "❌ Failed to delete project '{name}' in Todoist. Check server logs for details.",
        "project.delete.not_found": "⚠️ Project to delete not found: '{name}'.",
        "project.deleted": "🗑️ Project deleted successfully: {target}.",
        "project.delete_unconfirmed": "⚠️ The project could not be deleted: {target}.",
        # Sections
        "invalid.section_name_empty": "❌ Invalid input: Section name cannot be empty or whitespace.",
        "invalid.section_name_too_long": "❌ Invalid input: Section name exceeds maximum length of {limit} characters.",
        "invalid.section_identifier_empty": "❌ Invalid input: Section identifier cannot be empty or whitespace.",
        "invalid.new_section_name_empty": "❌ Invalid input: New section name cannot be empty or whitespace.",
        "invalid.new_section_name_too_long": "❌ Invalid input: New section name exceeds maximum length of {limit} characters.",
        "section.create_failed": "❌ Failed to create section '{name}' in Todoist. Check server logs for details.",
        "section.create.project_not_found": "⚠️ Target project for the new section not found: '{name}'.",
        "section.created": "✅ Section created successfully!\n• ID: {id}\n• Name: {name}\n• Project: '{project}' (ID: {project_id})",
        "section.list_failed": "❌ Failed to list sections from Todoist. Check server logs for details.",
        "section.list.empty_in_project": "ℹ️ No sections found in the Todoist project '{project}'.",
        "section.list.empty_all": "ℹ️ No sections found in your Todoist account.",
        "section.list.header_project": "📑 Available Sections (Project '{project}', Total: {count}):",
        "section.list.header_all": "📑 Available Sections (All Projects, Total: {count}):",
        "section.list.line": "{index}. [{id}] {name} (Project ID: {project_id})",
        "section.update_failed": "❌ Failed to update section '{name}' in Todoist. Check server logs for details.",
        "section.update.not_found": "⚠️ Section to update not found: '{name}'.",
        "section.updated": "✅ Section updated successfully (ID: {id})!\n• Old name: '{old_name}'\n• New name: '{new_name}'",
        "section.delete_failed": "❌ Failed to delete section '{name}' in Todoist. Check server logs for details.",
        "section.delete.not_found": "⚠️ Section to delete not found: '{name}'.",
        "section.deleted": "🗑️ Section deleted successfully: {target}.",
        "section.delete_unconfirmed": "⚠️ The section could not be deleted: {target}.",
        # Labels
        "label.list.empty": "ℹ️ No labels found in your Todoist account.",
        "label.list.header": "🏷️ Available Labels (Total: {count}):",
        "label.list.color_suffix": ", Color: {color}",
        "label.list_failed": "❌ Failed to list labels from Todoist. Check server logs for details.",
        "invalid.label_name_empty": "❌ Invalid input: Label name cannot be empty or whitespace.",
        "invalid.label_name_too_long": "❌ Invalid input: Label name exceeds maximum length of {limit} characters.",
        "label.created.color_line": "\n• Color: {color}",
        "label.created": "✅ Label created successfully!\n• ID: {id}\n• Name: @{name}{color_line}",
        "label.create_failed": "❌ Failed to create label '@{name}' in Todoist. Check server logs for details.",
        "invalid.label_identifier_empty": "❌ Invalid input: Label identifier cannot be empty or whitespace.",
        "invalid.label_identifier_too_long": "❌ Invalid input: Label identifier exceeds maximum length of {limit} characters.",
        "invalid.new_label_name_too_long": "❌ Invalid input: New label name exceeds maximum length of {limit} characters.",
        "label.update.no_fields": "⚠️ No fields to update were specified. Please provide the new_name or color parameter.",
        "label.update_failed": "❌ Failed to update label '@{name}' in Todoist. Check server logs for details.",
        "label.update.not_found": "⚠️ Label to update not found: '@{name}'.",
        "label.update.change.name": "Name: '@{value}'",
        "label.update.change.color": "Color: '{value}'",
        "label.updated": "✅ Label updated successfully (ID: {id})!\nChanges made:\n{changes}",
        "label.delete_failed": "❌ Failed to delete label '@{name}' in Todoist. Check server logs for details.",
        "label.delete.not_found": "⚠️ Label to delete not found: '@{name}'.",
        "label.display.named": "'@{name}' (ID: {id})",
        "label.deleted": "🗑️ Label deleted successfully: {target}.",
        "label.delete_unconfirmed": "⚠️ The label could not be deleted: {target}.",
        # Comments
        "invalid.comment_content_empty": "❌ Invalid input: Comment content cannot be empty or whitespace.",
        "invalid.comment_content_too_long": "❌ Invalid input: Comment content exceeds maximum length of {limit} characters.",
        "comment.added.posted_line": "\n• Date: {posted_at}",
        "comment.added": "💬 Comment added successfully!\n• Comment ID: {id}\n• Task ID: {task_id}\n• Content: {content}{posted_line}",
        "comment.add_failed": "❌ Failed to add comment to task (ID: {task_id}) in Todoist. Check server logs for details.",
        "comment.list.empty": "ℹ️ No comments or notes found for the task (ID: {task_id}).",
        "comment.list.header": "💬 Task Comments (Task ID: {task_id}, Total: {count}):",
        "comment.list_failed": "❌ Failed to retrieve comments for task (ID: {task_id}) from Todoist. Check server logs for details.",
    },
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
        # Shared: target display in delete messages
        "display.named": "'{name}' (ID: {id})",
        "display.id_only": "ID: {id}",
        # Shared: input validation (projects)
        "invalid.project_id_empty": "❌ Invalid input: Project ID cannot be empty or whitespace.",
        "invalid.project_id_too_long": "❌ Invalid input: Project ID exceeds maximum length of {limit} characters.",
        "invalid.project_name_empty": "❌ Invalid input: Project name cannot be empty or whitespace.",
        "invalid.parent_project_identifier_too_long": "❌ Invalid input: Parent project identifier exceeds maximum length of {limit} characters.",
        "invalid.color_too_long": "❌ Invalid input: Color name exceeds maximum length of {limit} characters.",
        "invalid.project_identifier_empty": "❌ Invalid input: Project identifier cannot be empty or whitespace.",
        "invalid.project_identifier_too_long": "❌ Invalid input: Project identifier exceeds maximum length of {limit} characters.",
        "invalid.new_project_name_empty": "❌ Invalid input: New project name cannot be empty or whitespace.",
        "invalid.new_project_name_too_long": "❌ Invalid input: New project name exceeds maximum length of {limit} characters.",
        # Projects
        "project.list.empty": "ℹ️ Todoist hesabınızda herhangi bir proje bulunamadı.",
        "project.list.header": "📁 Mevcut Projeler (Toplam: {count}):",
        "project.list.color_suffix": ", Renk: {color}",
        "project.list.url_line": "{indent}• URL: {url}",
        "project.list_failed": "❌ Failed to list projects from Todoist. Check server logs for details.",
        "project.detail.none": "Yok",
        "project.detail.no_parent": "Yok (üst seviye proje)",
        "project.detail.yes": "Evet",
        "project.detail.no": "Hayır",
        "project.detail.not_set": "Belirlenmedi",
        "project.detail": (
            "📁 Proje Detayları (ID: {id})\n"
            "• İsim: {name}\n"
            "• Renk: {color}\n"
            "• Üst Proje ID (parent_id): {parent}\n"
            "• Favori mi: {favorite}\n"
            "• Görünüm Stili: {view_style}\n"
            "• URL: {url}"
        ),
        "project.get_failed": "❌ Failed to retrieve project from Todoist (ID: {id}). Check server logs for details.",
        "project.create_failed": "❌ Failed to create project '{name}' in Todoist. Check server logs for details.",
        "project.parent_not_found": "⚠️ Belirtilen üst proje bulunamadı: '{name}'.",
        "project.created.parent_line": "\n• Üst Proje: '{name}' (ID: {id})",
        "project.created.color_line": "\n• Renk: {color}",
        "project.created.url_line": "\n• URL: {url}",
        "project.created": "✅ Proje başarıyla oluşturuldu!\n• ID: {id}\n• İsim: {name}{parent_line}{color_line}{url_line}",
        "project.update.no_fields": "⚠️ Güncellenecek hiçbir alan belirtilmedi. Lütfen name veya color parametresi girin.",
        "project.update_failed": "❌ Failed to update project '{name}' in Todoist. Check server logs for details.",
        "project.update.not_found": "⚠️ Güncellenecek proje bulunamadı: '{name}'.",
        "project.update.change.name": "İsim: '{value}'",
        "project.update.change.color": "Renk: '{value}'",
        "project.updated": "✅ Proje başarıyla güncellendi (ID: {id})!\nYapılan değişiklikler:\n{changes}",
        "project.delete_failed": "❌ Failed to delete project '{name}' in Todoist. Check server logs for details.",
        "project.delete.not_found": "⚠️ Silinecek proje bulunamadı: '{name}'.",
        "project.deleted": "🗑️ Proje başarıyla silindi: {target}.",
        "project.delete_unconfirmed": "⚠️ Proje silinemedi: {target}.",
        # Sections
        "invalid.section_name_empty": "❌ Invalid input: Section name cannot be empty or whitespace.",
        "invalid.section_name_too_long": "❌ Invalid input: Section name exceeds maximum length of {limit} characters.",
        "invalid.section_identifier_empty": "❌ Invalid input: Section identifier cannot be empty or whitespace.",
        "invalid.new_section_name_empty": "❌ Invalid input: New section name cannot be empty or whitespace.",
        "invalid.new_section_name_too_long": "❌ Invalid input: New section name exceeds maximum length of {limit} characters.",
        "section.create_failed": "❌ Failed to create section '{name}' in Todoist. Check server logs for details.",
        "section.create.project_not_found": "⚠️ Bölüm oluşturulacak hedef proje bulunamadı: '{name}'.",
        "section.created": "✅ Bölüm başarıyla oluşturuldu!\n• ID: {id}\n• İsim: {name}\n• Proje: '{project}' (ID: {project_id})",
        "section.list_failed": "❌ Failed to list sections from Todoist. Check server logs for details.",
        "section.list.empty_in_project": "ℹ️ Todoist '{project}' projesinde herhangi bir bölüm bulunamadı.",
        "section.list.empty_all": "ℹ️ Todoist hesabınızda herhangi bir bölüm bulunamadı.",
        "section.list.header_project": "📑 Mevcut Bölümler ('{project}' Projesi, Toplam: {count}):",
        "section.list.header_all": "📑 Mevcut Bölümler (Tüm Projeler, Toplam: {count}):",
        "section.list.line": "{index}. [{id}] {name} (Proje ID: {project_id})",
        "section.update_failed": "❌ Failed to update section '{name}' in Todoist. Check server logs for details.",
        "section.update.not_found": "⚠️ Güncellenecek bölüm bulunamadı: '{name}'.",
        "section.updated": "✅ Bölüm başarıyla güncellendi (ID: {id})!\n• Eski isim: '{old_name}'\n• Yeni isim: '{new_name}'",
        "section.delete_failed": "❌ Failed to delete section '{name}' in Todoist. Check server logs for details.",
        "section.delete.not_found": "⚠️ Silinecek bölüm bulunamadı: '{name}'.",
        "section.deleted": "🗑️ Bölüm başarıyla silindi: {target}.",
        "section.delete_unconfirmed": "⚠️ Bölüm silinemedi: {target}.",
        # Labels
        "label.list.empty": "ℹ️ Todoist hesabınızda herhangi bir etiket bulunamadı.",
        "label.list.header": "🏷️ Mevcut Etiketler (Toplam: {count}):",
        "label.list.color_suffix": ", Renk: {color}",
        "label.list_failed": "❌ Failed to list labels from Todoist. Check server logs for details.",
        "invalid.label_name_empty": "❌ Invalid input: Label name cannot be empty or whitespace.",
        "invalid.label_name_too_long": "❌ Invalid input: Label name exceeds maximum length of {limit} characters.",
        "label.created.color_line": "\n• Renk: {color}",
        "label.created": "✅ Etiket başarıyla oluşturuldu!\n• ID: {id}\n• İsim: @{name}{color_line}",
        "label.create_failed": "❌ Failed to create label '@{name}' in Todoist. Check server logs for details.",
        "invalid.label_identifier_empty": "❌ Invalid input: Label identifier cannot be empty or whitespace.",
        "invalid.label_identifier_too_long": "❌ Invalid input: Label identifier exceeds maximum length of {limit} characters.",
        "invalid.new_label_name_too_long": "❌ Invalid input: New label name exceeds maximum length of {limit} characters.",
        "label.update.no_fields": "⚠️ Güncellenecek hiçbir alan belirtilmedi. Lütfen new_name veya color parametresi girin.",
        "label.update_failed": "❌ Failed to update label '@{name}' in Todoist. Check server logs for details.",
        "label.update.not_found": "⚠️ Güncellenecek etiket bulunamadı: '@{name}'.",
        "label.update.change.name": "İsim: '@{value}'",
        "label.update.change.color": "Renk: '{value}'",
        "label.updated": "✅ Etiket başarıyla güncellendi (ID: {id})!\nYapılan değişiklikler:\n{changes}",
        "label.delete_failed": "❌ Failed to delete label '@{name}' in Todoist. Check server logs for details.",
        "label.delete.not_found": "⚠️ Silinecek etiket bulunamadı: '@{name}'.",
        "label.display.named": "'@{name}' (ID: {id})",
        "label.deleted": "🗑️ Etiket başarıyla silindi: {target}.",
        "label.delete_unconfirmed": "⚠️ Etiket silinemedi: {target}.",
        # Comments
        "invalid.comment_content_empty": "❌ Invalid input: Comment content cannot be empty or whitespace.",
        "invalid.comment_content_too_long": "❌ Invalid input: Comment content exceeds maximum length of {limit} characters.",
        "comment.added.posted_line": "\n• Tarih: {posted_at}",
        "comment.added": "💬 Yorum başarıyla eklendi!\n• Yorum ID: {id}\n• Görev ID: {task_id}\n• İçerik: {content}{posted_line}",
        "comment.add_failed": "❌ Failed to add comment to task (ID: {task_id}) in Todoist. Check server logs for details.",
        "comment.list.empty": "ℹ️ Göreve ait (ID: {task_id}) herhangi bir yorum veya not bulunamadı.",
        "comment.list.header": "💬 Görev Yorumları (Görev ID: {task_id}, Toplam: {count}):",
        "comment.list_failed": "❌ Failed to retrieve comments for task (ID: {task_id}) from Todoist. Check server logs for details.",
    },
}


def message(key: str, **params) -> str:
    """Returns the message `key` in the selected output language, formatted with `params`."""
    language = current_language()
    template = CATALOGS.get(language, {}).get(key)
    if template is None:
        raise MissingMessageError(f"No '{key}' message for language '{language}'")
    return template.format(**params)
