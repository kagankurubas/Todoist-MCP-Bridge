# CLAUDE.md

Bu dosya, Claude Code'a (claude.ai/code) bu repoda çalışırken rehberlik eder.

## Komutlar

```bash
# Mevcut venv'i etkinleştir (Windows)
.\venv\Scripts\activate

# Bağımlılıkları kur
pip install -r requirements.txt

# Tüm test paketini çalıştır
pytest
pytest -v

# Tek bir test dosyası / testi çalıştır
pytest tests/todoist/test_tasks.py
pytest tests/todoist/test_tasks.py::test_create_task_success -v

# FastAPI webhook sunucusunu çalıştır (app.py)
uvicorn app:app --port 8000
# Swagger UI: http://127.0.0.1:8000/docs

# MCP sunucusunu doğrudan çalıştır (normalde Claude Desktop tarafından STDIO üzerinden başlatılır)
python -m plugvan.todoist

# Bağımsız CLI ile görev oluşturma (main.py)
python main.py --file tasks_sample.json
python main.py --json '[{"content": "Task", "due_string": "today", "priority": 2}]'

# Google Tasks -> Todoist senkronizasyon servisi
python sync_worker.py                    # tek seferlik
python sync_worker.py --watch --interval 15   # sürekli izleme (polling)

# Webhook istemcisi (bir JSON dosyasını çalışan app.py örneğine gönderir)
python send_to_bridge.py --file tasks_sample.json

# Docker (varsayılan olarak sync_worker.py'yi tek seferlik çalıştırır)
docker build -t todoist-bridge .
docker run --env-file .env todoist-bridge
```

Bu repoda yapılandırılmış bir linter/formatter yok (ruff/black/mypy config yok) — böyle bir şey varmış gibi davranma.

Gerekli ortam değişkenleri (`.env`, bkz. `.env.example`): `TODOIST_API_TOKEN`, `WEBHOOK_SECRET_TOKEN`, opsiyonel `ALLOWED_ORIGINS` (CORS, varsayılan `*`). `config.py` içindeki Pydantic `Settings` üzerinden yüklenir. Sync worker ayrıca repo kökünde bir Google OAuth `credentials.json` (Desktop Client) dosyasına ihtiyaç duyar; `token.json` ilk kimlik doğrulamada otomatik oluşturulur. Sunucusuz/geçici (serverless/ephemeral) ortamlar için ikisi de `GOOGLE_CREDENTIALS_JSON` / `GOOGLE_TOKEN_JSON` ortam değişkenlerinden sağlanabilir.

## Mimari

Bu proje tek bir uygulama değil, **hepsi aynı doğrulama/görev-oluşturma çekirdeğinden geçen dört bağımsız giriş noktasından** oluşan bir Python araç setidir:

- `plugvan.todoist` (`plugvan/todoist/` paketi, `python -m plugvan.todoist`) — Claude Desktop'a sunulan araç yüzeyi; STDIO üzerinden çalışan FastMCP sunucusu. Kendi kendine yeterlidir: Todoist ile `todoist_client.py` üzerinden değil, doğrudan resmi `todoist-api-python` SDK'sı üzerinden konuşur ve kendi isim çözümleme/doğrulama mantığına sahiptir.
- `app.py` — FastAPI REST sunucusu (n8n/Make gibi otomasyonlar için webhook hedefi). Kimlik doğrulama, sabit-zamanlı (`secrets.compare_digest`) `X-Bridge-Token` header karşılaştırmasıyla yapılır.
- `main.py` — doğrudan çalıştırılan CLI aracı; ayrıca `build_project_map` / `resolve_project_id` fonksiyonlarını export eder ve bunlar `app.py` tarafından kendi proje-adı çözümlemesi için import edilip yeniden kullanılır.
- `sync_worker.py` — Google Tasks'ten görev çeken, her öğeyi `parse_google_task` ile dönüştüren, Todoist'e gönderen ve başarılı olan görevleri kaynak Google Task'ten silen OAuth 2.0 servisi.

### Paylaşılan çekirdek (`main.py`, `app.py`, `sync_worker.py` tarafından kullanılır)

