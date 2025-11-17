import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import re
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

# Bot States
(MSG_1, MSG_2, MSG_3, MSG_4, MSG_5, MSG_6, MSG_7, MSG_8, 
 EMAIL_CAPTURE, PRODUCT_INTRO, POST_PURCHASE_START, FIRST_INSIGHT, FOCUS_AREA, 
 SYSTEM_BUILDING, CHECKIN_RESPONSE) = range(15)

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Your Paystack payment link
PAYSTACK_LINK = "https://paystack.com/buy/unleash-your-ultimate-mindset-the-5-step-blueprint-to-uwsyav"

class MindsetBot:
    def __init__(self):
        self.user_data_file = "user_data.json"
        self.load_user_data()
    
    def load_user_data(self):
        """Load user data from file"""
        try:
            with open(self.user_data_file, 'r') as f:
                self.user_db = json.load(f)
        except FileNotFoundError:
            self.user_db = {}
    
    def save_user_data(self):
        """Save user data to file"""
        with open(self.user_data_file, 'w') as f:
            json.dump(self.user_db, f, indent=2)
    
    def get_user_data(self, user_id):
        """Get user data by ID"""
        return self.user_db.get(str(user_id), {})
    
    def update_user_data(self, user_id, data):
        """Update user data"""
        user_id_str = str(user_id)
        if user_id_str not in self.user_db:
            self.user_db[user_id_str] = {}
        self.user_db[user_id_str].update(data)
        self.save_user_data()
    
    # ============== PRE-SALE FLOW (Messages 1-10) ==============
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 1: Warm welcome"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        
        user_data = self.get_user_data(user_id)
        
        # Check if user has already purchased
        if user_data.get('purchased', False):
            # Route to a dedicated post-purchase handler for clarity
            return await self.post_purchase_start(update, context)

        # Check if returning user who didn't purchase
        if user_data.get('initial_concern'):
            await update.message.reply_text(
                f"Welcome back, {first_name}! 👋\n\n"
                "I remember we were talking before. How have things been going since then?\n\n"
                "Still dealing with those same challenges, or has something shifted?"
            )
        else:
            await update.message.reply_text(
                f"Hey {first_name}! 👋\n\n"
                "Quick question: If you could change one thing about how you show up each day, what would it be?\n\n"
                "No judgment—just one sentence."
            )
        
        self.update_user_data(user_id, {'first_name': first_name, 'started_at': str(datetime.now())})
        return MSG_1

    async def message_1(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 2: Empathetic reflection - SHORT and DYNAMIC"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'initial_concern': user_response})
        
        # Dynamic response based on keywords
        response_lower = user_response.lower()
        
        if any(word in response_lower for word in ['stuck', 'stagnant', 'plateau', 'same place', 'not moving']):
            reply = f"That stuck feeling is frustrating. You're putting in effort but nothing's moving, right?\n\nQuick question: Do you not know *what* to do next, or do you know but can't make yourself do it?"
        
        elif any(word in response_lower for word in ['motivation', 'motivate', 'discipline', 'willpower', 'lazy', 'unmotivated']):
            reply = f"Here's the thing, {first_name}—motivation isn't your real problem.\n\nBet you're super consistent in *some* areas but totally inconsistent in others. What's one thing you're already good at showing up for?"
        
        elif any(word in response_lower for word in ['goal', 'achieve', 'success', 'accomplish', 'want', 'dream']):
            reply = f"Love that you have goals.\n\nBut real talk: when you imagine achieving it, do you feel *excited* or *pressured*?"
        
        elif any(word in response_lower for word in ['start', 'begin', 'procrastinat', 'delay', 'later', 'tomorrow']):
            reply = f"The starting problem. Classic.\n\nWhen you *do* start something, do you finish it? Or does resistance show up at every stage?"
        
        elif any(word in response_lower for word in ['fail', 'failure', 'afraid', 'fear', 'scared', 'worry', 'anxious']):
            reply = f"That fear means you care, {first_name}. That's not weakness.\n\nWhat would you try if you knew no one would judge you for failing?"
        
        elif any(word in response_lower for word in ['don\'t know', 'unclear', 'lost', 'confused', 'direction', 'what to do']):
            reply = f"Not knowing what to do is rough.\n\nBut honest question: If you *did* know exactly what to do, would you actually do it? Or would something else get in the way?"
        
        elif any(word in response_lower for word in ['money', 'income', 'business', 'career', 'job', 'financial']):
            reply = f"Money goals. I get it.\n\nHere's what matters though: Are you chasing the money itself, or what you think the money will give you?"
        
        elif any(word in response_lower for word in ['relationship', 'partner', 'marriage', 'dating', 'people']):
            reply = f"Relationships are tough when you're not solid with yourself first.\n\nDo you feel like you're trying to fix the relationship, or are you trying to fix how *you* show up?"
        
        elif any(word in response_lower for word in ['health', 'weight', 'fitness', 'exercise', 'gym', 'diet']):
            reply = f"Health goals usually aren't about the gym or the diet, {first_name}.\n\nWhat's *really* behind wanting this change? What are you hoping will be different?"
        
        elif any(word in response_lower for word in ['time', 'busy', 'overwhelm', 'too much', 'stress']):
            reply = f"Too much on your plate?\n\nBe honest: Are you actually too busy, or are you busy with the *wrong* things?"
        
        elif any(word in response_lower for word in ['confident', 'self-esteem', 'doubt', 'not good enough', 'imposter']):
            reply = f"That self-doubt voice is loud, huh?\n\nWhat's one thing you *know* you're good at, even if you downplay it?"
        
        else:
            # Catch-all that uses their exact words
            reply = f"Got it. So you're dealing with: '{user_response[:50]}...'\n\nIf the version of you who *solved* this was sitting here, what would they say is different about how they think?"
        
        await update.message.reply_text(reply)
        return MSG_2

    async def post_purchase_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Post-purchase welcome shown to users who already purchased."""
        first_name = update.effective_user.first_name

        await update.message.reply_text(
            f"Hey {first_name}! 👋\n\n"
            "I'm really glad you're here. Can I ask you something honest?\n\n"
            "**What's the one thing you wish you could change about how you're showing up right now?**\n\n"
            "(No judgment—just curious what brought you here today.)"
        )

        return POST_PURCHASE_START

    async def capture_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Capture and validate user's email before sending payment link."""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        text = update.message.text.strip()

        # Simple email validation
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", text):
            await update.message.reply_text(
                "Hmm — that doesn't look like a valid email. Please reply with the email you'd like me to send the PDF to."
            )
            return EMAIL_CAPTURE

        # Save email and mark a pending payment (will be verified later via webhook ideally)
        self.update_user_data(user_id, {'email': text, 'pending_payment': True})

        # Send the payment link (placeholder link kept)
        payment_message = (
            f"Thanks, {first_name}! I've saved {text} as your email.\n\n"
            f"Tap below to securely pay GHS 75 and you'll get the PDF by email immediately:\n\n"
            f"👉 {PAYSTACK_LINK}\n\n"
            "After payment, tap the 'I've Completed Payment' button here so I can verify and get you onboarded."
        )

        keyboard = [[InlineKeyboardButton("✅ I've Completed Payment", callback_data="confirm_payment")]]
        await update.message.reply_text(payment_message, reply_markup=InlineKeyboardMarkup(keyboard))

        return PRODUCT_INTRO

    async def message_2(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 3: Deeper diagnosis - SHORT"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'msg_2_response': user_response})
        
        reply = (
            f"That makes sense.\n\n"
            f"Here's the pattern I see: most struggles aren't about *what* you're doing. "
            f"They're about the operating system running in the background—your mindset.\n\n"
            f"Ever feel like you're sabotaging yourself? Like part of you wants success but another part hits the brakes?"
        )
        
        await update.message.reply_text(reply)
        return MSG_3

    async def message_3(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 4: Pattern recognition - SHORTER"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'msg_3_response': user_response})
        
        reply = (
            f"Right? That internal conflict is the signal.\n\n"
            f"Most people try to 'push harder' or 'stay motivated.' But that just burns you out faster.\n\n"
            f"The real fix? Update the operating system itself.\n\n"
            f"If you could flip a switch and wake up with an unstoppable mindset tomorrow, what would you do differently?"
        )
        
        await update.message.reply_text(reply)
        return MSG_4

    async def message_4(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 5: Bridge to solution - CONCISE"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'msg_4_response': user_response})
        
        reply = (
            f"That vision is possible, {first_name}. And it's engineerable.\n\n"
            f"The gap between where you are and where you want to be is a systematic rewiring of 5 areas:\n\n"
            f"1. **Clarity** → Who you need to *be*\n"
            f"2. **Belief** → Catching the lies your brain tells you\n"
            f"3. **Failure** → Using it as fuel, not a stop sign\n"
            f"4. **Systems** → Making success automatic\n"
            f"5. **Momentum** → Building unstoppable progress\n\n"
            f"Does this feel like what's been missing?"
        )
        
        await update.message.reply_text(reply)
        return MSG_5

    async def message_5(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 6: Validation and specificity - PUNCHY"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'msg_5_response': user_response})
        
        reply = (
            f"Right? Suddenly 'just be positive' makes no sense.\n\n"
            f"So here's where I come in.\n\n"
            f"I've built a complete blueprint called **'Unleash Your Ultimate Mindset'** that rewires this exact system:\n\n"
            f"🔹 Unshakeable self-belief (even when doubt screams)\n"
            f"🔹 Systems that make procrastination impossible\n"
            f"🔹 Turning failure into your fastest teacher\n"
            f"🔹 Making success feel inevitable, not exhausting\n\n"
            f"**Plus,** after you read it, I personally help you build your custom system. You're not alone in this.\n\n"
            f"If you had this in place 3 months from now, where would you be?"
        )
        
        await update.message.reply_text(reply)
        return MSG_6

    async def message_6(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 7: Creating desire - TIGHT"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'msg_6_response': user_response})
        
        reply = (
            f"That version of you already exists, {first_name}. You just need the framework.\n\n"
            f"**Here's what you get:**\n\n"
            f"📖 The Complete 5-Step Blueprint\n"
            f"🧠 Actionable Frameworks (Evidence Inventory, MVE Method, If-Then Planning)\n"
            f"🤝 Personal Support — I help you build your system after you read\n"
            f"📲 3-Day Check-ins — I keep you on track every 3 days\n\n"
            f"**Investment:** GHS 75 ($6.85)\n\n"
            f"Less than two coffees for a complete mindset overhaul + ongoing guidance.\n\n"
            f"Does this feel like what you need?"
        )
        
        await update.message.reply_text(reply)
        return MSG_7

    async def message_7(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 8: Soft objection handling - NATURAL"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text.lower()
        
        self.update_user_data(user_id, {'msg_7_response': user_response})
        
        # Detect affirmation or hesitation
        if any(word in user_response for word in ['yes', 'yeah', 'definitely', 'absolutely', 'sure', 'ready', 'let\'s do', 'sounds good']):
            reply = (
                f"Let's go, {first_name}! 🔥\n\n"
                f"**Here's what happens:**\n"
                f"1. Tap the link below\n"
                f"2. Get instant PDF access via email\n"
                f"3. Read it\n"
                f"4. Click the link at the end to come back\n"
                f"5. We build your custom system\n\n"
                f"Ready? 👇"
            )
        else:
            reply = (
                f"Fair enough, {first_name}.\n\n"
                f"What's the hesitation? Is it:\n\n"
                f"A) Not sure it'll work for me\n"
                f"B) I've tried stuff before\n"
                f"C) Timing feels off\n"
                f"D) Something else\n\n"
                f"Just tell me what's on your mind."
            )
            await update.message.reply_text(reply)
            return MSG_8
        
        keyboard = [
            [InlineKeyboardButton("🔥 Get Instant Access", callback_data="show_payment")],
            [InlineKeyboardButton("I have a question", callback_data="ask_question")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(reply, reply_markup=reply_markup)
        return PRODUCT_INTRO

    async def message_8(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Objection handling, then transition to product"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text.upper().strip()
        
        self.update_user_data(user_id, {'msg_8_response': user_response})
        
        if 'A' in user_response or 'work for me' in update.message.text.lower():
            reply = (
                f"Fair concern, {first_name}. Here's the thing:\n\n"
                "This isn't about personality or 'being the right type of person.' It's about having a framework. "
                "The people who've used this come from all walks—burnt out employees, entrepreneurs, students, parents.\n\n"
                "**What they have in common?** They were tired of fighting themselves and ready for a system that actually works.\n\n"
                "If that's you, this will work."
            )
        elif 'B' in user_response or 'tried' in update.message.text.lower() or 'before' in update.message.text.lower():
            reply = (
                f"I hear you, {first_name}. You've been burned before. That sucks.\n\n"
                "**Here's the difference:** Most programs give you *what* to do. This gives you how to rewire the "
                "*operating system* so you actually do it.\n\n"
                "It's not about adding more tasks to your list. It's about fixing why you don't do the tasks in the first place.\n\n"
                "Plus, you're not doing this alone. I'll be checking in with you every 3 days. Accountability changes everything."
            )
        elif 'C' in user_response or 'time' in update.message.text.lower() or 'timing' in update.message.text.lower():
            reply = (
                f"Let me be real with you, {first_name}:\n\n"
                "There's never a 'perfect time.' That's just fear wearing a disguise.\n\n"
                "**But here's the good news:** This isn't a time-intensive program. It's about smart, small shifts. "
                "The PDF takes 45 minutes to read. The system takes 10 minutes a day to implement.\n\n"
                "If you're too busy to invest 10 minutes in yourself, that's exactly why you need this."
            )
        else:
            reply = (
                f"I appreciate you being honest, {first_name}.\n\n"
                "Look, I'm not here to pressure you. If this doesn't feel right, that's totally okay.\n\n"
                "But if what's holding you back is just *uncertainty*—not knowing if it'll work—then I'd say: "
                "GHS 75 is a pretty low-risk bet on yourself.\n\n"
                "Worst case? You're out the cost of two coffees. Best case? You completely shift how you operate.\n\n"
                "**Your call.** What feels right?"
            )
        
        keyboard = [
            [InlineKeyboardButton("🔥 Alright, let's do this", callback_data="show_payment")],
            [InlineKeyboardButton("I need to think about it", callback_data="think_about_it")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(reply, reply_markup=reply_markup)
        return PRODUCT_INTRO

    # ============== PRODUCT INTRODUCTION (Messages 9-10) ==============
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle all button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        first_name = query.from_user.first_name
        user_data = self.get_user_data(user_id)
        
        if query.data == "show_payment":
            # If we don't have an email for this user yet, capture it first
            if not user_data.get('email'):
                await query.edit_message_text(
                    "Great — which email should I send your PDF to?\n\n"
                    "Reply with your email address and I'll send the secure payment link there."
                )
                return EMAIL_CAPTURE
            payment_message = (
                f"Perfect, {first_name}! Here's your access link:\n\n"
                f"👉 {PAYSTACK_LINK}\n\n"
                "**What happens next:**\n"
                "1️⃣ Complete payment (GHS 75 / $6.85)\n"
                "2️⃣ Check your email for instant PDF access\n"
                "3️⃣ Read through the blueprint\n"
                "4️⃣ Click the link at the end to come back here\n"
                "5️⃣ We'll build your personalized system together\n\n"
                "See you on the other side! 🚀"
            )
            await query.edit_message_text(payment_message)
            
            keyboard = [[InlineKeyboardButton("✅ I've Completed Payment", callback_data="confirm_payment")]]
            await query.message.reply_text(
                "Tap below once you've completed your payment:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return PRODUCT_INTRO
            
        elif query.data == "ask_question":
            await query.edit_message_text(
                "No problem! What's your question?\n\n"
                "Just type it below and I'll answer honestly."
            )
            return MSG_8
            
        elif query.data == "think_about_it":
            await query.edit_message_text(
                f"Totally fair, {first_name}.\n\n"
                "Take your time. When you're ready, just type /start and we'll pick up where we left off.\n\n"
                "In the meantime—ask yourself this:\n\n"
                "**'If nothing changes, where will I be 6 months from now?'**\n\n"
                "That answer usually tells you everything you need to know.\n\n"
                "I'll be here whenever you're ready. 💪"
            )
            return ConversationHandler.END
            
        elif query.data == "confirm_payment":
            self.update_user_data(user_id, {
                'purchased': True, 
                'purchase_date': str(datetime.now()),
                'check_in_count': 0
            })
            
            await query.edit_message_text(
                f"🎉 Welcome to the other side, {first_name}!\n\n"
                "You should have the PDF in your email right now. Take your time reading through it—"
                "there's no rush.\n\n"
                "When you're done, click the link at the end of the PDF (or type /done here) "
                "and we'll start building your custom system.\n\n"
                "This is where the real transformation begins. See you soon! 💪"
            )
            
            # Schedule first check-in for 3 days from now
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
                f"Welcome back, {first_name}! 🙌\n\n"
                "Okay, let's talk about what you just learned."
            )
            await query.message.reply_text(
                "**First question:** What part of the PDF hit home the hardest for you?\n\n"
                "(Like, what made you think: 'Damn, that's exactly my problem'?)"
            )
            return FIRST_INSIGHT
        
        return PRODUCT_INTRO

    # ============== POST-PURCHASE FLOW ==============
    
    async def done_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /done command after reading PDF"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        
        user_data = self.get_user_data(user_id)
        
        if not user_data.get('purchased'):
            await update.message.reply_text(
                "Hmm, looks like you haven't grabbed the PDF yet!\n\n"
                "Type /start if you'd like to learn more about it."
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            f"Welcome back, {first_name}! 🙌\n\n"
            "Okay, let's talk about what you just learned.\n\n"
            "**First question:** What part of the PDF hit home the hardest for you?\n\n"
            "(Like, what made you think: 'Damn, that's exactly my problem'?)"
        )
        return FIRST_INSIGHT

    async def first_insight(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Gather initial feedback and identify focus area"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'key_insight': user_response})
        
        reply = (
            f"That's powerful self-awareness, {first_name}. Most people never even get to that recognition.\n\n"
            "Now let's make this practical. Based on the 5-step framework, **where's your biggest friction point right now?**\n\n"
            "**A) Clarity** — Not 100% sure what I'm actually working toward\n"
            "**B) Belief** — I know what to do but doubt creeps in\n"
            "**C) Failure** — I'm afraid to try because I might mess up\n"
            "**D) Systems** — I'm relying on willpower instead of design\n"
            "**E) Momentum** — I start strong but can't sustain it\n\n"
            "Just type the letter. (Be honest—there's no wrong answer.)"
        )
        
        await update.message.reply_text(reply)
        return FOCUS_AREA

    async def focus_area(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Provide personalized exercise based on focus area"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        choice = update.message.text.upper().strip()
        
        self.update_user_data(user_id, {'focus_area': choice})
        
        exercises = {
            'A': {
                'title': '**🎯 The North Star Exercise**',
                'prompt': (
                    f"Clarity is everything, {first_name}. If you're climbing the wrong ladder, speed doesn't matter.\n\n"
                    "**Here's your exercise:**\n\n"
                    "Complete this sentence:\n"
                    "'In 5 years, I want to be known as someone who...'\n\n"
                    "Then ask yourself: Does this definition *excite* me, or am I trying to impress someone?\n\n"
                    "Take your time. Send me your answer—be brutally honest—and let's refine it together."
                )
            },
            'B': {
                'title': '**🧠 The Evidence Inventory**',
                'prompt': (
                    f"Let's catch those lies your brain tells you, {first_name}.\n\n"
                    "**Here's your exercise:**\n\n"
                    "1. Write down ONE limiting belief that keeps showing up\n"
                    "   (e.g., 'I'm not disciplined enough' or 'I always give up')\n\n"
                    "2. List 3 times you PROVED that belief wrong\n"
                    "   (Even small wins count. Did you finish a book? Learn a skill? Show up when it was hard?)\n\n"
                    "Send me:\n"
                    "• The belief\n"
                    "• Your 3 counter-examples\n\n"
                    "We're going to demolish that lie with facts."
                )
            },
            'C': {
                'title': '**🔬 The MVE Challenge**',
                'prompt': (
                    f"Failure is data, {first_name}. Let's make it work for you instead of against you.\n\n"
                    "**Here's your exercise:**\n\n"
                    "Pick ONE goal you've been avoiding (because you're scared it won't work).\n\n"
                    "Now answer:\n"
                    "1. What's the absolute *smallest* step I can take in the next 2 hours?\n"
                    "2. What's the worst that can happen if this small step fails?\n"
                    "3. What will I learn even if it fails?\n\n"
                    "The goal: Fail small, learn fast.\n\n"
                    "Send me your goal + your MVE (Minimum Viable Effort). Let's run the experiment."
                )
            },
            'D': {
                'title': '**⚙️ The If-Then Builder**',
                'prompt': (
                    f"Systems beat willpower every time, {first_name}. Let's build yours.\n\n"
                    "**Here's your exercise:**\n\n"
                    "Think of ONE action you keep 'forgetting' to do.\n"
                    "(Working out? Deep work? Journaling? Reaching out to people?)\n\n"
                    "Now complete this formula:\n"
                    "**'If [specific trigger], then I will immediately [specific action].'**\n\n"
                    "Example:\n"
                    "'If I pour my morning coffee, then I immediately open my journal for 5 minutes.'\n\n"
                    "The more specific, the better.\n\n"
                    "What's YOUR If-Then? Send it to me."
                )
            },
            'E': {
                'title': '**🔥 The Small Win Ritual**',
                'prompt': (
                    f"Momentum comes from stacking tiny wins, {first_name}. Let's start your streak.\n\n"
                    "**Here's your exercise:**\n\n"
                    "1. Pick the SMALLEST meaningful action you can do today\n"
                    "   (Not 'run 5 miles'—think 'put on running shoes')\n\n"
                    "2. After you complete it, pause for 30 seconds and say:\n"
                    "   'I did what I said I'd do. That's who I am now.'\n\n"
                    "This trains your brain to associate completion with your identity.\n\n"
                    "What's your small win going to be today? Tell me right now."
                )
            }
        }
        
        if choice in exercises:
            exercise = exercises[choice]
            reply = f"{exercise['title']}\n\n{exercise['prompt']}"
        else:
            reply = (
                "Hmm, I didn't catch that. Just reply with the letter (A, B, C, D, or E) "
                "that matches your biggest friction point:\n\n"
                "**A** - Clarity\n**B** - Belief\n**C** - Failure\n**D** - Systems\n**E** - Momentum"
            )
            await update.message.reply_text(reply)
            return FOCUS_AREA
        
        await update.message.reply_text(reply)
        return SYSTEM_BUILDING

    async def system_building(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Guide user through their exercise and set next steps"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_input = update.message.text
        
        self.update_user_data(user_id, {
            'exercise_response': user_input,
            'last_interaction': str(datetime.now())
        })
        
        # Provide encouraging, personalized feedback
        reply = (
            f"This is excellent, {first_name}! You're already thinking differently. 🔥\n\n"
            "Here's what I want you to do in the next 3 days:\n\n"
            "**1. Test what you just defined**\n"
            "Don't overthink it. Just run the experiment.\n\n"
            "**2. Track what happens**\n"
            "No judgment, just data. Did it work? Did something get in the way? What surprised you?\n\n"
            "**3. Come back and tell me**\n"
            "I'll check in with you in 3 days, but you can message me anytime with /checkin if you need support.\n\n"
            "Remember: You're not looking for perfection. You're looking for the *next data point.*\n\n"
            "The version of you that wins? They're just someone who keeps showing up and adjusting.\n\n"
            "You've got this. Talk soon! 💪"
        )
        
        await update.message.reply_text(reply)
        
        # Schedule next check-in for 3 days
        job_queue = context.application.job_queue
        chat_id = update.effective_chat.id
        
        # Cancel any existing check-ins for this user
        current_jobs = job_queue.get_jobs_by_name(f"checkin_{user_id}")
        for job in current_jobs:
            job.schedule_removal()
        
        # Schedule new check-in
        job_queue.run_once(
            self.send_checkin,
            when=timedelta(days=3),
            data={'user_id': user_id, 'chat_id': chat_id},
            name=f"checkin_{user_id}"
        )
        
        return ConversationHandler.END

    # ============== AUTOMATED CHECK-INS ==============
    
    async def send_checkin(self, context: ContextTypes.DEFAULT_TYPE):
        """Send automated 3-day check-in"""
        job_data = context.job.data
        user_id = job_data['user_id']
        chat_id = job_data['chat_id']
        
        user_data = self.get_user_data(user_id)
        first_name = user_data.get('first_name', 'there')
        check_in_count = user_data.get('check_in_count', 0)
        focus_area = user_data.get('focus_area', 'your exercise')
        
        # Update check-in count
        self.update_user_data(user_id, {'check_in_count': check_in_count + 1})
        
        # Different messages based on check-in number
        if check_in_count == 0:
            message = (
                f"Hey {first_name}! 👋\n\n"
                "It's been 3 days. How did your experiment go?\n\n"
                "**Tell me:**\n"
                "1. What did you try?\n"
                "2. What actually happened?\n"
                "3. What did you learn?\n\n"
                "Remember—there's no such thing as failure, only data. Let's hear it!"
            )
        elif check_in_count == 1:
            message = (
                f"Check-in #2, {first_name}! 💪\n\n"
                "How's the system feeling? Are you noticing any shifts in how you're operating?\n\n"
                "**Quick reflection:**\n"
                "• What's working better than expected?\n"
                "• What's still feeling like a struggle?\n"
                "• What do you need to adjust?\n\n"
                "Hit me with the real update."
            )
        elif check_in_count == 2:
            message = (
                f"Week 1.5 check-in, {first_name}! 🔥\n\n"
                "You're almost at the 2-week mark. This is where most people either quit or level up.\n\n"
                "**Honest assessment:**\n"
                "Are you still showing up? Or are old patterns creeping back in?\n\n"
                "If you're struggling, that's not failure—that's the *exact* moment where breakthroughs happen.\n\n"
                "What's the truth right now?"
            )
        elif check_in_count == 3:
            message = (
                f"Two weeks down, {first_name}! 🎉\n\n"
                "This is a milestone. You're proving to yourself that you can sustain momentum.\n\n"
                "**Time for a mini-review:**\n"
                "1. What's the biggest shift you've noticed in yourself?\n"
                "2. What's one habit that's starting to feel automatic?\n"
                "3. What's the next constraint we need to tackle?\n\n"
                "Let's keep this going."
            )
        else:
            # Ongoing check-ins
            message = (
                f"Check-in time, {first_name}! 💪\n\n"
                "How are things going? Still building momentum or hitting any walls?\n\n"
                "Give me a quick update:\n"
                "• What's working?\n"
                "• What needs adjusting?\n"
                "• How can I help?\n\n"
                "You know the drill—honesty over perfection."
            )
        
        await context.bot.send_message(chat_id=chat_id, text=message)
        
        # Schedule next check-in (3 days from now)
        context.application.job_queue.run_once(
            self.send_checkin,
            when=timedelta(days=3),
            data=job_data,
            name=f"checkin_{user_id}"
        )

    async def checkin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle manual check-in from user"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        
        user_data = self.get_user_data(user_id)
        
        if not user_data.get('purchased'):
            await update.message.reply_text(
                "Hey! Looks like you haven't grabbed the PDF yet.\n\n"
                "Type /start if you'd like to learn more!"
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            f"Hey {first_name}! Love that you're checking in proactively. 💪\n\n"
            "How's it going? What's on your mind?\n\n"
            "Tell me:\n"
            "• What you've been working on\n"
            "• What's working\n"
            "• What's feeling stuck\n\n"
            "I'm all ears."
        )
        return CHECKIN_RESPONSE

    async def checkin_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Respond to user's check-in"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_message = update.message.text.lower()
        
        # Analyze the message for sentiment and keywords
        if any(word in user_message for word in ['great', 'good', 'working', 'progress', 'better']):
            reply = (
                f"That's what I like to hear, {first_name}! 🔥\n\n"
                "Keep riding that momentum. Small wins compound into massive shifts.\n\n"
                "**One challenge for you:**\n"
                "What's the *next* level? What would make this even better?\n\n"
                "Don't settle into comfort—keep pushing the edge."
            )
        elif any(word in user_message for word in ['stuck', 'struggling', 'hard', 'difficult', 'failing']):
            reply = (
                f"I appreciate you being honest, {first_name}. That takes guts.\n\n"
                "Here's the thing: Struggle isn't a sign you're failing. It's a sign you're pushing boundaries.\n\n"
                "**Let's troubleshoot:**\n"
                "• Is the goal too big? (Break it smaller—MVE style)\n"
                "• Is the system missing? (Add an If-Then)\n"
                "• Is belief creeping in? (Run the Evidence Inventory again)\n\n"
                "Which one resonates most? Let's fix it."
            )
        elif any(word in user_message for word in ['quit', 'give up', 'stop', 'done']):
            reply = (
                f"Whoa, hold up {first_name}. Before you walk away, let me ask you something:\n\n"
                "**What would you tell someone you cared about if they were in your exact position right now?**\n\n"
                "I bet you'd tell them to keep going. To give it one more shot.\n\n"
                "So here's my ask: Give me one more experiment. One more MVE. Just one.\n\n"
                "If it still doesn't work, we'll reassess. But I've seen too many people quit right before the breakthrough.\n\n"
                "You in?"
            )
        else:
            reply = (
                f"Thanks for the update, {first_name}.\n\n"
                "Here's what I'm hearing: You're in the middle of the process. Not at the beginning, not at the end—just in the messy middle.\n\n"
                "**That's exactly where growth happens.**\n\n"
                "Keep showing up. Keep adjusting. Keep collecting data.\n\n"
                "I'll check in with you in 3 days. In the meantime, focus on one thing:\n\n"
                "**What's the smallest action I can take today that moves me forward?**\n\n"
                "Do that. Then do it again tomorrow.\n\n"
                "You've got this. 💪"
            )
        
        await update.message.reply_text(reply)
        
        # Update last interaction
        self.update_user_data(user_id, {'last_interaction': str(datetime.now())})
        
        return ConversationHandler.END

    # ============== UTILITY COMMANDS ==============
    
    async def continue_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Continue conversation for returning users"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_data = self.get_user_data(user_id)
        
        if not user_data.get('purchased'):
            await update.message.reply_text(
                f"Hey {first_name}! Let's pick up where we left off.\n\n"
                "What's been on your mind since we last talked?"
            )
            return MSG_1
        else:
            await update.message.reply_text(
                f"Welcome back, {first_name}! 🙌\n\n"
                "How can I help you today?\n\n"
                "• Need to work through an exercise? Tell me what you're working on.\n"
                "• Want to check in on progress? Give me an update.\n"
                "• Hitting a wall? Let's troubleshoot.\n\n"
                "What's on your mind?"
            )
            return CHECKIN_RESPONSE

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show help menu"""
        help_text = (
            "**Available Commands:**\n\n"
            "/start - Start or restart our conversation\n"
            "/done - Tell me when you've finished reading the PDF\n"
            "/checkin - Check in with me anytime\n"
            "/continue - Pick up where we left off\n"
            "/help - Show this menu\n"
            "/cancel - End the current conversation\n\n"
            "You can also just message me directly anytime. I'm here to help! 💪"
        )
        await update.message.reply_text(help_text)
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel conversation"""
        first_name = update.effective_user.first_name
        await update.message.reply_text(
            f"No worries, {first_name}!\n\n"
            "Whenever you're ready to continue, just type /start or /continue.\n\n"
            "Remember: The best time to start was yesterday. The second best time is now. 💪"
        )
        return ConversationHandler.END


def main():
    """Start the bot"""
    # Replace with your bot token
    TOKEN = "8342995076:AAH9TosXOwx_1KF3Kb5TwrKEcVlWqUmPEBI"
    
    application = Application.builder().token(TOKEN).build()
    bot = MindsetBot()
    
    # Main conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', bot.start),
            CommandHandler('continue', bot.continue_command),
        ],
        states={
            MSG_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message_1)],
            MSG_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message_2)],
            MSG_3: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message_3)],
            MSG_4: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message_4)],
            MSG_5: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message_5)],
            MSG_6: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message_6)],
            MSG_7: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message_7)],
            MSG_8: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message_8)],
            PRODUCT_INTRO: [
                CallbackQueryHandler(bot.button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message_8)
            ],
            EMAIL_CAPTURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.capture_email)],
            POST_PURCHASE_START: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.continue_command)
            ],
            FIRST_INSIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.first_insight)],
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
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', bot.help_command))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Start the bot
    print("🚀 Mindset Bot is running...")
    print("✅ 8-message pre-sale flow activated")
    print("✅ 3-day check-in system enabled")
    print("✅ Dynamic responses ready")
    print("✅ Post-purchase support active")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()