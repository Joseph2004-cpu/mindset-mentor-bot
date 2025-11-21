import os
import re
import logging
import datetime
import requests
from typing import Dict, Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

import google.generativeai as genai

# ========== CONFIGURATION ==========
# Environment variables (must be set before running)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

# Validate environment variables
if not TELEGRAM_TOKEN or not GEMINI_API_KEY or not PAYSTACK_SECRET_KEY:
    raise ValueError("Missing required environment variables: TELEGRAM_TOKEN, GEMINI_API_KEY, PAYSTACK_SECRET_KEY")

# Initialize Gemini Client
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

# Paystack Configuration
PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"
PRO_AMOUNT = 2000  # 20.00 NGN in kobo (smallest currency unit)
CALLBACK_URL = "https://t.me/your_bot_username"  # Replace with your bot username

# Conversation States
AWAITING_EMAIL = 1
END = ConversationHandler.END

# Trial Configuration
TRIAL_DURATION_HOURS = 48  # 2 days

# System Prompt for AI
SOCRATIC_SYSTEM_PROMPT = """You are the ethical, infinitely patient High School Science Coach. Your mandate is to use the Socratic method to guide the student, never providing the final solution to a homework or test problem. If a user asks for a final answer, you must respond with a guiding question or the first step of the solution, using a positive and encouraging tone. Your expertise covers all core High School Science subjects, including Biology, Chemistry, and Physics."""

# ========== STATE MANAGEMENT ==========
# In-memory user data storage
user_data: Dict[int, Dict[str, Any]] = {}

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ========== HELPER FUNCTIONS ==========
def is_valid_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def initialize_user(user_id: int) -> None:
    """Initialize a new user's data."""
    if user_id not in user_data:
        user_data[user_id] = {
            'status': 'free',
            'email': None,
            'trial_start': datetime.datetime.now()
        }
        logger.info(f"Initialized new user: {user_id}")


def is_trial_active(user_id: int) -> bool:
    """Check if user's trial is still active."""
    if user_id not in user_data:
        return False
    
    user = user_data[user_id]
    
    # Pro/Elite users always have access
    if user['status'] in ['pro', 'elite']:
        return True
    
    # Check trial expiration for free users
    if user['status'] == 'free':
        time_diff = datetime.datetime.now() - user['trial_start']
        return time_diff.total_seconds() < (TRIAL_DURATION_HOURS * 3600)
    
    return False


