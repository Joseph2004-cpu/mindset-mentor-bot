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
        
        self.question_sequences = {
            'stuck': [
                "So you feel stuck. Let me ask—when you look at areas where you ARE making progress, what's different about those?",
                "Interesting. So there are areas working. What would happen if you applied that same approach to where you're stuck?",
                "That's solid thinking. Now real question: if you had to pick ONE specific area where you're stuck, what would it be?",
                "Got it. And in that area, are you struggling because you don't know WHAT to do, or because you can't make yourself DO it?",
                "Ah, so it's a {struggle_type} issue. How long have you been dealing with this particular block?",
                "And during that time, have you tried changing anything, or has it pretty much stayed the same?",
                "Why do you think your previous attempts didn't stick? What usually gets in the way?",
                "That's the real insight. So the problem isn't knowledge—it's something in your operating system. Sound right?",
                "What if I told you there's a way to rewire that operating system so this block becomes impossible? Would that interest you?",
                "Before I show you what that looks like, help me understand: if this block disappeared tomorrow, what would actually change in your life?"
            ],
            'motivation': [
                "Motivation's tricky. But here's what I notice—you're probably crushing it in SOME areas. What's one thing you never skip?",
                "Interesting! So you CAN sustain. The question is: what's different about that versus where you struggle?",
                "Got it. So when you're strong in that area, what does your mindset feel like compared to other areas?",
                "That's key. So it's not about finding MORE motivation—it's about replicating that mindset. Make sense?",
                "Now let me ask the hard one: why do you think you can't replicate it elsewhere? What's the real difference?",
                "And that difference you mentioned—is that something about YOU, or something about the environment/systems?",
                "So if you fixed that one thing, do you think everything else would fall into place? Or are there other blocks?",
                "Tell me this: if someone gave you a proven system that made showing up automatic (not something you had to willpower), would you use it?",
                "Why do you think systems matter more than motivation for sustaining change?",
                "Okay, here's the real question: what would your life look like 6 months from now if you had that kind of automatic system in place?"
            ],
            'goals': [
                "Goals are great. But let me ask—when you imagine achieving this goal, what emotion comes up? Excitement or anxiety?",
                "Interesting. So there's {emotion} underneath. What do you think that's about—is it the goal itself, or something about achieving it?",
                "Got it. And if we removed that {emotion}, would you be all in? Or is there something else?",
                "Okay. So beyond the emotion, what's the actual gap between where you are now and that goal?",
                "And in that gap, what scares you most? Being honest—what's the real fear?",
                "That fear is smart—it means you care. But here's what I'm curious: what would happen if you reframed that fear as DATA instead of a stop sign?",
                "What if failure in this goal wasn't the end, but actually the fastest way to learn what works?",
                "If that were true, how would you approach this goal differently? What would you try that you're currently avoiding?",
                "So you'd be bolder, smarter, faster. What's stopping you from doing that right now?",
                "Last one: if you HAD to achieve this goal in the next 6 months no matter what, and you could change any beliefs holding you back—what would you change about yourself?"
            ],
            'procrastination': [
                "Procrastination's interesting. It's not laziness—it's resistance. What specifically are you resisting about this thing?",
                "Got it. So there's resistance around {resistance_type}. When did that resistance start? Was it always there for this?",
                "And when you try to push through that resistance, what happens? Do you force yourself, or do you just... not do it?",
                "Okay. So it's avoidance, not inability. Here's the question: what feeling are you avoiding when you procrastinate?",
                "That feeling—{avoided_feeling}—where did it come from? When's the first time you remember feeling that way about starting something?",
                "Interesting. So there's a deeper pattern. But let me ask: are there things you DON'T procrastinate on? Times when you just... start?",
                "Yes! So you CAN do it. What's different about those things? Why don't you resist them?",
                "That's crucial. So if we could make your goal feel as {non_resistance_quality} as that, you'd just do it. Right?",
                "What if I told you that's actually possible—not through motivation, but through changing how you approach the thing itself?",
                "Before I explain how, tell me: if you could eliminate procrastination on this ONE thing, what would that make possible for you?"
            ],
            'fear': [
                "Fear makes sense. It means you care about this. But let me ask—what specifically are you afraid of? Be specific.",
                "Got it. So the fear is {specific_fear}. Has that happened before, or is it a fear of the unknown?",
                "And if it DID happen, what would that actually mean about you? What's the worst-case narrative in your head?",
                "That narrative—where did it come from? Who taught you that story?",
                "Interesting. So that story has been running for a while. But here's what I want to know: have you ever DISPROVEN that story? Any counter-evidence?",
                "See, that's proof the story isn't true. So why does your brain keep telling it?",
                "What if instead of trying to eliminate the fear, you just... did it scared? What's stopping you?",
                "Real talk: what would happen if you failed at this thing you're afraid of? Would you actually die, lose everything, or is it more abstract?",
                "So the actual consequence is manageable. Why does your brain treat it like a death sentence?",
                "Okay, final one: if you knew you'd fail safely—that you'd learn, adapt, and come out stronger—would you try? What would that change?"
            ],
            'money': [
                "Money goals are really about *what money enables*. So let me ask: what do you think this money will actually change about your life?",
                "Interesting. So it's not the money itself—it's the freedom/security/respect/whatever. Let me ask: can you get SOME of that without waiting for the money?",
                "Thought so. So the blocker isn't money—it's something else. What IS actually holding you back from having that now, in some form?",
                "Got it. So if we fixed THAT, would the money follow? Or are they separate?",
                "Let me reframe: if you had to choose between the money and the mindset/skill/confidence it represents, which matters more?",
                "Right. So the real goal is becoming the person who earns/commands that money. How do you become that person?",
                "And what's stopping you from starting that transformation TODAY, before the money shows up?",
                "What if I told you the transformation comes first, THEN the money follows? Have you seen that happen?",
                "So you know it's possible. What would be different about you if you started now instead of waiting?",
                "Okay, final question: what's ONE move you could make in the next 48 hours that would put you on that path? What's the real blocker?"
            ],
            'general': [
                "Interesting. Help me understand the deeper layer—when you imagine solving this, what REALLY changes in your life?",
                "That shift you described—is that about external things changing, or is it about YOU changing how you see things?",
                "Got it. So there's both external and internal. Which one feels more in your control right now?",
                "And the one that feels less in your control—what makes it feel impossible?",
                "Okay, so that feels impossible. But have you ever accomplished something that ALSO felt impossible before you started?",
                "How did you overcome that? What was different about that time?",
                "So you've done hard things. What's different about THIS situation that makes it feel different?",
                "Is it actually different, or are you bringing a different mindset to it? What's actually changed about you since then?",
                "Here's the question: if you brought THAT version of you—the one who conquered the impossible—to this current situation, what would shift?",
                "What would that person do RIGHT NOW to move forward? And what's stopping you from being that person today?"
            ]
        }
    
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
                "Let's pick up from where we left off."
            )
            concern_type = user_data.get('concern_type', 'general')
            exchange_count = user_data.get('exchange_count', 0)
            if exchange_count < 10:
                context.user_data['concern_type'] = concern_type
                context.user_data['exchange_count'] = exchange_count
        else:
            await update.message.reply_text(
                f"Hey {first_name}! 👋\n\n"
                "I'm glad you're here. I want to ask you something real:\n\n"
                "**What's the one thing about yourself right now that you want to change?**"
            )
            self.update_user_data(user_id, {
                'first_name': first_name,
                'started_at': str(datetime.now()),
                'exchange_count': 0
            })
            return CONVERSATION
        
        return CONVERSATION

    async def handle_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_response = update.message.text
        
        user_data = self.get_user_data(user_id)
        exchange_count = context.user_data.get('exchange_count', user_data.get('exchange_count', 0))
        at_sales_pitch = context.user_data.get('at_sales_pitch', False)
        
        if not user_data.get('initial_concern'):
            concern_type = self.adapt_response(user_response)
            self.update_user_data(user_id, {
                'initial_concern': user_response,
                'concern_type': concern_type,
                'exchange_count': 0,
                'user_responses': [user_response]
            })
            context.user_data['concern_type'] = concern_type
            context.user_data['exchange_count'] = 0
            context.user_data['at_sales_pitch'] = False
            
            next_question = self.question_sequences.get(concern_type, self.question_sequences['general'])[0]
            await update.message.reply_text(next_question)
            return CONVERSATION
        
        if at_sales_pitch:
            answer = (
                f"Great question. Here's the thing: most people know WHAT to do. "
                f"They just can't make themselves do it consistently.\n\n"
                f"This blueprint isn't about adding more to your plate. It's about rewiring the operating system "
                f"so doing it becomes automatic.\n\n"
                f"That's why the check-ins matter—I keep you accountable to the *system*, not willpower.\n\n"
                f"Does that clarify it?"
            )
            await update.message.reply_text(answer)
            
            keyboard = [
                [InlineKeyboardButton("🔥 Okay, I'm in", callback_data="show_payment")],
                [InlineKeyboardButton("Need to think", callback_data="think_about_it")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "What do you want to do?",
                reply_markup=reply_markup
            )
            return PRODUCT_INTRO
        
        exchange_count += 1
        context.user_data['exchange_count'] = exchange_count
        
        user_responses = user_data.get('user_responses', [])
        user_responses.append(user_response)
        self.update_user_data(user_id, {'user_responses': user_responses, 'exchange_count': exchange_count})
        
        if exchange_count < 10:
            concern_type = context.user_data.get('concern_type', user_data.get('concern_type', 'general'))
            questions = self.question_sequences.get(concern_type, self.question_sequences['general'])
            
            if exchange_count < len(questions):
                next_question = questions[exchange_count]
                await update.message.reply_text(next_question)
            else:
                last_question = questions[-1]
                await update.message.reply_text(last_question)
            
            return CONVERSATION
        else:
            context.user_data['at_sales_pitch'] = True
            reply = (
                f"Okay {first_name}, I've learned a lot about where you are.\n\n"
                f"Here's what's clear to me: your challenge isn't about trying harder or knowing more.\n\n"
                f"It's about having the right framework—a system that rewires how you operate at the deepest level.\n\n"
                f"I've built exactly that. It's called **'Unleash Your Ultimate Mindset'**—a complete blueprint that addresses every friction point we just discussed.\n\n"
                f"🔹 Unshakeable self-belief (even when doubt screams)\n"
                f"🔹 Systems that make procrastination impossible\n"
                f"🔹 Turning failure into your fastest teacher\n"
                f"🔹 Making success feel inevitable, not exhausting\n"
                f"🔹 3-Day check-ins with me for accountability\n\n"
                f"**Investment:** GHS 75 ($6.85) — less than two coffees.\n\n"
                f"Ready to actually change this?"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔥 Yes, let's go", callback_data="show_payment")],
                [InlineKeyboardButton("I have one more question", callback_data="ask_question")],
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
                "What's your question? I'll answer, then we'll move forward."
            )
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