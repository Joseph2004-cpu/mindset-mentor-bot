import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
import requests
import hmac
import hashlib

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ConversationHandler, ContextTypes, filters, CallbackQueryHandler
)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Get from environment variables (set these in your hosting platform)
TELEGRAM_TOKEN = os.getenv("8342995076:AAF-oiY5mOqp-Jjf9dy78xXlC7x6efs64_0", "8342995076:AAF-oiY5mOqp-Jjf9dy78xXlC7x6efs64_0")
PAYSTACK_SECRET_KEY = os.getenv("sk_test_85dbe5736b58511083732359b6a5441292463430", "sk_test_85dbe5736b58511083732359b6a5441292463430")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY")  # Optional: For AI responses

# Pricing in USD (Paystack converts to GHS automatically)
PRICING = {
    "starter": {
        "price_usd": 5,
        "price_ghs": 55,
        "name": "Starter 💪",
        "habits": 3,
        "features": "• 3 habits max\n• Daily check-ins\n• Basic tracking\n• Weekly summary"
    },
    "pro": {
        "price_usd": 10,
        "price_ghs": 110,
        "name": "Pro 🚀",
        "habits": 10,
        "features": "• Unlimited habits (10)\n• AI coaching\n• Advanced analytics\n• 1 streak save/month\n• Priority support"
    },
    "elite": {
        "price_usd": 15,
        "price_ghs": 165,
        "name": "Elite 👑",
        "habits": 10,
        "features": "• Everything in Pro\n• Consequence Mode\n• Accountability partners\n• 2 streak saves/month\n• Weekly coaching insights\n• Community access"
    }
}

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONVERSATION STATES
# =============================================================================

(
    ONBOARDING_HABIT,
    ONBOARDING_TIME,
    ONBOARDING_FIRST_ACTION,
    TRIAL_ACTIVE,
    WAITING_FOR_PROOF,
    PAYMENT_SELECT,
    PAID_ACTIVE,
    AI_COACHING,
) = range(8)

# =============================================================================
# IN-MEMORY DATABASE (Replace with PostgreSQL/MongoDB in production)
# =============================================================================

users_db: Dict[int, dict] = {}

def get_user(user_id: int) -> dict:
    """Get or create user record"""
    if user_id not in users_db:
        users_db[user_id] = {
            "user_id": user_id,
            "username": None,
            "email": None,
            "trial_start": None,
            "trial_days_completed": 0,
            "subscription_tier": None,
            "subscription_expires": None,
            "payment_reference": None,
            "habits": [],
            "current_habit": None,
            "check_in_time": "19:00",
            "streak": 0,
            "best_streak": 0,
            "total_completions": 0,
            "failed_days": 0,
            "last_check_in": None,
            "streak_saves_used": 0,
            "created_at": datetime.now().isoformat()
        }
    return users_db[user_id]

def save_user(user_data: dict):
    """Save user data"""
    users_db[user_data["user_id"]] = user_data
    # In production, save to database here
    logger.info(f"User {user_data['user_id']} data saved")

# =============================================================================
# PAYSTACK PAYMENT INTEGRATION
# =============================================================================

def initialize_paystack_payment(user_id: int, email: str, tier: str, username: str = None) -> dict:
    """
    Initialize Paystack payment
    Returns: {"status": bool, "authorization_url": str, "reference": str, "error": str}
    """
    try:
        tier_info = PRICING[tier]
        amount = tier_info["price_ghs"] * 100  # Convert to pesewas (GHS cents)
        
        url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": email,
            "amount": amount,
            "currency": "GHS",
            "reference": f"HAB_{user_id}_{tier}_{int(datetime.now().timestamp())}",
            "callback_url": "https://your-domain.com/payment-success",  # Update with your domain
            "metadata": {
                "user_id": user_id,
                "username": username,
                "tier": tier,
                "custom_fields": [
                    {
                        "display_name": "Subscription Tier",
                        "variable_name": "tier",
                        "value": tier_info["name"]
                    },
                    {
                        "display_name": "Telegram User ID",
                        "variable_name": "telegram_id",
                        "value": str(user_id)
                    }
                ]
            },
            "channels": ["card", "bank", "ussd", "mobile_money"]  # All payment methods
        }
        
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        if result.get("status"):
            return {
                "status": True,
                "authorization_url": result["data"]["authorization_url"],
                "reference": result["data"]["reference"],
                "access_code": result["data"]["access_code"],
                "error": None
            }
        else:
            return {
                "status": False,
                "authorization_url": None,
                "reference": None,
                "error": result.get("message", "Payment initialization failed")
            }
    
    except Exception as e:
        logger.error(f"Paystack initialization error: {e}")
        return {
            "status": False,
            "authorization_url": None,
            "reference": None,
            "error": str(e)
        }

