# CODEX IMPLEMENTATION MASTER PROMPT
## MAX Hackathon — «Навигатор льгот и субсидий»
### Версия: bot-first production-like MVP → mini-app only after bot acceptance
### Revision: skill-orchestrated / security-hardened / token-efficient

---

# 0. РОЛЬ CODEX И КОНТРАКТ ВЫПОЛНЕНИЯ

Ты — senior backend/platform engineer и одновременно implementation agent. Твоя задача — не предложить архитектуру и не выдать scaffold, а **создать полностью запускаемый репозиторий**, установить и зафиксировать зависимости, подготовить Docker-окружение, миграции, seed-данные, интеграции, state machine, тесты, документацию и команды запуска.

Работай автономно. Не задавай уточняющих вопросов, если решение можно принять из этой спецификации. Если есть техническая неоднозначность, выбирай наиболее простое, устойчивое и расширяемое решение, фиксируй его в README в разделе `Architecture decisions`.

Главный принцип: **сначала идеально работающий MAX-бот, затем mini-app**. Нельзя начинать mini-app, пока acceptance criteria бота не выполнены.

После каждого этапа:
1. форматируй код;
2. запускай lint;
3. запускай type-check, если он не блокирует разработку из-за сторонних stubs;
4. запускай unit/integration tests;
5. исправляй ошибки;
6. только затем переходи дальше.

