import os
import logging
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

# Bot States
INITIAL_CHAT, ASSESS_SITUATION, OFFER_SOLUTION, POST_PURCHASE, GATHER_FEEDBACK, BUILD_SYSTEM = range(6)

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Your Paystack payment link
PAYSTACK_LINK = "https://paystack.com/buy/unleash-your-ultimate-mindset-the-5-step-blueprint-to-uwsyav"  # Replace with your actual link

class MindsetBot:
    def __init__(self):
        self.user_data = {}
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Initial interaction - warm and welcoming"""
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        
        # Check if user has already purchased
        if context.user_data.get('purchased', False):
            await update.message.reply_text(
                f"Welcome back, {first_name}! 🙌\n\n"
                "Ready to build your personalized system? Type 'done' or tap the button below when you're ready to dive in!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done Reading", callback_data="done_reading")]])
            )
            return POST_PURCHASE
        
        await update.message.reply_text(
            f"Hey {first_name}! 👋\n\n"
            "I'm curious—what brought you here today? What's been on your mind lately?"
        )
        return INITIAL_CHAT

    async def initial_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Listen and empathize"""
        user_response = update.message.text.lower()
        context.user_data['initial_concern'] = update.message.text
        
        # Analyze response for keywords
        if any(word in user_response for word in ['stuck', 'motivation', 'procrastination', 'start']):
            response = (
                "I hear you. That feeling of being stuck is frustrating, right? "
                "Like you know what you want to do, but something invisible keeps pulling you back.\n\n"
                "Can I ask—is this something that happens once in a while, or does it feel like a pattern you keep falling into?"
            )
        elif any(word in user_response for word in ['goal', 'achieve', 'success', 'business']):
            response = (
                "That's exciting! Having goals is powerful. "
                "But let me ask you something real—when you set these goals, do they feel like *your* goals, or are they shaped by what others expect?\n\n"
                "Be honest. There's no wrong answer."
            )
        else:
            response = (
                "Thanks for sharing that with me. "
                "Here's what I'm noticing—a lot of people feel like they're working hard but not really moving forward. "
                "Does that resonate with you at all?"
            )
        
        await update.message.reply_text(response)
        return ASSESS_SITUATION

    async def assess_situation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Dig deeper and position the solution"""
        context.user_data['assessment'] = update.message.text
        
        response = (
            "You know what's interesting? Most people think the problem is motivation or discipline. "
            "But it's actually something deeper—it's your *mindset*, the invisible operating system running in the background.\n\n"
            "Think of it like this: You can have the best apps (goals, plans, strategies), "
            "but if your phone's operating system is outdated or buggy, nothing works smoothly.\n\n"
            "Have you ever felt like you're sabotaging yourself? Like part of you wants success but another part keeps hitting the brakes?"
        )
        
        await update.message.reply_text(response)
        return OFFER_SOLUTION

    async def offer_solution(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Present the PDF naturally"""
        user_response = update.message.text.lower()
        
        response = (
            "That's exactly what I thought. And here's the thing—you can't just 'think positive' your way out of this. "
            "You need a systematic approach to rewire how you operate.\n\n"
            "I've been working with a blueprint that breaks this down into 5 concrete steps:\n"
            "1️⃣ Getting crystal clear on WHO you need to be (not just what you want)\n"
            "2️⃣ Rewiring the inner voice that tells you you're not enough\n"
            "3️⃣ Using failure as fuel instead of letting it stop you\n"
            "4️⃣ Building systems that make success automatic\n"
            "5️⃣ Creating momentum that compounds over time\n\n"
            "I've put all of this into a complete guide—*'Unleash Your Ultimate Mindset'*. "
            "It's not theory. It's the exact framework that turns the invisible wall into rocket fuel.\n\n"
            "I genuinely think this could be exactly what you need right now. "
        )
        
        keyboard = [
            [InlineKeyboardButton("🔥 Yes, I'm ready to shift my mindset", callback_data="show_payment")],
            [InlineKeyboardButton("Tell me more", callback_data="more_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, reply_markup=reply_markup)
        return OFFER_SOLUTION

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "show_payment":
            payment_message = (
                "Perfect! Here's what you're getting:\n\n"
                "📖 *'Unleash Your Ultimate Mindset'* - Complete Blueprint\n"
                "✅ 5-Step System to Rewire Your Operating System\n"
                "✅ Actionable Frameworks (Evidence Inventory, MVE, If-Then Planning)\n"
                "✅ Quarterly Review System for Long-Term Success\n\n"
                "Investment: [GHS 75/$6.85]\n\n"
                "Plus, after you finish reading, I'll personally help you build your custom system. "
                "You won't be doing this alone.\n\n"
                f"Ready? 👇\n{PAYSTACK_LINK}\n\n"
                "After payment, you'll get instant access to the PDF. When you're done reading, "
                "click the link at the end to come back here, and we'll build your personalized game plan together."
            )
            await query.edit_message_text(payment_message, parse_mode='Markdown')
            
            # Simulate purchase for demo - in production, integrate Paystack webhook
            keyboard = [[InlineKeyboardButton("✅ I've Completed Payment", callback_data="confirm_payment")]]
            await query.message.reply_text(
                "Tap below once you've completed your payment:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return POST_PURCHASE
            
        elif query.data == "more_info":
            more_info = (
                "Fair enough! Let me be straight with you:\n\n"
                "This isn't another 'feel-good' motivation book. This is an engineering manual for your mind.\n\n"
                "Most people fail because they're trying to build a skyscraper on a cracked foundation. "
                "This guide shows you how to:\n"
                "• Stop climbing ladders leaning on the wrong buildings\n"
                "• Turn your brain's lies into proof of your capability\n"
                "• Make failure productive instead of paralyzing\n"
                "• Design your environment so success is inevitable\n\n"
                "The people who've applied this? They don't talk about 'finding motivation' anymore. "
                "They just execute.\n\n"
                "Sound like what you need?"
            )
            keyboard = [[InlineKeyboardButton("🔥 Yes, let's do this", callback_data="show_payment")]]
            await query.edit_message_text(more_info, reply_markup=InlineKeyboardMarkup(keyboard))
            return OFFER_SOLUTION
            
        elif query.data == "confirm_payment":
            context.user_data['purchased'] = True
            await query.edit_message_text(
                "🎉 Awesome! Check your email for the PDF.\n\n"
                "Take your time reading through it. When you're done, "
                "click the link at the end of the PDF and we'll build your custom system together.\n\n"
                "See you on the other side! 💪"
            )
            return ConversationHandler.END
            
        elif query.data == "done_reading":
            await query.edit_message_text("Welcome back! Let's talk about what you just learned. 🚀")
            await query.message.reply_text(
                "First things first—how was the read? What hit home for you the most?\n\n"
                "(Be real with me. What part made you think: 'Damn, that's exactly my problem'?)"
            )
            return GATHER_FEEDBACK

    async def gather_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect feedback and transition to system building"""
        context.user_data['feedback'] = update.message.text
        
        response = (
            "I love that insight! That self-awareness is exactly where the shift begins.\n\n"
            "Now, let's make this practical. Based on what you read, "
            "where do you think your biggest friction point is *right now*?\n\n"
            "Is it:\n"
            "A) Clarity - You're not 100% sure what you're actually working toward\n"
            "B) Belief - You know what to do but doubt creeps in\n"
            "C) Execution - You have the plan but don't follow through\n"
            "D) Systems - You're relying on willpower instead of design\n\n"
            "Just type the letter (A, B, C, or D)."
        )
        
        await update.message.reply_text(response)
        return BUILD_SYSTEM

    async def build_system(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Guide user through building their personalized system"""
        choice = update.message.text.upper().strip()
        
        if choice == 'A':
            response = (
                "Clarity is the foundation. If you're climbing the wrong ladder, speed doesn't matter.\n\n"
                "Let's do this exercise right now:\n\n"
                "*The North Star Exercise*\n"
                "1. Complete this sentence: 'In 5 years, I want to be known as someone who...'\n"
                "2. Now ask: Does this definition excite me, or am I trying to impress someone?\n\n"
                "Take your time. Send me your answer, and let's refine it together."
            )
        elif choice == 'B':
            response = (
                "Belief is the software update your brain needs. Let's catch those lies.\n\n"
                "*The Evidence Inventory (Start Now)*\n"
                "1. Write down ONE limiting belief that keeps showing up (e.g., 'I'm not disciplined enough')\n"
                "2. List 3 times you PROVED that belief wrong (even small wins count)\n\n"
                "Send me the belief and your 3 examples. We're going to demolish it."
            )
        elif choice == 'C':
            response = (
                "Execution is where most people stall. You need MVE—Minimum Viable Effort.\n\n"
                "*The MVE Challenge*\n"
                "Pick ONE goal you've been avoiding. Now answer:\n"
                "1. What's the absolute smallest step I can take in the next 2 hours?\n"
                "2. What's the worst that can happen if this small step fails?\n\n"
                "The goal is to fail small and learn fast. What's your MVE going to be?"
            )
        elif choice == 'D':
            response = (
                "Systems beat willpower every time. Let's build your first If-Then.\n\n"
                "*The If-Then Builder*\n"
                "Think of ONE action you keep 'forgetting' to do (e.g., working out, writing, deep work).\n\n"
                "Now complete this:\n"
                "'If [specific trigger], then I will immediately [specific action].'\n\n"
                "Example: 'If I pour my morning coffee, then I immediately open my journal.'\n\n"
                "What's yours? Send it to me."
            )
        else:
            response = (
                "Hmm, I didn't catch that. Just reply with A, B, C, or D based on your biggest friction point:\n\n"
                "A) Clarity\nB) Belief\nC) Execution\nD) Systems"
            )
            await update.message.reply_text(response)
            return BUILD_SYSTEM
        
        await update.message.reply_text(response, parse_mode='Markdown')
        context.user_data['focus_area'] = choice
        return BUILD_SYSTEM

    async def handle_system_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Continue guiding through system building"""
        user_input = update.message.text
        focus_area = context.user_data.get('focus_area', '')
        
        response = (
            "This is solid! You're already thinking differently.\n\n"
            "Here's what I want you to do in the next 48 hours:\n"
            "1. Test what you just defined\n"
            "2. Track what happens (no judgment, just data)\n"
            "3. Come back here and tell me how it went\n\n"
            "Remember: You're not looking for perfection. You're looking for the next data point.\n\n"
            "I'll check in with you in 2 days. Type /checkin when you're ready to report back.\n\n"
            "You've got this! 🔥"
        )
        
        await update.message.reply_text(response)
        return ConversationHandler.END

    async def checkin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Allow users to check back in"""
        await update.message.reply_text(
            "Welcome back! How'd your experiment go?\n\n"
            "Tell me:\n"
            "1. What did you try?\n"
            "2. What actually happened?\n"
            "3. What did you learn?\n\n"
            "Remember—there's no such thing as failure, only data. Let's hear it!"
        )
        return BUILD_SYSTEM

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel conversation"""
        await update.message.reply_text(
            "No worries! Whenever you're ready to continue, just type /start.\n\n"
            "Remember: The best time to start was yesterday. The second best time is now. 💪"
        )
        return ConversationHandler.END


def main():
    """Start the bot"""
    # Replace with your bot token
    TOKEN = "8342995076:AAH9TosXOwx_1KF3Kb5TwrKEcVlWqUmPEBI"
    
    application = Application.builder().token(TOKEN).build()
    bot = MindsetBot()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', bot.start)],
        states={
            INITIAL_CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.initial_chat)],
            ASSESS_SITUATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.assess_situation)],
            OFFER_SOLUTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.offer_solution),
                CallbackQueryHandler(bot.button_handler)
            ],
            POST_PURCHASE: [CallbackQueryHandler(bot.button_handler)],
            GATHER_FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.gather_feedback)],
            BUILD_SYSTEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_system_response)],
        },
        fallbacks=[
            CommandHandler('cancel', bot.cancel),
            CommandHandler('checkin', bot.checkin)
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Start the bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()