def verify_paystack_payment(reference: str) -> dict:
    """
    Verify Paystack payment
    Returns: {"status": bool, "amount": int, "metadata": dict, "error": str}
    """
    try:
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
        }
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        if result.get("status") and result["data"]["status"] == "success":
            return {
                "status": True,
                "amount": result["data"]["amount"],
                "metadata": result["data"]["metadata"],
                "paid_at": result["data"]["paid_at"],
                "error": None
            }
        else:
            return {
                "status": False,
                "amount": None,
                "metadata": None,
                "error": "Payment verification failed"
            }
    
    except Exception as e:
        logger.error(f"Paystack verification error: {e}")
        return {
            "status": False,
            "amount": None,
            "metadata": None,
            "error": str(e)
        }

def verify_webhook_signature(payload: str, signature: str) -> bool:
    """Verify Paystack webhook signature for security"""
    try:
        hash_value = hmac.new(
            PAYSTACK_SECRET_KEY.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        return hash_value == signature
    except Exception as e:
        logger.error(f"Webhook verification error: {e}")
        return False

# =============================================================================
# AI COACHING (Optional - using simple responses if no API key)
# =============================================================================

def get_ai_response(user_message: str, context: str = "") -> str:
    """
    Get AI response for coaching
    Falls back to predefined responses if no API key
    """
    if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "YOUR_ANTHROPIC_KEY":
        try:
            # Call Claude API for personalized coaching
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 300,
                    "messages": [{
                        "role": "user",
                        "content": f"You are a tough-love accountability coach. {context}\n\nUser says: {user_message}\n\nRespond in 2-3 sentences with motivation or advice."
                    }]
                }
            )
            
            if response.status_code == 200:
                return response.json()["content"][0]["text"]
        except Exception as e:
            logger.error(f"AI API error: {e}")
    
    # Fallback responses
    responses = {
        "failed": "Look, missing days happens. But you need to figure out WHY. What's blocking you? Reply and let's fix this.",
        "success": "That's what I'm talking about! You showed up. Keep this energy going tomorrow.",
        "struggle": "I hear you. Building habits is hard. But you know what's harder? Living with regret. Let's break this down - what's ONE small thing you can do today?",
        "motivation": "Remember why you started. That person you want to become? They show up even when they don't feel like it. Be that person today."
    }
    
    # Simple keyword matching
    user_lower = user_message.lower()
    if any(word in user_lower for word in ["tired", "busy", "hard", "difficult", "can't"]):
        return responses["struggle"]
    elif any(word in user_lower for word in ["failed", "missed", "forgot", "didn't"]):
        return responses["failed"]
    else:
        return responses["motivation"]