Запрещено оставлять критический функционал в виде `TODO`, псевдокода или `pass`.
\n\n---\n\n# 0A. SKILL ORCHESTRATION, SECURITY И ЭКОНОМИЯ ТОКЕНОВ\n\nЭта спецификация уже содержит утверждённую архитектуру, UX, data model, phases и acceptance criteria. Поэтому skills должны **ускорять выполнение и повышать качество**, а не заново изобретать проект.\n\n## 0A.1. Общая политика\n\nПеред началом реализации:\n\n1. Используй `$doctor` **один раз**, чтобы проверить, что OMX/Codex runtime и доступные skills работают корректно.\n2. Используй `$skill` для получения фактического списка доступных skills в текущем окружении.\n3. Не запускай несколько перекрывающихся orchestration-skills для одной и той же работы.\n4. Не запускай повторное интервью и повторное полное планирование: требования уже определены этим документом.\n5. Выбирай минимально достаточный skill и минимально достаточную глубину reasoning.\n6. После каждого крупного этапа сохраняй устойчивые решения и найденные особенности API в project knowledge/wiki, чтобы не исследовать их повторно.\n7. Никогда не передавай subagents секреты без необходимости. Не копируй `.env`, MAX token, OpenRouter key, webhook secret или реальные контакты в prompts/notes/wiki.\n\nОсновной workflow:\n\n```text\n$doctor\n   ↓\ntargeted $best-practice-research (только там, где внешний API/безопасность реально требуют свежей проверки)\n   ↓\n$ultragoal\n   ├── обычная последовательная реализация\n   └── $team только для независимых параллельных lanes\n   ↓\ntargeted $code-review после крупных milestones\n   ↓\n$ai-slop-cleaner один раз после feature-complete bot MVP\n   ↓\n$code-review с security/concurrency/architecture focus\n   ↓\n$ultraqa\n   ↓\n$final-check\n```\n\n## 0A.2. Skills, которые ОБЯЗАТЕЛЬНО использовать\n\n### `$ultragoal` — основной execution orchestrator\n\nИспользуй `$ultragoal` как главный durable execution workflow для PHASE 0 → PHASE 9.\n\nПричина:\n- проект уже имеет подробный spec;\n- не нужно ещё раз проходить interview → planning;\n- нужен устойчивый goal ledger, который не позволит потерять acceptance criteria между длинными сессиями.\n\nПравила:\n- один активный `$ultragoal` для проекта;\n- каждая PHASE — отдельная цель/checkpoint;\n- завершать goal только при наличии проверяемого evidence: tests/commands/health/smoke;\n- не объявлять phase завершённой только потому, что файлы созданы.\n\n### `$best-practice-research` — только bounded research по официальным источникам\n\nЗапускай только перед решениями, где свежая документация влияет на correctness:\n\n1. MAX Bot API contract, auth, polling, callbacks;\n2. MAX webhook subscriptions и secret validation;\n3. MAX bot commands / keyboard limitations;\n4. FNS/RMSP open data и доступный lookup-механизм;\n5. OpenRouter OpenAI-compatible API;\n6. Caddy/Docker production hardening, если требуется подтверждение актуальной практики.\n\nПриоритет источников:\n1. official docs;\n2. upstream repository/release notes;\n3. standards;\n4. только потом secondary sources.\n\nResearch output должен быть коротким:\n- verified fact;\n- source;\n- impact on our implementation;\n- decision.\n\nНе выполнять повторный research, если вывод уже сохранён в wiki/project docs и API/version не изменились.\n\n### `$code-review` — quality + security gate\n\nЗапускай после:\n- PHASE 2 — persistence/FSM;\n- PHASE 4 — matching/FNS;\n- PHASE 5 — checklist;\n- PHASE 7 — webhook/production;\n- feature-complete bot MVP;\n- после `$ai-slop-cleaner`.\n\nНа review проверять не только style, но и:\n\n**Architecture**\n- границы domain/application/infrastructure;\n- нет ли SQL/HTTP в handlers;\n- нет ли God objects;\n- нет ли runtime circular dependencies.\n\n**Security**\n- secrets exposure;\n- webhook authentication;\n- callback ownership/authorization;\n- injection risks;\n- SSRF/open redirect через импортируемые URL;\n- sensitive logging;\n- PII leakage в OpenRouter;\n- unsafe debug endpoints;\n- dependency/config risks;\n- production DB/Redis exposure.\n\n**Concurrency**\n- duplicate MAX delivery;\n- double taps;\n- race conditions checklist toggle;\n- usage counter atomicity;\n- reminder duplication;\n- advisory lock correctness.\n\n**Reliability**\n- network timeouts;\n- bounded retry;\n- proper transaction scope;\n- graceful degradation;\n- restart persistence.\n\nВсе high/critical findings исправить до следующего phase.\n\n### `$ultraqa` — adversarial QA\n\nПосле feature-complete bot MVP выполнить полный `$ultraqa`.\n\nQA должен специально атаковать:\n\n- duplicate `message_created`;\n- duplicate callbacks;\n- double-click по mutation button;\n- container restart в каждом onboarding state;\n- malformed/unknown callback payload;\n- callback с чужим entity id;\n- invalid UUID;\n- FNS timeout;\n- FNS 429/5xx;\n- malformed FNS response;\n- FNS schema drift;\n- Redis restart/unavailable;\n- PostgreSQL reconnect;\n- OpenRouter disabled;\n- OpenRouter timeout/500/malformed JSON;\n- expired measure;\n- inactive measure;\n- zero recommendations;\n- `NEEDS_MORE_INFO`;\n- repeated `/start`;\n- `/reset` в середине onboarding;\n- duplicate checklist add;\n- checklist document concurrent toggle;\n- investor decline followed by restart;\n- webhook request with wrong/missing secret;\n- rate-limit boundary/bypass attempts;\n- logging redaction;\n- production compose port exposure;\n- migration from empty DB;\n- seed repeated twice;\n- importer repeated twice.\n\nЦикл:\n`test → find defect → fix → rerun targeted tests → rerun QA`.\n\nНе завершать QA при известных high-severity defects.\n\n### `$final-check` — последний release gate\n\nИспользовать только после зелёного `$ultraqa`.\n\nПроверить фактическим выполнением команд:\n\n```text\ndocker compose build\ndocker compose up -d\nmigrations\nseed-demo\nlint\ntypecheck where practical\nunit tests\nintegration tests\nscenario tests\nhealth/live\nhealth/ready\nMAX smoke\nrestart persistence\nsecret scan\nproduction compose config\n```\n\nФинальный отчёт обязан отделять:\n- verified;\n- not verified because external access/credentials unavailable;\n- known limitations.\n\nНе писать «готово», если обязательный пункт не был реально проверен.\n\n## 0A.3. Skills, которые использовать ТОЧЕЧНО\n\n### `$team`\n\nИспользовать только когда есть **реально независимые lanes**.\n\nМаксимум 3 параллельных workers по умолчанию. Больше — только если доказано, что это ускоряет работу без дублирования контекста.\n\nХорошие места:\n\n**PHASE 0**\n- lane A: Docker/Compose;\n- lane B: SQLAlchemy/Alembic;\n- lane C: config/health/logging.\n\n**PHASE 3**\n- lane A: domain matching;\n- lane B: seed/importer;\n- lane C: tests.\n\n**PHASE 5**\n- lane A: checklist application/repository;\n- lane B: MAX checklist UX;\n- lane C: integration/scenario tests.\n\n**PHASE 7**\n- lane A: webhook/idempotency;\n- lane B: Caddy/prod compose;\n- lane C: deployment/security tests/docs.\n\nЗапрещено:\n- двум workers одновременно владеть одним файлом;\n- нескольким workers независимо проектировать одну и ту же abstraction;\n- использовать `$team` для последовательной цепочки;\n- создавать subagent ради одного маленького файла.\n\nКаждый worker возвращает кратко:\n- files changed;\n- tests/evidence;\n- unresolved issue.\n\nНе возвращать длинный chain-of-thought или повтор всего spec.\n\n### `$analyze`\n\nИспользовать для конкретной read-only диагностики:\n- перед серьёзным refactor;\n- при непонятном bug;\n- при поиске architectural drift;\n- при анализе performance/query issue.\n\nНе запускать полный `$analyze` после каждого коммита.\n\n### `$code-research`\n\nЕсли skill доступен — применять только для конкретной задачи поиска уже существующего решения:\n- найти текущий repository pattern;\n- найти upstream implementation;\n- выяснить правильную библиотечную API surface.\n\nНе использовать как отдельную обязательную фазу.\n\n### `$feature-research`\n\nЕсли skill доступен — использовать перед неоднозначной feature, которой нет в этом spec.\nДля уже описанных функций не проводить feature research повторно.\n\n### `$design`\n\nИспользовать для фиксации UX-решений в `DESIGN.md`.\n\nНа этапе bot MVP туда должны попасть:\n- тексты основных состояний;\n- layouts кнопок;\n- primary/secondary/destructive actions;\n- error states;\n- fallback messages;\n- требования mobile/web MAX;\n- checklist UX.\n\n`DESIGN.md` не должен заменять эту спецификацию и не должен порождать второй конфликтующий product spec.\n\n### `$visual-ralph`\n\nНе использовать на backend/bot-only этапах.\n\nИспользовать только после перехода к PHASE 10, когда реально есть mini-app + reference screenshots/Figma.\nЦель:\n- сравнить implementation с макетом;\n- исправить visual drift;\n- проверить mobile viewport.\n\n### `$ai-slop-cleaner`\n\nЗапускать **один раз** после feature-complete bot MVP и до последнего code review.\n\nИскать:\n- бессмысленные abstractions;\n- чрезмерную дробность классов;\n- duplicate helpers;\n- unused wrappers;\n- dead code;\n- comments, просто повторяющие код;\n- generated boilerplate;\n- лишние dependencies;\n- premature abstraction;\n- naming noise.\n\nНельзя:\n- менять product semantics;\n- «упрощать» security checks;\n- удалять ports, которые реально обеспечивают заменяемость внешних систем;\n- объединять слои в God module.\n\nПосле cleanup:\n- format;\n- lint;\n- full tests.\n\n### `$doctor`\n\nОдин раз в начале.\nПовторно — только если:\n- skill не находится;\n- team runtime падает;\n- OMX artifacts повреждены;\n- hooks/runtime явно работают некорректно.\n\nНе тратить токены на doctor после каждой phase.\n\n## 0A.4. Skills, которые НЕ НАДО запускать автоматически\n\n### `$deep-interview`\n\nНе использовать: данный файл уже является подробной спецификацией.\n\nРазрешено только если найдено **реальное бизнес-противоречие**, которое невозможно безопасно разрешить техническим решением.\n\n### `$plan`\n\nНе строить ещё один полный implementation plan поверх этого документа.\n\nДопустим только короткий local plan для отдельной сложной подзадачи.\n\n### `$autopilot`\n\nНе использовать как основной entrypoint.\nПричина: он предназначен для идеи → уточнение → planning → execution, а здесь requirements и execution phases уже заданы.\n\nЗапуск autopilot поверх этой спецификации приведёт к повторному анализу и расходу context.\n\n### `$ralph` и `$ultrawork`\n\nЕсли они присутствуют как legacy/sunset skills — не использовать.\nДля durable execution использовать `$ultragoal`.\nДля parallel work использовать `$team`.\n\n### `$explore`\n\nНе использовать как heavyweight обязательный этап.\nПредпочитать targeted repository search/read.\nЕсли установленная версия помечает `$explore` deprecated — полностью пропустить.\n\n### `$agent-reach`\n\nНе использовать автоматически.\nПрименять только если конкретная внешняя система требует capability, которой нет у обычного research/tooling, и польза явно превышает стоимость дополнительного контекста.\n\n### `$omx-setup`\n\nНе запускать в каждом проектном run.\nИспользовать только если OMX ещё не настроен или `$doctor` выявил configuration issue.\n\n## 0A.5. Дополнительные skills, которые полезно установить, если их ещё нет\n\nСначала проверить `$skill`.\n\nЕсли официальный OMX skill доступен, а локально отсутствует, разрешается использовать `$skill-installer`.\n\nУстанавливать только официальный/upstream skill, не случайные сторонние пакеты.\n\n### `$wiki` — РЕКОМЕНДУЕТСЯ\n\nНазначение:\npersistent repository knowledge между длинными сессиями.\n\nИспользовать для:\n- architecture decisions;\n- проверенного MAX API contract;\n- FNS caveats;\n- Docker/deployment decisions;\n- migration conventions;\n- debugging root causes;\n- important external API findings;\n- exact tested commands.\n\nНе сохранять:\n- secrets;\n- токены;\n- `.env`;\n- raw personal data;\n- длинные логи;\n- временные hypotheses.\n\nПеред повторным внешним research:\n1. проверить repository;\n2. проверить wiki;\n3. только потом web/research.\n\nЭто ключевая мера экономии токенов и повторной работы.\n\n### `$git-master` — РЕКОМЕНДУЕТСЯ\n\nИспользовать для:\n- atomic commits;\n- понятной истории;\n- безопасного rebase;\n- commits по фазам.\n\nНе создавать один гигантский commit на весь проект.\n\nРекомендуемая история:\n```text\nfeat(infra): bootstrap docker and persistence\nfeat(max): add polling transport and commands\nfeat(onboarding): add persisted FSM\nfeat(matching): add deterministic eligibility\nfeat(fns): add company lookup adapter\nfeat(checklist): add document progress\nfeat(prod): add webhook and caddy\ntest: harden bot scenarios\n```\n\n### `$hud` — ОПЦИОНАЛЬНО, НО ПОЛЕЗНО ДЛЯ БЮДЖЕТА\n\nЕсли доступен, включить для контроля:\n- context usage;\n- active workflow;\n- workers;\n- ownership.\n\nНе использовать HUD как повод запускать дополнительные workflows.\n\n### `$performance-goal` — ТОЛЬКО ПОСЛЕ FUNCTIONAL DONE\n\nНе использовать premature optimization.\n\nЗапускать после:\n- bot acceptance green;\n- code review green;\n- ultraqa green.\n\nТолько с измеримым evaluator/benchmark.\n\nПримеры:\n```text\np95 internal webhook handling < 300ms excluding external FNS/MAX network time\nno N+1 queries in recommendation/checklist path\nstartup readiness < 10s after DB is healthy\nbounded memory under synthetic concurrency test\n```\n\nНе оптимизировать «на глаз».\n\n## 0A.6. Security-specific skill strategy\n\nНе требовать отдельный `$security-review`, если текущая версия OMX его не поддерживает или он retired.\n\nВместо этого использовать тройной gate:\n\n```text\n$best-practice-research\n    ↓\n$code-review "security + auth + trust boundaries + secrets + SSRF + concurrency"\n    ↓\n$ultraqa adversarial security scenarios\n```\n\nДля high-risk изменений использовать более глубокий reasoning tier:\n- webhook authentication;\n- secrets;\n- user ownership;\n- reset/data deletion;\n- OpenRouter privacy;\n- production network exposure;\n- import URL validation.\n\n## 0A.7. Token/context discipline\n\nЭто обязательная часть выполнения.\n\n### Не перечитывать весь репозиторий без необходимости\n\nПеред задачей:\n1. определить subsystem;\n2. targeted search;\n3. открыть минимальный набор файлов;\n4. расширять только если требуется evidence.\n\n### Не повторять уже выполненную работу\n\nПеред research:\n1. README/ARCHITECTURE;\n2. relevant code;\n3. tests;\n4. wiki;\n5. только потом external research.\n\nПеред проектированием abstraction:\n1. проверить существующие ports/interfaces;\n2. переиспользовать совместимую abstraction;\n3. не создавать дубль.\n\n### Ограничивать subagent context\n\nWorker получает:\n- конкретную цель;\n- relevant file paths;\n- acceptance criteria;\n- минимально необходимый контекст.\n\nНе пересылать каждому worker весь этот большой spec, если ему нужны 2 раздела.\n\nLead/orchestrator сам извлекает нужные требования и передаёт краткий scoped brief.\n\n### Tier/model budget, если OMX поддерживает tiers\n\nИспользовать минимально достаточный уровень:\n\n**LOW / fast lane**\n- file discovery;\n- narrow repository search;\n- formatting/docs;\n- простая проверка конфигов;\n- короткая synthesis.\n\n**STANDARD**\n- обычная implementation;\n- tests;\n- debugging;\n- repositories;\n- handlers.\n\n**THOROUGH**\n- architecture boundary;\n- security/auth;\n- concurrency/idempotency;\n- production deployment;\n- final critical review;\n- сложный cross-module refactor.\n\nНе использовать THOROUGH для trivial CRUD/formatting.\n\n### Не дублировать quality gates\n\n- lint/test на каждом phase — обычными командами;\n- `$code-review` — только на крупных checkpoints;\n- `$ultraqa` — только когда feature set завершён;\n- `$final-check` — только один финальный gate.\n\n### Compact evidence\n\nОтчёты должны быть outcome-first:\n\n```text\nChanged:\n- ...\n\nVerified:\n- command → result\n\nRemaining:\n- ...\n```\n\nНе писать длинные narrative summaries после каждого маленького изменения.\n\n## 0A.8. Project knowledge lifecycle\n\nЕсли `$wiki` доступен:\n\nПосле PHASE 1 сохранить:\n- подтверждённый MAX contract;\n- polling details;\n- callback payload details.\n\nПосле PHASE 4:\n- фактический FNS lookup behavior;\n- schema/caveats;\n- fallback rules.\n\nПосле PHASE 7:\n- webhook auth;\n- Caddy/prod deployment;\n- tested production commands.\n\nПосле сложного bug:\n- symptom;\n- root cause;\n- final fix;\n- regression test.\n\nПри изменении решения обновлять существующую wiki-страницу, а не создавать дубли.\n\n## 0A.9. Skill mapping по фазам\n\n```text\nBOOTSTRAP\n$doctor\n$skill\noptional install: $wiki, $git-master, $hud\n\nPHASE 0\n$ultragoal\noptional $team\n\nPHASE 1 MAX\n$best-practice-research\n$ultragoal\noptional $team\nMAX smoke\n\nPHASE 2 FSM/PERSISTENCE\n$ultragoal\n$code-review\n\nPHASE 3 MATCHING/DATA\n$ultragoal\noptional $team\ntargeted $analyze if matching architecture drifts\n\nPHASE 4 FNS\n$best-practice-research\n$ultragoal\n$code-review\n\nPHASE 5 CHECKLIST\n$ultragoal\noptional $team\n$code-review\n\nPHASE 6 FEEDBACK/ANALYTICS\n$ultragoal\n\nPHASE 7 WEBHOOK/PRODUCTION\n$best-practice-research\n$ultragoal\noptional $team\n$code-review with explicit security focus\n\nPHASE 8 REMINDERS\n$ultragoal\n\nPHASE 9 OPENROUTER\n$best-practice-research if current API contract not already verified\n$ultragoal\nprivacy-focused $code-review\n\nFEATURE COMPLETE\n$ai-slop-cleaner\nfull tests\n$code-review\n$ultraqa\n$final-check\n\nPHASE 10 MINI-APP\n$design\n$ultragoal\n$visual-ralph only when reference UI exists\n```\n\n## 0A.10. Skill installation safety\n\nЕсли `$skill-installer` используется:\n\n- сначала найти skill через официальный registry/upstream;\n- проверить имя и источник;\n- не устанавливать неизвестный third-party skill автоматически;\n- не выполнять install script из непроверенного gist/repository;\n- не давать skill доступ к секретам без необходимости;\n- после установки при необходимости снова запустить `$doctor`.\n\nЕсли рекомендуемый skill недоступен — продолжить без него. Отсутствие `$wiki`, `$git-master`, `$hud` или `$performance-goal` не должно блокировать разработку.\n
---

