# Canteen Menu Bot - System Documentation

## Overview

This Rasa-based chatbot helps users check the daily menu at university canteens in Berlin. The bot supports three
canteens (Hardenbergstrasse, Marchstrasse, Vegan Mensa) and allows users to browse menu categories interactively.

---

## System Flowchart

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER STARTS                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INITIAL USER INPUT                                  │
│                                                                             │
│  User can say:                                                              │
│  • Greeting ("Hello", "Hi")                                                 │
│  • Menu request ("What's for lunch?", "Show me the menu")                   │
│  • Menu + Canteen ("Menu at Hardenbergstrasse")                             │
│  • Menu + Canteen + Date ("Vegan menu for tomorrow")                        │
│  • Goodbye ("Bye")                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                ┌─────────────────────┼─────────────────────┐
                │                     │                     │
                ▼                     ▼                     ▼
┌───────────────────────┐ ┌─────────────────────┐ ┌───────────────────────┐
│      GREETING         │ │    MENU REQUEST     │ │       GOODBYE         │
│                       │ │                     │ │                       │
│ Bot: "Hey! How can I  │ │  (See Menu Flow     │ │ Bot: "Bye! Have a     │
│  help you today?"     │ │   below)            │ │  nice meal!"          │
│                       │ │                     │ │                       │
│ → Wait for next input │ │                     │ │ → End conversation    │
└───────────────────────┘ └─────────────────────┘ └───────────────────────┘
```

---

## Menu Request Flow (Detailed)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MENU REQUEST RECEIVED                              │
│                                                                             │
│  Intent: ask_canteen_menu                                                   │
│  Possible entities: canteen, date                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                        ┌─────────────────────────┐
                        │  Is CANTEEN slot set?   │
                        │                         │
                        │  Check: canteen entity  │
                        │  or existing slot value │
                        └─────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ NO                                │ YES
                    ▼                                   ▼
┌───────────────────────────────────┐   ┌───────────────────────────────────┐
│      ASK FOR CANTEEN              │   │      CANTEEN IDENTIFIED           │
│                                   │   │                                   │
│ Bot: "Which canteen would you     │   │ Resolve canteen name to ID:       │
│  like to check? Available:        │   │ • hardenbergstrasse → 1004        │
│  Hardenbergstrasse, Marchstrasse, │   │ • marchstrasse → 1010             │
│  or Vegan."                       │   │ • vegan → 2456                    │
│                                   │   │                                   │
│ Set: awaiting_canteen = true      │   │                                   │
└───────────────────────────────────┘   └───────────────────────────────────┘
                    │                                   │
                    ▼                                   │
┌───────────────────────────────────┐                   │
│      WAIT FOR CANTEEN INPUT       │                   │
│                                   │                   │
│ User can say:                     │                   │
│ • "Hardenbergstrasse"             │                   │
│ • "The vegan one"                 │                   │
│ • "March" (alias)                 │                   │
└───────────────────────────────────┘                   │
                    │                                   │
                    ▼                                   │
        ┌───────────────────────┐                       │
        │ Is canteen valid?     │                       │
        └───────────────────────┘                       │
                    │                                   │
        ┌───────────┴───────────┐                       │
        │ NO                    │ YES                   │
        ▼                       ▼                       │
┌─────────────────┐   ┌─────────────────┐               │
│ INVALID CANTEEN │   │ SET CANTEEN     │               │
│                 │   │                 │               │
│ Bot: "I didn't  │   │ Bot: "Got it,   │               │
│  recognize that │   │  checking       │               │
│  canteen..."    │   │  [name]."       │               │
│                 │   │                 │               │
│ → Loop back to  │   │ Set slot and    │               │
│   waiting       │   │ continue        │───────────────┤
└─────────────────┘   └─────────────────┘               │
                                                        │
                                                        ▼
                              ┌─────────────────────────────────────┐
                              │        CHECK DATE SLOT              │
                              │                                     │
                              │ Is menu_date set?                   │
                              │ • YES → Use provided date           │
                              │ • NO → Default to today's date      │
                              └─────────────────────────────────────┘
                                                        │
                                                        ▼
                              ┌─────────────────────────────────────┐
                              │         FETCH MENU FROM API         │
                              │                                     │
                              │ POST to stw.berlin API              │
                              │ Parameters: resources_id, date      │
                              └─────────────────────────────────────┘
                                                        │
                          ┌─────────────────────────────┼─────────────────────────────┐
                          │                             │                             │
                          ▼                             ▼                             ▼
              ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
              │    FETCH ERROR      │     │    PARSE ERROR      │     │   SUCCESS           │
              │                     │     │                     │     │                     │
              │ • Timeout           │     │ • Invalid HTML      │     │ Menu data received  │
              │ • Connection failed │     │ • No categories     │     │ and parsed          │
              │ • HTTP error        │     │   found             │     │                     │
              └─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                          │                             │                             │
                          ▼                             ▼                             ▼
              ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
              │ Bot: "Sorry, I      │     │ Bot: "Sorry, I      │     │ Check if menu has   │
              │  couldn't fetch     │     │  couldn't read      │     │ items               │
              │  the menu: [error]" │     │  the menu: [error]" │     │                     │
              │                     │     │                     │     │                     │
              │ → End flow, user    │     │ → End flow, user    │     │                     │
              │   can try again     │     │   can try again     │     │                     │
              └─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                                                                  │
                                                                    ┌─────────────┴─────────────┐
                                                                    │                           │
                                                                    ▼                           ▼
                                                      ┌─────────────────────┐     ┌─────────────────────┐
                                                      │   NO MENU ITEMS     │     │   MENU AVAILABLE    │
                                                      │                     │     │                     │
                                                      │ Bot: "No menu       │     │ Extract categories  │
                                                      │  available for      │     │ with items          │
                                                      │  [canteen] on       │     │                     │
                                                      │  [date]."           │     │                     │
                                                      └─────────────────────┘     └─────────────────────┘
                                                                                              │
                                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DISPLAY CATEGORIES                                                   │
│                                                                                                         │
│ Bot: "Menu for [Canteen] on [Date] has the following categories:                                        │
│       Vorspeisen, Salate, Suppen, Aktionen, Essen, Beilagen, Desserts                                   │
│                                                                                                         │
│       Which category would you like to see?"                                                            │
│                                                                                                         │
│ Set: awaiting_category = true                                                                           │
│ Set: available_categories = [list of category names]                                                    │
│ Set: cached_menu = [serialized menu JSON]                                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
                              ┌─────────────────────────────────────┐
                              │     WAIT FOR CATEGORY INPUT         │
                              │                                     │
                              │ User can say:                       │
                              │ • "Desserts"                        │
                              │ • "Show me Vorspeisen"              │
                              │ • "The salads please"               │
                              │ • "Essen" / "Main dishes"           │
                              └─────────────────────────────────────┘
                                                        │
                                                        ▼
                              ┌─────────────────────────────────────┐
                              │     IS CATEGORY RECOGNIZED?         │
                              │                                     │
                              │ Match against available_categories  │
                              │ (case-insensitive)                  │
                              └─────────────────────────────────────┘
                                                        │
                                          ┌─────────────┴─────────────┐
                                          │ NO                        │ YES
                                          ▼                           ▼
                              ┌─────────────────────┐     ┌─────────────────────┐
                              │ INVALID CATEGORY    │     │ SHOW CATEGORY       │
                              │                     │     │                     │
                              │ Bot: "I didn't      │     │ Deserialize cached  │
                              │  recognize that     │     │ menu, find category │
                              │  category.          │     │                     │
                              │  Available: ..."    │     │ Display items with: │
                              │                     │     │ • Name              │
                              │ → Loop back to      │     │ • Price             │
                              │   waiting           │     │ • Allergens         │
                              └─────────────────────┘     │ • Additives         │
                                                          └─────────────────────┘
                                                                      │
                                                                      ▼
                              ┌─────────────────────────────────────────────────┐
                              │              OFFER MORE OPTIONS                 │
                              │                                                 │
                              │ Bot: "Would you like to see another category?   │
                              │       Available: [categories]"                  │
                              │                                                 │
                              │ User can:                                       │
                              │ • Select another category → Loop back           │
                              │ • Ask for different canteen → New menu flow     │
                              │ • Ask for different date → Set date, new flow   │
                              │ • Say goodbye → End conversation                │
                              └─────────────────────────────────────────────────┘
```