# =============================================================================
# BOT HANDLERS
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - Begin onboarding"""
    user = update.effective_user
    user_data = get_user(user.id)
    user_data["username"] = user.username
    
    # Check if user has active subscription
    if user_data["subscription_tier"] and user_data["subscription_expires"]:
        if datetime.fromisoformat(user_data["subscription_expires"]) > datetime.now():
            await update.message.reply_text(
                f"Welcome back, {user.first_name}! 🔥\n\n"
                f"Streak: {user_data['streak']} days\n"
                f"Subscription: {PRICING[user_data['subscription_tier']]['name']}\n\n"
                "Commands:\n"
                "/checkin - Log today's habit\n"
                "/coach - Get AI coaching\n"
                "/stats - View your progress\n"
                "/help - All commands"
            )
            return PAID_ACTIVE
    
    # Check if trial is active
    if user_data["trial_start"]:
        trial_start = datetime.fromisoformat(user_data["trial_start"])
        days_elapsed = (datetime.now() - trial_start).days
        
        if days_elapsed < 2:
            await update.message.reply_text(
                f"Welcome back! You're on Day {user_data['trial_days_completed'] + 1} of your trial.\n\n"
                f"Current habit: {user_data['current_habit']}\n"
                f"Check-in time: {user_data['check_in_time']}\n\n"
                "Type /checkin when you've completed your habit!"
            )
            return TRIAL_ACTIVE
        else:
            # Trial expired, show payment options
            return await show_payment_options(update, context)
    
    # New user - start onboarding
    await update.message.reply_text(
        f"🔥 Welcome, {user.first_name}!\n\n"
        "I'm your AI accountability partner. No BS, just results.\n\n"
        "Here's how this works:\n"
        "→ You tell me ONE habit you want to build\n"
        "→ I check in on you EVERY DAY\n"
        "→ You send proof or explain what happened\n"
        "→ We build your streak together\n\n"
        "You get 2 days FREE to try this.\n\n"
        "Ready? What's ONE habit you've been putting off?\n"
        "(Example: 'Go to the gym', 'Wake up at 6am', 'Study for 1 hour')"
    )
    
    return ONBOARDING_HABIT

async def onboarding_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture user's first habit"""
    user_data = get_user(update.effective_user.id)
    habit = update.message.text.strip()
    
    user_data["current_habit"] = habit
    user_data["habits"] = [{"name": habit, "created": datetime.now().isoformat()}]
    save_user(user_data)
    
    await update.message.reply_text(
        f"Perfect. Your habit: \"{habit}\"\n\n"
        "When should I check in with you DAILY?\n"
        "(Example: '7 PM', '19:00', '6:30 AM')\n\n"
        "Pick a time when you'll definitely be free to respond."
    )
    
    return ONBOARDING_TIME

async def onboarding_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set check-in time"""
    user_data = get_user(update.effective_user.id)
    time_text = update.message.text.strip()
    
    # Simple time parsing (expand this for production)
    user_data["check_in_time"] = time_text
    save_user(user_data)
    
    await update.message.reply_text(
        f"Got it. I'll check in at {time_text} every day.\n\n"
        "But let's not wait until tomorrow.\n\n"
        f"Do your habit RIGHT NOW: \"{user_data['current_habit']}\"\n\n"
        "Even if it's just 5 minutes. Then send me proof (photo, screenshot, or just type 'DONE').\n\n"
        "I'll wait. ⏳"
    )
    
    return ONBOARDING_FIRST_ACTION

async def onboarding_first_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User completes first action"""
    user_data = get_user(update.effective_user.id)
    
    # Start trial
    user_data["trial_start"] = datetime.now().isoformat()
    user_data["trial_days_completed"] = 1
    user_data["streak"] = 1
    user_data["best_streak"] = 1
    user_data["total_completions"] = 1
    user_data["last_check_in"] = datetime.now().isoformat()
    save_user(user_data)
    
    await update.message.reply_text(
        "🔥 DAY 1 COMPLETE! 🔥\n\n"
        f"Habit: {user_data['current_habit']} ✅\n"
        "Streak: 1 day\n"
        "Completion rate: 100%\n\n"
        "That's what I'm talking about! You actually showed up.\n\n"
        "Most people quit before they start. You're different.\n\n"
        f"I'll check in tomorrow at {user_data['check_in_time']}. Don't let me down.\n\n"
        "Commands:\n"
        "/checkin - Log your habit anytime\n"
        "/coach - Talk to me if you're struggling\n"
        "/stats - See your progress"
    )
    
    return TRIAL_ACTIVE