# 1. ПРОДУКТ

Название проекта: **Навигатор льгот и субсидий**.

Основной интерфейс: **чат-бот в MAX**.

Целевая аудитория:
- ИП и ООО;
- в первую очередь бизнес младше 2–3 лет;
- без отдельного бухгалтера/юриста;
- пользователь взаимодействует в основном с телефона;
- пользователь не должен читать бюрократические формулировки.

Продукт решает задачу:
1. определить профиль бизнеса по ИНН либо короткой анкете;
2. подобрать 1–3 наиболее релевантные меры поддержки;
3. показать понятные карточки;
4. дать список документов;
5. сохранить выбранную меру в чек-лист;
6. позволить отслеживать готовность документов;
7. позднее — сравнить две меры в mini-app.

Ключевой UX-принцип:
**диалог с ботом вместо каталога мер**.

---

# 2. MVP: ЧТО ДОЛЖНО РЕАЛЬНО РАБОТАТЬ

Обязательный end-to-end flow:

```text
/start
→ приветствие
→ [Начать]
→ ввод ИНН ИЛИ ручная анкета
→ автоматическое/ручное формирование профиля
→ подтверждение профиля
→ детерминированный подбор
→ 1–3 карточки мер прямо в MAX
→ [Подробнее]
→ [Добавить в чек-лист]
→ /checklist
→ список документов
→ отметить документ готовым
→ повторный /checklist показывает сохранённое состояние
```

Также работают:
- `/help`;
- `/profile`;
- `/reset`;
- повторный вход пользователя;
- обработка неверного ИНН;
- ФНС недоступна;
- компания не найдена;
- 0 мер;
- feedback;
- one-time investor interest;
- persistent state после restart контейнеров.

Mini-app:
- **НЕ делать до завершения бота**;
- после бота — только сравнение ровно двух мер.

LLM:
- **не нужен для основной логики**;
- OpenRouter должен быть предусмотрен архитектурно;
- eligibility никогда не определяется LLM.

---

# 3. ТЕХНИЧЕСКИЙ СТЕК

Использовать:

## Runtime
- Python 3.12
- FastAPI
- Uvicorn
- httpx
- SQLAlchemy 2.x async
- asyncpg
- Alembic
- Pydantic 2
- pydantic-settings
- redis-py asyncio
- standard logging/json

## Dev/Test
- pytest
- pytest-asyncio
- pytest-cov
- ruff
- mypy
- httpx MockTransport

## Infrastructure
- PostgreSQL 16 Alpine
- Redis 7 Alpine
- Caddy 2 Alpine для production reverse proxy / HTTPS

Не использовать без крайней необходимости:
- Django;
- Celery;
- RabbitMQ;
- Kafka;
- LangChain;
- LlamaIndex;
- pandas runtime;
- тяжёлые DI frameworks;
- Kubernetes;
- отдельный Node.js backend;
- Telegram-specific библиотеки.

Причина: MVP должен быть переносимым на обычный VPS, быстрым в сборке и не зависеть от тяжёлой инфраструктуры.

---

# 4. БАЗОВЫЕ ПРИНЦИПЫ АРХИТЕКТУРЫ

Использовать modular monolith + лёгкую Clean/Hexagonal Architecture.

Слои:

```text
presentation
    ↓
application
    ↓
domain
    ↑
ports
    ↑
infrastructure
```

Правила:
- `domain` ничего не знает о FastAPI, SQLAlchemy, MAX, Redis;
- `application` работает через ports/interfaces;
- `infrastructure` реализует ports;
- роутеры не содержат бизнес-логику;
- MAX handlers не выполняют SQL напрямую;
- matching engine — отдельный domain/application service;
- внешние системы могут быть заменены без переписывания use cases;
- state machine — отдельный компонент;
- repositories инкапсулируют persistence;
- все побочные эффекты через сервисы/ports.

Не создавать отдельные network microservices для каждого модуля. Проект должен быть логически разделён, но операционно прост.

---

# 5. СТРУКТУРА РЕПОЗИТОРИЯ

Создать:

```text
benefit-navigator/
├── README.md
├── ARCHITECTURE.md
├── SECURITY.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── alembic.ini
├── compose.yml
├── compose.prod.yml
├── Makefile
│
├── docker/
│   ├── bot.Dockerfile
│   ├── worker.Dockerfile
│   ├── importer.Dockerfile
│   └── Caddyfile
│
├── migrations/
│   ├── env.py
│   └── versions/
│
├── data/
│   ├── README.md
│   ├── sphere_categories.csv
│   ├── okved_mapping.csv
│   ├── measures.example.csv
│   └── courses.example.csv
│
├── scripts/
│   ├── wait_for_db.py
│   └── smoke.sh
│
├── src/
│   └── navigator/
│       ├── __init__.py
│       ├── config.py
│       ├── bootstrap.py
│       │
│       ├── domain/
│       │   ├── enums.py
│       │   ├── entities.py
│       │   ├── value_objects.py
│       │   ├── matching.py
│       │   ├── inn.py
│       │   └── errors.py
│       │
│       ├── ports/
│       │   ├── repositories.py
│       │   ├── max_gateway.py
│       │   ├── company_lookup.py
│       │   ├── explanation_provider.py
│       │   ├── rate_limiter.py
│       │   └── clock.py
│       │
│       ├── application/
│       │   ├── dto.py
│       │   ├── onboarding.py
│       │   ├── profiles.py
│       │   ├── recommendations.py
│       │   ├── checklists.py
│       │   ├── feedback.py
│       │   ├── investors.py
│       │   ├── reminders.py
│       │   └── analytics.py
│       │
│       ├── infrastructure/
│       │   ├── db/
│       │   │   ├── base.py
│       │   │   ├── session.py
│       │   │   ├── models.py
│       │   │   └── repositories/
│       │   ├── max_api/
│       │   │   ├── client.py
│       │   │   ├── schemas.py
│       │   │   ├── transport.py
│       │   │   └── errors.py
│       │   ├── fns/
│       │   │   ├── rmsp_portal.py
│       │   │   ├── local_snapshot.py
│       │   │   ├── mock.py
│       │   │   └── schemas.py
│       │   ├── openrouter/
│       │   │   ├── client.py
│       │   │   └── template.py
│       │   ├── redis/
│       │   │   ├── rate_limit.py
│       │   │   ├── idempotency.py
│       │   │   └── cache.py
│       │   └── observability/
│       │       ├── logging.py
│       │       └── metrics.py
│       │
│       ├── presentation/
│       │   ├── http/
│       │   │   ├── app.py
│       │   │   ├── health.py
│       │   │   └── webhook.py
│       │   └── maxbot/
│       │       ├── dispatcher.py
│       │       ├── state_machine.py
│       │       ├── handlers/
│       │       │   ├── global_commands.py
│       │       │   ├── onboarding.py
│       │       │   ├── recommendations.py
│       │       │   ├── checklist.py
│       │       │   ├── feedback.py
│       │       │   └── investors.py
│       │       ├── keyboards.py
│       │       ├── messages.py
│       │       ├── callbacks.py
│       │       └── renderers.py
│       │
│       └── entrypoints/
│           ├── api.py
│           ├── worker.py
│           ├── seed.py
│           ├── import_measures.py
│           ├── register_webhook.py
│           └── max_smoke.py
│
└── tests/
    ├── unit/
    ├── integration/
    ├── contract/
    ├── scenarios/
    └── fixtures/
```

---

# 6. DOCKER: НЕ ОДИН КОНТЕЙНЕР

## 6.1. `bot`

Отдельный `docker/bot.Dockerfile`.

Обязан:
- использовать `python:3.12-slim`;
- multi-stage build при необходимости;
- non-root user;
- устанавливать только runtime-зависимости;
- запускать FastAPI/Uvicorn;
- expose 8000;
- иметь healthcheck или compose healthcheck;
- не содержать secrets;
- не монтировать source code в production.

