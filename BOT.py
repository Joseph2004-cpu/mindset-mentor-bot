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

# Bot States
(MSG_1, MSG_2, MSG_3, MSG_4, MSG_5, MSG_6, MSG_7, MSG_8, 
 PRODUCT_INTRO, POST_PURCHASE_START, FIRST_INSIGHT, FOCUS_AREA, 
 SYSTEM_BUILDING, CHECKIN_RESPONSE) = range(14)

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
            await update.message.reply_text(
                f"Hey {first_name}! Welcome back! 🙌\n\n"
                "Ready to continue building your system? I'm here whenever you need me.\n\n"
                "Type /continue to pick up where we left off, or just tell me what's on your mind."
            )
            return POST_PURCHASE_START
        
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
                "I'm really glad you're here. Can I ask you something honest?\n\n"
                "**What's the one thing you wish you could change about how you're showing up right now?**\n\n"
                "(No judgment—just curious what brought you here today.)"
            )
        
        self.update_user_data(user_id, {'first_name': first_name, 'started_at': str(datetime.now())})
        return MSG_1

    async def message_1(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 2: Empathetic reflection"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'initial_concern': user_response})
        
        # Dynamic response based on keywords
        response_lower = user_response.lower()
        
        if any(word in response_lower for word in ['stuck', 'stagnant', 'plateau', 'same place']):
            reply = (
                f"That stuck feeling is so frustrating, {first_name}. Like you're putting in effort "
                "but the needle isn't moving, right?\n\n"
                "Here's what I'm curious about—**when you think about being stuck, does it feel like:**\n"
                "• You don't know *what* to do next, or\n"
                "• You know what to do but can't seem to *make yourself* do it?\n\n"
                "(This difference matters more than you might think.)"
            )
        elif any(word in response_lower for word in ['motivation', 'motivate', 'discipline', 'willpower', 'lazy']):
            reply = (
                f"Okay, {first_name}, I'm going to tell you something that might surprise you:\n\n"
                "The fact that you're blaming motivation or discipline? That's actually a *symptom*, not the problem.\n\n"
                "**Real talk:** Have you noticed that you *do* have discipline in some areas of your life, "
                "but it completely disappears in others? Like maybe you're super consistent at work but can't stick "
                "to personal goals?\n\n"
                "What's an example of something you *are* consistent with?"
            )
        elif any(word in response_lower for word in ['goal', 'achieve', 'success', 'accomplish', 'want']):
            reply = (
                f"I love that you have goals, {first_name}. That's already ahead of most people.\n\n"
                "But let me ask you something that might feel uncomfortable:\n\n"
                "**When you close your eyes and imagine achieving that goal—do you feel excited, or do you feel pressure?**\n\n"
                "(Be honest. There's no wrong answer here.)"
            )
        elif any(word in response_lower for word in ['start', 'begin', 'procrastinat', 'delay']):
            reply = (
                f"That starting problem is real, {first_name}. It's like there's an invisible force field "
                "around the thing you need to do.\n\n"
                "**Quick question:** When you *do* finally start something, do you usually finish it? "
                "Or does the resistance show up at every stage?\n\n"
                "(I'm trying to figure out if this is a *starting* problem or a *sustaining* problem.)"
            )
        elif any(word in response_lower for word in ['fail', 'failure', 'afraid', 'fear', 'scared']):
            reply = (
                f"{first_name}, that fear of failing? It means you actually care. That's not weakness—that's proof you're invested.\n\n"
                "But here's what I want to know:\n\n"
                "**What would you attempt if you *knew* you wouldn't be judged for failing?**\n\n"
                "(Dream big for a second. What's the thing you'd go for?)"
            )
        elif any(word in response_lower for word in ['don\'t know', 'unclear', 'lost', 'confused', 'direction']):
            reply = (
                f"That uncertainty is tough, {first_name}. It's hard to move forward when you're not sure "
                "which direction is even *forward*.\n\n"
                "**Let me ask this differently:** If you had absolute clarity on what to do next, "
                "do you think you'd actually do it? Or would something else get in the way?\n\n"
                "(I'm asking because sometimes 'I don't know what to do' is actually protecting us from something else.)"
            )
        else:
            reply = (
                f"Thanks for sharing that with me, {first_name}. I can tell you've been thinking about this.\n\n"
                "**Here's what I'm hearing:** You want something more. A better version of how things are going right now.\n\n"
                "If I asked you to describe the *version of yourself* who has figured this out—"
                "what's different about that person compared to who you are today?"
            )
        
        await update.message.reply_text(reply)
        return MSG_2

    async def message_2(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 3: Deeper diagnosis"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'msg_2_response': user_response})
        
        reply = (
            f"That's really insightful, {first_name}. You're already seeing patterns most people miss.\n\n"
            "Here's something I've noticed working with people like you:\n\n"
            "Most struggles aren't about *what* you're doing. They're about the **invisible operating system** "
            "running in the background—your mindset.\n\n"
            "**Think of it like this:** You can have the best apps (goals, plans, strategies), "
            "but if your phone's OS is outdated or has bugs, nothing runs smoothly.\n\n"
            "**Quick check:** Do you ever feel like you're sabotaging yourself? Like one part of you wants "
            "to succeed but another part keeps hitting the brakes?"
        )
        
        await update.message.reply_text(reply)
        return MSG_3

    async def message_3(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 4: Pattern recognition"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'msg_3_response': user_response})
        
        reply = (
            f"Exactly. That internal conflict? That's the signal, {first_name}.\n\n"
            "Most people think the solution is to 'push harder' or 'stay motivated.' But that's like trying "
            "to run better software on broken hardware—it just burns you out faster.\n\n"
            "**The real fix?** You need to update the operating system itself.\n\n"
            "Here's what that looks like in practice:\n\n"
            "**Instead of:**\n"
            "❌ Constantly fighting yourself\n"
            "❌ Needing motivation to start\n"
            "❌ Feeling guilty when you 'fail'\n\n"
            "**You get to:**\n"
            "✅ Move forward automatically\n"
            "✅ Trust yourself to follow through\n"
            "✅ Use setbacks as data, not disasters\n\n"
            "**Honest question:** If you could flip a switch and wake up with that kind of mindset tomorrow, "
            "what would you do differently?"
        )
        
        await update.message.reply_text(reply)
        return MSG_4

    async def message_4(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 5: Bridge to solution"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'msg_4_response': user_response})
        
        reply = (
            f"I love that vision, {first_name}. And here's the thing—it's not a fantasy. It's actually engineerable.\n\n"
            "The difference between where you are now and where you want to be isn't some magical personality trait. "
            "It's a **systematic rewiring** of five specific areas:\n\n"
            "**1. Clarity** → Knowing exactly who you need to *be* (not just what you want to *have*)\n"
            "**2. Belief** → Catching and replacing the lies your brain tells you\n"
            "**3. Failure** → Using setbacks as fuel instead of letting them stop you\n"
            "**4. Systems** → Designing your environment so success is automatic\n"
            "**5. Momentum** → Building compound progress that doesn't rely on motivation\n\n"
            "**Real talk:** Does this feel like what's been missing for you?"
        )
        
        await update.message.reply_text(reply)
        return MSG_5

    async def message_5(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 6: Validation and specificity"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'msg_5_response': user_response})
        
        reply = (
            f"Right? When you see it laid out like that, it suddenly makes sense why 'just be positive' never worked.\n\n"
            "So here's where I come in, {first_name}.\n\n"
            "I've been helping people rewire this exact operating system using a complete blueprint called "
            "**'Unleash Your Ultimate Mindset.'**\n\n"
            "It's not fluff. It's not another 'visualize your dreams' book. It's the **engineering manual** for:\n\n"
            "🔹 Building unshakeable self-belief (even when your brain screams 'you can't')\n"
            "🔹 Creating systems that make procrastination literally impossible\n"
            "🔹 Turning failure into your fastest teacher\n"
            "🔹 Making success feel inevitable instead of exhausting\n\n"
            "**And the best part?** After you read it, **I personally help you build your custom system.** "
            "You're not doing this alone.\n\n"
            "**Quick question:** If you had this kind of system in place 3 months from now, where would you be?"
        )
        
        await update.message.reply_text(reply)
        return MSG_6

    async def message_6(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 7: Creating desire"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        self.update_user_data(user_id, {'msg_6_response': user_response})
        
        reply = (
            f"That's the version of you that already exists, {first_name}. You just need the right framework to unlock it.\n\n"
            "**Here's exactly what you get:**\n\n"
            "📖 **The Complete Blueprint** — The 5-step system to rewire your mindset from the ground up\n\n"
            "🧠 **Actionable Frameworks:**\n"
            "• The Evidence Inventory (demolish limiting beliefs)\n"
            "• MVE Method (fail small, learn fast)\n"
            "• If-Then Planning (make execution automatic)\n"
            "• Quarterly Mindset Review (sustain long-term growth)\n\n"
            "🤝 **Ongoing Support** — After you finish reading, I'll help you build your personalized system. "
            "We'll work through your specific situation together.\n\n"
            "📲 **3-Day Check-ins** — I'll check in with you every 3 days to keep you on track, "
            "troubleshoot obstacles, and celebrate wins.\n\n"
            "**Investment:** GHS 75 ($6.85)\n\n"
            "That's less than two coffees. For a complete mindset overhaul + personal guidance.\n\n"
            "**Be honest—does this feel like what you need right now?**"
        )
        
        await update.message.reply_text(reply)
        return MSG_7

    async def message_7(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Message 8: Soft objection handling"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text.lower()
        
        self.update_user_data(user_id, {'msg_7_response': user_response})
        
        # Detect hesitation or affirmation
        if any(word in user_response for word in ['yes', 'yeah', 'definitely', 'absolutely', 'sure', 'ready']):
            reply = (
                f"Love that energy, {first_name}! 🔥\n\n"
                "Alright, let's lock this in. Here's what happens next:\n\n"
                "**Step 1:** Tap the payment link below\n"
                "**Step 2:** You'll get instant access to the PDF via email\n"
                "**Step 3:** Read through it at your own pace\n"
                "**Step 4:** Click the link at the end of the PDF to come back here\n"
                "**Step 5:** We build your custom system together\n\n"
                "You're about to shift how you operate. Let's do this. 👇"
            )
        else:
            reply = (
                f"I get it, {first_name}. Big decisions deserve thought.\n\n"
                "**Let me ask you this:** What's your hesitation right now? Is it:\n\n"
                "A) 'I'm not sure this will work for *me*'\n"
                "B) 'I've tried stuff like this before and it didn't stick'\n"
                "C) 'Not sure if now is the right time'\n"
                "D) Something else\n\n"
                "Just type the letter (or tell me what's on your mind). I want to make sure this is actually right for you."
            )
            await update.message.reply_text(reply)
            return MSG_8
        
        keyboard = [
            [InlineKeyboardButton("🔥 Get Instant Access Now", callback_data="show_payment")],
            [InlineKeyboardButton("Wait, I have a question", callback_data="ask_question")]
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
        
        if query.data == "show_payment":
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