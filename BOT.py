import logging
import os
import pickle
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ConversationHandler, ContextTypes, filters
)

# --- CONFIGURATION ---
# Replace this with your actual Token or set it as an environment variable
TOKEN = os.getenv("8342995076:AAH9TosXOwx_1KF3Kb5TwrKEcVlWqUmPEBI", "8342995076:AAH9TosXOwx_1KF3Kb5TwrKEcVlWqUmPEBI")
DATA_FILE = "user_data.pkl"

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- STATES ---
(
    CONFIRM_PDF_READ,       # 0
    WAITING_FOR_NEXT,       # 1 (Idle, waiting for user to say 'next')
    EXERCISE_IN_PROGRESS,   # 2 (Waiting for user to say 'done')
    EVIDENCE_BELIEF,        # 3
    EVIDENCE_EVIDENCE,      # 4
    EVIDENCE_REWRITE,       # 5
    MVE_GOAL,               # 6
    MVE_WORST,              # 7
    MVE_LEARNINGS,          # 8
    IFTHEN_INPUT,           # 9
    SMALL_WIN_INPUT,        # 10
    QUARTERLY_REVIEW        # 11
) = range(12)

# --- DATA ---
DAILY_EXERCISES = [
    "Day 1: Define your North Star — what’s your purpose?",
    "Day 2: Identify your core values.",
    "Day 3: Write your identity statements (I am someone who...).",
    "Day 4: Align current goals with your identity.",
    "Day 5: Start your Evidence Inventory: Name one limiting belief.",
    "Day 6: List 3 examples disproving that belief.",
    "Day 7: Rewrite the belief with evidence-based truth.",
    "Day 8: Create one 'If-Then' plan for a difficult habit.",
    "Day 9: Identify a 'Minimum Viable Experiment' for a fear you have.",
    "Day 30: Complete your first Quarterly Mindset Review."
]

# --- PERSISTENCE HELPERS ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'rb') as f:
            return pickle.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(data, f)

# Global in-memory store, loaded on startup
user_data_store = load_data()

def get_user_db(user_id):
    if user_id not in user_data_store:
        user_data_store[user_id] = {
            "pdf_read_confirmed": False,
            "current_day": 1,
            "evidence_inventory": [],
            "mve_logs": [],
            "if_then_plans": [],
            "small_win_log": [],
            "quarterly_reviews": []
        }
    return user_data_store[user_id]

def save_user_db():
    save_data(user_data_store)

# --- MAIN FLOW HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    userdata = get_user_db(user_id)
    
    if not userdata["pdf_read_confirmed"]:
        await update.message.reply_text(
            "Welcome! Have you finished reading the mindset blueprint PDF? "
            "Please type 'done' when you've completed it to start your journey."
        )
        return CONFIRM_PDF_READ
    else:
        await update.message.reply_text(
            f"Welcome back! You are on Day {userdata['current_day']}.\n"
            "Type 'next' to get today's exercise, or use the menu commands (/help)."
        )
        return WAITING_FOR_NEXT

async def confirm_pdf_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    userdata = get_user_db(user_id)
    text = update.message.text.lower().strip()

    if text == "done":
        userdata["pdf_read_confirmed"] = True
        save_user_db()
        await update.message.reply_text(
            "Fantastic! Let's start your 30-day mindset installation plan.\n"
            "Type 'next' to get Day 1."
        )
        return WAITING_FOR_NEXT
    else:
        await update.message.reply_text("Please type 'done' when you finish reading the PDF.")
        return CONFIRM_PDF_READ

async def send_next_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    userdata = get_user_db(user_id)
    day = userdata["current_day"]

    # Check if program is finished
    if day > len(DAILY_EXERCISES):
        await update.message.reply_text(
            "🎉 Congrats on completing the 30-day program!\n"
            "You can now use the tools indefinitely:\n"
            "/evidence, /experiment, /ifthen, /smallwin"
        )
        return WAITING_FOR_NEXT

    # Get exercise text (adjusting for 0-index)
    exercise_text = DAILY_EXERCISES[day - 1] if (day - 1) < len(DAILY_EXERCISES) else "Review your notes."
    
    await update.message.reply_text(
        f"🗓 <b>Day {day} Exercise:</b>\n{exercise_text}\n\n"
        "Type 'done' when you have completed this task.",
        parse_mode='HTML'
    )
    return EXERCISE_IN_PROGRESS

async def exercise_completed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    userdata = get_user_db(user_id)
    
    # Increment Day
    userdata["current_day"] += 1
    save_user_db()
    
    await update.message.reply_text(
        "✅ Great work! Progress saved.\n"
        "Come back tomorrow and type 'next' for the next step, "
        "or explore tools via /help."
    )
    return WAITING_FOR_NEXT

# --- TOOL HANDLERS (EVIDENCE, MVE, ETC) ---

async def start_evidence_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🕵️ <b>Evidence Inventory</b>\nWhat is one limiting belief holding you back?", parse_mode='HTML')
    return EVIDENCE_BELIEF

async def evidence_belief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['limiting_belief'] = update.message.text
    await update.message.reply_text("List 3 instances that prove this belief wrong (separate by commas).")
    return EVIDENCE_EVIDENCE

async def evidence_evidence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['belief_evidence'] = update.message.text
    await update.message.reply_text("Now, rewrite this belief into a new truth based on that evidence.")
    return EVIDENCE_REWRITE