Local:
- MAX long polling можно запускать как background task приложения либо отдельным entrypoint; предпочтительно background task только в `APP_ENV=local`.

Production:
- только webhook;
- background polling выключен.

## 6.2. `worker`

Отдельный `docker/worker.Dockerfile`.

Назначение:
- reminders;
- периодическая очистка expired cache metadata;
- future background tasks.

Не использовать Celery.
Обычный asyncio loop:
- controlled interval;
- graceful shutdown;
- advisory lock PostgreSQL;
- каждая итерация должна быть идемпотентной.

## 6.3. `postgres`

`postgres:16-alpine`

Настройки:
- persistent named volume;
- healthcheck через `pg_isready`;
- credentials только env;
- порт наружу в production не публиковать.

## 6.4. `redis`

`redis:7-alpine`

Использование:
- rate limits;
- update idempotency;
- короткий FNS cache;
- debounce callbacks.

Не хранить только в Redis:
- profile;
- checklist;
- measures;
- feedback;
- conversation state.

Redis потерялся → основная пользовательская информация не должна потеряться.

## 6.5. `migrate`

Отдельный one-shot compose service:
- depends_on postgres healthy;
- `alembic upgrade head`;
- завершается code 0.

Bot/worker должны стартовать после успешной migration.

## 6.6. `caddy`

Только production compose.
Отдельный контейнер.

Функции:
- HTTPS;
- reverse proxy к bot:8000;
- HTTP→HTTPS;
- security headers;
- наружу 80/443.

## 6.7. `importer`

Отдельный Dockerfile/compose profile, не стартует постоянно.

Для будущего:
- импорт официальной bulk XML выгрузки ФНС;
- CSV импорты аналитиков.

---

# 7. COMPOSE

## `compose.yml` local

Сервисы:
- postgres
- redis
- migrate
- bot
- worker

Worker можно держать включённым, но reminders disabled через env.

Local MAX:
`MAX_TRANSPORT=polling`.

Никакого Caddy.

Добавить named volumes:
- `postgres_data`
- при необходимости `redis_data`, но Redis persistence не является обязательной для correctness.

Использовать:
- `restart: unless-stopped` для bot/worker;
- healthcheck;
- `depends_on` health conditions, но приложение всё равно должно иметь retry на подключение при старте.

## `compose.prod.yml`

Добавляет/переопределяет:
- caddy;
- `MAX_TRANSPORT=webhook`;
- worker enabled;
- restart policies;
- отсутствие открытого PostgreSQL/Redis ports;
- production Uvicorn workers.

Не запускать много Uvicorn workers при local polling: один polling consumer.
В webhook production допустимо несколько workers/replicas, потому что idempotency и DB constraints защищают side effects.

---

# 8. DEPENDENCY MANAGEMENT

Использовать `pyproject.toml`.

Не оставлять unpinned wildcard dependencies.
Зафиксировать разумные совместимые диапазоны или lock, если выбран uv/pip-tools.

Предпочтительно:
- `uv` для быстрой установки;
- если Codex выбирает uv, создать `uv.lock`;
- Docker build должен быть reproducible.

Команды разработчика не должны требовать ручной установки PostgreSQL/Redis на host: всё инфраструктурное поднимается Compose.

---

# 9. ENVIRONMENT

`.env.example`:

```dotenv
APP_ENV=local
LOG_LEVEL=INFO

POSTGRES_DB=benefit_navigator
POSTGRES_USER=benefit
POSTGRES_PASSWORD=change_me
DATABASE_URL=postgresql+asyncpg://benefit:change_me@postgres:5432/benefit_navigator

REDIS_URL=redis://redis:6379/0

MAX_API_BASE_URL=https://platform-api2.max.ru
MAX_BOT_TOKEN=
MAX_TRANSPORT=polling
MAX_WEBHOOK_PUBLIC_URL=
MAX_WEBHOOK_SECRET=
MAX_POLL_TIMEOUT_SECONDS=30
MAX_HTTP_TIMEOUT_SECONDS=10

FNS_PROVIDER=rmsp_portal
FNS_LOOKUP_ENABLED=true
FNS_TIMEOUT_SECONDS=4
FNS_CACHE_TTL_SECONDS=21600
FNS_LOOKUP_LIMIT_10M=5
FNS_LOOKUP_LIMIT_1H=30

OPENROUTER_ENABLED=false
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=
OPENROUTER_TIMEOUT_SECONDS=12

MINIAPP_ENABLED=false
MINIAPP_COMPARE_URL=

REMINDERS_ENABLED=false
REMINDER_DAYS=7,3,1
REMINDER_SCAN_INTERVAL_SECONDS=600

DEBUG_ENDPOINTS_ENABLED=false
```

Fail-fast validation:
- MAX token обязателен для real MAX mode;
- webhook url/secret обязательны для webhook;
- OpenRouter key/model обязательны только если OpenRouter enabled;
- miniapp URL обязателен только если miniapp enabled.

Секреты:
- `.env` gitignored;
- не выводить значения secrets в logs;
- не хранить в README примеры реального токена.

---

# 10. MAX API — АКТУАЛЬНЫЕ ТРЕБОВАНИЯ

Использовать:
`https://platform-api2.max.ru`

Authorization:
```http
Authorization: <MAX_BOT_TOKEN>
```

Не передавать токен query parameter.

Сделать `MaxApiClient` единственной точкой HTTP-взаимодействия с MAX.

Общие настройки:
- `httpx.AsyncClient`;
- connection pooling;
- timeout;
- keep-alive;
- ограниченный retry только на network/5xx/429;
- no retry для 4xx кроме 429;
- respect `Retry-After`, если присутствует.

Методы клиента должны покрыть:
- get bot info `/me`;
- get updates `/updates`;
- send message;
- edit/answer callback, где применимо;
- create/list/delete webhook subscription;
- bot commands при необходимости.

Если фактическая схема MAX API отличается от названия метода в этом документе, сверить **официальную документацию dev.max.ru** и реализовать актуальный контракт, не придумывать поля.

---

# 11. LOCAL POLLING И PRODUCTION WEBHOOK

## Long Polling

Только local/dev.

Логика:
1. получить marker;
2. вызвать `GET /updates`;
3. обработать обновления последовательно или ограниченно параллельно;
4. двигать marker только после безопасной обработки;
5. при временной сетевой ошибке backoff:
   - 1s
   - 2s
   - 4s
   - 8s
   - максимум 30s;
6. graceful cancellation.

Важно:
- Long Polling не должен быть активен при webhook subscription;
- local README должен объяснять, как удалить/отключить webhook перед polling.

## Webhook

Production endpoint:
`POST /webhooks/max`.

Проверить MAX webhook secret header согласно актуальной документации платформы.

Алгоритм:
1. authentication/secret validation;
2. schema parse;
3. extract event id;
4. idempotency check;
5. dispatch;
6. commit side effects;
7. return 200.

Повторный event:
- вернуть 200;
- не повторять действия.

Webhook handler не должен ждать LLM.
LLM optional и с fallback.

---

# 12. BUTTONS И CALLBACK UX

Все inline buttons строить централизованно.

Никаких проверок бизнес-логики по пользовательскому label кнопки.

Callback payload:

```text
nav:start
nav:how
nav:help
nav:profile
nav:checklist

inn:manual
inn:retry

employees:1
employees:2_15
employees:16_100
employees:100_plus

business_form:ip
business_form:ooo
business_form:self_employed

sphere:foodservice
sphere:retail
sphere:household_services
sphere:it_digital
sphere:manufacturing
sphere:construction_repair
sphere:beauty_health
sphere:education
sphere:transport_logistics
sphere:other

stage:new
stage:lt1
stage:1_3
stage:gt3

profile:confirm
profile:edit
profile:edit_inn
profile:edit_manual

measure:details:<uuid>
measure:add:<uuid>
measure:remove_ask:<uuid>
measure:remove_confirm:<uuid>
measure:feedback:<uuid>

feedback:not_eligible:<uuid>
feedback:outdated:<uuid>
feedback:other:<uuid>

document:toggle:<uuid>

reset:confirm
reset:cancel

investor:yes
investor:no

compare:<uuid1>:<uuid2>
```

Callback parser:
- строгая схема;
- неизвестный callback → безопасное сообщение;
- UUID validation;
- user ownership checks для checklist actions.

---

# 13. FSM / СОСТОЯНИЯ

Хранить в PostgreSQL.

Enum:

```text
IDLE
WELCOME
AWAITING_INN
AWAITING_EMPLOYEE_BUCKET
AWAITING_STAGE
MANUAL_REGION
MANUAL_BUSINESS_FORM
MANUAL_SPHERE
MANUAL_STAGE
MANUAL_EMPLOYEES
CONFIRM_PROFILE
RESET_CONFIRM
FEEDBACK_REASON
FEEDBACK_TEXT
INVESTOR_NAME
INVESTOR_CONTACT
READY
```

`conversation_states`:
- max_user_id PK/FK;
- state;
- context JSONB;
- updated_at.

`context` разрешён только для transient draft:
- current INN;
- temporary profile;
- selected measure;
- pending feedback id.

Постоянные данные не прятать в context.

При restart state восстанавливается.

---

# 14. ПОРЯДОК DISPATCH

На каждый update:

1. определить update identity;
2. idempotency;
3. upsert user/last_seen;
4. проверить global commands;
5. проверить unsupported media;
6. callback handler;
7. state-specific text handler;
8. fallback текущего state;
9. analytics event.

Глобальные команды работают из любого состояния:
- `/start`
- `/help`
- `/profile`
- `/checklist`
- `/reset`

---

# 15. ТОЧНЫЙ UX БОТА

## 15.1 `/start`

Если новый пользователь:

