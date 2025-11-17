# Telegram Sales Bot - Complete Flow Guide

## Overview
This bot acts as a mentor/friend that guides users through a structured conversation, adapts based on their responses, compels them to purchase, and then provides post-purchase guidance on building their system.

---

## Pre-Sale Flow (Automatic Adaptive Conversation)

### `/start` Command
- **First Time**: "What's the one thing about yourself right now that you want to change?"
- **Returning**: "How have things been since we last talked?"

### Conversation Phase (5 Interactive Messages)
The bot **adapts responses dynamically** based on keyword detection:

**User concern types automatically detected:**
- **Stuck** (stagnant, plateau, same place)
- **Motivation** (discipline, lazy, willpower)
- **Goals** (achieve, success, dream)
- **Procrastination** (delay, tomorrow, start)
- **Fear** (scared, anxious, afraid)
- **Money** (income, business, career)
- **Relationships** (partner, people, social)
- **Health** (weight, fitness, gym)
- **Time** (busy, overwhelm, stress)
- **Confidence** (doubt, imposter, not good enough)

### Natural Progression (Mentorship Tone)
1. **Message 1**: Empathetic question based on their concern
2. **Message 2**: Deeper diagnosis about mindset
3. **Message 3**: Introduce the 5-step framework (Clarity, Belief, Failure, Systems, Momentum)
4. **Message 4**: Present the blueprint solution
5. **Message 5**: Share product details and pricing, show buttons for purchase decision

### Buttons After Message 5
- 🔥 "Yes, let's go" → Payment flow
- "I have questions" → Continue conversation loop
- "Need time to think" → End conversation (can resume with /start)

---

## Payment & PDF Access

### Payment Flow
1. User clicks "Yes, let's go"
2. Bot shows Paystack link in compelling message
3. User completes payment
4. User marks payment as complete
5. Bot confirms purchase and directs to check email for PDF

### PDF Content
Include this message at the **END of your PDF**:

```
🔗 **Got value from this? Let's go deeper.**

Click here to continue: t.me/YOUR_BOT_USERNAME?start=pdf_redirect

We'll transform this knowledge into your personal system. 💪
```

---

## Post-Purchase Flow

### After User Reads PDF
User either:
- Clicks the link in the PDF, or
- Types `/done`

### PDF Feedback Phase
**Bot asks:** "What part of the PDF hit you the hardest? What made you go 'yeah, that's exactly me'?"

**User responds** with their key insight, which the bot records.

### Focus Area Selection
Bot asks user to identify their biggest friction point:
- **A) Clarity** — Not 100% sure what I'm working toward
- **B) Belief** — I know what to do but doubt kills me
- **C) Failure** — I'm scared to try because I might fail
- **D) Systems** — I rely on willpower instead of design
- **E) Momentum** — I start strong but can't keep it going

### Personalized Exercises (Based on Choice)

**A - North Star Exercise (Clarity)**
- Complete: "In 5 years, I want to be known as someone who..."
- Reflection: Does this excite you or are you trying to impress someone?

**B - Evidence Inventory (Belief)**
- Write down ONE limiting belief
- List 3 times you PROVED it wrong
- Bot helps demolish the lie with facts

**C - MVE Challenge (Failure)**
- Pick ONE goal you've been avoiding
- What's the smallest step in the next 2 hours?
- What's the worst that happens if it fails?
- What do you learn even if it fails?

**D - If-Then Builder (Systems)**
- Complete: "If [trigger], then I will [specific action]"
- Example: "If I pour coffee, then I journal for 5 min"
- Specificity is key

**E - Small Win Ritual (Momentum)**
- Pick the SMALLEST action you can do today
- After completion, say: "I did what I said. That's who I am."
- Trains brain to link completion with identity

### System Building Response
Bot provides encouragement and sets expectations:
- Run the experiment
- Track what happens
- Come back to report

**3-Day Automatic Check-ins Begin**

