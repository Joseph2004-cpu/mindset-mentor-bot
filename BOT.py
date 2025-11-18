import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
(
    CONFIRM_PDF_READ, DAILY_EXERCISE, EVIDENCE_BELIEF, EVIDENCE_EVIDENCE, EVIDENCE_REWRITE,
    MVE_GOAL, MVE_WORST, MVE_LEARNINGS, IFTHEN_INPUT, SMALL_WIN_INPUT, QUARTERLY_REVIEW,
    FOCUS_AREA_SELECTION, EXERCISE_RESPONSE
) = range(13)

# Sample 30-day mindset installation exercises aligned with the PDF
DAILY_EXERCISES = [
    "Day 1: Define your North Star — what’s your purpose?",
    "Day 2: Identify your core values.",
    "Day 3: Write your identity statements (I am someone who...).",
    "Day 4: Align current goals with your identity.",
    "Day 5: Start your Evidence Inventory: Name one limiting belief.",
    "Day 6: List 3 examples disproving that belief.",
    "Day 7: Rewrite the belief with evidence-based truth.",
    # ... fill in remaining days as appropriate ...
    "Day 30: Complete your first Quarterly Mindset Review."
]

# In-memory user data store (replace with persistent database in production)
user_data_store = {}

def get_user_data(user_id):
    return user_data_store.setdefault(user_id, {
        "pdf_read_confirmed": False,
        "current_day": 0,
        "evidence_inventory": [],
        "mve_logs": [],
        "if_then_plans": [],
        "small_win_log": [],
        "quarterly_reviews": []
    })

def save_user_data(user_id, data):
    user_data_store[user_id] = data


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    userdata = get_user_data(user_id)
    if not userdata.get("pdf_read_confirmed"):
        await update.message.reply_text(
            "Welcome! Have you finished reading the mindset blueprint PDF? "
            "Please type 'done' when you've completed it to start your mindset journey."
        )
        return CONFIRM_PDF_READ
    else:
        await update.message.reply_text(
            "Welcome back! Ready to continue your mindset growth? "
            "Type 'next' to get your next mindset exercise."
        )
        return DAILY_EXERCISE

async def confirm_pdf_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user_id = update.effective_user.id
    if text == "done":
        userdata = get_user_data(user_id)
        userdata["pdf_read_confirmed"] = True
        userdata["current_day"] = 1
        save_user_data(user_id, userdata)
        await update.message.reply_text(
            "Fantastic! Let's start your 30-day mindset installation plan.\n"
            "Type 'next' anytime to get today's exercise."
        )
        return DAILY_EXERCISE
    else:
        await update.message.reply_text("Please type 'done' when you finish reading the PDF.")
        return CONFIRM_PDF_READ

async def daily_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    userdata = get_user_data(user_id)
    day = userdata.get("current_day", 0)
    if day == 0:
        await update.message.reply_text("Please confirm you have read the PDF first by typing 'done'.")
        return CONFIRM_PDF_READ
    if day > len(DAILY_EXERCISES):
        await update.message.reply_text(
            "Congrats on completing the 30-day program!\n"
            "You can now use commands to work on specific areas:\n"
            "/evidence - for Evidence Inventory\n"
            "/experiment - for Failure experiments\n"
            "/ifthen - to create If-Then plans\n"
            "/smallwin - to celebrate small wins\n"
            "/review - to do a Quarterly Mindset Review\n"
            "Type /help for more."
        )
        return ConversationHandler.END
    exercise_text = DAILY_EXERCISES[day - 1]
    await update.message.reply_text(f"{exercise_text}\nType 'done' when you complete this exercise.")
    return DAILY_EXERCISE

async def daily_exercise_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    userdata = get_user_data(user_id)
    userdata["current_day"] = userdata.get("current_day", 1) + 1
    save_user_data(user_id, userdata)
    if userdata["current_day"] > len(DAILY_EXERCISES):
        await update.message.reply_text("You've completed the 30-day mindset installation! Great work. Use /help to explore next steps.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Great! Type 'next' for your next exercise.")
        return DAILY_EXERCISE

# Evidence Inventory feature handlers:
async def start_evidence_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Let's work on your limiting belief.\nWhat is one limiting belief holding you back?")
    return EVIDENCE_BELIEF

async def evidence_belief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    belief = update.message.text.strip()
    context.user_data['limiting_belief'] = belief
    await update.message.reply_text("List 3 instances that prove this belief wrong (separate by commas).")
    return EVIDENCE_EVIDENCE

async def evidence_evidence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    evidence_list = [e.strip() for e in update.message.text.split(",")]
    context.user_data['belief_evidence'] = evidence_list
    await update.message.reply_text("Rewrite this belief based on the evidence.")
    return EVIDENCE_REWRITE

async def evidence_rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rewrite = update.message.text.strip()
    user_id = update.effective_user.id
    userdata = get_user_data(user_id)
    userdata["evidence_inventory"].append({
        "belief": context.user_data.get('limiting_belief'),
        "evidence": context.user_data.get('belief_evidence'),
        "rewrite": rewrite,
        "timestamp": datetime.now().isoformat()
    })
    save_user_data(user_id, userdata)
    await update.message.reply_text(
        "Amazing! You've added a new rewired belief to your Evidence Inventory.\n"
        "You can work on another belief with /evidence or continue your mindset exercises with 'next'."
    )
    return ConversationHandler.END