**Сообщение:**
```text
Привет! Я помогу подобрать меры поддержки для вашего бизнеса.

Это займёт несколько минут: попробуем определить компанию по ИНН, уточним пару параметров и покажем 1–3 подходящие меры.
```

Кнопки:
1. `Начать подбор`
2. `Как это работает?`

Если профиль уже есть:
```text
С возвращением! Профиль компании уже сохранён.

Что хотите сделать?
```

Кнопки:
1. `Подобрать меры`
2. `Мой профиль`
3. `Мой чек-лист`
4. `Начать сначала`

`Начать сначала` сбрасывает текущий dialog state, но не удаляет профиль.

## 15.2 «Как это работает?»

```text
1. Вы вводите ИНН или заполняете короткую анкету.
2. Я сопоставляю профиль бизнеса с курируемой базой мер поддержки.
3. Показываю до трёх вариантов и объясняю, почему они подходят.

Данные из ФНС и условия мер носят справочный характер. Перед подачей всегда проверяйте первоисточник.
```

Кнопка:
`Начать подбор`

## 15.3 Ввод ИНН

```text
Введите ИНН компании или ИП.

Для организации — 10 цифр.
Для ИП — 12 цифр.
```

Кнопка:
`Заполнить вручную`

Под полем/следующим сообщением подсказка:
```text
По ИНН попробуем автоматически определить название, регион, основной ОКВЭД и статус МСП.
```

### invalid syntax/checksum

```text
Похоже, ИНН введён с ошибкой.

Проверьте число: нужно 10 цифр для организации или 12 цифр для ИП.
```

Кнопки:
- `Ввести снова`
- `Заполнить вручную`

### not found

```text
Не нашли компанию с таким ИНН в доступном источнике.

Проверьте номер ещё раз или заполните профиль вручную.
```

### unavailable

```text
Сейчас не получилось проверить ИНН: внешний сервис временно недоступен.

Можно повторить попытку или продолжить вручную — подбор мер всё равно будет работать.
```

Кнопки:
- `Повторить`
- `Заполнить вручную`

## 15.4 После FNS FOUND

Показать:
```text
Нашёл данные компании:

{company_name}
Регион: {region}
Основной ОКВЭД: {okved}
Сфера: {sphere}
Статус МСП: {msp_category or "нет данных"}

Осталось уточнить пару вещей.
```

Если employees нет:
```text
Сколько сотрудников работает в бизнесе?
```

Кнопки:
- `1`
- `2–15`
- `16–100`
- `Больше 100`

Затем stage:
```text
На каком этапе сейчас бизнес?
```

Кнопки:
- `Только открылись`
- `До 1 года`
- `1–3 года`
- `Больше 3 лет`

Если registration_date надёжно известна, вычислить stage и спросить:
```text
По дате регистрации бизнес относится к категории «{stage}». Всё верно?
```

Кнопки:
- `Да`
- `Выбрать вручную`

## 15.5 Ручная анкета

### Регион
```text
Укажите регион регистрации бизнеса.

Например: Москва, Татарстан, Московская область.
```

Нормализовать через справочник субъектов РФ.
При нескольких совпадениях предложить кнопки.
Не сохранять произвольную строку без normalization.

### Форма
```text
Какая у вас форма бизнеса?
```
Кнопки:
- `ИП`
- `ООО`
- `Самозанятый`

### Сфера
```text
Выберите основную сферу деятельности.
```

Кнопки желательно разбить в несколько рядов по 1–2, чтобы не делать слишком длинные строки:

- `Общепит`
- `Розничная торговля`
- `Бытовые услуги`
- `IT и цифровые услуги`
- `Производство`
- `Строительство и ремонт`
- `Красота и здоровье`
- `Образование`
- `Транспорт и логистика`
- `Прочее`

### Stage
те же четыре кнопки.

### Employees
те же четыре bucket.

## 15.6 Подтверждение

```text
Проверьте профиль:

Компания: {name or "не указано"}
ИНН: {inn or "не указан"}
Регион: {region}
Форма: {business_form}
Сфера: {sphere}
Этап бизнеса: {stage}
Сотрудники: {employee_bucket}
Статус МСП: {msp_category or "нет данных"}
Источник: {ФНС | введено вручную}

Всё верно, и вы подтверждаете, что представляете этот бизнес?
```

Кнопки:
- `Да, всё верно`
- `Изменить данные`

Следующая строка:
```text
Данные из открытых источников носят справочный характер. Сервис не проверяет ваши полномочия представлять компанию.
```

---

# 16. MATCHING ENGINE

Никакого ML.

Никакого LLM.

Никакого cosine similarity.

Только structured eligibility.

## 16.1 Профиль

```text
region_code
sphere_category
business_stage
business_form
msp_category optional
employee_count/bucket
```

## 16.2 Criteria меры

```text
regions
spheres
business_stages
business_forms
msp_categories
employee_min
employee_max
valid_from
application_deadline
is_active
```

Отсутствие restriction = любое значение.

## 16.3 Match status

```text
ELIGIBLE
NEEDS_MORE_INFO
INELIGIBLE
```

`INELIGIBLE`:
хотя бы один известный hard criterion конфликтует.

`NEEDS_MORE_INFO`:
конфликтов нет, но для критерия меры в profile отсутствует значение.

`ELIGIBLE`:
все hard criteria либо совпадают, либо unrestricted.

## 16.4 Expiration

Не рекомендовать:
- `is_active=false`;
- deadline < today;
- valid_from > today.

## 16.5 Sorting

1. priority DESC
2. amount_max_rub DESC NULLS LAST
3. application_deadline ASC NULLS LAST
4. stable tie-breaker name/id

Возвращать максимум 3.

## 16.6 Zero results

Если 0 ELIGIBLE, есть NEEDS_MORE_INFO:
```text
Я пока не могу уверенно отобрать меру — не хватает нескольких данных.
```
Кнопка:
`Уточнить детали`

Задать только реально недостающие criteria.

Если вообще нет:
```text
Пока не нашли меру именно под ваш профиль.

Это не означает, что поддержки нет: база MVP ограничена и пополняется вручную.
```

Кнопки:
- `Изменить профиль`
- `Сообщить о недостающей мере`

---

# 17. КАРТОЧКИ МЕР

Краткая карточка:

```text
{Название}

{Федеральная | Региональная}
{amount_display}
{benefit_detail optional}

Почему может подойти:
• {matched reason 1}
• {matched reason 2}
• {matched reason 3}
```

Кнопки:
- `Подробнее`
- `В чек-лист`
- `Мера не подходит`

После 2+ рекомендаций и только при `MINIAPP_ENABLED=true`:
- `Сравнить 2 меры`

Если mini-app disabled, кнопку вообще не показывать.

## Подробнее

```text
{Название}

Что это
{what_is_it}

Кто может получить
{who_can_receive}

Поддержка
{amount_display}
{benefit_detail}

Документы
1. ...
2. ...
3. ...

Куда подавать
{where_to_apply}

Срок рассмотрения
{review_days or "зависит от программы"}

Срок подачи
{application_deadline or "уточните в первоисточнике"}

Источник
{source_name}
{source_url}

Источник проверен: {source_checked_at}
```

Внизу:
```text
По данным профиля мера соответствует указанным структурированным критериям. Перед подачей проверьте актуальные условия в первоисточнике.
```

Нельзя использовать:
- «вам точно положено»;
- «гарантированно получите»;
- выдуманные критерии.

---

# 18. DATABASE MODEL

Все migration через Alembic.

## `users`
- `max_user_id` BIGINT PK
- `first_seen_at`
- `last_seen_at`
- `investor_prompt_state`
- `created_at`
- `updated_at`

Индекс last_seen.

## `conversation_states`
- `max_user_id` PK FK
- `state`
- `context JSONB NOT NULL DEFAULT {}`
- `updated_at`

## `sphere_categories`
- UUID id
- code varchar unique
- name varchar unique
- is_active bool

## `okved_mappings`
- `okved_class CHAR(2)` PK
- sphere_category_id FK
- note nullable

## `regions`
- code PK
- name
- aliases JSONB or normalized aliases table

## `company_profiles`
- UUID id
- max_user_id unique FK
- inn nullable indexed
- company_name nullable
- region_code FK
- primary_okved nullable
- sphere_category_id FK
- business_stage enum
- business_form enum
- employee_bucket enum
- employee_count nullable
- msp_category nullable
- source enum
- consent_at
- fns_checked_at nullable
- created_at
- updated_at

## `measures`
- UUID id PK
- external_code unique
- name
- support_level enum
- amount_display
- amount_min_rub numeric nullable
- amount_max_rub numeric nullable
- benefit_detail nullable
- what_is_it text
- who_can_receive text
- where_to_apply text
- review_days int nullable
- source_name
- source_url
- source_checked_at
- valid_from date nullable
- application_deadline date nullable
- employee_min nullable
- employee_max nullable
- is_active bool
- is_demo bool
- priority int default 0
- created_at
- updated_at

Indexes:
- is_active
- deadline
- priority
- amount_max

## Restrictions

Отдельные join tables:
- `measure_regions`
- `measure_spheres`
- `measure_business_forms`
- `measure_business_stages`
- `measure_msp_categories`

Если у меры нет записей в соответствующей join table → unrestricted.

Все composite unique.

## `measure_documents`
- UUID id
- measure_id FK cascade
- code
- title
- sort_order
- unique(measure_id, code)

## `user_measure_checklists`
- UUID id
- max_user_id FK
- measure_id FK
- added_at
- unique(max_user_id, measure_id)

## `checklist_document_states`
- UUID id
- checklist_id FK cascade
- measure_document_id FK
- is_done bool
- done_at nullable
- unique(checklist_id, measure_document_id)

## `courses`
- UUID id
- name
- is_free
- description
- url
- source_name
- sphere_category_id nullable
- is_active
- created_at
- updated_at