async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle check-in"""
    user_data = get_user(update.effective_user.id)
    
    # Check if already checked in today
    if user_data["last_check_in"]:
        last_checkin = datetime.fromisoformat(user_data["last_check_in"])
        if last_checkin.date() == datetime.now().date():
            await update.message.reply_text(
                "You already checked in today! ✅\n\n"
                f"Current streak: {user_data['streak']} days 🔥\n\n"
                "Come back tomorrow to keep it going."
            )
            return TRIAL_ACTIVE if not user_data["subscription_tier"] else PAID_ACTIVE
    
    await update.message.reply_text(
        f"Did you complete your habit today?\n"
        f"📋 {user_data['current_habit']}\n\n"
        "Reply:\n"
        "✅ YES (or send proof)\n"
        "❌ NO (be honest)"
    )
    
    return WAITING_FOR_PROOF

async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user's proof submission"""
    user_data = get_user(update.effective_user.id)
    message = update.message.text.lower().strip() if update.message.text else ""
    
    # Check if it's a success
    if message in ["yes", "done", "✅", "completed"] or update.message.photo:
        # Success!
        user_data["streak"] += 1
        user_data["total_completions"] += 1
        user_data["last_check_in"] = datetime.now().isoformat()
        
        if user_data["streak"] > user_data["best_streak"]:
            user_data["best_streak"] = user_data["streak"]
        
        # Check if trial day completed
        if user_data["trial_start"] and not user_data["subscription_tier"]:
            trial_start = datetime.fromisoformat(user_data["trial_start"])
            days_elapsed = (datetime.now() - trial_start).days
            user_data["trial_days_completed"] = days_elapsed + 1
        
        save_user(user_data)
        
        response = (
            f"🔥 STREAK: {user_data['streak']} DAYS 🔥\n\n"
            f"That's what I'm talking about! You showed up.\n\n"
            f"Total completions: {user_data['total_completions']}\n"
            f"Best streak: {user_data['best_streak']} days\n\n"
        )
        
        # Check if trial is ending
        if user_data["trial_days_completed"] >= 2 and not user_data["subscription_tier"]:
            response += (
                "\n━━━━━━━━━━━━━━━━━━\n"
                "⚠️ YOUR FREE TRIAL ENDS TONIGHT ⚠️\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"You built a {user_data['streak']}-day streak.\n"
                "Your streak dies at midnight unless you continue.\n\n"
                "Ready to commit? Type /subscribe"
            )
        else:
            response += f"See you tomorrow. Keep this energy going! 💪"
        
        await update.message.reply_text(response)
        
        # Show payment if trial done
        if user_data["trial_days_completed"] >= 2 and not user_data["subscription_tier"]:
            return await show_payment_options(update, context)
        
        return TRIAL_ACTIVE if not user_data["subscription_tier"] else PAID_ACTIVE
    
    elif message in ["no", "❌", "failed", "missed"]:
        # Failed
        user_data["failed_days"] += 1
        user_data["streak"] = 0
        user_data["last_check_in"] = datetime.now().isoformat()
        
        # Check if trial day completed
        if user_data["trial_start"] and not user_data["subscription_tier"]:
            trial_start = datetime.fromisoformat(user_data["trial_start"])
            days_elapsed = (datetime.now() - trial_start).days
            user_data["trial_days_completed"] = days_elapsed + 1
        
        save_user(user_data)
        
        response = (
            f"Streak broken. Back to Day 0.\n\n"
            f"What happened? Why did you skip?\n"
            "(Be honest - I'm here to help, not judge)\n\n"
            f"Best streak: {user_data['best_streak']} days\n"
            f"You've done it before. You can do it again."
        )
        
        # Check if trial is ending
        if user_data["trial_days_completed"] >= 2 and not user_data["subscription_tier"]:
            response += (
                "\n\n━━━━━━━━━━━━━━━━━━\n"
                "⚠️ TRIAL ENDING ⚠️\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "You missed Day 2. But Day 1 happened.\n"
                "That counts.\n\n"
                "If you want accountability that actually works, let's keep going.\n\n"
                "Type /subscribe to continue."
            )
        
        await update.message.reply_text(response)
        
        if user_data["trial_days_completed"] >= 2 and not user_data["subscription_tier"]:
            return await show_payment_options(update, context)
        
        return TRIAL_ACTIVE if not user_data["subscription_tier"] else PAID_ACTIVE
    
    else:
        await update.message.reply_text(
            "I need a clear answer:\n"
            "✅ YES (completed)\n"
            "❌ NO (missed it)"
        )
        return WAITING_FOR_PROOF