def initialize_paystack_transaction(email: str, amount: int) -> Dict[str, Any]:
    """Initialize a Paystack transaction."""
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "email": email,
        "amount": amount,
        "callback_url": CALLBACK_URL,
        "currency": "NGN"
    }
    
    try:
        response = requests.post(PAYSTACK_INIT_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Paystack API error: {type(e).__name__}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                logger.error(f"Paystack error detail: {error_detail}")
                return {"status": False, "message": error_detail.get('message', str(e))}
            except:
                pass
        return {"status": False, "message": str(e)}


# ========== COMMAND HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user_id = update.effective_user.id
    initialize_user(user_id)
    
    user = user_data[user_id]
    trial_end = user['trial_start'] + datetime.timedelta(hours=TRIAL_DURATION_HOURS)
    
    welcome_message = f"""🎓 *Welcome to the Socratic Science Tutor!*

I'm here to guide you through High School Science (Biology, Chemistry, Physics) using the Socratic method. I won't give you direct answers, but I'll help you discover them yourself!

📅 *Your 2-Day Free Trial Started!*
Trial expires: {trial_end.strftime('%Y-%m-%d %H:%M:%S')}

Simply send me your science questions and I'll guide you through the solution step by step.

*Commands:*
/help - Show help information
/pro - Subscribe for unlimited access after trial

Let's begin your learning journey! 🚀"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = """📚 *How to Use This Bot*

*Free Trial:*
• 2 days of unlimited AI tutoring
• Covers Biology, Chemistry, and Physics
• Uses Socratic method to guide your learning

*After Trial:*
• Subscribe with /pro for continued access
• Only 40.00 for unlimited tutoring

*How It Works:*
1. Send me any science question
2. I'll guide you with questions and hints
3. You discover the answer yourself!

*Example:*
You: "What is photosynthesis?"
Me: "Great question! Let's explore this together. What do you know about how plants get their energy?"

Ready to learn? Just send me your question! 🔬"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


# ========== SOCRATIC TUTOR (AI Handler) ==========
async def socratic_qna(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle general messages with AI-powered Socratic guidance."""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Initialize user if needed
    initialize_user(user_id)
    
    # Check trial status
    if not is_trial_active(user_id):
        expired_message = """⏰ *Your 2-Day Trial Has Expired*

Thank you for trying the Socratic Science Tutor! To continue learning with unlimited AI guidance, please subscribe:

Use /pro to get unlimited access for just 40.00

Stay curious! 🌟"""
        await update.message.reply_text(expired_message, parse_mode='Markdown')
        return
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    try:
        # Generate AI response with Socratic system prompt
        full_prompt = f"{SOCRATIC_SYSTEM_PROMPT}\n\nStudent Question: {user_message}"
        response = gemini_model.generate_content(full_prompt)
        
        # Send AI response
        await update.message.reply_text(response.text)
        
    except Exception as e:
        logger.error(f"Gemini API error: {type(e).__name__}: {str(e)}")
        error_msg = f"I apologize, but I encountered an error processing your question.\n\nError: {type(e).__name__}\n\nPlease try again in a moment."
        await update.message.reply_text(error_msg)


# ========== PAYMENT FLOW (ConversationHandler) ==========
async def pro_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the subscription conversation."""
    user_id = update.effective_user.id
    initialize_user(user_id)
    
    message = """💎 *Upgrade to Pro Access*

Get unlimited AI-powered Socratic tutoring for High School Science!

*Price:* 40.00
*Benefits:*
• Unlimited questions and guidance
• 24/7 access to AI tutor
• All science subjects covered

To proceed, please enter your email address:"""
    
    await update.message.reply_text(message, parse_mode='Markdown')
    return AWAITING_EMAIL


async def collect_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect and validate email, then initialize Paystack transaction."""
    user_id = update.effective_user.id
    email = update.message.text.strip()
    
    # Validate email
    if not is_valid_email(email):
        await update.message.reply_text(
            "❌ Invalid email format. Please enter a valid email address:"
        )
        return AWAITING_EMAIL
    
    # Store email
    user_data[user_id]['email'] = email
    
    # Initialize Paystack transaction
    await update.message.reply_text("⏳ Initializing payment...")
    
    result = initialize_paystack_transaction(email, PRO_AMOUNT)
    
    if result.get('status'):
        authorization_url = result['data']['authorization_url']
        reference = result['data']['reference']
        
        payment_message = f"""✅ *Payment Link Generated!*

Click the link below to complete your payment:
{authorization_url}

*Reference:* `{reference}`

After payment, your account will be automatically upgraded to Pro access.

If you have any issues, please contact support."""
        
        await update.message.reply_text(payment_message, parse_mode='Markdown')
    else:
        error_message = f"""❌ *Payment Initialization Failed*

Error: {result.get('message', 'Unknown error')}

Please try again with /pro or contact support."""
        
        await update.message.reply_text(error_message, parse_mode='Markdown')
    
    return END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text(
        "Subscription cancelled. Use /pro anytime to subscribe!"
    )
    return END


# ========== MAIN APPLICATION ==========
def main() -> None:
    """Start the bot."""
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Payment conversation handler (highest priority)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('pro', pro_command)],
        states={
            AWAITING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_email)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Register handlers in priority order
    application.add_handler(conv_handler)  # Highest priority
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, socratic_qna))  # Fallback
    
    # Start the bot
    logger.info("Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()