## `measure_feedback`
- UUID id
- max_user_id
- measure_id
- feedback_type enum
- comment nullable
- created_at

## `investor_leads`
- UUID id
- max_user_id unique
- name
- contact
- created_at

## `usage_counters`
- measure_id PK
- checklist_add_count bigint default 0
- updated_at

## `analytics_events`
- UUID id
- max_user_id nullable
- event_type
- measure_id nullable
- properties JSONB
- created_at

Indexes:
- event_type + created_at
- max_user_id + created_at

## `reminder_deliveries`
- UUID id
- max_user_id
- measure_id
- days_before
- sent_at
- unique(max_user_id, measure_id, days_before)

---

# 19. CHECKLIST

При `Добавить в чек-лист` транзакционно:

1. создать `user_measure_checklists`, если нет;
2. если уже есть — не создавать повторно;
3. для каждого measure_document создать checklist state, если нет;
4. usage counter увеличить только при фактическом первом add;
5. analytics `checklist_added`.

Ответ:
```text
Добавил «{measure}» в чек-лист.

Документы можно открыть командой /checklist.
```

`/checklist`:

Если пуст:
```text
Чек-лист пока пуст.

Сначала подберите меры через /start и добавьте нужную.
```

Если есть:

```text
Ваш чек-лист

{measure_name}
Готово: 3 из 5
Срок подачи: 28 сентября 2026

✅ Выписка из реестра МСП
✅ Финансовая отчётность
✅ Заявка
⬜ Бизнес-план
⬜ Документы на залог
```

Каждый незавершённый/завершённый документ имеет callback toggle.

Toggle:
- transaction;
- set is_done;
- done_at now/null;
- обновить сообщение или отправить компактное подтверждение.

Удаление меры:
- кнопка `Убрать из чек-листа`;
- обязательно confirmation;
- только после confirm delete checklist + states;
- usage counter не декрементировать, если это исторический metric «сколько раз добавляли».

---

# 20. COURSES

После recommendations, если есть совпадающие курсы:

```text
Ещё может пригодиться

Нашёл бесплатные материалы по вашей сфере:
• ...
• ...
```

Не блокировать main flow.

Для MVP ссылки обычные.

Если курсов нет — молча пропустить.

---

# 21. FEEDBACK FLOW

На каждой measure details:
`Мера не подходит`.

Ответ:
```text
Спасибо. Что именно не так?
```

Кнопки:
- `Не подхожу по условиям`
- `Информация устарела`
- `Другое`

Для первых двух:
- сохранить;
- подтвердить;
- можно исключить measure из текущей session recommendations.

Для `Другое`:
```text
Напишите коротко, что не так.
```
Следующий текст сохранить как comment.

Не отправлять feedback в LLM.

---

# 22. INVESTOR LEAD

Показывается только один раз после первого успешного показа рекомендаций.

```text
Скоро хотим добавить раздел с частными инвесторами и менторами — на случай, если одной господдержки недостаточно.

Хотите узнать о запуске первыми?
```

Кнопки:
- `Да, интересно`
- `Не сейчас`

Если отказ:
- `investor_prompt_state=declined`;
- больше автоматически не показывать.

Если да:
1. спросить имя;
2. спросить контакт;
3. сохранить;
4. `interested`.

Контакт не логировать целиком.

---

# 23. FNS

## Ключевой факт

Не предполагать наличие официального простого REST endpoint `GET /company/{inn}`.

Официальный реестр МСП ФНС — bulk dataset XML/ZIP.

Для хакатона реализовать adapter best-effort lookup через доступную публичную web-витрину/поиск реестра МСП, но изолировать за интерфейсом.

## Port

```python
class CompanyLookup(Protocol):
    async def find_by_inn(self, inn: str) -> CompanyLookupResult: ...
```

`CompanyLookupResult`:
- status `FOUND | NOT_FOUND | TEMPORARILY_UNAVAILABLE`
- company_name
- inn
- ogrn optional
- business_form
- region_code/name
- primary_okved
- msp_category
- registration_date optional
- employee_count optional
- source_checked_at

## Provider `RmspPortalLookup`

- Async HTTP;
- timeout 4s;
- max 1 retry transient;
- schema validation;
- changed/malformed schema → temporarily unavailable;
- cache success/not-found separately;
- no unbounded loops;
- user-agent identifiable.

## `LocalSnapshotLookup`

Заготовить repository/implementation boundary.
Не обязательно скачивать многогигабайтный dataset на первом запуске.

## `MockCompanyLookup`

Fixtures:
- legal entity FOUND;
- IP FOUND;
- NOT_FOUND;
- TIMEOUT;
- malformed response.

---

# 24. INN VALIDATION

До внешнего запроса:
- strip spaces;
- digits only;
- length 10 or 12;
- checksum.

Реализовать отдельно domain/value object.
Покрыть unit tests известными валидными/невалидными примерами.

Неверный checksum не отправлять во ФНС.

---

# 25. OKVED NORMALIZATION

`62.01` → class `62`.

`okved_mapping` содержит ровно двузначные классы.

Seed должен расширять диапазоны аналитиков:
например 58–63 → 58,59,60,61,62,63.

Если mapping отсутствует:
`sphere=other`, но analytics событие:
`okved_unmapped`.

Не падать.

---

# 26. MEASURE DATA IMPORT

Реальные меры команда отдаёт CSV.

Не генерировать реальные записи искусственно.

Создать шаблон CSV минимум с:

```text
external_code
name
support_level
regions
spheres
business_forms
business_stages
msp_categories
employee_min
employee_max
amount_display
amount_min_rub
amount_max_rub
benefit_detail
what_is_it
who_can_receive
documents
where_to_apply
review_days
valid_from
application_deadline
source_name
source_url
source_checked_at
is_active
priority
```

Для list fields разделитель согласован, например `|`.

`documents` тоже parse по `|`.

Importer:
```bash
python -m navigator.entrypoints.import_measures \
  --file data/measures.csv \
  --validate-only
```

и:
```bash
python -m navigator.entrypoints.import_measures \
  --file data/measures.csv \
  --apply
```

Validation:
- unknown enum;
- invalid date;
- invalid URL;
- duplicate external_code;
- min > max;
- deadline < valid_from;
- unknown region;
- unknown sphere;
- empty name/source;
- invalid monetary number.

Ошибки вывести:
`row 12, column spheres: unknown value ...`

Apply:
- transaction;
- upsert по external_code;
- replace restrictions/documents atomically;
- не удалять отсутствующие меры автоматически без explicit flag.

---

# 27. DEMO SEED

Для smoke/demo создать 5 фиктивных мер.

Названия строго:
- `DEMO — ...`

`is_demo=true`.

URLs:
`https://example.com/...`

README:
«DEMO записи нужны только для проверки функциональности и не являются действующими мерами господдержки».

Создать 3 demo courses.

---

# 28. OPENROUTER

OpenRouter — только future enhancement.

Port:
```python
class ExplanationProvider(Protocol):
    async def explain_match(...) -> str: ...
```

Default:
`TemplateExplanationProvider`.

OpenRouter:
- OpenAI-compatible `/chat/completions`;
- `Authorization: Bearer ...`;
- timeout;
- max 1 retry;
- fallback template;
- feature flag.

Запрещено отправлять:
- ИНН;
- MAX user id;
- investor contacts;
- персональные данные.

Можно:
- region category;
- sphere;
- stage;
- business form;
- abstract MСП category;
- structured measure criteria.

System prompt LLM:
- объяснить только переданные matched reasons;
- не добавлять факты;
- не обещать получение поддержки;
- до 3 коротких bullet points.

LLM failure:
- пользователь ничего не замечает;
- template explanation.

---

# 29. RATE LIMITING

Redis.

## INN lookup
Per user:
- 5 / 10 min;
- 30 / hour.

При превышении:
```text
Слишком много проверок подряд.

Попробуйте позже или заполните профиль вручную.
```

## Callback debounce
- callback id idempotent;
- дополнительно short lock на mutation callbacks.

## Global bot abuse
Мягкий per-user message limit, например:
- 60/minute;
- при превышении no expensive operations.

Никаких CAPTCHA в MVP.

---

# 30. IDEMPOTENCY

MAX может доставить событие повторно.

Ключ:
- callback id;
- message id;
- update id;
- fallback stable hash.

Redis:
`SET event-key 1 NX EX 86400`.

Но критичные side effects дополнительно защищаются DB constraints.

Примеры:
- checklist unique(user, measure);
- investor_lead unique(user);
- reminder unique(user, measure, days_before).

---

# 31. REMINDERS

Feature flag default false, но код должен быть готов.

Worker:
- scan каждые 10 минут;
- reminder thresholds env;
- учитывать timezone в понятном и последовательном виде; MVP может хранить даты без времени и отправлять в фиксированное дневное окно;
- дедлайн уже прошёл → не напоминать;
- sent marker в reminder_deliveries.

Сообщение:
```text
Напоминание: до срока подачи по мере «{measure}» осталось {N} дн.

Проверьте, все ли документы готовы.
```

Кнопка:
`Открыть чек-лист`

---

# 32. ANALYTICS

Собирать продуктовые события, не добавляя внешнюю аналитическую платформу.

События:
- bot_started;
- onboarding_started;
- manual_onboarding_started;
- inn_lookup_started;
- inn_lookup_success;
- inn_lookup_not_found;
- inn_lookup_failed;
- profile_confirmed;
- recommendations_shown;
- zero_recommendations;
- measure_details_opened;
- checklist_added;
- checklist_document_done;
- feedback_submitted;
- investor_interest_submitted.

Метрики:
1. onboarding completion:
`profile_confirmed / onboarding_started`
2. result completion:
`recommendations_shown / onboarding_started`
3. time to first result:
`recommendations_shown.timestamp - onboarding_started.timestamp`
4. checklist conversion:
`checklist_added / recommendations_shown`