async def show_payment_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show subscription tiers"""
    user_data = get_user(update.effective_user.id)
    
    keyboard = [
        [InlineKeyboardButton(
            f"{PRICING['starter']['name']} - ${PRICING['starter']['price_usd']}/mo (GHS {PRICING['starter']['price_ghs']})",
            callback_data='pay_starter'
        )],
        [InlineKeyboardButton(
            f"{PRICING['pro']['name']} - ${PRICING['pro']['price_usd']}/mo (GHS {PRICING['pro']['price_ghs']}) ⭐ BEST",
            callback_data='pay_pro'
        )],
        [InlineKeyboardButton(
            f"{PRICING['elite']['name']} - ${PRICING['elite']['price_usd']}/mo (GHS {PRICING['elite']['price_ghs']})",
            callback_data='pay_elite'
        )],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"🔥 {user_data['trial_days_completed']}-DAY TRIAL COMPLETE 🔥\n\n"
        "You showed up. Most people don't make it this far.\n\n"
        "Your free trial ends tonight. Here's what happens next:\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💪 {PRICING['starter']['name']} - ${PRICING['starter']['price_usd']}/month (GHS {PRICING['starter']['price_ghs']})\n"
        f"{PRICING['starter']['features']}\n\n"
        f"🚀 {PRICING['pro']['name']} - ${PRICING['pro']['price_usd']}/month (GHS {PRICING['pro']['price_ghs']}) ⭐\n"
        f"{PRICING['pro']['features']}\n\n"
        f"👑 {PRICING['elite']['name']} - ${PRICING['elite']['price_usd']}/month (GHS {PRICING['elite']['price_ghs']})\n"
        f"{PRICING['elite']['features']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Your streak: {user_data['streak']} days\n\n"
        "Your streak dies at midnight unless you choose.\n\n"
        "Which level matches your commitment?"
    )
    
    await update.message.reply_text(message, reply_markup=reply_markup)
    return PAYMENT_SELECT

async def handle_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tier selection and initiate Paystack payment"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_data = get_user(user.id)
    
    # Extract tier from callback
    tier = query.data.replace('pay_', '')
    
    if tier not in PRICING:
        await query.edit_message_text("Invalid plan selected. Please try again with /subscribe")
        return PAYMENT_SELECT
    
    tier_info = PRICING[tier]
    
    # Request email if not provided
    if not user_data.get("email"):
        await query.edit_message_text(
            f"You selected: {tier_info['name']}\n"
            f"Price: ${tier_info['price_usd']}/month (GHS {tier_info['price_ghs']})\n\n"
            "Please provide your email address for payment:\n"
            "(Type your email below)"
        )
        context.user_data['selected_tier'] = tier
        return PAYMENT_SELECT
    
    # Initialize Paystack payment
    email = user_data.get("email", f"{user.id}@telegram.user")  # Fallback email
    payment_result = initialize_paystack_payment(
        user_id=user.id,
        email=email,
        tier=tier,
        username=user.username
    )
    
    if payment_result["status"]:
        # Save payment reference
        user_data["payment_reference"] = payment_result["reference"]
        user_data["pending_tier"] = tier
        save_user(user_data)
        
        keyboard = [[InlineKeyboardButton("💳 Pay Now with Paystack", url=payment_result["authorization_url"])]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Perfect! You selected: {tier_info['name']}\n\n"
            f"Amount: GHS {tier_info['price_ghs']} (~${tier_info['price_usd']} USD)\n\n"
            "Click the button below to complete payment with Paystack.\n"
            "You can pay with:\n"
            "💳 Card (Visa/Mastercard)\n"
            "🏦 Bank Transfer\n"
            "📱 Mobile Money\n\n"
            "After payment, type /verify to activate your subscription!",
            reply_markup=reply_markup
        )
        
        return PAYMENT_SELECT
    else:
        await query.edit_message_text(
            f"❌ Payment initialization failed: {payment_result['error']}\n\n"
            "Please try again with /subscribe or contact support."
        )
        return PAYMENT_SELECT

async def capture_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture user email for payment"""
    email = update.message.text.strip()
    
    # Basic email validation
    if '@' not in email or '.' not in email:
        await update.message.reply_text(
            "That doesn't look like a valid email. Please try again:\n"
            "(Example: yourname@gmail.com)"
        )
        return PAYMENT_SELECT
    
    user_data = get_user(update.effective_user.id)
    user_data["email"] = email
    save_user(user_data)
    
    # Get selected tier from context
    tier = context.user_data.get('selected_tier', 'pro')
    
    # Initialize payment
    payment_result = initialize_paystack_payment(
        user_id=update.effective_user.id,
        email=email,
        tier=tier,
        username=update.effective_user.username
    )
    
    if payment_result["status"]:
        user_data["payment_reference"] = payment_result["reference"]
        user_data["pending_tier"] = tier
        save_user(user_data)
        
        tier_info = PRICING[tier]
        keyboard = [[InlineKeyboardButton("💳 Pay Now with Paystack", url=payment_result["authorization_url"])]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Email saved: {email}\n\n"
            f"Plan: {tier_info['name']}\n"
            f"Amount: GHS {tier_info['price_ghs']}\n\n"
            "Click below to complete payment:",
            reply_markup=reply_markup
        )
        
        await update.message.reply_text(
            "After payment completes, type /verify to activate your subscription! 🚀"
        )
        
        return PAYMENT_SELECT
    else:
        await update.message.reply_text(
            f"❌ Payment initialization failed: {payment_result['error']}\n\n"
            "Please try /subscribe again."
        )
        return PAYMENT_SELECT

