import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
ONBOARDING_TIMEZONE, ONBOARDING_MORNING, ONBOARDING_EVENING, ONBOARDING_STYLE = range(4)
NS_PURPOSE_Q1, NS_PURPOSE_Q2, NS_PURPOSE_Q3, NS_PURPOSE_DRAFT, NS_VALUES, NS_IDENTITY = range(7, 13)
BELIEF_IDENTIFY, BELIEF_PROOF, BELIEF_COUNTER, BELIEF_REWRITE = range(14, 18)
MVE_GOAL, MVE_DESIGN, MVE_WORST, MVE_LEARNING = range(18, 22)
IFTHEN_GOAL, IFTHEN_FRICTION, IFTHEN_SOLUTION = range(22, 25)
CHECKIN_TOP3, CHECKIN_ENERGY, CHECKIN_CLARITY, CHECKIN_COMMITMENT = range(25, 29)
REFLECT_COMPLETION, REFLECT_WIN, REFLECT_TOMORROW = range(29, 32)

class UserData:
    DATA_DIR = "user_data"
    
    @classmethod
    def _ensure_dir(cls):
        if not os.path.exists(cls.DATA_DIR):
            os.makedirs(cls.DATA_DIR)
    
    @classmethod
    def save(cls, user_id: int, data: dict):
        cls._ensure_dir()
        filepath = os.path.join(cls.DATA_DIR, f"{user_id}.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    @classmethod
    def load(cls, user_id: int) -> dict:
        cls._ensure_dir()
        filepath = os.path.join(cls.DATA_DIR, f"{user_id}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return cls._get_default_user_data()
    
    @classmethod
    def _get_default_user_data(cls) -> dict:
        return {
            "user_id": None,
            "username": None,
            "first_name": None,
            "onboarding_complete": False,
            "timezone": "UTC",
            "morning_time": "08:00",
            "evening_time": "20:00",
            "communication_style": "mix",
            "start_date": None,
            "purpose": None,
            "values": [],
            "identity_statements": [],
            "goals": [],
            "limiting_beliefs": [],
            "belief_vault": [],
            "experiments": [],
            "total_experiments": 0,
            "completed_experiments": 0,
            "if_then_systems": [],
            "active_systems": 0,
            "daily_check_ins": [],
            "evening_reflections": [],
            "small_wins": [],
            "streak_current": 0,
            "streak_longest": 0,
            "last_check_in": None,
            "last_reflection": None,
            "total_wins_logged": 0,
            "chapters_completed": [],
            "last_qmr": None,
            "next_qmr": None,
        }

def get_user_greeting(style: str, name: str) -> str:
    greetings = {
        "direct": f"Let's go, {name}. 💪",
        "supportive": f"Hey {name}! You've got this! 🌟",
        "mix": f"Ready to level up, {name}? 🔥"
    }
    return greetings.get(style, greetings["mix"])

def calculate_streak(check_ins: List[dict]) -> tuple:
    if not check_ins:
        return 0, 0
    
    sorted_checkins = sorted(check_ins, key=lambda x: x.get('date', ''))
    current_streak = 0
    longest_streak = 0
    temp_streak = 1
    
    for i in range(len(sorted_checkins) - 1):
        current_date = datetime.fromisoformat(sorted_checkins[i]['date']).date()
        next_date = datetime.fromisoformat(sorted_checkins[i + 1]['date']).date()
        
        if (next_date - current_date).days == 1:
            temp_streak += 1
        else:
            longest_streak = max(longest_streak, temp_streak)
            temp_streak = 1
    
    longest_streak = max(longest_streak, temp_streak)
    last_date = datetime.fromisoformat(sorted_checkins[-1]['date']).date()
    today = datetime.now().date()
    
    if (today - last_date).days <= 1:
        current_streak = temp_streak
    
    return current_streak, longest_streak

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    data = UserData.load(user_id)
    data['user_id'] = user_id
    data['username'] = user.username
    data['first_name'] = user.first_name
    data['start_date'] = datetime.now().isoformat()
    UserData.save(user_id, data)
    
    if data['onboarding_complete']:
        await update.message.reply_text(
            f"Welcome back, {user.first_name}! 🔥\n\n"
            "Use these commands:\n"
            "/morning - Morning check-in\n"
            "/evening - Evening reflection\n"
            "/north_star - Define your purpose\n"
            "/belief - Demolish limiting beliefs\n"
            "/experiment - Launch new MVE\n"
            "/if_then - Create system\n"
            "/progress - View dashboard\n"
            "/help - All commands"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"🎉 Welcome, {user.first_name}!\n\n"
        "I'm your mindset coach for the next 30 days (and beyond).\n\n"
        "I've read the PDF you got. Now let's make it REAL.\n\n"
        "Quick setup (2 minutes) ⏱️"
    )
    
    await update.message.reply_text(
        "1️⃣ What's your timezone?\n\n"
        "Examples:\n"
        "• America/New_York\n"
        "• Europe/London\n"
        "• Asia/Tokyo\n"
        "• Africa/Lagos\n\n"
        "Type your timezone:"
    )
    
    return ONBOARDING_TIMEZONE

async def onboarding_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    timezone_input = update.message.text.strip()
    
    try:
        pytz.timezone(timezone_input)
        data['timezone'] = timezone_input
        UserData.save(user_id, data)
        
        await update.message.reply_text(
            "✅ Timezone saved!\n\n"
            "2️⃣ Best time for MORNING check-in?\n\n"
            "Format: HH:MM (24-hour)\n"
            "Example: 08:00 for 8 AM\n\n"
            "Type your preferred time:"
        )
        return ONBOARDING_MORNING
    except:
        await update.message.reply_text(
            "❌ Invalid timezone. Please try again.\n\n"
            "Common timezones:\n"
            "• America/New_York\n"
            "• America/Los_Angeles\n"
            "• Europe/London\n"
            "• Asia/Tokyo"
        )
        return ONBOARDING_TIMEZONE

async def onboarding_morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    time_input = update.message.text.strip()
    
    try:
        datetime.strptime(time_input, "%H:%M")
        data['morning_time'] = time_input
        UserData.save(user_id, data)
        
        await update.message.reply_text(
            "✅ Morning time saved!\n\n"
            "3️⃣ Best time for EVENING reflection?\n\n"
            "Format: HH:MM (24-hour)\n"
            "Example: 20:00 for 8 PM\n\n"
            "Type your preferred time:"
        )
        return ONBOARDING_EVENING
    except:
        await update.message.reply_text(
            "❌ Invalid time format.\n\n"
            "Use HH:MM format (24-hour)\n"
            "Example: 08:00 or 20:30"
        )
        return ONBOARDING_MORNING

async def onboarding_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    time_input = update.message.text.strip()
    
    try:
        datetime.strptime(time_input, "%H:%M")
        data['evening_time'] = time_input
        UserData.save(user_id, data)
        
        keyboard = [
            ['Direct & no-nonsense'],
            ['Encouraging & supportive'],
            ['Mix of both']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "✅ Evening time saved!\n\n"
            "4️⃣ How should I talk to you?\n\n"
            "Pick your style:",
            reply_markup=reply_markup
        )
        return ONBOARDING_STYLE
    except:
        await update.message.reply_text(
            "❌ Invalid time format.\n\n"
            "Use HH:MM format (24-hour)\n"
            "Example: 20:00 or 21:30"
        )
        return ONBOARDING_EVENING

async def onboarding_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    
    style_map = {
        'Direct & no-nonsense': 'direct',
        'Encouraging & supportive': 'supportive',
        'Mix of both': 'mix'
    }
    
    style = style_map.get(update.message.text, 'mix')
    data['communication_style'] = style
    data['onboarding_complete'] = True
    UserData.save(user_id, data)
    
    greeting = get_user_greeting(style, data['first_name'])
    
    await update.message.reply_text(
        f"✅ SETUP COMPLETE!\n\n"
        f"{greeting}\n\n"
        f"Your schedule:\n"
        f"🌅 Morning check-ins: {data['morning_time']}\n"
        f"🌙 Evening reflections: {data['evening_time']}\n"
        f"⏰ Timezone: {data['timezone']}\n\n"
        f"I'll message you automatically at these times.\n\n"
        f"But don't wait - let's start NOW.\n\n"
        f"First step: Define your North Star.\n\n"
        f"Ready? Type /north_star",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

async def north_star_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧭 LET'S DEFINE YOUR NORTH STAR\n\n"
        "This takes 15 minutes. Find a quiet space.\n\n"
        "Ready? Let's begin.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "STEP 1: PURPOSE DISCOVERY\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Question 1 of 3:\n\n"
        "If money were NO object, what would you spend your time doing?\n\n"
        "Think deeply. Type your answer:"
    )
    
    return NS_PURPOSE_Q1

async def ns_purpose_q1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['purpose_q1'] = update.message.text
    
    await update.message.reply_text(
        "Interesting! 🤔\n\n"
        "Question 2 of 3:\n\n"
        "At 80 years old, what do you want to be KNOWN for?\n\n"
        "Your legacy. Type your answer:"
    )
    
    return NS_PURPOSE_Q2

async def ns_purpose_q2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['purpose_q2'] = update.message.text
    
    await update.message.reply_text(
        "Powerful. 💭\n\n"
        "Question 3 of 3:\n\n"
        "What problem in the world genuinely makes you ANGRY?\n\n"
        "What injustice or inefficiency bothers you most?\n\n"
        "Type your answer:"
    )
    
    return NS_PURPOSE_Q3

async def ns_purpose_q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['purpose_q3'] = update.message.text
    draft_purpose = f"To help others and create meaningful impact"
    
    keyboard = [['✅ Yes, this is perfect'], ['✏️ Let me edit it']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Based on your answers, here's a draft purpose:\n\n"
        f"💫 \"{draft_purpose}\"\n\n"
        "Does this feel TRUE to you?",
        reply_markup=reply_markup
    )
    
    context.user_data['draft_purpose'] = draft_purpose
    
    return NS_PURPOSE_DRAFT

async def ns_purpose_draft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    response = update.message.text
    
    if '✅' in response or 'yes' in response.lower():
        data['purpose'] = context.user_data['draft_purpose']
        UserData.save(user_id, data)
        
        await update.message.reply_text(
            "✅ PURPOSE LOCKED IN!\n\n"
            f"Your North Star: \"{data['purpose']}\"\n\n"
            "This will guide everything we build.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "STEP 2: VALUES CLARIFICATION\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Pick 5 values that resonate most:\n\n"
            "Type them separated by commas:\n"
            "Example: Integrity, Growth, Courage, Freedom, Impact\n\n"
            "Options: Integrity, Growth, Courage, Creativity, Freedom, "
            "Impact, Connection, Health, Authenticity, Excellence, "
            "Discipline, Presence\n\n"
            "Your 5 values:",
            reply_markup=ReplyKeyboardRemove()
        )
        return NS_VALUES
    else:
        await update.message.reply_text(
            "No problem! Write your purpose statement:\n\n"
            "Start with: \"To...\"",
            reply_markup=ReplyKeyboardRemove()
        )
        return NS_PURPOSE_DRAFT

async def ns_values(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    
    values_text = update.message.text
    values = [v.strip() for v in values_text.split(',')][:5]
    
    data['values'] = values
    UserData.save(user_id, data)
    
    await update.message.reply_text(
        f"✅ VALUES SAVED!\n\n"
        f"Your core values:\n" +
        '\n'.join([f"• {v}" for v in values]) +
        "\n\n━━━━━━━━━━━━━━━━━━━━\n"
        "STEP 3: IDENTITY STATEMENTS\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Complete this sentence 3-5 times:\n\n"
        "\"I am someone who...\"\n\n"
        "Examples:\n"
        "• I am someone who shows up consistently\n"
        "• I am someone who treats my body with respect\n"
        "• I am someone who creates value\n\n"
        "Type each statement on a new line:"
    )
    
    return NS_IDENTITY

async def ns_identity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    
    statements = [s.strip() for s in update.message.text.split('\n') if s.strip()]
    data['identity_statements'] = statements
    
    if 'Chapter 1' not in data['chapters_completed']:
        data['chapters_completed'].append('Chapter 1')
    
    UserData.save(user_id, data)
    
    await update.message.reply_text(
        "🎉 NORTH STAR COMPLETE!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "YOUR NORTH STAR:\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💫 Purpose: {data['purpose']}\n\n"
        f"⭐ Values:\n" +
        '\n'.join([f"  • {v}" for v in data['values']]) +
        f"\n\n🎯 Identity:\n" +
        '\n'.join([f"  • {s}" for s in statements]) +
        "\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "This is YOUR operating system.\n\n"
        "I'll remind you of this weekly and we'll review quarterly.\n\n"
        "Next step: Let's demolish some limiting beliefs.\n\n"
        "Type /belief when ready. 💪"
    )
    
    return ConversationHandler.END

async def belief_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 BELIEF DEMOLISHER\n\n"
        "Let's challenge the lies your brain tells you.\n\n"
        "What limiting belief is holding you back RIGHT NOW?\n\n"
        "Examples:\n"
        "• \"I'm not disciplined enough\"\n"
        "• \"I'm not smart enough to start a business\"\n"
        "• \"I'm too old to change\"\n\n"
        "Type your limiting belief:"
    )
    
    return BELIEF_IDENTIFY

async def belief_identify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_belief'] = update.message.text
    
    await update.message.reply_text(
        f"Got it. Let's challenge:\n\n"
        f"\"{update.message.text}\"\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "STEP 1: YOUR \"PROOF\"\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "What evidence does your brain offer for this belief?\n\n"
        "List everything, even if it sounds stupid.\n"
        "One piece of \"evidence\" per line:"
    )
    
    return BELIEF_PROOF

async def belief_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['belief_proof'] = update.message.text
    
    await update.message.reply_text(
        "Interesting. That's what your brain is using as \"proof.\"\n\n"
        "Now let's destroy it with REAL evidence.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "STEP 2: COUNTER-EVIDENCE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "List times you've:\n"
        "• Learned something difficult\n"
        "• Solved a complex problem\n"
        "• Figured something out\n"
        "• Overcame a challenge\n"
        "• Successfully completed something hard\n\n"
        "Give me at least 5 examples (one per line):"
    )
    
    return BELIEF_COUNTER

async def belief_counter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['counter_evidence'] = update.message.text
    original_belief = context.user_data['current_belief']
    rewritten = f"I have repeatedly proven I can overcome challenges. My track record shows I figure things out when it matters."
    
    keyboard = [['✅ Perfect!'], ['✏️ Let me edit']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "💪 Look at that evidence!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "STEP 3: NEW BELIEF\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"OLD: \"{original_belief}\"\n\n"
        f"NEW: \"{rewritten}\"\n\n"
        "Based on ACTUAL evidence, does this feel more true?",
        reply_markup=reply_markup
    )
    
    context.user_data['rewritten_belief'] = rewritten
    
    return BELIEF_REWRITE

async def belief_rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    response = update.message.text
    
    if '✅' in response or 'perfect' in response.lower():
        belief_entry = {
            'original': context.user_data['current_belief'],
            'proof': context.user_data['belief_proof'],
            'counter_evidence': context.user_data['counter_evidence'],
            'rewritten': context.user_data['rewritten_belief'],
            'date': datetime.now().isoformat()
        }
        
        data['belief_vault'].append(belief_entry)
        data['limiting_beliefs'].append(context.user_data['current_belief'])
        
        if 'Chapter 2' not in data['chapters_completed']:
            data['chapters_completed'].append('Chapter 2')
        
        UserData.save(user_id, data)
        
        await update.message.reply_text(
            "✅ NEW BELIEF SAVED TO VAULT!\n\n"
            f"\"{context.user_data['rewritten_belief']}\"\n\n"
            "I'll remind you of this when you need it.\n\n"
            "Want to demolish another belief?\n"
            "Type /belief\n\n"
            "Or move to Chapter 3: Experiments\n"
            "Type /experiment 🔬",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Write your new belief statement:",
            reply_markup=ReplyKeyboardRemove()
        )
        return BELIEF_REWRITE

async def experiment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔬 MVE EXPERIMENT LAB\n\n"
        "Let's turn fear into action.\n\n"
        "What goal have you been AVOIDING because failure feels too risky?\n\n"
        "Examples:\n"
        "• Launch a YouTube channel\n"
        "• Start a business\n"
        "• Ask for a raise\n"
        "• Post content online\n\n"
        "Type your scary goal:"
    )
    
    return MVE_GOAL

async def mve_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mve_goal'] = update.message.text
    
    keyboard = [
        ['A) Smallest possible first step'],
        ['B) Research/plan only'],
        ['C) Test with one person'],
        ['D) Something else']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Got it: \"{update.message.text}\"\n\n"
        "Let's make this SMALL and SAFE.\n\n"
        "What's the SMALLEST version you could test in 48 hours?\n\n"
        "Pick an approach:",
        reply_markup=reply_markup
    )
    
    return MVE_DESIGN

async def mve_design(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = update.message.text
    
    if response.startswith('D)') or 'something else' in response.lower():
        await update.message.reply_text(
            "Describe your MVE:\n\n"
            "What's the smallest thing you can do in 48 hours?",
            reply_markup=ReplyKeyboardRemove()
        )
        return MVE_DESIGN
    
    context.user_data['mve_design'] = response
    
    await update.message.reply_text(
        "Perfect! Now let's set psychological safety.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "WORST CASE SCENARIO\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "If this MVE \"fails,\" what ACTUALLY happens?\n\n"
        "Be specific. Type your answer:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return MVE_WORST

async def mve_worst(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mve_worst'] = update.message.text
    
    await update.message.reply_text(
        "Usually not that bad, right? 😉\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "LEARNING GOAL\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Even if this MVE fails, what will you LEARN?\n\n"
        "Type your answer:"
    )
    
    return MVE_LEARNING

async def mve_learning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    context.user_data['mve_learning'] = update.message.text
    deadline = datetime.now() + timedelta(hours=48)
    
    experiment = {
        'goal': context.user_data['mve_goal'],
        'mve_design': context.user_data['mve_design'],
        'worst_case': context.user_data['mve_worst'],
        'learning_goal': context.user_data['mve_learning'],
        'created': datetime.now().isoformat(),
        'deadline': deadline.isoformat(),
        'status': 'active',
        'result': None
    }
    
    data['experiments'].append(experiment)
    data['total_experiments'] += 1
    
    if 'Chapter 3' not in data['chapters_completed']:
        data['chapters_completed'].append('Chapter 3')
    
    UserData.save(user_id, data)
    
    await update.message.reply_text(
        "✅ EXPERIMENT CREATED!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"MVE: {context.user_data['mve_design']}\n"
        f"Deadline: {deadline.strftime('%B %d at %I:%M %p')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "I'll check in with you in 48 hours.\n\n"
        "Go execute! 🚀",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

async def ifthen_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏗️ SYSTEM BUILDER\n\n"
        "Let's eliminate willpower battles.\n\n"
        "What goal keeps requiring WILLPOWER?\n\n"
        "Examples:\n"
        "• I keep getting distracted by my phone\n"
        "• I can't stick to working out\n"
        "• I procrastinate on important work\n"
        "• I eat junk food mindlessly\n\n"
        "Type your goal:"
    )
    
    return IFTHEN_GOAL

async def ifthen_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['system_goal'] = update.message.text
    
    keyboard = [
        ['A) During work sessions'],
        ['B) First thing in morning'],
        ['C) During conversations'],
        ['D) All day long']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Got it. Let's design a system.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "FRICTION AUDIT\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "WHEN does this happen most?",
        reply_markup=reply_markup
    )
    
    return IFTHEN_FRICTION

async def ifthen_friction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['friction_point'] = update.message.text
    
    await update.message.reply_text(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "IF-THEN SOLUTIONS\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Design your system:\n\n"
        "Format: \"If [trigger], then I will [action]\"\n\n"
        "Example:\n"
        "\"If I sit at my desk, then I put my phone in a drawer\"\n\n"
        "Type your If-Then statement:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return IFTHEN_SOLUTION

async def ifthen_solution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    ifthen_statement = update.message.text
    
    system = {
        'goal': context.user_data['system_goal'],
        'friction_point': context.user_data['friction_point'],
        'if_then': ifthen_statement,
        'created': datetime.now().isoformat(),
        'active': True,
        'adherence_count': 0
    }
    
    data['if_then_systems'].append(system)
    data['active_systems'] += 1
    
    if 'Chapter 4' not in data['chapters_completed']:
        data['chapters_completed'].append('Chapter 4')
    
    UserData.save(user_id, data)
    
    await update.message.reply_text(
        "✅ SYSTEM ACTIVATED!\n\n"
        f"\"{ifthen_statement}\"\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "This removes the need for willpower.\n\n"
        f"Active systems: {data['active_systems']}\n\n"
        "Keep building! 💪",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

async def morning_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    
    identity = "someone who executes consistently"
    if data['identity_statements']:
        import random
        identity = random.choice(data['identity_statements'])
        identity = identity.replace("I am someone who ", "")
    
    days_active = 1
    if data['start_date']:
        start = datetime.fromisoformat(data['start_date'])
        days_active = (datetime.now() - start).days + 1
    
    await update.message.reply_text(
        f"🌅 Good morning, {data['first_name']}!\n\n"
        f"Day {days_active} of your transformation.\n\n"
        f"TODAY'S IDENTITY REMINDER:\n"
        f"\"I am {identity}\"\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"What are your TOP 3 priorities today?\n\n"
        f"Type them (one per line):"
    )
    
    return CHECKIN_TOP3

async def checkin_top3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['today_top3'] = update.message.text
    
    await update.message.reply_text(
        "✅ Top 3 locked in!\n\n"
        "Quick mindset check:\n\n"
        "Energy level (1-10):\n"
        "Type a number:"
    )
    
    return CHECKIN_ENERGY

async def checkin_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        energy = int(update.message.text)
        context.user_data['today_energy'] = energy
        
        await update.message.reply_text(
            f"Energy: {energy}/10 ✅\n\n"
            "Clarity level (1-10):\n"
            "Type a number:"
        )
        
        return CHECKIN_CLARITY
    except:
        await update.message.reply_text("Please type a number between 1 and 10:")
        return CHECKIN_ENERGY

async def checkin_clarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        clarity = int(update.message.text)
        context.user_data['today_clarity'] = clarity
        
        await update.message.reply_text(
            f"Clarity: {clarity}/10 ✅\n\n"
            "One small win you're COMMITTED to today?\n\n"
            "Type it:"
        )
        
        return CHECKIN_COMMITMENT
    except:
        await update.message.reply_text("Please type a number between 1 and 10:")
        return CHECKIN_CLARITY

async def checkin_commitment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    context.user_data['today_commitment'] = update.message.text
    
    checkin = {
        'date': datetime.now().isoformat(),
        'top3': context.user_data['today_top3'],
        'energy': context.user_data['today_energy'],
        'clarity': context.user_data['today_clarity'],
        'commitment': context.user_data['today_commitment']
    }
    
    data['daily_check_ins'].append(checkin)
    data['last_check_in'] = datetime.now().isoformat()
    
    current_streak, longest_streak = calculate_streak(data['daily_check_ins'])
    data['streak_current'] = current_streak
    data['streak_longest'] = max(longest_streak, data['streak_longest'])
    
    UserData.save(user_id, data)
    
    encouragement = "Let's execute. 🔥"
    if data['communication_style'] == 'supportive':
        encouragement = "You've got this! I believe in you! 🌟"
    elif data['communication_style'] == 'direct':
        encouragement = "Now execute. No excuses. 💪"
    
    await update.message.reply_text(
        f"✅ MORNING CHECK-IN COMPLETE!\n\n"
        f"🔥 Current streak: {current_streak} days\n\n"
        f"{encouragement}\n\n"
        f"I'll check back tonight at {data['evening_time']}.\n\n"
        f"Go crush those Top 3! 🚀",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

async def evening_reflection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    
    days_active = 1
    if data['start_date']:
        start = datetime.fromisoformat(data['start_date'])
        days_active = (datetime.now() - start).days + 1
    
    top3_text = ""
    if data['daily_check_ins']:
        last_checkin = data['daily_check_ins'][-1]
        checkin_date = datetime.fromisoformat(last_checkin['date']).date()
        if checkin_date == datetime.now().date():
            top3_text = f"\nYour Top 3:\n{last_checkin['top3']}\n\n"
    
    keyboard = [['✅ Yes, all 3'], ['⏸️ Partially'], ['❌ No']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"🌙 Day {days_active} complete, {data['first_name']}.\n\n"
        f"{top3_text}"
        "Did you complete your Top 3?",
        reply_markup=reply_markup
    )
    
    return REFLECT_COMPLETION

async def reflect_completion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['completion_status'] = update.message.text
    
    response_map = {
        '✅ Yes, all 3': "🎉 EXCELLENT!",
        '⏸️ Partially': "Progress is progress. 👍",
        '❌ No': "That's okay. Tomorrow is a fresh start. 🌅"
    }
    
    response = response_map.get(update.message.text, "Got it.")
    
    await update.message.reply_text(
        f"{response}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎉 CELEBRATION TIME\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Tell me ONE win from today.\n\n"
        "(Could be tiny - \"I drank water first thing\" counts!)\n\n"
        "Type your win:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return REFLECT_WIN

async def reflect_win(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    win = update.message.text
    context.user_data['today_win'] = win
    
    win_entry = {'date': datetime.now().isoformat(), 'win': win}
    data['small_wins'].append(win_entry)
    data['total_wins_logged'] += 1
    
    celebration = "Nice! That's exactly what we're building on. 💪"
    if data['communication_style'] == 'supportive':
        celebration = "That's amazing! Every win matters! Keep it up! 🌟"
    elif data['communication_style'] == 'direct':
        celebration = "Good. Stack another one tomorrow. 🔥"
    
    keyboard = [['Keep same Top 3'], ['Adjust tomorrow']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"{celebration}\n\n"
        f"Total wins logged: {data['total_wins_logged']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📊 TOMORROW'S FORECAST\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Should we keep the same Top 3, or adjust?",
        reply_markup=reply_markup
    )
    
    UserData.save(user_id, data)
    return REFLECT_TOMORROW

async def reflect_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    
    reflection = {
        'date': datetime.now().isoformat(),
        'completion_status': context.user_data['completion_status'],
        'win': context.user_data['today_win'],
        'tomorrow_plan': update.message.text
    }
    
    data['evening_reflections'].append(reflection)
    data['last_reflection'] = datetime.now().isoformat()
    
    if 'Chapter 5' not in data['chapters_completed']:
        data['chapters_completed'].append('Chapter 5')
    
    UserData.save(user_id, data)
    
    await update.message.reply_text(
        "✅ EVENING REFLECTION COMPLETE!\n\n"
        "Sleep well. Tomorrow we level up. 💤\n\n"
        f"I'll check in tomorrow at {data['morning_time']}.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    
    current_streak, longest_streak = calculate_streak(data['daily_check_ins'])
    total_checkins = len(data['daily_check_ins'])
    total_reflections = len(data['evening_reflections'])
    total_wins = data['total_wins_logged']
    
    chapters = data['chapters_completed']
    chapter_status = {
        'Chapter 1': '✅' if 'Chapter 1' in chapters else '⏳',
        'Chapter 2': '✅' if 'Chapter 2' in chapters else '⏳',
        'Chapter 3': '✅' if 'Chapter 3' in chapters else '⏳',
        'Chapter 4': '✅' if 'Chapter 4' in chapters else '⏳',
        'Chapter 5': '✅' if 'Chapter 5' in chapters else '⏳'
    }
    
    completion_rate = 0
    if total_reflections > 0:
        completed = sum(1 for r in data['evening_reflections'] if '✅' in r.get('completion_status', ''))
        completion_rate = int((completed / total_reflections) * 100)
    
    days_active = 1
    if data['start_date']:
        start = datetime.fromisoformat(data['start_date'])
        days_active = (datetime.now() - start).days + 1
    
    qmr_days = 90 - days_active if days_active < 90 else 0
    
    dashboard = (
        f"📊 YOUR PROGRESS\n\n"
        f"🔥 CURRENT STREAK: {current_streak} days\n"
        f"⭐ TOTAL WINS LOGGED: {total_wins}\n"
        f"📅 DAYS ACTIVE: {days_active}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"CHAPTER COMPLETION:\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{chapter_status['Chapter 1']} Ch 1: North Star\n"
        f"{chapter_status['Chapter 2']} Ch 2: Beliefs ({len(data['belief_vault'])} demolished)\n"
        f"{chapter_status['Chapter 3']} Ch 3: Experiments ({data['completed_experiments']}/{data['total_experiments']} completed)\n"
        f"{chapter_status['Chapter 4']} Ch 4: Systems ({data['active_systems']} active)\n"
        f"{chapter_status['Chapter 5']} Ch 5: Momentum\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"DAILY HABITS:\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"• Morning check-ins: {total_checkins}\n"
        f"• Evening reflections: {total_reflections}\n"
        f"• Top 3 completion: {completion_rate}%\n"
        f"• Longest streak: {longest_streak} days\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"SYSTEMS:\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"• Belief Vault: {len(data['belief_vault'])} rewired beliefs\n"
        f"• Active If-Thens: {data['active_systems']}\n"
        f"• Total Experiments: {data['total_experiments']}\n\n"
    )
    
    if qmr_days > 0:
        dashboard += f"🎯 NEXT QMR: {qmr_days} days\n\n"
    
    dashboard += "Keep going. The system is working. 💪"
    
    await update.message.reply_text(dashboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 AVAILABLE COMMANDS\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "DAILY PRACTICE:\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "/morning - Morning check-in\n"
        "/evening - Evening reflection\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "BUILD YOUR SYSTEM:\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "/north_star - Define purpose & identity\n"
        "/belief - Demolish limiting beliefs\n"
        "/experiment - Launch MVE test\n"
        "/if_then - Create If-Then system\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "TRACKING:\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "/progress - View dashboard\n"
        "/wins - See all wins\n"
        "/vault - View belief vault\n"
        "/systems - Active If-Thens\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "SUPPORT:\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "/stuck - Get help\n\n"
        "Questions? Just message me anytime! 💬"
    )
    
    await update.message.reply_text(help_text)

async def view_vault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    
    if not data['belief_vault']:
        await update.message.reply_text(
            "Your Belief Vault is empty.\n\n"
            "Demolish your first limiting belief:\n"
            "/belief"
        )
        return
    
    vault_text = "🧠 YOUR BELIEF VAULT\n\n"
    
    for i, belief in enumerate(data['belief_vault'], 1):
        vault_text += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"BELIEF #{i}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"❌ Old: \"{belief['original']}\"\n"
            f"✅ New: \"{belief['rewritten']}\"\n\n"
        )
    
    vault_text += "These are your evidence-based truths. 💪"
    
    await update.message.reply_text(vault_text)

async def view_wins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    
    if not data['small_wins']:
        await update.message.reply_text(
            "No wins logged yet!\n\n"
            "Complete your evening reflection to log wins:\n"
            "/evening"
        )
        return
    
    recent_wins = data['small_wins'][-10:]
    wins_text = f"🎉 YOUR RECENT WINS\n\nTotal wins logged: {data['total_wins_logged']}\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for win in reversed(recent_wins):
        date = datetime.fromisoformat(win['date']).strftime('%b %d')
        wins_text += f"✅ {date}: {win['win']}\n\n"
    
    wins_text += "━━━━━━━━━━━━━━━━━━━━\n\nEvery win matters. Keep stacking them! 💪"
    
    await update.message.reply_text(wins_text)

async def view_systems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    
    if not data['if_then_systems']:
        await update.message.reply_text(
            "No systems created yet!\n\n"
            "Build your first If-Then system:\n"
            "/if_then"
        )
        return
    
    systems_text = "🏗️ YOUR ACTIVE SYSTEMS\n\n"
    active_systems = [s for s in data['if_then_systems'] if s.get('active', True)]
    
    for i, system in enumerate(active_systems, 1):
        systems_text += f"{i}. {system['if_then']}\n   Goal: {system['goal']}\n\n"
    
    systems_text += f"Total active: {len(active_systems)}\n\nThese systems eliminate willpower. 💪"
    
    await update.message.reply_text(systems_text)

async def stuck_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = UserData.load(user_id)
    
    keyboard = [
        ['💭 North Star check'],
        ['🧠 Belief sabotage'],
        ['⚙️ Systems broken'],
        ['😓 Just overwhelmed']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"🚨 Hey {data['first_name']},\n\n"
        "I'm here to help. No judgment.\n\n"
        "Let's troubleshoot:\n\n"
        "What's actually going on?",
        reply_markup=reply_markup
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Cancelled. No problem!\n\n"
        "Type /help to see all commands.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    application = Application.builder().token(TOKEN).build()
    
    onboarding_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ONBOARDING_TIMEZONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_timezone)],
            ONBOARDING_MORNING: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_morning)],
            ONBOARDING_EVENING: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_evening)],
            ONBOARDING_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_style)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    north_star_conv = ConversationHandler(
        entry_points=[CommandHandler('north_star', north_star_start)],
        states={
            NS_PURPOSE_Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, ns_purpose_q1)],
            NS_PURPOSE_Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, ns_purpose_q2)],
            NS_PURPOSE_Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, ns_purpose_q3)],
            NS_PURPOSE_DRAFT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ns_purpose_draft)],
            NS_VALUES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ns_values)],
            NS_IDENTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ns_identity)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    belief_conv = ConversationHandler(
        entry_points=[CommandHandler('belief', belief_start)],
        states={
            BELIEF_IDENTIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, belief_identify)],
            BELIEF_PROOF: [MessageHandler(filters.TEXT & ~filters.COMMAND, belief_proof)],
            BELIEF_COUNTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, belief_counter)],
            BELIEF_REWRITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, belief_rewrite)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    mve_conv = ConversationHandler(
        entry_points=[CommandHandler('experiment', experiment_start)],
        states={
            MVE_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, mve_goal)],
            MVE_DESIGN: [MessageHandler(filters.TEXT & ~filters.COMMAND, mve_design)],
            MVE_WORST: [MessageHandler(filters.TEXT & ~filters.COMMAND, mve_worst)],
            MVE_LEARNING: [MessageHandler(filters.TEXT & ~filters.COMMAND, mve_learning)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    ifthen_conv = ConversationHandler(
        entry_points=[CommandHandler('if_then', ifthen_start)],
        states={
            IFTHEN_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ifthen_goal)],
            IFTHEN_FRICTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ifthen_friction)],
            IFTHEN_SOLUTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ifthen_solution)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    morning_conv = ConversationHandler(
        entry_points=[CommandHandler('morning', morning_checkin)],
        states={
            CHECKIN_TOP3: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkin_top3)],
            CHECKIN_ENERGY: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkin_energy)],
            CHECKIN_CLARITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkin_clarity)],
            CHECKIN_COMMITMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkin_commitment)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    evening_conv = ConversationHandler(
        entry_points=[CommandHandler('evening', evening_reflection)],
        states={
            REFLECT_COMPLETION: [MessageHandler(filters.TEXT & ~filters.COMMAND, reflect_completion)],
            REFLECT_WIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, reflect_win)],
            REFLECT_TOMORROW: [MessageHandler(filters.TEXT & ~filters.COMMAND, reflect_tomorrow)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(onboarding_conv)
    application.add_handler(north_star_conv)
    application.add_handler(belief_conv)
    application.add_handler(mve_conv)
    application.add_handler(ifthen_conv)
    application.add_handler(morning_conv)
    application.add_handler(evening_conv)
    
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('progress', progress))
    application.add_handler(CommandHandler('vault', view_vault))
    application.add_handler(CommandHandler('wins', view_wins))
    application.add_handler(CommandHandler('systems', view_systems))
    application.add_handler(CommandHandler('stuck', stuck_handler))
    
    print("🤖 Bot is starting...")
    print("Press Ctrl+C to stop")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()