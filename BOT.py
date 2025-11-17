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
    JobQueue,
)
import json

(CONVERSATION, PRODUCT_INTRO, PDF_READING, PDF_FEEDBACK, FOCUS_AREA, 
 SYSTEM_BUILDING, CHECKIN_RESPONSE) = range(7)

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Your Paystack payment link
PAYSTACK_LINK = "https://paystack.com/buy/unleash-your-ultimate-mindset-the-5-step-blueprint-to-uwsyav"

class MindsetBot:
    def __init__(self):
        self.user_data_file = "user_data.json"
        self.load_user_data()
        self.pdf_redirect_message = (
            "🔗 **Got value from this? Let's go deeper.**\n\n"
            "Click here to continue: t.me/YOUR_BOT_USERNAME?start=pdf_redirect\n\n"
            "We'll transform this knowledge into your personal system. 💪"
        )
    
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
    
    def adapt_response(self, text: str) -> str:
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['stuck', 'stagnant', 'plateau', 'same place']):
            return "stuck"
        elif any(word in text_lower for word in ['motivat', 'discipline', 'lazy', 'willpower']):
            return "motivation"
        elif any(word in text_lower for word in ['goal', 'achieve', 'success', 'dream', 'want']):
            return "goals"
        elif any(word in text_lower for word in ['start', 'procrastin', 'delay', 'later']):
            return "procrastination"
        elif any(word in text_lower for word in ['fail', 'fear', 'scared', 'anxious', 'afraid']):
            return "fear"
        elif any(word in text_lower for word in ['money', 'income', 'business', 'career', 'financial']):
            return "money"
        elif any(word in text_lower for word in ['relationship', 'partner', 'people', 'social']):
            return "relationships"
        elif any(word in text_lower for word in ['health', 'weight', 'fitness', 'gym', 'diet']):
            return "health"
        elif any(word in text_lower for word in ['time', 'busy', 'overwhelm', 'stress', 'chaos']):
            return "time"
        elif any(word in text_lower for word in ['confident', 'doubt', 'imposter', 'good enough']):
            return "confidence"
        return "general"
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_data = self.get_user_data(user_id)
        
        if user_data.get('purchased'):
            await update.message.reply_text(
                f"Hey {first_name}! Welcome back! 🙌\n\n"
                "Ready to keep building? What's on your mind right now?"
            )
            return CHECKIN_RESPONSE
        
        if user_data.get('initial_concern'):
            await update.message.reply_text(
                f"Hey {first_name}! 👋 Good to see you again.\n\n"
                "How have things been since we last talked?"
            )
        else:
            await update.message.reply_text(
                f"Hey {first_name}! 👋\n\n"
                "I'm glad you're here. Let me ask you something real:\n\n"
                "**What's the one thing about yourself right now that you want to change?**"
            )
        
        self.update_user_data(user_id, {'first_name': first_name, 'started_at': str(datetime.now())})
        return CONVERSATION

    async def handle_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        user_data = self.get_user_data(user_id)
        concern_type = self.adapt_response(user_response)
        
        if not user_data.get('initial_concern'):
            self.update_user_data(user_id, {
                'initial_concern': user_response,
                'concern_type': concern_type,
                'conversation_count': 0
            })
            
            concern_responses = {
                'stuck': f"That stuck feeling is real. You're doing things, but nothing's shifting, right?\n\n**Real question:** Do you not know what to do, or do you know but can't make yourself do it?",
                'motivation': f"Here's the truth, {first_name}—motivation isn't your problem. You're probably consistent in *some* things but completely blocked in others.\n\nWhat's one thing you *always* show up for, no matter what?",
                'goals': f"I love that you have vision. But let me ask:\n\nWhen you picture achieving this, do you feel **excited** or **scared**?",
                'procrastination': f"The resistance is real. But here's what I'm curious about:\n\nWhen you DO start something, do you usually finish it? Or does resistance show up at every step?",
                'fear': f"That fear? It means you care. That's strength, not weakness.\n\n**What would you try if nobody would ever know you failed?**",
                'money': f"Money goals. I hear you. But real talk:\n\nAre you chasing money itself, or what you *think* money will give you?",
                'relationships': f"Relationships are complicated when you're not solid with yourself first.\n\nAre you trying to fix the relationship, or fix how you show up *in* it?",
                'health': f"Health goals aren't really about the gym, {first_name}.\n\nWhat's the deeper reason? What would be different if you actually did this?",
                'time': f"Too much on your plate?\n\nBe real: Are you actually too busy, or just busy with the *wrong* things?",
                'confidence': f"That voice telling you you're not enough? It's lying.\n\nTell me: What's one thing you *know* you're genuinely good at?",
                'general': f"Got it. So that's what's on your mind.\n\nIf the version of you who *already solved* this was here, what would they tell you is different about how they think?"
            }
            
            reply = concern_responses.get(concern_type, concern_responses['general'])
            await update.message.reply_text(reply)
            return CONVERSATION
        
        context.user_data['response_count'] = context.user_data.get('response_count', 0) + 1
        response_count = context.user_data['response_count']
        
        if response_count == 1:
            self.update_user_data(user_id, {'msg_response_1': user_response})
            reply = (
                f"That makes sense.\n\n"
                f"Here's what I'm noticing: Most struggles aren't about *what* you do. "
                f"They're about the operating system underneath—your mindset.\n\n"
                f"**Ever catch yourself sabotaging your own progress?** Like part of you wants to win but another part hits the brakes?"
            )
            await update.message.reply_text(reply)
            return CONVERSATION
        
        elif response_count == 2:
            self.update_user_data(user_id, {'msg_response_2': user_response})
            reply = (
                f"Right? That's the signal.\n\n"
                f"Most people try to 'push harder' or 'stay positive.' But that just burns you out faster.\n\n"
                f"The real move? **Update the operating system itself.**\n\n"
                f"If you could wake up tomorrow with an unstoppable mindset, what would you do differently?"
            )
            await update.message.reply_text(reply)
            return CONVERSATION
        
        elif response_count == 3:
            self.update_user_data(user_id, {'msg_response_3': user_response})
            reply = (
                f"That vision is possible, {first_name}. And it's engineerable.\n\n"
                f"The path between where you are and where you want to be comes down to **5 core areas:**\n\n"
                f"1️⃣ **Clarity** → Knowing who you need to become\n"
                f"2️⃣ **Belief** → Rewiring the lies your brain tells you\n"
                f"3️⃣ **Failure** → Using setbacks as fuel, not stop signs\n"
                f"4️⃣ **Systems** → Making success automatic\n"
                f"5️⃣ **Momentum** → Building unstoppable progress\n\n"
                f"Does this feel like what's been missing?"
            )
            await update.message.reply_text(reply)
            return CONVERSATION
        
        elif response_count == 4:
            self.update_user_data(user_id, {'msg_response_4': user_response})
            reply = (
                f"Exactly. Suddenly 'just believe in yourself' makes no sense, right?\n\n"
                f"So I've built something called **'Unleash Your Ultimate Mindset'**—"
                f"a complete blueprint that rewires this exact system:\n\n"
                f"✓ Unshakeable self-belief (even when doubt screams)\n"
                f"✓ Systems that make procrastination impossible\n"
                f"✓ Turning failure into your fastest teacher\n"
                f"✓ Making success feel inevitable, not exhausting\n\n"
                f"Plus, after you read it, I personally help you build your custom system.\n\n"
                f"**If you had this working in 3 months, where would you be?**"
            )
            await update.message.reply_text(reply)
            return CONVERSATION
        
        elif response_count == 5:
            self.update_user_data(user_id, {'msg_response_5': user_response})
            reply = (
                f"That's the real outcome you're after.\n\n"
                f"Here's what you get with the blueprint:\n\n"
                f"📖 The Complete 5-Step System\n"
                f"🧠 Actionable Frameworks (Evidence Inventory, MVE Method, If-Then Planning)\n"
                f"🤝 Personal Support — I help you build your custom system\n"
                f"📲 Check-ins Every 3 Days — Accountability that actually works\n\n"
                f"**Investment:** GHS 75 ($6.85)\n\n"
                f"Less than two coffees for a complete mindset shift + ongoing guidance.\n\n"
                f"Ready to do this?"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔥 Yes, let's go", callback_data="show_payment")],
                [InlineKeyboardButton("I have questions", callback_data="ask_question")],
                [InlineKeyboardButton("Need time to think", callback_data="think_about_it")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(reply, reply_markup=reply_markup)
            return PRODUCT_INTRO
        
        return CONVERSATION

    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
                "4️⃣ Click the link at the end to come back\n"
                "5️⃣ We build YOUR custom system\n\n"
                "Let's go. See you on the other side!"
            )
            await query.edit_message_text(payment_message)
            
            keyboard = [[InlineKeyboardButton("✅ I've Paid", callback_data="confirm_payment")]]
            await query.message.reply_text(
                "Once you've completed payment, tap below:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return PRODUCT_INTRO
            
        elif query.data == "ask_question":
            await query.edit_message_text(
                "What's your question? I'm here to help."
            )
            context.user_data['response_count'] = 0
            return CONVERSATION
            
        elif query.data == "think_about_it":
            await query.edit_message_text(
                f"No rush, {first_name}. Take your time.\n\n"
                "Type /start whenever you're ready to continue.\n\n"
                "**Real talk:** If nothing changes, where are you in 6 months? 🤔"
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
                "When you're done, use the link at the end of the PDF to come back (or type /done).\n\n"
                "That's when we build your system. 💪"
            )
            
            return ConversationHandler.END
        
        elif query.data == "done_reading":
            await query.edit_message_text(
                f"Welcome back, {first_name}! 🙌\n\n"
                "Let's talk about what you just read."
            )
            await query.message.reply_text(
                "**What part of the PDF hit home the most?**\n\n"
                "Tell me what resonated with you."
            )
            return PDF_FEEDBACK
        
        return PRODUCT_INTRO

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
        return PDF_FEEDBACK
    
    async def pdf_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        
        self.update_user_data(user_id, {'focus_area': choice})
        
        exercises = {
            'A': (
                f"**🎯 North Star Exercise**\n\n"
                f"Clarity is everything. If you're climbing the wrong ladder, speed doesn't matter.\n\n"
                f"Complete this:\n"
                f"'In 5 years, I want to be known as someone who...'\n\n"
                f"Send me your answer. Be honest—does this *excite* you, or are you trying to impress someone?"
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
                f"**🔬 MVE Challenge**\n\n"
                f"Failure is data. Let's make it work for you.\n\n"
                f"Pick ONE goal you've been avoiding.\n\n"
                f"Answer:\n"
                f"1. What's the smallest step in the next 2 hours?\n"
                f"2. What's the worst that happens if it fails?\n"
                f"3. What do you learn even if it fails?\n\n"
                f"Send me your goal + MVE. Let's run the experiment."
            ),
            'D': (
                f"**⚙️ If-Then Builder**\n\n"
                f"Systems beat willpower every time.\n\n"
                f"Think of ONE action you keep 'forgetting'.\n\n"
                f"Complete this:\n"
                f"'If [trigger], then I will [specific action].'\n\n"
                f"Example: 'If I pour coffee, then I journal for 5 min.'\n\n"
                f"What's YOUR If-Then? Send it."
            ),
            'E': (
                f"**🔥 Small Win Ritual**\n\n"
                f"Momentum comes from stacking tiny wins.\n\n"
                f"1. Pick the SMALLEST action you can do today\n"
                f"   (Not 'run 5 miles'—think 'put on shoes')\n\n"
                f"2. After doing it, say:\n"
                f"   'I did what I said. That's who I am.'\n\n"
                f"What's your small win TODAY? Tell me now."
            )
        }
        
        if choice in exercises:
            reply = exercises[choice]
        else:
            reply = (
                "Got it. Just reply with the letter:\n\n"
                "**A** - Clarity\n**B** - Belief\n**C** - Failure\n"
                "**D** - Systems\n**E** - Momentum"
            )
            await update.message.reply_text(reply)
            return FOCUS_AREA
        
        await update.message.reply_text(reply)
        return SYSTEM_BUILDING

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
            CONVERSATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_conversation)],
            PRODUCT_INTRO: [
                CallbackQueryHandler(bot.button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_conversation)
            ],
            PDF_FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.pdf_feedback)],
            FOCUS_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.focus_area)],
            SYSTEM_BUILDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.system_building)],
            CHECKIN_RESPONSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.checkin_response)],
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
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    print("🚀 Mindset Bot Running")
    print("✅ Adaptive mentor flow active")
    print("✅ 3-day check-ins enabled")
    print("✅ Post-purchase support ready")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()