async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify payment and activate subscription"""
    user_data = get_user(update.effective_user.id)
    
    if not user_data.get("payment_reference"):
        await update.message.reply_text(
            "No pending payment found. Please start with /subscribe"
        )
        return PAYMENT_SELECT
    
    # Verify with Paystack
    verification = verify_paystack_payment(user_data["payment_reference"])
    
    if verification["status"]:
        # Activate subscription
        tier = user_data.get("pending_tier", "pro")
        user_data["subscription_tier"] = tier
        user_data["subscription_expires"] = (datetime.now() + timedelta(days=30)).isoformat()
        user_data["payment_reference"] = None
        user_data["pending_tier"] = None
        save_user(user_data)
        
        tier_info = PRICING[tier]
        
        await update.message.reply_text(
            f"✅ PAYMENT CONFIRMED!\n\n"
            f"Welcome to {tier_info['name']}! 🎉\n\n"
            f"Your subscription is active for 30 days.\n"
            f"Expires: {datetime.fromisoformat(user_data['subscription_expires']).strftime('%B %d, %Y')}\n\n"
            f"Features unlocked:\n{tier_info['features']}\n\n"
            f"Current streak: {user_data['streak']} days 🔥\n\n"
            "Let's keep building. Type /checkin when you complete your habit!"
        )
        
        return PAID_ACTIVE
    else:
        await update.message.reply_text(
            f"❌ Payment verification failed: {verification['error']}\n\n"
            "If you completed payment, please wait a moment and try /verify again.\n"
            "Or contact support if the issue persists."
        )
        return PAYMENT_SELECT

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe command - show payment options"""
    return await show_payment_options(update, context)

async def coach_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI Coaching command"""
    user_data = get_user(update.effective_user.id)
    
    # Check if user has access to coaching (Pro/Elite tiers or trial)
    tier = user_data.get("subscription_tier")
    if tier and tier not in ["pro", "elite"]:
        await update.message.reply_text(
            "AI Coaching is available in Pro 🚀 and Elite 👑 plans.\n\n"
            "Upgrade with /subscribe"
        )
        return TRIAL_ACTIVE if not tier else PAID_ACTIVE
    
    await update.message.reply_text(
        "💬 AI Coach Activated\n\n"
        "Tell me what's on your mind:\n"
        "• Why did you skip today?\n"
        "• What's blocking you?\n"
        "• Need motivation?\n\n"
        "I'm listening..."
    )
    
    return AI_COACHING

async def handle_coaching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle AI coaching conversation"""
    user_data = get_user(update.effective_user.id)
    user_message = update.message.text
    
    # Get AI response
    context_info = f"User's habit: {user_data['current_habit']}. Streak: {user_data['streak']} days."
    ai_response = get_ai_response(user_message, context_info)
    
    await update.message.reply_text(
        f"{ai_response}\n\n"
        "Need more help? Keep talking.\n"
        "Or type /done when you're ready to get back on track."
    )
    
    return AI_COACHING