---

## Automated 3-Day Check-Ins

Bot sends check-ins at days 3, 6, 9, 12, etc. with progressively deeper questions:

### Check-in #1 (Day 3)
"How'd the experiment go? What did you try? What happened? What did you learn?"

### Check-in #2 (Day 6)
"Any shifts yet? What's working? What's still hard? What needs adjusting?"

### Check-in #3 (Day 9)
"This is where people either quit or level up. Are you still showing up?"

### Check-in #4 (Day 12)
"Two weeks down! What's the biggest shift? What's becoming automatic? What's next?"

### Ongoing (Day 15+)
"How are things going? Still building momentum or hitting walls?"

---

## Manual Check-In Command

Users can type `/checkin` anytime to trigger adaptive response:
- **Good progress**: Celebrate, encourage next level
- **Struggling**: Troubleshoot, offer framework options
- **Quitting thoughts**: Compassionate push to continue
- **General update**: Reinforce consistency and small daily actions

---

## Helper Commands

- `/start` — Begin or restart conversation
- `/done` — Finished reading PDF
- `/checkin` — Manual check-in
- `/help` — Show commands
- `/cancel` — End chat

---

## Key Design Principles

### 1. **Adaptive Responses**
- Bot detects user's core concern from keywords
- Tailors messaging to their specific friction point
- Never feels generic or salesy

### 2. **Mentor/Friend Tone**
- Honest, direct language
- Empathetic but challenging
- Uses "I/you" language, not "this program"
- Celebrates small wins
- Acknowledges struggle as growth

### 3. **Natural Progression to Sales**
- Only after deep rapport built (5 messages in)
- Solution naturally emerges from conversation
- Pricing positioned as "less than two coffees"
- Buttons give user control (not pushy)

### 4. **Post-Purchase Guidance**
- Continues mentor relationship
- Provides specific exercises (not vague advice)
- Regular accountability check-ins
- Responsive to user's actual progress

### 5. **Data Collection**
- Tracks user concerns, responses, and progress
- Stored in `user_data.json`
- Allows personalization across sessions

---

## User Data Structure (user_data.json)

```json
{
  "user_id": {
    "first_name": "John",
    "initial_concern": "I feel stuck",
    "concern_type": "stuck",
    "purchased": true,
    "purchase_date": "2024-11-17 10:00:00",
    "pdf_feedback": "The systems section really hit home",
    "focus_area": "D",
    "exercise_response": "If I finish my coffee, then I journal for 5 minutes",
    "last_interaction": "2024-11-17 15:30:00",
    "check_in_count": 2,
    "started_at": "2024-11-17 09:00:00"
  }
}
```

---

## Setup Instructions

1. **Get Bot Token**: Create bot with @BotFather on Telegram
2. **Replace TOKEN**: Update line 596 with your bot token
3. **Replace USERNAME**: In PDF_REDIRECT_MESSAGE.txt, replace `YOUR_BOT_USERNAME`
4. **Update PAYSTACK_LINK**: Insert your actual Paystack payment link (line 25)
5. **Run**: `python BOT.py`

---

## Flow Summary

```
/start 
  ↓
Conversation (5 dynamic messages)
  ↓
Payment Decision (buttons)
  ↓
Payment + PDF Delivery
  ↓
User Reads PDF (clicks link or /done)
  ↓
PDF Feedback → Focus Area → Exercise
  ↓
System Building Response
  ↓
3-Day Check-ins (Ongoing Mentorship)
  ↓
Adaptive Responses (based on user progress)
```

---

## Customization Notes

- **Messages**: Edit concern_responses dict in `handle_conversation()` method
- **Exercises**: Modify exercises dict in `focus_area()` method
- **Check-in Messages**: Edit messages list in `send_checkin()` method
- **Tone**: Change language throughout while keeping adaptive structure
- **Pricing**: Update in message_5 section of `handle_conversation()`