- `models.py` — `TaskPayload` (tekil görev) ve `BatchTaskPayload` (`tasks: List[TaskPayload]`, maksimum 50) her şeyin doğrulandığı Pydantic şemalarıdır. `project_name` varsayılan olarak `"Odak & Gelişim"`dir; `priority` 1 (normal) ile 4 (acil) arasındadır — dikkat: Todoist'in kendi API'si ve `sync_worker.py`'nin etiket ayrıştırıcısı (`p1`=acil..`p4`=normal) bu skalayı tersine çevirir, bu nedenle öncelik eşlemesi `parse_google_task` içinde açıkça yapılır.
- `parser.py` — `parse_tasks_from_json`, ham LLM çıktısındaki markdown kod bloklarını (` ```json ... ``` `) temizler, ardından üç JSON biçimini kabul eder: düz bir liste, `{"tasks": [...]}` ya da tekil bir görev objesi. Hata durumunda `TaskParseError` fırlatır.
- `todoist_client.py` — Todoist REST API v1 üzerine ince bir `requests` sarmalayıcısı (`main.py`, `app.py`, `sync_worker.py` tarafından kullanılır; `plugvan.todoist` tarafından KULLANILMAZ, o SDK kullanır). `app.py`'nin FastAPI exception handler'ları aracılığıyla HTTP yanıtlarına eşlediği tipli exception'lar fırlatır (`TodoistAuthError` 401, `TodoistValidationError` 400, `TodoistServerError` 5xx, temel sınıf olarak `TodoistAPIError`). `create_task`, ilk pozisyonel argüman olarak hem keyword argümanları hem de bir `TaskPayload`/dict kabul eder.
- Proje-adı çözümlemesi, aynı case-insensitive/Unicode-normalize edilmiş mantıkla bilinçli olarak üç farklı yerde tekrarlanır: `main.py::resolve_project_id` (dict lookup), `todoist_client.py::resolve_project_name` (Todoist REST), ve `plugvan/todoist/resolvers.py::resolve_project` (SDK; ek olarak Inbox takma adı, tek adaylı kısmi eşleşme ve belirsizlik katmanlarıyla). Davranış farkı bilinçlidir: MCP tool'ları bilinmeyen isimde hata döndürür, CLI/webhook/sync worker ise Inbox'a düşer. Çözümleme mantığına dokunurken değişikliğin her üçüne de uygulanması gerekip gerekmediğini kontrol et.

### `plugvan.todoist` iç yapısı

Üst düzey `plugvan/` paketi boştur (henüz çok uygulamalı sunucu kodu yok); Todoist entegrasyonu `plugvan/todoist/` altındadır:
- `server.py` — `FastMCP("Todoist")` nesnesi; 22 tool burada `mcp.add_tool(...)` ile **sabit sırada** açıkça kaydedilir (sıra yayınlanan yüzeyin parçasıdır, değiştirme).
- `tools/` — domain başına bir modül (`tasks`, `projects`, `sections`, `labels`, `comments`); tool'lar dekoratörsüz düz fonksiyonlardır. Deadline/HTTP hata yardımcıları yalnızca `tasks.py` içindedir.
- `client.py` — `get_api_client()`; `TODOIST_API_TOKEN`'dan her çağrıda bir `TodoistAPI` oluşturur. Tool'lar bunu modül özniteliği üzerinden çağırır (`client.get_api_client()`), böylece testlerde **tek patch hedefi** `plugvan.todoist.client.get_api_client` olur.
- `limits.py` — `MAX_*_LENGTH` sabitleri. `resolvers.py` — `resolve_project` / `resolve_section` / `resolve_label`, dört sonuç tipi (`Found`, `NotFound`, `Ambiguous`, `LookupFailed`), `ambiguous_message`, `_normalize`.
- `__main__.py` — giriş noktası: `load_dotenv()` ve `logging.basicConfig(...)` yalnızca burada çalışır. Logger adı tüm modüllerde `"todoist_mcp"`dir.

Import yan etkileri: bizim modüllerimizin import yan etkisi yoktur. Ancak `server.py` import edildiğinde SDK'nın `FastMCP()` constructor'ı root logger'a bir log handler (`RichHandler`) ekler; bu bizim kodumuzdan değil SDK'dan gelir.