# Failure experiment handlers:
async def start_experiment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Let's set a Minimum Viable Experiment (MVE).\nWhat's one goal you've been avoiding?")
    return MVE_GOAL

async def mve_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mve_goal'] = update.message.text.strip()
    await update.message.reply_text("What’s the worst that can happen if this experiment fails?")
    return MVE_WORST

async def mve_worst(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mve_worst'] = update.message.text.strip()
    await update.message.reply_text("Even if it fails, what will you learn from it?")
    return MVE_LEARNINGS

async def mve_learnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mve_data = {
        "goal": context.user_data.get('mve_goal'),
        "worst": context.user_data.get('mve_worst'),
        "learning": update.message.text.strip(),
        "timestamp": datetime.now().isoformat()
    }
    userdata = get_user_data(user_id)
    userdata["mve_logs"].append(mve_data)
    save_user_data(user_id, userdata)
    await update.message.reply_text("Great! Your experiment is logged. Take action and return for a check-in anytime.")
    return ConversationHandler.END

# If-Then plan handlers:
async def start_ifthen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Let's build an If-Then plan to eliminate friction.\n"
        "Complete this sentence: If [trigger], then I will [action].\n"
        "Send your If-Then statement."
    )
    return IFTHEN_INPUT

async def ifthen_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan = update.message.text.strip()
    user_id = update.effective_user.id
    userdata = get_user_data(user_id)
    userdata["if_then_plans"].append({
        "plan": plan,
        "timestamp": datetime.now().isoformat()
    })
    save_user_data(user_id, userdata)
    await update.message.reply_text(f"Saved your If-Then plan:\n{plan}\nUse /ifthen anytime to add more.")
    return ConversationHandler.END

# Small win celebration handlers:
async def start_smallwin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "What’s a small win you achieved today? Remember, small wins keep momentum going!"
    )
    return SMALL_WIN_INPUT

async def smallwin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    win = update.message.text.strip()
    user_id = update.effective_user.id
    userdata = get_user_data(user_id)
    userdata["small_win_log"].append({
        "win": win,
        "timestamp": datetime.now().isoformat()
    })
    save_user_data(user_id, userdata)
    await update.message.reply_text(
        f"Awesome! Celebrate that win fully.\nKeep it up and share more small wins anytime with /smallwin."
    )
    return ConversationHandler.END

# Quarterly mindset review handlers:
async def start_quarterly_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Let’s do your Quarterly Mindset Review.\n"
        "1. Are you still aligned with your purpose?\n"
        "2. What habits need adjustment?\n"
        "3. What is your biggest constraint right now?\n"
        "4. What’s your next smallest experiment?"
        "\nPlease send your answers separated by semicolons (;)."
    )
    return QUARTERLY_REVIEW

async def quarterly_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    responses = update.message.text.split(";")
    if len(responses) < 4:
        await update.message.reply_text("Please provide all 4 review answers separated by semicolons(;).")
        return QUARTERLY_REVIEW
    user_id = update.effective_user.id
    review_data = {
        "purpose_alignment": responses[0].strip(),
        "habit_adjustments": responses[1].strip(),
        "biggest_constraint": responses[2].strip(),
        "next_experiment": responses[3].strip(),
        "timestamp": datetime.now().isoformat()
    }
    userdata = get_user_data(user_id)
    userdata["quarterly_reviews"].append(review_data)
    save_user_data(user_id, userdata)
    await update.message.reply_text("Quarterly Review saved! Remember to keep maintaining your mindset systems.")
    return ConversationHandler.END

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start - Begin or continue after confirming PDF\n"
        "/evidence - Work on Evidence Inventory to rewire beliefs\n"
        "/experiment - Log a Minimum Viable Experiment\n"
        "/ifthen - Create an If-Then plan for better systems\n"
        "/smallwin - Celebrate and log small daily wins\n"
        "/review - Conduct a Quarterly Mindset Review\n"
        "'done' - Confirm completing current exercise\n"
        "'next' - Get today's mindset exercise\n"
        "/help - This help message"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Goodbye! Come back anytime to continue your mindset growth.")
    return ConversationHandler.END

def main():
    import os
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("Please set the TELEGRAM_BOT_TOKEN environment variable.")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CONFIRM_PDF_READ: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_pdf_read)],
            DAILY_EXERCISE: [
                MessageHandler(filters.Regex('^(done|next)$'), daily_exercise_done),
                MessageHandler(filters.Regex('^(next)$'), daily_exercise)
            ],
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
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('help', help_command)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('evidence', start_evidence_inventory))
    application.add_handler(CommandHandler('experiment', start_experiment))
    application.add_handler(CommandHandler('ifthen', start_ifthen))
    application.add_handler(CommandHandler('smallwin', start_smallwin))
    application.add_handler(CommandHandler('review', start_quarterly_review))

    logger.info("Mindset Bot started")
    application.run_polling()

if __name__ == '__main__':
    main()
