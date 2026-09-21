# Bot UX Design

Bot-first means the first useful screen is a MAX dialog, not a catalog.

Initial bot states:

- `/start`: short welcome, primary action `Начать`, secondary action `Как это работает?`.
- Profile input: primary path asks for ИНН; secondary path starts manual questionnaire.
- Error states must be short, actionable, and mobile-friendly: invalid ИНН, company not found, FNS temporarily unavailable.
- Measure card actions: `Подробнее`, `Добавить в чек-лист`, and navigation through recommendations.
- Checklist actions: one button per document state toggle, plus back to recommendations.

Do not add mini-app UX here until the bot acceptance path is green.