---

## Correction and Recovery Flows

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     USER WANTS TO CHANGE CANTEEN                            │
│                                                                             │
│ At any point, user can say:                                                 │
│ • "Actually, show me Marchstrasse"                                          │
│ • "Switch to vegan canteen"                                                 │
│ • "Menu for Hardenbergstrasse instead"                                      │
│                                                                             │
│ → Bot recognizes canteen entity, starts new menu flow with new canteen      │
│ → Previous cached data is replaced                                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      USER WANTS TO CHANGE DATE                              │
│                                                                             │
│ At any point, user can say:                                                 │
│ • "Show me tomorrow's menu"                                                 │
│ • "What about next Monday?"                                                 │
│ • "Menu for 2026-01-25"                                                     │
│                                                                             │
│ → Bot sets menu_date slot                                                   │
│ → User needs to request menu again for new date to take effect              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      USER INPUT NOT RECOGNIZED                              │
│                                                                             │
│ When bot doesn't understand:                                                │
│                                                                             │
│ Canteen not recognized:                                                     │
│ → "I didn't recognize that canteen. Please choose from:                     │
│    Hardenbergstrasse, Marchstrasse, or Vegan."                              │
│                                                                             │
│ Category not recognized:                                                    │
│ → "I didn't recognize that category. Available categories are:              │
│    [list from current menu]"                                                │
│                                                                             │
│ General fallback:                                                           │
│ → Rasa's default fallback behavior                                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         START OVER / RESET                                  │
│                                                                             │
│ User can always:                                                            │
│ • Ask for menu again ("Show me the menu") → Fresh start                     │
│ • Specify new canteen → Overrides previous selection                        │
│                                                                             │
│ System reset happens when:                                                  │
│ • Session expires (60 minutes)                                              │
│ • action_reset_menu_slots is triggered                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Example Dialogues

