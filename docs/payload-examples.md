# Примеры dashboard payload и API responses

Снимок документации: 2026-07-05.

Это компактные синтетические примеры, а не полный dump. Source of truth:

```text
anki_study_report/dashboard_payload.py
web-dashboard/src/types/report.ts
tests/test_dashboard_payload.py
```

## Minimal valid `StudyReport`

```json
{
  "metadata": {
    "title": "Anki Study Report",
    "period": "Все время",
    "selectedDecks": ["Все колоды"],
    "includeChildren": true,
    "answerMode": "pass_fail",
    "createdAt": "2026-07-05 17:00",
    "detailMode": "normal",
    "deletedCardReviews": 0,
    "unavailableTrackerNotes": [],
    "reportSchemaVersion": 2,
    "cardLevelSchemaVersion": 2,
    "cardLevelSource": "fresh"
  },
  "summary": {
    "verdict": "Отчет готов.",
    "riskLevel": "neutral",
    "mainAction": "Продолжайте текущий режим.",
    "warning": "Критичных проблем не найдено.",
    "newCardsAdvice": "Новые карточки в норме."
  },
  "kpis": [],
  "answerDistribution": [],
  "activity": {
    "available": false,
    "activeDays": 0,
    "missedDays": 0,
    "currentStreak": 0,
    "bestStreak": 0,
    "bestDay": "",
    "weekdayAverage": [],
    "days": []
  },
  "decks": [],
  "attentionCards": [],
  "attentionCardsStatus": {
    "status": "available",
    "scannedCards": 0,
    "returnedCards": 0,
    "source": "fresh"
  },
  "noteTypeCatalog": [],
  "forecast": {
    "available": false,
    "tomorrow": 0,
    "next7Days": 0,
    "next30Days": 0,
    "activeDayBaseline": 0,
    "overloadRisk": "neutral",
    "daily": [],
    "recommendation": ""
  },
  "fsrs": {
    "predictedRecall": null,
    "cardsBelowTarget": 0,
    "highForgettingRisk": 0,
    "averageDifficulty": null,
    "futureLoad30Days": 0,
    "settings": {
      "enabled": false,
      "desiredRetention": null,
      "helperDetected": false,
      "helperConfigAvailable": false,
      "rescheduleEnabled": false,
      "autoDisperse": false
    }
  },
  "recommendations": {
    "mainAction": "",
    "why": "",
    "avoid": "",
    "checklist": []
  },
  "cache": {
    "status": "empty",
    "updatedAt": 0,
    "cachedDays": 0,
    "cachedDeckDays": 0
  }
}
```

## Payload с основными блоками

```json
{
  "summary": {
    "verdict": "Сегодня качество нормальное.",
    "riskLevel": "good",
    "mainAction": "Повторить проблемные карточки.",
    "warning": "Again ниже порога.",
    "newCardsAdvice": "Можно добавить немного новых."
  },
  "kpis": [
    {
      "id": "pass_rate",
      "label": "Pass rate",
      "value": "87%",
      "caption": "Pass/Fail mode",
      "status": "good",
      "icon": "check"
    }
  ],
  "answerDistribution": [
    { "label": "Pass", "value": 87, "color": "#67d391" },
    { "label": "Fail", "value": 13, "color": "#ef6f6c" }
  ],
  "activity": {
    "available": true,
    "activeDays": 5,
    "missedDays": 2,
    "currentStreak": 3,
    "bestStreak": 14,
    "bestDay": "2026-07-04",
    "weekdayAverage": [{ "day": "Mon", "reviews": 42, "activeRate": 0.8 }],
    "days": [{ "date": "2026-07-05", "reviews": 60, "newCards": 5, "again": 4, "pass": 56, "fail": 4 }]
  },
  "decks": [
    {
      "id": 1,
      "name": "Japanese::N5",
      "totalReviews": 60,
      "newCards": 5,
      "passCount": 56,
      "failCount": 4,
      "hardCount": 8,
      "easyCount": 10,
      "passRate": 0.93,
      "failRate": 0.07,
      "averageAnswerSeconds": 4.2,
      "studyMinutes": 18,
      "status": "good",
      "explanation": "Стабильная колода."
    }
  ]
}
```

## `attentionCards` + `attentionCardsStatus`

```json
{
  "attentionCards": [
    {
      "cardId": 123,
      "noteId": 456,
      "deckName": "Japanese::N5",
      "frontPreview": "要望",
      "issues": ["repeated_again", "missing_audio"],
      "riskScore": 72,
      "againCount": 3,
      "lapses": 1,
      "averageAnswerSeconds": 15.4,
      "passRate": 0.5,
      "lastReviewedAt": "2026-07-05T10:30:00",
      "searchQuery": "cid:123"
    }
  ],
  "attentionCardsStatus": {
    "status": "available",
    "scannedCards": 180,
    "returnedCards": 1,
    "collectorRan": true,
    "collectionAvailable": true,
    "source": "fresh",
    "issueCounts": {
      "repeatedAgain": 1,
      "missingAudio": 1
    },
    "thresholds": {
      "repeatedAgainThreshold": 2,
      "slowAnswerSeconds": 10,
      "lowPassRateThreshold": 0.6,
      "leechLapsesFallback": 8,
      "maxResults": 100
    }
  }
}
```

## `renderedPreview`

```json
{
  "renderedPreview": {
    "frontHtml": "<span class=\"word-focus\">要望</span><img src=\"/api/media?name=%E8%A6%81.gif\">",
    "backHtml": "<span>request</span>",
    "frontPlainText": "要望",
    "backPlainText": "request",
    "css": ".word-focus { color: red; }",
    "mediaRefs": [
      {
        "name": "要.gif",
        "type": "image",
        "url": "/api/media?name=%E8%A6%81.gif"
      }
    ],
    "cardOrd": 0,
    "cardId": 123,
    "renderSource": "anki_native",
    "renderStatus": "available"
  }
}
```

`renderSource` может быть `anki_native` или `anki_like_fallback`. Frontend type
также допускает string для будущих источников.

## Cache summary

```json
{
  "cache": {
    "status": "ready",
    "dataSource": "mixed",
    "usedFor": ["activity", "comparison"],
    "version": 2,
    "updatedAt": 1783260000,
    "lastRevlogId": 987654321,
    "cachedDays": 120,
    "cachedDeckDays": 360,
    "isBuilding": false,
    "fallbackReason": null,
    "limitations": [
      "Deck daily aggregates use the card's current deck, not necessarily the historical deck at review time."
    ]
  }
}
```

## Forbidden/error response для неверного token

Подтверждено `dashboard_server.py`:

```json
{
  "error": "invalid_dashboard_token",
  "ok": false,
  "message": "Недействительная ссылка dashboard. Откройте dashboard из Anki Study Report."
}
```

HTTP status: `403`.

## Media URL pattern

Backend отдает media через:

```text
/api/media?name=<encoded-media-name>&token=<dashboard-token>
```

`mediaRefs` в payload обычно хранят URL без token:

```text
/api/media?name=front.gif
```

Frontend добавляет token при рендере preview.
