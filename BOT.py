import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
import json

PRE_PURCHASE_QUESTION = range(1)
WAITING_FOR_PURCHASE = range(1)
POST_PURCHASE_FEEDBACK = range(1)
FOCUS_AREA = range(1)
SYSTEM_BUILDING = range(1)
CHECKIN_RESPONSE = range(1)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

PAYSTACK_LINK = "https://paystack.com/buy/unleash-your-ultimate-mindset-the-5-step-blueprint-to-uwsyav"

class MindsetBot:
    def __init__(self):
        self.user_data_file = "user_data.json"
        self.load_user_data()
        
        self.mindset_questions = [
            "So you want to change something about yourself. Help me understand—what does change look like for you? What's the outcome you're actually chasing?",
            "Interesting. So {outcome} is the goal. But here's the real question: what stops you from having that NOW? What's the actual blocker?",
            "Got it. So it's about {blocker}. Is that something outside your control, or something inside?",
            "And that {inner_issue}—when did it start? Was it always there, or did something create it?",
            "That makes sense. But let me ask: have you EVER overcome something similar before? Any time you crushed a challenge?",
            "Yes! So you KNOW how. What was different about that situation versus now? Why could you do it then but not now?",
            "So it comes down to {difference}. That's the real insight. But here's what I want to know: what if you brought THAT version of you to this situation? What would shift?",
            "Right. So you already have the capability. It's a mindset thing, not a skill thing. The question becomes: what's keeping you stuck in the old mindset?",
            "Is it fear? Doubt? Past failures? Feeling like you don't deserve it? What's the real belief holding you back?",
            "Okay. Here's what's clear: your challenge isn't about trying harder or knowing more. It's about rewiring that belief at the deepest level—your operating system. Does that resonate?"
        ]
    
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
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_data = self.get_user_data(user_id)
        
        if user_data.get('purchased'):
            await update.message.reply_text(
                f"Hey {first_name}! Welcome back! 🙌\n\n"
                "Ready to keep building? What's on your mind?"
            )
            return CHECKIN_RESPONSE
        
        if user_data.get('question_count', 0) > 0:
            question_count = user_data.get('question_count', 0)
            await update.message.reply_text(
                f"Hey {first_name}! Let's pick up where we left off."
            )
            if question_count < 10:
                next_question = self.mindset_questions[question_count]
                await update.message.reply_text(next_question)
                return PRE_PURCHASE_QUESTION
            else:
                await update.message.reply_text(
                    "Looks like you're ready for the next step. Check the message below 👇"
                )
                return WAITING_FOR_PURCHASE
        
        await update.message.reply_text(
            f"Hey {first_name}! 👋\n\n"
            "I'm glad you're here. I want to ask you something real:\n\n"
            "**What's the one thing about yourself right now that you want to change?**"
        )
        
        self.update_user_data(user_id, {
            'first_name': first_name,
            'started_at': str(datetime.now()),
            'question_count': 0,
            'responses': []
        })
        
        return PRE_PURCHASE_QUESTION
    
    async def pre_purchase_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        user_data = self.get_user_data(user_id)
        question_count = user_data.get('question_count', 0)
        responses = user_data.get('responses', [])
        
        responses.append(user_response)
        question_count += 1
        
        self.update_user_data(user_id, {
            'question_count': question_count,
            'responses': responses
        })
        
        if question_count < 10:
            next_question = self.mindset_questions[question_count]
            await update.message.reply_text(next_question)
            return PRE_PURCHASE_QUESTION
        else:
            sales_pitch = (
                f"Okay {first_name}, I've learned a lot about where you are.\n\n"
                f"Here's what's clear to me: your challenge isn't about trying harder or knowing more.\n\n"
                f"It's about having the right **framework**—a system that rewires how you operate at the deepest level.\n\n"
                f"I've built exactly that. It's called **'Unleash Your Ultimate Mindset'**—a complete blueprint that turns insight into unshakeable action.\n\n"
                f"🔹 Build unshakeable self-belief (even when doubt screams)\n"
                f"🔹 Create systems that make procrastination impossible\n"
                f"🔹 Turn failure into your fastest teacher\n"
                f"🔹 Make success feel inevitable, not exhausting\n"
                f"🔹 Get 3-day check-ins with me for accountability\n\n"
                f"**Investment:** GHS 75 ($6.85) — less than two coffees.\n\n"
                f"This changes everything if you're ready."
            )
            
            keyboard = [
                [InlineKeyboardButton("🔥 Yes, I'm ready", callback_data="show_payment")],
                [InlineKeyboardButton("I have one more question", callback_data="ask_question")],
                [InlineKeyboardButton("Let me think about it", callback_data="think_about_it")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(sales_pitch, reply_markup=reply_markup)
            
            return WAITING_FOR_PURCHASE
    
    async def waiting_for_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        first_name = query.from_user.first_name
        
        if query.data == "show_payment":
            payment_message = (
                f"Perfect, {first_name}! 🔥\n\n"
                f"👉 **Grab your access here:** {PAYSTACK_LINK}\n\n"
                "**Here's what happens:**\n"
                "1️⃣ Complete payment (GHS 75)\n"
                "2️⃣ Get the PDF in your email instantly\n"
                "3️⃣ Read through it at your pace\n"
                "4️⃣ Click the link at the end of the PDF\n"
                "5️⃣ We build YOUR custom mindset system\n\n"
                "Let's go. See you on the other side!"
            )
            await query.edit_message_text(payment_message)
            
            keyboard = [[InlineKeyboardButton("✅ I've Paid & Have the PDF", callback_data="confirm_payment")]]
            await query.message.reply_text(
                "Once you've completed payment and have the PDF, tap below:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return WAITING_FOR_PURCHASE
        
        elif query.data == "ask_question":
            await query.edit_message_text("What's your question? I'll answer, then we move forward.")
            return PRE_PURCHASE_QUESTION
        
        elif query.data == "think_about_it":
            await query.edit_message_text(
                f"No rush, {first_name}. Take your time.\n\n"
                "Type /start whenever you're ready to continue.\n\n"
                "**Real talk:** If nothing changes, where are you in 6 months?"
            )
            return ConversationHandler.END
        
        elif query.data == "confirm_payment":
            self.update_user_data(user_id, {
                'purchased': True,
                'purchase_date': str(datetime.now())
            })
            
            await query.edit_message_text(
                f"🎉 You're in, {first_name}!\n\n"
                "Check your email for the PDF. Read it whenever you're ready—no rush.\n\n"
                "When you're done, use the link at the end of the PDF (or type /done).\n\n"
                "That's when we build YOUR system. 💪"
            )
            return ConversationHandler.END
        
        return WAITING_FOR_PURCHASE
    
    async def done_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_data = self.get_user_data(user_id)
        
        if not user_data.get('purchased'):
            await update.message.reply_text(
                "Hey! Looks like you haven't purchased yet.\n\n"
                "Type /start to get started."
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            f"Welcome back, {first_name}! 🙌\n\n"
            "So you finished the PDF. Nice.\n\n"
            "**What part hit you the hardest?** What made you go 'yeah, that's exactly me'?"
        )
        return POST_PURCHASE_FEEDBACK
    
    async def post_purchase_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'pdf_feedback': user_response})
        
        reply = (
            f"That insight right there, {first_name}—that's powerful.\n\n"
            "So if that's the biggest thing that resonated, let's use it.\n\n"
            "The 5-step framework breaks down into specific areas. "
            "**Which one is your biggest friction point right now?**\n\n"
            "**A) Clarity** — I'm not 100% sure what I'm working toward\n"
            "**B) Belief** — I know what to do but doubt kills me\n"
            "**C) Failure** — I'm scared to try because I might fail\n"
            "**D) Systems** — I rely on willpower instead of design\n"
            "**E) Momentum** — I start strong but can't keep it going\n\n"
            "Which one? Just type the letter."
        )
        
        await update.message.reply_text(reply)
        return FOCUS_AREA
    
    async def focus_area(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        choice = update.message.text.upper().strip()
        
        exercises = {
            'A': (
                "**🎯 North Star Exercise**\n\n"
                "Clarity is everything. If you're climbing the wrong ladder, speed doesn't matter.\n\n"
                "Complete this:\n"
                "'In 5 years, I want to be known as someone who...'\n\n"
                "Send me your answer. Be honest—does this *excite* you, or are you trying to impress someone?"
            ),
            'B': (
                f"**🧠 Evidence Inventory**\n\n"
                f"Let's catch the lies your brain tells you, {first_name}.\n\n"
                f"1. Write down ONE limiting belief\n"
                f"   (like: 'I'm not disciplined' or 'I always give up')\n\n"
                f"2. List 3 times you PROVED it wrong\n"
                f"   (big or small—anything counts)\n\n"
                f"Send me both. We're going to demolish that lie with facts."
            ),
            'C': (
                "**🔬 MVE Challenge**\n\n"
                "Failure is data. Let's make it work for you.\n\n"
                "Pick ONE goal you've been avoiding.\n\n"
                "Answer:\n"
                "1. What's the smallest step in the next 2 hours?\n"
                "2. What's the worst that happens if it fails?\n"
                "3. What do you learn even if it fails?\n\n"
                "Send me your goal + MVE. Let's run the experiment."
            ),
            'D': (
                "**⚙️ If-Then Builder**\n\n"
                "Systems beat willpower every time.\n\n"
                "Think of ONE action you keep 'forgetting'.\n\n"
                "Complete this:\n"
                "'If [trigger], then I will [specific action].'\n\n"
                "Example: 'If I pour coffee, then I journal for 5 min.'\n\n"
                "What's YOUR If-Then? Send it."
            ),
            'E': (
                "**🔥 Small Win Ritual**\n\n"
                "Momentum comes from stacking tiny wins.\n\n"
                "1. Pick the SMALLEST action you can do today\n"
                "   (Not 'run 5 miles'—think 'put on shoes')\n\n"
                "2. After doing it, say:\n"
                "   'I did what I said. That's who I am.'\n\n"
                "What's your small win TODAY? Tell me now."
            )
        }
        
        if choice in exercises:
            self.update_user_data(user_id, {'focus_area': choice})
            await update.message.reply_text(exercises[choice])
            return SYSTEM_BUILDING
        else:
            reply = (
                "Got it. Just reply with the letter:\n\n"
                "**A** - Clarity\n**B** - Belief\n**C** - Failure\n"
                "**D** - Systems\n**E** - Momentum"
            )
            await update.message.reply_text(reply)
            return FOCUS_AREA
    
    async def system_building(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_input = update.message.text
        
        self.update_user_data(user_id, {
            'exercise_response': user_input,
            'last_interaction': str(datetime.now())
        })
        
        reply = (
            f"This is solid, {first_name}. You're already thinking differently. 🔥\n\n"
            "Here's what to do in the next 3 days:\n\n"
            "**1. Run the experiment**\n"
            "Don't overthink. Just do it.\n\n"
            "**2. Track what happens**\n"
            "Did it work? What got in the way? What surprised you?\n\n"
            "**3. Come back**\n"
            "I'll check in in 3 days, or message /checkin if you need support sooner.\n\n"
            "You're not looking for perfection. Just the next data point.\n\n"
            "The winning version of you? They just keep showing up and adjusting.\n\n"
            "Let's go. Talk soon! 💪"
        )
        
        await update.message.reply_text(reply)
        
        job_queue = context.application.job_queue
        chat_id = update.effective_chat.id
        
        current_jobs = job_queue.get_jobs_by_name(f"checkin_{user_id}")
        for job in current_jobs:
            job.schedule_removal()
        
        job_queue.run_once(
            self.send_checkin,
            when=timedelta(days=3),
            data={'user_id': user_id, 'chat_id': chat_id},
            name=f"checkin_{user_id}"
        )
        
        return ConversationHandler.END
    
    async def send_checkin(self, context: ContextTypes.DEFAULT_TYPE):
        job_data = context.job.data
        user_id = job_data['user_id']
        chat_id = job_data['chat_id']
        
        user_data = self.get_user_data(user_id)
        first_name = user_data.get('first_name', 'there')
        check_in_count = user_data.get('check_in_count', 0)
        
        self.update_user_data(user_id, {'check_in_count': check_in_count + 1})
        
        messages = [
            (
                f"Hey {first_name}! 👋\n\n"
                f"3 days in. How'd the experiment go?\n\n"
                f"Tell me:\n"
                f"1. What did you try?\n"
                f"2. What happened?\n"
                f"3. What'd you learn?\n\n"
                f"No failure, just data."
            ),
            (
                f"Check-in #2, {first_name}! 💪\n\n"
                f"How's the system feeling? Any shifts yet?\n\n"
                f"• What's working?\n"
                f"• What's still hard?\n"
                f"• What needs adjusting?\n\n"
                f"Be real with me."
            ),
            (
                f"Week 1.5, {first_name}! 🔥\n\n"
                f"This is where people either quit or level up.\n\n"
                f"Are you still showing up?\n"
                f"Or are old patterns creeping back?\n\n"
                f"If struggling: That's where breakthroughs happen.\n\n"
                f"What's the real update?"
            ),
            (
                f"Two weeks down, {first_name}! 🎉\n\n"
                f"This is a milestone. You're sustaining momentum.\n\n"
                f"1. Biggest shift you've noticed?\n"
                f"2. What's starting to feel automatic?\n"
                f"3. What's next to tackle?\n\n"
                f"Let's keep going."
            )
        ]
        
        message = messages[min(check_in_count, len(messages) - 1)]
        await context.bot.send_message(chat_id=chat_id, text=message)
        
        context.application.job_queue.run_once(
            self.send_checkin,
            when=timedelta(days=3),
            data=job_data,
            name=f"checkin_{user_id}"
        )
    
    async def checkin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_data = self.get_user_data(user_id)
        
        if not user_data.get('purchased'):
            await update.message.reply_text(
                "Hey! Grab the PDF first.\n\n"
                "Type /start to get started."
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            f"Hey {first_name}! 💪\n\n"
            "What's on your mind? Tell me:\n\n"
            "• What you're working on\n"
            "• What's working\n"
            "• What's stuck\n\n"
            "I'm here."
        )
        return CHECKIN_RESPONSE
    
    async def checkin_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_message = update.message.text.lower()
        
        if any(word in user_message for word in ['great', 'good', 'working', 'progress', 'better', 'awesome']):
            reply = (
                f"YES, {first_name}! 🔥\n\n"
                "Keep riding that momentum.\n\n"
                "**Next level:** What would make this even better? Don't settle—keep pushing."
            )
        elif any(word in user_message for word in ['stuck', 'struggling', 'hard', 'difficult', 'failing', 'blocked']):
            reply = (
                f"Thanks for being real, {first_name}.\n\n"
                "Struggle = you're pushing boundaries. That's good.\n\n"
                "Let's troubleshoot:\n"
                "• Goal too big? Break it smaller (MVE style)\n"
                "• Missing system? Add an If-Then\n"
                "• Doubt creeping in? Evidence Inventory again\n\n"
                "Which resonates? Let's fix it."
            )
        elif any(word in user_message for word in ['quit', 'give up', 'stop', 'done', 'tired']):
            reply = (
                f"Hold up, {first_name}.\n\n"
                "What would you tell someone you love if they were here right now?\n\n"
                "I bet: 'Keep going. One more shot.'\n\n"
                "So: Give me one more experiment. One more MVE.\n\n"
                "Most people quit right before breakthrough. You're not most people.\n\n"
                "You in?"
            )
        else:
            reply = (
                f"Thanks for the update, {first_name}.\n\n"
                "You're in the messy middle. That's where growth happens.\n\n"
                "Keep showing up. Keep adjusting. Keep collecting data.\n\n"
                "**Right now:** What's the smallest action that moves you forward today?\n\n"
                "Do that. Then again tomorrow.\n\n"
                "You've got this. 💪"
            )
        
        await update.message.reply_text(reply)
        self.update_user_data(user_id, {'last_interaction': str(datetime.now())})
        
        return ConversationHandler.END
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        help_text = (
            "**Commands:**\n\n"
            "/start - Begin conversation\n"
            "/done - Finished reading PDF\n"
            "/checkin - Check in anytime\n"
            "/help - This menu\n"
            "/cancel - End chat\n\n"
            "Or just message me. I'm here. 💪"
        )
        await update.message.reply_text(help_text)
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        first_name = update.effective_user.first_name
        await update.message.reply_text(
            f"No worries, {first_name}!\n\n"
            "When you're ready, type /start.\n\n"
            "Best time to start was yesterday. Second best is now. 💪"
        )
        return ConversationHandler.END


def main():
    TOKEN = "8342995076:AAH9TosXOwx_1KF3Kb5TwrKEcVlWqUmPEBI"
    
    application = Application.builder().token(TOKEN).build()
    bot = MindsetBot()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', bot.start),
        ],
        states={
            PRE_PURCHASE_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.pre_purchase_question)
            ],
            WAITING_FOR_PURCHASE: [
                CallbackQueryHandler(bot.waiting_for_purchase),
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.pre_purchase_question)
            ],
            POST_PURCHASE_FEEDBACK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.post_purchase_feedback)
            ],
            FOCUS_AREA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.focus_area)
            ],
            SYSTEM_BUILDING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.system_building)
            ],
            CHECKIN_RESPONSE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.checkin_response)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', bot.cancel),
            CommandHandler('checkin', bot.checkin_command),
            CommandHandler('done', bot.done_command),
            CommandHandler('help', bot.help_command),
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', bot.help_command))
    
    print("🚀 Mindset Bot Running")
    print("✅ 10-question mindset exchange active")
    print("✅ Clear pre-purchase flow")
    print("✅ Post-purchase support ready")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
