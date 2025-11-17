# Quick Start Guide - 10 Question Exchange Bot

## What's New?

Your bot now asks **exactly 10 personalized questions** to each user before introducing the digital PDF. This builds deep rapport and makes the sale feel natural.

---

## The Flow (Simple Version)

1. User starts bot → tells their main concern
2. Bot asks 10 customized questions back-and-forth
3. After 10 exchanges → bot introduces the PDF
4. User decides to buy (or asks more questions)

---

## Test It Now

```
1. Run: python BOT.py
2. Open Telegram, find your bot
3. Type: /start
4. Share a concern like "I'm stuck in my career"
5. Keep responding to the 10 questions
6. After question 10 → see the sales pitch
```

---

## Key Files

| File | What It Is |
|------|-----------|
| `BOT.py` | The main bot (completely rewritten) |
| `10_QUESTION_EXCHANGE_GUIDE.md` | Deep dive into how it works |
| `IMPLEMENTATION_SUMMARY.md` | Technical overview of changes |
| `user_data.json` | Stores all user responses (auto-generated) |

---

## Customize the Questions

### Find the Questions
In `BOT.py`, around line 37:
```python
self.question_sequences = {
    'stuck': [
        "Question 1...",
        "Question 2...",
        # ... 10 questions
    ],
    'money': [ ... ],
    'fear': [ ... ],
    # etc
}
```

### Edit a Question
Change any question to match your style:
```python
'stuck': [
    "Instead of this question",
    "Put your custom question here",  # ← Edit this
    # ...
]
```

### Add a New Concern Type
```python
'custom_concern': [
    "Question 1?",
    "Question 2?",
    # ... 10 questions total
]
```

Then in `adapt_response()` method, add:
```python
elif any(word in text_lower for word in ['keyword1', 'keyword2']):
    return 'custom_concern'
```

---

## The Sales Pitch (After 10 Questions)

After the 10th exchange, bot shows:
```
Okay [name], I've learned a lot about where you are.

Here's what's clear: your challenge isn't about trying harder 
or knowing more. It's about the right framework.

I've built exactly that. It's called 'Unleash Your Ultimate Mindset'...

Investment: GHS 75 ($6.85) — less than two coffees.

Ready to actually change this?

[🔥 Yes, let's go] [I have one more question] [Need time to think]
```

---

## Track User Responses

All user responses are saved in `user_data.json`:
```json
{
  "user_id": {
    "user_responses": [
      "I feel stuck",
      "In my career",
      "I tried...",
      // ... 10 total
    ]
  }
}
```

You can read this to see what users said during the 10 exchanges.

---

## Common Customizations

### 1. Change Price
Find: `**Investment:** GHS 75 ($6.85)`
Change to: `**Investment:** GHS 100 ($8.50)`

### 2. Change Product Name
Find: `'Unleash Your Ultimate Mindset'`
Change to: `'Your Product Name'`

### 3. Change to 15 Questions Instead of 10
Find: `if exchange_count < 10:`
Change to: `if exchange_count < 15:`

(Make sure your question arrays have 15 items)

### 4. Skip a Question Type
In `__init__`, comment out:
```python
# 'fear': [...]  # No longer ask fear-based questions
```

---

## Troubleshooting

**Q: Bot keeps asking the same question**
A: Check that exchange_count is incrementing. Look in `user_data.json` for your user ID.

**Q: Bot shows sales pitch too early**
A: Make sure your questions array has exactly 10 items.

**Q: Questions don't match my concern**
A: Edit `adapt_response()` method to detect your keywords.

---

## Contact Points to Update

1. **Paystack Link** (line 25): Update payment link
2. **Bot Token** (line 671): Use your actual bot token
3. **Questions** (lines 37-122): Customize for your niche
4. **Price** (in sales pitch message): Update your pricing
5. **Product Name** (in sales pitch message): Your product

---

## Data You Can Extract

After users go through the flow:
- What concern type are most users?
- What questions do they answer differently?
- At which question do most people drop off?
- What responses predict purchase?

This helps you optimize questions over time.

---

## How to Deploy

1. Update all customization points above
2. Test with /start (ask a question, answer the 10 questions)
3. Verify user_data.json saves responses
4. Check Paystack link works
5. Deploy to your server/hosting

---

## Still Have Questions?

See:
- `10_QUESTION_EXCHANGE_GUIDE.md` - Full documentation
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- `BOT_FLOW_GUIDE.md` - Original flow documentation