### Ideal Flow - Full Path

```
User: Hello
Bot:  Hey! How can I help you today?

User: What's on the menu?
Bot:  Which canteen would you like to check? Available options:
      Hardenbergstrasse, Marchstrasse, or Vegan.

User: Hardenbergstrasse
Bot:  Got it, checking Hardenbergstrasse.
Bot:  Menu for Hardenbergstrasse on 2026-01-21 has the following categories:
      Vorspeisen, Salate, Suppen, Aktionen, Essen, Beilagen, Desserts

      Which category would you like to see?

User: Desserts
Bot:  **Desserts**

      • Marinierter Obstsalat - € 1,50/1,65/1,80
      • Bananen-Kokos-Joghurt - € 0,75/1,50/1,75
        Allergens: Milk and dairy products (incl. lactose)
      • Kokospudding - € 0,75/1,50/1,75
        Allergens: Soy

Bot:  Would you like to see another category? Available: Vorspeisen,
      Salate, Suppen, Aktionen, Essen, Beilagen, Desserts

User: Show me Essen
Bot:  **Essen**

      • 3 Gemüsebällchen in Kichererbsen-Kokos-Sauce - € 1,95/3,90/4,50
        Allergens: Wheat
      ...

User: Bye
Bot:  Bye! Have a nice meal!
```

### Quick Path - Canteen Specified Upfront

```
User: Menu at vegan canteen
Bot:  Menu for Vegan Mensa on 2026-01-21 has the following categories:
      Vorspeisen, Salate, Suppen, Essen, Beilagen, Desserts

      Which category would you like to see?

User: Suppen
Bot:  **Suppen**

      • Berliner Kartoffelsuppe mit Möhren - € 0,75/1,50/1,75
        Allergens: Celery, Mustard
```

### Error Recovery - Wrong Canteen

```
User: What's the menu at TU Mensa?
Bot:  Which canteen would you like to check? Available options:
      Hardenbergstrasse, Marchstrasse, or Vegan.

User: Berlin Mitte
Bot:  I didn't recognize that canteen. Please choose from:
      Hardenbergstrasse, Marchstrasse, or Vegan.

User: Marchstrasse
Bot:  Got it, checking Marchstrasse.
Bot:  Menu for Marchstrasse on 2026-01-21 has the following categories:
      ...
```

### Changing Selection Mid-Flow

```
User: Menu at Hardenbergstrasse
Bot:  Menu for Hardenbergstrasse on 2026-01-21 has the following categories:
      Vorspeisen, Salate, Suppen, Aktionen, Essen, Beilagen, Desserts

      Which category would you like to see?

User: Actually, show me Marchstrasse instead
Bot:  Got it, checking Marchstrasse.
Bot:  Menu for Marchstrasse on 2026-01-21 has the following categories:
      ...
```

### Date Specification

```
User: What's for lunch tomorrow at the vegan canteen?
Bot:  Setting menu date to tomorrow.
Bot:  Menu for Vegan Mensa on 2026-01-22 has the following categories:
      ...
```

---

## Decision Points Summary

| Decision Point     | Condition                          | Action                      |
|--------------------|------------------------------------|-----------------------------|
| Canteen needed?    | `canteen` slot is empty            | Ask user for canteen        |
| Canteen valid?     | Input matches known canteens       | Proceed / Ask again         |
| Date needed?       | `menu_date` slot is empty          | Default to today            |
| API fetch success? | HTTP 200, valid response           | Parse menu / Show error     |
| Menu has items?    | Categories with items exist        | Show categories / "No menu" |
| Category valid?    | Input matches available categories | Show items / Ask again      |

---

## Slots Reference

| Slot                   | Type | Purpose                        |
|------------------------|------|--------------------------------|
| `canteen`              | text | Selected canteen name          |
| `menu_date`            | text | Selected date (YYYY-MM-DD)     |
| `menu_category`        | text | Currently viewed category      |
| `awaiting_canteen`     | bool | Bot waiting for canteen input  |
| `awaiting_category`    | bool | Bot waiting for category input |
| `available_categories` | list | Categories in current menu     |
| `cached_menu`          | text | JSON-serialized menu data      |

---

## Supported Canteens

| Display Name      | Aliases                      | Resource ID |
|-------------------|------------------------------|-------------|
| Hardenbergstrasse | hardenberg, hardenbergstraße | 1004        |
| Marchstrasse      | march, marchstraße           | 1010        |
| Vegan Mensa       | vegan, veggie                | 2456        |
