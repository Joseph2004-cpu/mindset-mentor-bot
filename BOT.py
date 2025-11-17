import logging
import json
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler, JobQueue
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot states
(
    Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10,
    PRODUCT_INTRO, POST_PURCHASE, FEEDBACK, SYSTEM_GUIDANCE
) = range(14)

# Paystack link (replace with your actual link)
PAYSTACK_LINK = "https://paystack.com/buy/unleash-your-ultimate-mindset-the-5-step-blueprint-to-uwsyav"

# Question sets mapped by theme for dynamic follow-ups
QUESTION_SETS = {
    'stuck': [
        "When you try moving forward, what's the biggest thing holding you back?",
        "Do you feel it's not knowing the next step, or not doing it?",
        "What's one small change you'd want to see today?"
    ],
    'motivation': [
        "What usually gets you motivated in other areas?",
        "Can you remember a time recently when you felt very driven?",
        "What could help you keep that motivation longer?"
    ],
    'goal': [
        "When you think about your goal, do you feel excitement or pressure?",
        "What part of your goal feels most achievable right now?",
        "What would success look like for you in the next month?"
    ],
    # Add more themes and questions as needed...
}

GENERIC_FOLLOW_UPS = [
    "Can you tell me more about that?",
    "How does that affect your daily routine?",
    "What would you change if you could?"
]