Her araç bağımsız olarak:
1. Girdileri `limits.py`'deki `MAX_*_LENGTH` sabitlerine göre doğrular.
2. İnsan tarafından okunabilir isimleri `resolve_project` / `resolve_section` / `resolve_label` ile ID'lere çözümler (`_normalize` ile Türkçe'ye duyarlı normalizasyon dahil). Her çözümleme dört sonuçtan birini döndürür ve tool her birini ayrı ele alır; hata durumlarında hiçbir şey yazılmaz:
   - `Found(id, name)`: tek eşleşme; mesajlarda kullanıcının girdisi değil `name` (Todoist'teki gerçek ad) gösterilir. `id=None` yalnızca listede Inbox yokken Inbox takma adı kullanıldığında olur.
   - `NotFound(query)`: `⚠️ … bulunamadı` mesajı, aday listesi yok.
   - `Ambiguous(query, candidates, has_more)`: `ambiguous_message` ile en fazla 5 `isim (ID)` aday ve ID kullanma önerisi.
   - `LookupFailed(error_type)`: tool'un genel `❌ … Check server logs` mesajı; log'a yalnızca `error_type` yazılır, exception metni veya HTTP yanıtı asla.

   Eşleşme kuralları tool'a göre değişir:
   - Proje, yıkıcı tool'larda (`delete_project`, `update_project`): yalnızca ID veya tam isim.
   - Proje, `update_section`'ın proje kapsamında: ID → Inbox takma adı → tam isim.
   - Proje, diğer tool'larda (`create_task`, `update_task`, `create_project` üst proje, `create_section`, `list_sections`): ID → Inbox takma adı → tam isim → yalnızca tek aday varsa kısmi eşleşme.
   - Bölüm, her yerde: yalnızca ID veya tam isim, kısmi eşleşme yok. Görev tool'larında yalnızca çözümlenen projenin içinde aranır; `update_task`'ta proje verilmemişse görevin mevcut projesinde.
   - Etiket: baştaki `@` atılır; yalnızca ID veya tam isim. Yalnızca harf farkı olan iki etiket belirsizdir.
   - `create_task`/`update_task` hedefi önce doğrular, sonra yazar.
3. Todoist SDK'sını `client.get_api_client()` ile oluşturulan `TodoistAPI` üzerinden çağırır.

Tool isimlerine uygulama prefix'i (`todoist_create_task` gibi) verme kararı ertelendi: ileride bağımsız `fastmcp`'nin `mount(server, namespace=...)` özelliğiyle, kod değiştirmeden yapılacak. Bu, SDK'daki FastMCP'den bağımsız `fastmcp`'ye geçişi gerektirir; bu yüzden `requirements.txt`'teki `fastmcp` bağımlılığını silme.

### `sync_worker.py` etiket sözdizimi

`parse_google_task`, serbest metin Google Task başlıklarından/notlarından regex ile yapılandırılmış alanları şu sırayla çıkarır: öncelik (`p[1-4]`), teslim tarihi (`@today`, `@tomorrow at 15:00`, ...), proje (`[Proje Adı]` veya `#Proje Adı`), ardından notlardan çekilen ve Google'ın `due` tarihiyle birleştirilip ISO `due_datetime` haline getirilen satır içi bir saat (`Saat: HH:MM` veya çıplak `HH:MM`). Etiket çıkarımından sonra kalan metin `content` olur.

### Testler

`tests/` modül yapısını yansıtır ve tüm ağ/API çağrılarını mock'lar — gerçek bir Todoist veya Google çağrısı yapılmaz.
- `tests/todoist/` — `plugvan.todoist` testleri, paketi birebir yansıtır: `test_tasks.py`, `test_projects.py`, `test_sections.py`, `test_labels.py`, `test_comments.py`, `test_resolvers.py`, `test_server_surface.py`. Kendi `__init__.py`'si vardır (`tests.todoist` olarak import edilir).
- `tests/todoist/helpers.py` — SDK client'ını topyekûn mock'lamak yerine SDK'nın obje özniteliklerini yansıtan hafif `MockProject`/`MockLabel`/`MockSection`/`MockComment`/`MockTask` sınıfları, `_make_http_status_error` ve `write_call_count` (mock'lanmış SDK'daki tüm yazma çağrılarını sayar; `get_`/`filter_`/`search_` dışındaki her public metot yazma sayılır). `test_` ile başlamadığı için pytest tarafından toplanmaz.
- Diğerleri kökte: `test_api.py`, `test_models.py`, `test_parser.py`, `test_todoist_client.py`, `test_project_resolution.py`.

**Surface snapshot kuralı:** `tests/fixtures/todoist_mcp_tool_surface.json`, MCP tool yüzeyinin (22 tool: isim, açıklama, `inputSchema`, `outputSchema`) taşımadan önce eski modülden bir kez kaydedilmiş halidir; `test_server_surface.py` canlı sunucuyu buna isme göre (sıradan bağımsız) karşılaştırır. Fixture bilinçli bir davranış değişikliği olmadıkça **asla yeniden üretilmez**; bir tool'un açıklamasını/parametresini değiştirmek testi kırar ve fixture'ı güncellemek o değişikliği bilerek kabul etmek demektir.

## Agent skills

### Issue tracker

Issue'lar GitHub Issues'ta (`kagankurubas/plugvan`) tutulur, `gh` CLI ile yönetilir. Bkz. `docs/agents/issue-tracker.md`.

### Triage labels

Varsayılan beş etiket kullanılır: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. Bkz. `docs/agents/triage-labels.md`.

### Domain docs

Single-context düzen: repo kökünde tek bir `CONTEXT.md` + `docs/adr/`. Bkz. `docs/agents/domain.md`.