Не строить отдельную analytics UI для MVP.

---

# 33. OBSERVABILITY

## Logging

JSON logs.

Поля:
- ts;
- level;
- service;
- event;
- correlation_id;
- max_user_id_hash;
- state;
- update_type;
- duration_ms;
- error_type.

PII masking.

Не логировать:
- tokens;
- Authorization;
- raw .env;
- investor contact;
- полный FNS response на INFO;
- полный user message, если он может содержать contact/ИНН.

## Health

`GET /health/live`
- process alive;
- без внешних checks.

`GET /health/ready`
- DB;
- Redis.

FNS/MAX не включать в readiness.

## Metrics

Не обязательно Prometheus в MVP.
Можно добавить lightweight `/internal/metrics` только feature-flag/local.
Production endpoint наружу не публиковать.

---

# 34. SECURITY

1. non-root containers;
2. secrets only env;
3. `.env` ignored;
4. DB/Redis no public prod ports;
5. webhook secret;
6. rate limits;
7. idempotency;
8. URL allow/validation for imported source links;
9. SQLAlchemy parameterized SQL only;
10. no dynamic eval;
11. no rendering raw HTML from CSV;
12. external responses validated via Pydantic;
13. outbound timeouts;
14. dependency vulnerability-aware minimal set;
15. reset confirmation;
16. no sensitive data to OpenRouter.

Написать `SECURITY.md`.

---

# 35. RESET SEMANTICS

`/start`:
- сбрасывает только текущий dialog;
- профиль не удаляет.

`/reset`:
```text
Удалить профиль компании, чек-лист и сохранённые данные?

Это действие нельзя отменить.
```

Кнопки:
- `Да, удалить`
- `Отмена`

После confirm transaction:
- profile;
- checklist/states;
- feedback, если policy продукта требует user deletion;
- investor lead;
- conversation context.

Analytics:
оставить только обезличенные события либо null user reference, если реализовано корректно.

Ответ:
```text
Данные удалены. Чтобы начать заново, используйте /start.
```

---

# 36. UNSUPPORTED INPUT

Фото/стикер/audio/file:
```text
Я пока работаю только с текстом и кнопками.

Продолжим с текущего шага.
```

После этого повторить подсказку текущего state.

Произвольный invalid input:
- не «не понимаю»;
- конкретная ошибка state.

Пример:
в business form:
```text
Выберите форму бизнеса одной из кнопок ниже.
```

---

# 37. UX КНОПОК

Правила расположения:

1. Главная primary action — первая.
2. destructive action — отдельно последней строкой.
3. не больше 2 длинных кнопок в одном ряду.
4. короткие category buttons можно по 2 в ряд, если MAX layout позволяет.
5. `Назад`/`Отмена` — нижний ряд.
6. кнопки должны быть повторяемы после invalid input.
7. label короткий, callback стабильный.

Примеры layouts:

Welcome:
```text
[ Начать подбор ]
[ Как это работает? ]
```

INN error:
```text
[ Ввести снова ]
[ Заполнить вручную ]
```

Confirm:
```text
[ Да, всё верно ]
[ Изменить данные ]
```

Measure:
```text
[ Подробнее ]
[ В чек-лист ]
[ Мера не подходит ]
```

Reset:
```text
[ Да, удалить ]
[ Отмена ]
```

---

# 38. PERFORMANCE / LOAD

Цель MVP:
- сотни одновременных пользователей без архитектурного переписывания;
- тысячи профилей/чек-листов;
- тысячи мер в будущем.

Правила:
- Async I/O;
- connection pooling;
- DB indexes;
- не держать DB transaction во время внешнего HTTP;
- FNS cached;
- matching желательно SQL-prefilter + domain validation либо простой in-memory для 20–30, но repository API должен позволить масштабирование;
- не `SELECT *` всей базы при каждом message в зрелой версии;
- LIMIT recommendations;
- pagination для checklist при необходимости;
- no blocking file/network calls.

Uvicorn production:
- webhook mode;
- несколько workers допустимо;
- worker count configurable;
- state в PostgreSQL, поэтому sticky session не нужен.

---

# 39. TRANSACTION BOUNDARIES

Использовать Unit of Work или ясные service-level transactions.

Атомарно:
- profile confirm;
- checklist add + docs + usage counter;
- checklist remove;
- investor lead state;
- feedback insert + optional session exclusion.

Не держать transaction:
- во время MAX API request;
- во время FNS request;
- во время OpenRouter request.

Pattern:
1. read/prepare;
2. external request;
3. short DB transaction;
4. outgoing MAX message.

Для сложных production semantics можно future outbox, но MVP не требует отдельной outbox, если операции идемпотентны.

---

# 40. ERROR HANDLING

Ошибки domain:
- InvalidInn
- CompanyNotFound
- CompanyLookupUnavailable
- ProfileIncomplete
- InvalidStateTransition
- MeasureNotFound
- ChecklistAlreadyExists
- ChecklistNotFound
- RateLimitExceeded

Нельзя:
```python
except Exception:
    pass
```

Infrastructure exceptions:
- log;
- map to controlled application errors.

MAX send failure:
- bounded retry;
- не ломать DB consistency.

FNS failure:
- manual fallback.

OpenRouter:
- template fallback.

---

# 41. TEST PLAN

## Unit mandatory

### INN
- valid legal entity;
- invalid legal checksum;
- valid IP;
- invalid IP checksum;
- non-digit;
- lengths.

### Matching
- unrestricted region;
- matching region;
- mismatching region;
- sphere;
- form;
- stage;
- msp category;
- employee lower/upper;
- missing criterion;
- expired measure;
- inactive;
- future valid_from;
- sorting;
- limit 3.

### FSM
- every valid transition;
- invalid transition remains state;
- global command overrides;
- start preserves profile;
- reset requires confirm.

### Checklist
- first add;
- duplicate add;
- document generation;
- toggle;
- remove confirm;
- usage count once.

### Investor
- shown first time;
- decline;
- never repeated;
- interested creates lead.

### Feedback
- each type;
- other text.

## Integration
PostgreSQL:
- migrations;
- repositories;
- constraints;
- transactions.

Redis:
- limit;
- idempotency;
- cache.

## Contract
MAX MockTransport:
- auth header exactly correct;
- `/me`;
- updates marker;
- 429 retry;
- 500 bounded retry;
- callback response.

FNS:
- found;
- not found;
- timeout;
- 500;
- malformed JSON;
- unexpected schema.

OpenRouter:
- success;
- timeout;
- malformed → fallback.

## Scenario
Happy path through actual dispatcher with fake MAX gateway.

Manual flow.

FNS unavailable flow.

Zero result flow.

Restart simulation:
- state persisted in DB;
- new application instance continues.

---

# 42. CODE QUALITY

Ruff:
- formatting;
- lint.

Mypy:
- strict-ish for domain/application;
- exceptions allowed around third-party untyped payloads.

Functions:
- small;
- typed;
- no mega handlers.

Avoid:
- God class;
- global mutable singleton state;
- circular imports;
- raw dicts across all layers.

Use Pydantic DTO at external boundary, dataclasses/value objects in domain where useful.

---

# 43. MAKEFILE COMMANDS

Реализовать:

```text
make build
make up
make down
make restart
make logs
make ps
make migrate
make seed-demo
make validate-data
make import-data
make test
make test-unit
make test-integration
make lint
make format
make typecheck
make max-smoke
make webhook-register
make webhook-list
make webhook-delete
```

README должен объяснить каждую.

---

# 44. MAX SMOKE

`make max-smoke`:
- читает env;
- calls `/me`;
- выводит:
  - bot user id;
  - username;
  - display name;
- не выводит token.

Если 401:
- понятная диагностика.

Если DNS/cert:
- понятная диагностика.

---

# 45. BOT COMMANDS

При старте/регистрации по возможности выставить команды через актуальный MAX API:

```text
/start — начать подбор
/profile — мой профиль
/checklist — мои документы
/help — помощь
/reset — удалить сохранённые данные
```

Если установка commands требует отдельного API action, реализовать отдельный CLI:
`python -m navigator.entrypoints.configure_bot`.

---

# 46. PRODUCTION DEPLOYMENT

README VPS flow:

1. Ubuntu server with Docker Engine + compose plugin.
2. clone repository.
3. copy `.env.example` → `.env`.
4. fill secrets.
5. DNS A record.
6. set `MAX_TRANSPORT=webhook`.
7. set public domain.
8. `docker compose -f compose.yml -f compose.prod.yml up -d --build`.
9. wait health.
10. register webhook.
11. verify subscription.
12. send `/start`.
13. inspect logs.

Backup:
- documented `pg_dump`;
- named volume backup note.

Upgrade:
1. pull;
2. build;
3. migrations;
4. rolling-ish restart;
5. health check.

---

# 47. MINI-APP: ТОЛЬКО ПОСЛЕ БОТА

После acceptance бота:

Отдельный frontend container, например:
- React/Vite;
- MAX UI;
- MAX Bridge.

Но только:
1. screen Compare;
2. screen Details;
3. add/remove checklist via backend;
4. exactly two measure IDs.

Mini-app не имеет:
- onboarding;
- INN form;
- own catalog;
- investors;
- separate profile DB.

Backend будет single source of truth.

До mini-app заранее создать только:
```python
class ComparisonLinkBuilder:
    ...
```

Feature flag.

---

# 48. MINI-APP SECURITY ROADMAP

Когда будет реализовано:
- не доверять `user_id` из query;
- валидировать launch/init data согласно MAX Bridge/официальной схеме;
- backend authorizes user;
- measure IDs validate;
- no arbitrary internal DB access.

---