async def evidence_rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    userdata = get_user_db(user_id)
    
    entry = {
        "belief": context.user_data['limiting_belief'],
        "evidence": context.user_data['belief_evidence'],
        "rewrite": update.message.text,
        "date": datetime.now().isoformat()
    }
    userdata["evidence_inventory"].append(entry)
    save_user_db()
    
    await update.message.reply_text("✨ New belief installed! Returning to menu.")
    return WAITING_FOR_NEXT

async def start_experiment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧪 <b>Minimum Viable Experiment</b>\nWhat's one goal you've been avoiding?", parse_mode='HTML')
    return MVE_GOAL

async def mve_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mve_goal'] = update.message.text
    await update.message.reply_text("What’s the worst that can happen if this experiment fails?")
    return MVE_WORST

async def mve_worst(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mve_worst'] = update.message.text
    await update.message.reply_text("Even if it fails, what will you learn from it?")
    return MVE_LEARNINGS

async def mve_learnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    userdata = get_user_db(user_id)
    
    entry = {
        "goal": context.user_data['mve_goal'],
        "worst": context.user_data['mve_worst'],
        "learning": update.message.text,
        "date": datetime.now().isoformat()
    }
    userdata["mve_logs"].append(entry)
    save_user_db()

    await update.message.reply_text("🚀 Experiment logged. Go take action! Returning to menu.")
    return WAITING_FOR_NEXT

async def start_ifthen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔗 <b>If-Then Planning</b>\nComplete this sentence:\nIf [trigger], then I will [action].", 
        parse_mode='HTML'
    )
    return IFTHEN_INPUT

async def ifthen_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    userdata = get_user_db(user_id)
    
    userdata["if_then_plans"].append({
        "plan": update.message.text,
        "date": datetime.now().isoformat()
    })
    save_user_db()
    
    await update.message.reply_text("✅ Plan saved. Returning to menu.")
    return WAITING_FOR_NEXT

async def start_smallwin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏆 What is a small win you achieved today?")
    return SMALL_WIN_INPUT

async def smallwin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    userdata = get_user_db(user_id)
    
    userdata["small_win_log"].append({
        "win": update.message.text,
        "date": datetime.now().isoformat()
    })
    save_user_db()
    
    await update.message.reply_text("🎉 Win celebrated! Returning to menu.")
    return WAITING_FOR_NEXT

async def start_quarterly_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 <b>Quarterly Review</b>\n"
        "Please answer these 4 questions separated by semicolons (;):\n"
        "1. Am I aligned with my purpose?\n2. Habits to adjust?\n3. Biggest constraint?\n4. Next experiment?",
        parse_mode='HTML'
    )
    return QUARTERLY_REVIEW

async def quarterly_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if ";" not in text:
        await update.message.reply_text("⚠️ Please separate your answers with semicolons (;). Try again.")
        return QUARTERLY_REVIEW

    user_id = update.effective_user.id
    userdata = get_user_db(user_id)
    
    userdata["quarterly_reviews"].append({
        "raw_text": text,
        "date": datetime.now().isoformat()
    })
    save_user_db()
    
    await update.message.reply_text("💾 Review saved. Returning to menu.")
    return WAITING_FOR_NEXT

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Mindset Bot Commands:</b>\n\n"
        "🔄 <b>Daily Flow:</b>\n"
        "'next' - Get today's exercise\n"
        "'done' - Mark exercise complete\n\n"
        "🛠 <b>Tools:</b>\n"
        "/evidence - Rewire limiting beliefs\n"
        "/experiment - Plan a failure experiment\n"
        "/ifthen - Create implementation intentions\n"
        "/smallwin - Log a daily win\n"
        "/review - Quarterly review",
        parse_mode='HTML'
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled. Type 'next' or use a command to restart.")
    return WAITING_FOR_NEXT

# --- MAIN SETUP ---
def main():
    if TOKEN == "YOUR_TOKEN_HERE":
        print("ERROR: Please put your Telegram Token in the script code or environment variables.")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Common tool commands that can be triggered from the menu
    tool_entry_points = [
        CommandHandler('evidence', start_evidence_inventory),
        CommandHandler('experiment', start_experiment),
        CommandHandler('ifthen', start_ifthen),
        CommandHandler('smallwin', start_smallwin),
        CommandHandler('review', start_quarterly_review),
    ]

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CONFIRM_PDF_READ: [
                MessageHandler(filters.Regex(r'(?i)^done$'), confirm_pdf_read)
            ],
            # State: Waiting for user to ask for the next exercise
            WAITING_FOR_NEXT: [
                MessageHandler(filters.Regex(r'(?i)^next$'), send_next_exercise),
            ] + tool_entry_points, # Add tools here so they work while waiting
            
            # State: Waiting for user to finish the exercise
            EXERCISE_IN_PROGRESS: [
                MessageHandler(filters.Regex(r'(?i)^done$'), exercise_completed)
            ],

            # Tool States
            EVIDENCE_BELIEF: [MessageHandler(filters.TEXT & ~filters.COMMAND, evidence_belief)],
            EVIDENCE_EVIDENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, evidence_evidence)],
            EVIDENCE_REWRITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, evidence_rewrite)],
            
            MVE_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, mve_goal)],
            MVE_WORST: [MessageHandler(filters.TEXT & ~filters.COMMAND, mve_worst)],
            MVE_LEARNINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, mve_learnings)],
            
            IFTHEN_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ifthen_input)],
            SMALL_WIN_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, smallwin_input)],
            QUARTERLY_REVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, quarterly_review)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel), 
            CommandHandler('help', help_command),
            CommandHandler('start', start) # Allow restarting
        ],
    )

    application.add_handler(conv_handler)

    # Fallback for commands if sent outside conversation (rare, but good practice)
    application.add_handler(CommandHandler('help', help_command))

    print("Mindset Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()