async def done_coaching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exit coaching mode"""
    await update.message.reply_text(
        "Alright. You know what to do.\n\n"
        "Type /checkin when you complete your habit. 💪"
    )
    
    user_data = get_user(update.effective_user.id)
    return TRIAL_ACTIVE if not user_data.get("subscription_tier") else PAID_ACTIVE

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user_data = get_user(update.effective_user.id)
    
    completion_rate = 0
    total_days = user_data["total_completions"] + user_data["failed_days"]
    if total_days > 0:
        completion_rate = (user_data["total_completions"] / total_days) * 100
    
    tier_name = "Free Trial"
    if user_data.get("subscription_tier"):
        tier_name = PRICING[user_data["subscription_tier"]]["name"]
    
    expires = "N/A"
    if user_data.get("subscription_expires"):
        expires = datetime.fromisoformat(user_data["subscription_expires"]).strftime('%B %d, %Y')
    
    stats_message = (
        "📊 YOUR PROGRESS\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Current Streak: {user_data['streak']} days 🔥\n"
        f"Best Streak: {user_data['best_streak']} days\n"
        f"Total Completions: {user_data['total_completions']}\n"
        f"Missed Days: {user_data['failed_days']}\n"
        f"Completion Rate: {completion_rate:.1f}%\n\n"
        f"Current Habit: {user_data['current_habit']}\n"
        f"Check-in Time: {user_data['check_in_time']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Plan: {tier_name}\n"
        f"Expires: {expires}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Keep showing up. That's all that matters. 💪"
    )
    
    await update.message.reply_text(stats_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    help_text = (
        "🤖 HABIT BOT COMMANDS\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "/start - Start or restart bot\n"
        "/checkin - Log your daily habit\n"
        "/coach - AI coaching session (Pro/Elite)\n"
        "/stats - View your progress\n"
        "/subscribe - View/change subscription\n"
        "/verify - Verify payment after checkout\n"
        "/help - Show this message\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Questions? Issues?\n"
        "Contact: @your_support_handle"
    )
    
    await update.message.reply_text(help_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    await update.message.reply_text(
        "Operation cancelled.\n\n"
        "Type /help to see available commands."
    )
    
    user_data = get_user(update.effective_user.id)
    return TRIAL_ACTIVE if not user_data.get("subscription_tier") else PAID_ACTIVE

# =============================================================================
# WEBHOOK HANDLER FOR PAYSTACK (Deploy as separate endpoint)
# =============================================================================

"""
IMPORTANT: Deploy this as a Flask/FastAPI webhook endpoint
Paystack will POST payment confirmations here

Example Flask implementation:

from flask import Flask, request
import hmac
import hashlib

app = Flask(__name__)

@app.route('/paystack-webhook', methods=['POST'])
def paystack_webhook():
    # Verify webhook signature
    signature = request.headers.get('x-paystack-signature')
    payload = request.get_data(as_text=True)
    
    hash_value = hmac.new(
        PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    
    if hash_value != signature:
        return 'Invalid signature', 401
    
    event = request.json
    
    if event['event'] == 'charge.success':
        # Extract user info
        metadata = event['data']['metadata']
        user_id = metadata['user_id']
        tier = metadata['tier']
        
        # Activate subscription in your database
        user_data = get_user(user_id)
        user_data['subscription_tier'] = tier
        user_data['subscription_expires'] = (datetime.now() + timedelta(days=30)).isoformat()
        save_user(user_data)
        
        # Send confirmation to user via Telegram
        # (You'll need to store the bot instance globally)
        
        return 'OK', 200
    
    return 'Ignored', 200

if __name__ == '__main__':
    app.run(port=5000)
"""

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Run the bot"""
    
    if TELEGRAM_TOKEN == "8342995076:AAF-oiY5mOqp-Jjf9dy78xXlC7x6efs64_0":
        logger.error("ERROR: Please set TELEGRAM_BOT_TOKEN environment variable")
        return
    
    if PAYSTACK_SECRET_KEY == "sk_test_85dbe5736b58511083732359b6a5441292463430":
        logger.error("ERROR: Please set PAYSTACK_SECRET_KEY environment variable")
        return
    
    # Build application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ONBOARDING_HABIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_habit)
            ],
            ONBOARDING_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_time)
            ],
            ONBOARDING_FIRST_ACTION: [
                MessageHandler(filters.TEXT | filters.PHOTO, onboarding_first_action)
            ],
            TRIAL_ACTIVE: [
                CommandHandler('checkin', checkin),
                CommandHandler('coach', coach_command),
                CommandHandler('stats', stats_command),
                CommandHandler('subscribe', subscribe_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proof)
            ],
            WAITING_FOR_PROOF: [
                MessageHandler(filters.TEXT | filters.PHOTO, handle_proof)
            ],
            PAYMENT_SELECT: [
                CallbackQueryHandler(handle_payment_selection, pattern='^pay_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, capture_email),
                CommandHandler('verify', verify_payment)
            ],
            PAID_ACTIVE: [
                CommandHandler('checkin', checkin),
                CommandHandler('coach', coach_command),
                CommandHandler('stats', stats_command),
                CommandHandler('subscribe', subscribe_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proof)
            ],
            AI_COACHING: [
                CommandHandler('done', done_coaching),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_coaching)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('help', help_command),
            CommandHandler('start', start)
        ]
    )
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('stats', stats_command))
    application.add_handler(CommandHandler('verify', verify_payment))
    
    # Start bot
    logger.info("🔥 Habit Accountability Bot is running...")
    logger.info("Paystack integration active")
    application.run_polling()

if __name__ == '__main__':
    main()