class MindsetMentorBot:
    def __init__(self):
        # Load or initialize user data store
        self.user_data_file = "user_data.json"
        self.load_user_data()

    def load_user_data(self):
        try:
            with open(self.user_data_file, 'r') as f:
                self.user_db = json.load(f)
        except FileNotFoundError:
            self.user_db = {}

    def save_user_data(self):
        with open(self.user_data_file, 'w') as f:
            json.dump(self.user_db, f, indent=2)

    def get_user_data(self, user_id):
        return self.user_db.get(str(user_id), {})

    def update_user_data(self, user_id, data):
        user_id_str = str(user_id)
        if user_id_str not in self.user_db:
            self.user_db[user_id_str] = {}
        self.user_db[user_id_str].update(data)
        self.save_user_data()

    # Start command - welcome and first lead question
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.effective_user
        user_id = user.id

        user_data = self.get_user_data(user_id)
        if user_data.get('purchased', False):
            await update.message.reply_text(
                f"Welcome back, {user.first_name}! 🙌\n"
                "Ready to continue building your system? Type /continue or tell me how I can help."
            )
            return POST_PURCHASE

        # Reset question count & conversation history on new start
        self.update_user_data(user_id, {
            'question_count': 1,
            'conversation': [],
            'started_at': str(datetime.now())
        })

        welcome_msg = (
            f"Hey {user.first_name}! 👋\n\n"
            "**Let's get real:** What's the one thing you wish you could change "
            "about how you're showing up right now?\n\n(No judgment—just honest thoughts.)"
        )
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
        return Q1

    # Helper to detect theme from reply (basic keyword detection)
    def detect_theme(self, text):
        text = text.lower()
        if any(w in text for w in ['stuck', 'block', 'nothing', 'stop']):
            return 'stuck'
        if any(w in text for w in ['motivate', 'motivation', 'lazy', 'discipline']):
            return 'motivation'
        if any(w in text for w in ['goal', 'success', 'achieve']):
            return 'goal'
        return None

    # General method to ask next dynamic question or move to product intro
    async def ask_next_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        user_response = update.message.text

        user_data = self.get_user_data(user_id)

        # Append the current user response to conversation log
        conv = user_data.get('conversation', [])
        conv.append(user_response)

        # Increment question count
        question_count = user_data.get('question_count', 1)

        # Save updated data
        self.update_user_data(user_id, {
            'conversation': conv,
            'question_count': question_count
        })

        # For Q1 - detect theme for follow-ups, else use the last known theme
        theme = user_data.get('theme')
        if question_count == 1:
            theme = self.detect_theme(user_response) or 'general'
            self.update_user_data(user_id, {'theme': theme})

        # Select next question based on theme and question count
        next_question = None
        if theme in QUESTION_SETS:
            questions = QUESTION_SETS[theme]
            idx = question_count - 1  # zero-based index
            if idx < len(questions):
                next_question = questions[idx]
        if not next_question:
            # fallback to generic questions or signal end of questions
            if question_count < 10:
                next_question = random.choice(GENERIC_FOLLOW_UPS)
            else:
                # End question series and go to product intro
                await update.message.reply_text(
                    "Thanks for sharing so much! I have something I want to show you that could help.\n"
                    "Do you want to check it out?"
                )
                keyboard = [
                    [InlineKeyboardButton("Yes, show me!", callback_data="show_payment")],
                    [InlineKeyboardButton("Not now", callback_data="decline_payment")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Choose an option:", reply_markup=reply_markup)
                return PRODUCT_INTRO

        # Increase question count and save
        self.update_user_data(user_id, {'question_count': question_count + 1})

        # Ask next question
        await update.message.reply_text(next_question)
        # Return next state based on question count (Q2..Q10)
        if question_count == 1:
            return Q2
        elif question_count == 2:
            return Q3
        elif question_count == 3:
            return Q4
        elif question_count == 4:
            return Q5
        elif question_count == 5:
            return Q6
        elif question_count == 6:
            return Q7
        elif question_count == 7:
            return Q8
        elif question_count == 8:
            return Q9
        elif question_count == 9:
            return Q10
        else:
            return ConversationHandler.END

    # Handle button presses for product offer and payment
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        first_name = query.from_user.first_name

        if query.data == "show_payment":
            payment_message = (
                f"Great, {first_name}! Let's get you instant access 👇\n\n"
                f"[Pay here]({PAYSTACK_LINK}) (GHS 75 / $6.85)\n\n"
                "After payment, check your email for the PDF.\n"
                "Then come back here to type /done or tap the 'Done' button below."
            )
            keyboard = [
                [InlineKeyboardButton("✅ I've Completed Payment", callback_data="confirm_payment")],
                [InlineKeyboardButton("Need help", callback_data="need_help")]
            ]
            await query.edit_message_text(payment_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return PRODUCT_INTRO

        elif query.data == "confirm_payment":
            self.update_user_data(user_id, {
                'purchased': True,
                'purchase_date': str(datetime.now()),
                'check_in_count': 0
            })
            await query.edit_message_text(
                f"🎉 Thanks for your purchase, {first_name}!\n\n"
                "Check your email for the PDF now. When you're ready, type /done or click the button below."
            )
            done_button = [[InlineKeyboardButton("Done", callback_data="done_reading")]]
            await query.message.reply_text(
                "Click 'Done' when you've finished reading:",
                reply_markup=InlineKeyboardMarkup(done_button)
            )
            # Schedule first check-in
            job_queue = context.application.job_queue
            job_queue.run_once(
                self.send_checkin,
                when=timedelta(days=3),
                data={'user_id': user_id, 'chat_id': query.message.chat_id},
                name=f"checkin_{user_id}"
            )
            return ConversationHandler.END

        elif query.data == "done_reading":
            await query.edit_message_text(
                f"Welcome back, {first_name}! 🙌\nLet's discuss what you learned."
            )
            await query.message.reply_text(
                "What part of the PDF hit home hardest for you?\n(Be honest!)"
            )
            return FEEDBACK

        elif query.data == "decline_payment":
            await query.edit_message_text(
                "No worries! Take your time. Come back anytime by typing /start."
            )
            return ConversationHandler.END

        elif query.data == "need_help":
            await query.edit_message_text(
                "I'm here to help! What questions do you have? Please type them below."
            )
            return PRODUCT_INTRO

        return ConversationHandler.END

    # Gather feedback after PDF reading
    async def feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_response = update.message.text
        user_id = update.effective_user.id
        self.update_user_data(user_id, {'pdf_feedback': user_response})
        await update.message.reply_text(
            "Thanks for sharing that insight! Based on what you said, "
            "where's your biggest friction right now?\n\n"
            "A) Clarity\nB) Belief\nC) Failure\nD) Systems\nE) Momentum\n\n"
            "Just reply with the letter."
        )
        return SYSTEM_GUIDANCE

    # System building exercise based on feedback
    async def system_guidance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_choice = update.message.text.upper()
        user_id = update.effective_user.id

        exercises = {
            'A': "🎯 The North Star Exercise: Define how you want to be known in 5 years...",
            'B': "🧠 The Evidence Inventory: Identify limiting beliefs and counter examples...",
            'C': "🔬 The MVE Challenge: Pick a small step toward a goal and test it...",
            'D': "⚙️ The If-Then Builder: Create triggers linked to actions...",
            'E': "🔥 The Small Win Ritual: Start a streak of tiny meaningful achievements...",
        }

        if user_choice in exercises:
            self.update_user_data(user_id, {'focus_area': user_choice})
            await update.message.reply_text(exercises[user_choice])
        else:
            await update.message.reply_text(
                "I didn't get that. Please reply with one of these letters: A, B, C, D, or E."
            )
            return SYSTEM_GUIDANCE

        # End or loop back short term for deeper mentoring
        await update.message.reply_text(
            "Try this exercise and come back in a few days! You can use /checkin anytime to update me."
        )
        return ConversationHandler.END

    # Automated check-ins every 3 days
    async def send_checkin(self, context: ContextTypes.DEFAULT_TYPE):
        job_data = context.job.data
        user_id = job_data['user_id']
        chat_id = job_data['chat_id']

        user_data = self.get_user_data(user_id)
        first_name = user_data.get('first_name', 'there')
        count = user_data.get('check_in_count', 0) + 1
        self.update_user_data(user_id, {'check_in_count': count})

        msg = (
            f"Hey {first_name}, it's been 3 days! How did your recent experiment go? "
            "Tell me what you tried, what happened, and what you learned."
        )
        await context.bot.send_message(chat_id=chat_id, text=msg)

        # Schedule next check-in
        context.application.job_queue.run_once(
            self.send_checkin,
            when=timedelta(days=3),
            data={'user_id': user_id, 'chat_id': chat_id},
            name=f"checkin_{user_id}"
        )

    # Manual check-in command handler
    async def checkin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        if not user_data.get('purchased'):
            await update.message.reply_text(
                "Looks like you haven't grabbed the PDF yet. Type /start to learn more!"
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "Great to see you checking in! What's on your mind regarding your progress?"
        )
        return ConversationHandler.END

def main():
    bot = MindsetMentorBot()
    application = Application.builder().token("<YOUR_BOT_TOKEN>").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', bot.start)],
        states={
            Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ask_next_question)],
            Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ask_next_question)],
            Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ask_next_question)],
            Q4: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ask_next_question)],
            Q5: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ask_next_question)],
            Q6: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ask_next_question)],
            Q7: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ask_next_question)],
            Q8: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ask_next_question)],
            Q9: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ask_next_question)],
            Q10: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ask_next_question)],
            PRODUCT_INTRO: [CallbackQueryHandler(bot.button_handler)],
            POST_PURCHASE: [CommandHandler('continue', bot.start)],
            FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.feedback)],
            SYSTEM_GUIDANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.system_guidance)]
        },
        fallbacks=[CommandHandler('start', bot.start)],
        per_user=True,
        per_chat=True
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('done', bot.button_handler))
    application.add_handler(CommandHandler('checkin', bot.checkin))

    application.run_polling()

if __name__ == '__main__':
    main()