# 49. README ОБЯЗАТЕЛЬНО ДОЛЖЕН СОДЕРЖАТЬ

1. Product overview.
2. Why bot-first.
3. Architecture Mermaid.
4. Repository layout.
5. Local quick start.
6. MAX polling.
7. MAX webhook production.
8. Environment variables.
9. Database migrations.
10. Seed demo.
11. Import real measures.
12. FNS integration limitation.
13. Manual fallback.
14. OpenRouter off by default.
15. Checklist.
16. Reminders.
17. Testing.
18. VPS deployment.
19. Security.
20. Known limitations.
21. Mini-app roadmap.
22. Explicit statement:
   - measure/course database is manually curated;
   - not live МСП.РФ API;
   - FNS is separate profile enrichment integration.

---

# 50. ARCHITECTURE DIAGRAM

README Mermaid:

```mermaid
flowchart TD
    MAX[MAX User] --> MAXAPI[MAX Platform]
    MAXAPI --> BOT[Bot/API Container]

    BOT --> APP[Application Services]
    APP --> MATCH[Deterministic Matching]
    APP --> DB[(PostgreSQL)]
    APP --> REDIS[(Redis)]
    APP --> FNS[FNS Adapter]
    APP --> EXPLAIN[Explanation Provider]

    FNS --> RMSP[Public FNS/RMSP source]
    EXPLAIN --> TEMPLATE[Template]
    EXPLAIN -. feature flag .-> OR[OpenRouter]

    WORKER[Worker Container] --> DB
    WORKER --> MAXAPI

    CADDY[Caddy HTTPS] --> BOT

    MINI[Future Mini App] -. later .-> BOT
```

---

# 51. IMPLEMENTATION PHASES

> **Skill rule for all phases:** PHASE 0–9 выполняются внутри одного `$ultragoal`. `$team` разрешён только для независимых lanes. `$best-practice-research` вызывается только в фазах, явно отмеченных ниже. Обычные lint/tests не требуют отдельного heavyweight skill.


## PHASE 0 — Foundation

Создать repo, Docker, config, FastAPI, PostgreSQL, Redis, Alembic, health.

Definition:
```bash
docker compose up --build
curl localhost:8000/health/live
curl localhost:8000/health/ready
```
успешны.

## PHASE 1 — Real MAX smoke

**Перед реализацией:** выполнить один bounded `$best-practice-research` по актуальным official MAX Bot API docs и сохранить подтверждённые детали в project wiki, если `$wiki` доступен.

- MaxApiClient;
- auth;
- `/me`;
- polling;
- dispatcher;
- `/start`;
- `/help`;
- buttons.

Definition:
реальный бот отвечает в MAX.

## PHASE 2 — Persistence/FSM/manual onboarding

После завершения и зелёных тестов выполнить targeted `$code-review` по persistence, transaction boundaries, FSM consistency и data deletion semantics.

Definition:
полный manual profile и restart persistence.

## PHASE 3 — Data/matching/demo measures

Definition:
manual profile → 1–3 demo recommendations.

## PHASE 4 — FNS lookup

Перед реализацией выполнить `$best-practice-research` по актуальным официальным данным ФНС/РМСП и фактическому lookup source. После реализации выполнить `$code-review` на timeouts, schema drift, caching, privacy и fallback.

Definition:
FOUND / NOT_FOUND / UNAVAILABLE работают отдельно.

## PHASE 5 — Details/checklist

После реализации выполнить `$code-review` с фокусом на idempotency, concurrent toggles, transactions и ownership.

Definition:
add → docs → toggle → restart.

## PHASE 6 — feedback/courses/investor/analytics

Definition:
flows работают.

## PHASE 7 — Webhook + production

Перед реализацией выполнить `$best-practice-research` по MAX webhook contract и production hardening. После реализации обязательно выполнить `$code-review` с фокусом на authentication, trust boundaries, replay/idempotency, secrets, Caddy и exposed ports.

Definition:
Caddy HTTPS + webhook + idempotency.

## PHASE 8 — Reminder worker

Definition:
test deadline produces one notification, no duplicates.

## PHASE 9 — OpenRouter optional

Если актуальный OpenRouter contract ещё не подтверждён в wiki/project docs — выполнить bounded `$best-practice-research`. После реализации провести privacy-focused `$code-review`: никакой ИНН/MAX user id/contact data не уходит во внешний LLM.

Definition:
enabled works, disabled no change, failure fallback.

## PHASE 10 — mini-app

Только после bot acceptance.

---

# 52. ACCEPTANCE TEST MATRIX

### Startup
- fresh compose works
- migrations work
- seed works
- no host DB needed

### MAX
- token env only
- `/start`
- `/help`
- callbacks
- repeated callback safe

### INN
- format
- checksum
- found
- not found
- unavailable
- rate limit
- cache
- manual fallback

### Profile
- manual
- FNS
- persisted
- editable
- `/profile`

### Matching
- correct hard filters
- expired hidden
- inactive hidden
- max 3
- deterministic
- explain reasons

### Checklist
- add
- no duplicate
- docs
- progress
- remove confirmation
- persistence

### Feedback
- all reasons
- free text

### Investors
- once
- decline never repeats

### Reset
- confirmation
- actual deletion

### Resilience
- Redis temporary outage gives controlled degradation where possible
- FNS outage no crash
- OpenRouter outage no crash
- duplicated event no duplicate side effects

### Deployment
- production compose
- webhook secret
- no DB/Redis exposed
- health
- restart

---

# 53. LOAD / SCALABILITY DECISIONS

Этот MVP должен быть не «костылём», а базой для дальнейшего роста.

Поэтому:
- stateless HTTP/webhook app;
- PostgreSQL source of truth;
- Redis ephemeral;
- async clients;
- pooling;
- indexes;
- adapter interfaces;
- worker separate;
- deterministic matching;
- no in-process session dependency;
- no local files as operational DB;
- no giant singleton state;
- no hard-coded measure conditions in Python.

При росте можно:
- масштабировать bot replicas;
- managed PostgreSQL;
- Redis managed;
- outbox;
- queue;
- separate importer;
- full FNS snapshot;
- mini-app frontend;
без переписывания domain model.

---

# 54. ЧТО НЕ ДЕЛАТЬ

Запрещено:

1. Всё в одном `main.py`.
2. Всё в одном Docker container.
3. SQLite вместо Postgres.
4. State только в memory.
5. Business rules inside button handlers.
6. Hard-coded measures in Python.
7. LLM eligibility.
8. Fake real government programs.
9. Infinite retry.
10. No timeouts.
11. `except Exception: pass`.
12. Secrets in repository.
13. Logging token/contacts.
14. Redis as permanent profile DB.
15. Mini-app first.
16. Catalog-first UX.
17. Scraping МСП.РФ on every user request.
18. Assuming unofficial FNS endpoint is stable.
19. Sending raw INN to OpenRouter.
20. Claiming support is guaranteed.
21. Ignoring duplicate MAX events.
22. Manual DB editing required for normal startup.
23. Requiring local Python/Postgres install outside Docker for the normal path.
24. Leaving tests broken.
25. Leaving migrations missing.

---

# 55. ПЕРВЫЙ DEMO, КОТОРЫЙ ДОЛЖЕН БЫТЬ ГОТОВ

После реализации команда должна иметь возможность:

```bash
cp .env.example .env
# вставить MAX token
docker compose up -d --build
make migrate
make seed-demo
make max-smoke
```

Затем в MAX:

```text
/start
→ Начать подбор
→ Заполнить вручную
→ Москва
→ ООО
→ IT и цифровые услуги
→ До 1 года
→ 2–15 сотрудников
→ Подтвердить
→ получить 1–3 DEMO меры
→ Подробнее
→ Добавить
→ /checklist
→ отметить документ
```

После:
```bash
docker compose restart bot
```

`/profile` и `/checklist` должны остаться.

---

# 56. ПОСЛЕДНЯЯ ИНСТРУКЦИЯ CODEX

Теперь реализуй проект полностью.

Не выдавай мне только код в ответе — создавай/изменяй файлы репозитория и запускай команды в рабочей среде.

Порядок:
1. проанализируй эту спецификацию;
2. составь внутренний список задач;
3. создай структуру;
4. реализуй Phase 0;
5. запусти;
6. исправь ошибки;
7. двигайся фазами;
8. после каждой фазы запускай тесты;
9. не переходи к mini-app;
10. в конце выполни полный acceptance smoke test.

Если реальный MAX API contract отличается от предположенного payload:
- открой актуальную официальную документацию `dev.max.ru`;
- адаптируй client;
- сохрани внешнюю разницу внутри infrastructure adapter;
- не меняй domain/application архитектуру.

Если публичная FNS web-витрина не отвечает либо изменилась:
- не ломай проект;
- реализуй `TEMPORARILY_UNAVAILABLE`;
- сохрани manual onboarding;
- tests должны проходить через mock.

Перед завершением обязательно:

**Skill quality gate в указанном порядке:**
1. `$ai-slop-cleaner` — один проход без изменения product semantics;
2. полный lint/tests после cleanup;
3. `$code-review` — architecture + security + concurrency + reliability;
4. `$ultraqa` — adversarial end-to-end loop до зелёного результата;
5. `$final-check` — финальный evidence-based release gate.

После этого фактически выполнить:
- `docker compose build`;
- `docker compose up -d`;
- migrations;
- seed demo;
- lint;
- tests;
- health checks;
- убедиться, что в git-tracked файлах нет секретов;
- сформировать README с точными командами;
- вывести финальный отчёт: что реализовано, какие команды запуска, какие env нужно заполнить, какие ограничения остались.

**Definition of Done:** проект можно перенести на обычный Ubuntu VPS с Docker, заполнить `.env`, выполнить documented commands и получить рабочего MAX-бота без архитектурных переделок.
