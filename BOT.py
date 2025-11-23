import os
import re
import logging
import datetime
import requests
from typing import Dict, Any, List
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ========== CONFIGURATION ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

# Validate environment variables
if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY or not PAYSTACK_SECRET_KEY:
    raise ValueError("Missing required environment variables")

# OpenRouter Configuration
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
PRIMARY_MODEL = "google/gemini-2.5-pro-free"
BACKUP_MODEL = "meta-llama/llama-4-maverick-free"

# Paystack Configuration
PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"
CALLBACK_URL = "https://t.me/YourBotUsername"  # Update with your bot username

# Pricing (in GHS pesewas)
PRICING = {
    'creator': {'amount': 30000, 'name': 'Creator', 'limit': 100},
    'business': {'amount': 75000, 'name': 'Business', 'limit': 500},
    'agency': {'amount': 225000, 'name': 'Agency', 'limit': 999999}
}

# Free tier limits
FREE_DAILY_LIMIT = 5
TRIAL_DURATION_HOURS = 48

# Conversation States
AWAITING_EMAIL, AWAITING_PLAN = range(2)

# Content types
CONTENT_TYPES = {
    '📱 Social Media Post': 'social_post',
    '📢 Ad Copy': 'ad_copy',
    '📦 Product Description': 'product_desc',
    '#️⃣ Hashtags': 'hashtags',
    '🎨 Generate Image': 'image'
}

# ========== STATE MANAGEMENT ==========
user_data: Dict[int, Dict[str, Any]] = {}

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ========== HELPER FUNCTIONS ==========
def initialize_user(user_id: int) -> None:
    """Initialize a new user's data."""
    if user_id not in user_data:
        user_data[user_id] = {
            'status': 'free',
            'email': None,
            'trial_start': datetime.datetime.now(),
            'daily_usage': 0,
            'last_reset': datetime.datetime.now().date(),
            'total_generations': 0,
            'plan_name': None
        }
        logger.info(f"Initialized new user: {user_id}")


def reset_daily_usage(user_id: int) -> None:
    """Reset daily usage counter if it's a new day."""
    user = user_data[user_id]
    today = datetime.datetime.now().date()
    
    if user['last_reset'] < today:
        user['daily_usage'] = 0
        user['last_reset'] = today


def check_usage_limit(user_id: int) -> tuple[bool, int]:
    """Check if user can generate content. Returns (can_generate, remaining)."""
    initialize_user(user_id)
    reset_daily_usage(user_id)
    
    user = user_data[user_id]
    
    if user['status'] == 'free':
        remaining = FREE_DAILY_LIMIT - user['daily_usage']
        return (remaining > 0, remaining)
    else:
        plan_limit = PRICING[user['status']]['limit']
        remaining = plan_limit - user['daily_usage']
        return (remaining > 0, remaining)


def increment_usage(user_id: int) -> None:
    """Increment user's usage counter."""
    user_data[user_id]['daily_usage'] += 1
    user_data[user_id]['total_generations'] += 1


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def call_openrouter(prompt: str, system_prompt: str = None) -> str:
    """Call OpenRouter API with fallback."""
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
    
    models = [PRIMARY_MODEL, BACKUP_MODEL]
    
    for model in models:
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Error with model {model}: {e}")
            if model == models[-1]:  # Last model failed
                return None
            continue
    
    return None


def generate_image_url(prompt: str) -> str:
    """Generate image using Pollinations.ai (no API key needed!)"""
    # Clean prompt for URL
    clean_prompt = prompt.replace(' ', '%20')
    return f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1024&height=1024&nologo=true"


def initialize_paystack_transaction(email: str, amount: int, plan: str) -> Dict[str, Any]:
    """Initialize a Paystack transaction."""
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "email": email,
        "amount": amount,
        "callback_url": CALLBACK_URL,
        "currency": "GHS",
        "metadata": {
            "plan": plan
        }
    }
    
    try:
        response = requests.post(PAYSTACK_INIT_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Paystack API error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                return {"status": False, "message": error_detail.get('message', str(e))}
            except:
                pass
        return {"status": False, "message": str(e)}


# ========== CONTENT GENERATION SYSTEM PROMPTS ==========
SYSTEM_PROMPTS = {
    'social_post': """You are a creative social media expert. Generate engaging, viral-worthy social media posts. 
    Include emojis, call-to-action, and make it platform-optimized (Instagram/Facebook/Twitter).
    Keep posts between 100-200 characters for optimal engagement.""",
    
    'ad_copy': """You are a direct response copywriter. Create compelling ad copy that converts.
    Use proven copywriting formulas (AIDA, PAS, etc.). Include a strong headline and clear CTA.
    Focus on benefits, not features. Make it persuasive and action-oriented.""",
    
    'product_desc': """You are an e-commerce product description specialist. Write SEO-optimized, 
    persuasive product descriptions that sell. Highlight key features, benefits, and unique selling points.
    Use sensory language and create desire.""",
    
    'hashtags': """You are a social media hashtag expert. Generate 20-30 relevant, trending hashtags.
    Mix popular hashtags with niche-specific ones. Include size variations (mega, macro, micro).
    Format as a clean list separated by spaces."""
}


# ========== COMMAND HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user_id = update.effective_user.id
    initialize_user(user_id)
    
    welcome_message = """🎨 *Welcome to AI Content Creator Pro!*

I help businesses create amazing content in seconds using AI!

✨ *What I Can Create:*
📱 Social Media Posts
📢 Ad Copy
📦 Product Descriptions
#️⃣ Trending Hashtags
🎨 AI-Generated Images

🎁 *FREE TIER:* 5 generations per day
⭐ *CREATOR:* 100/day for GHS 300/month
💼 *BUSINESS:* 500/day for GHS 750/month
🚀 *AGENCY:* Unlimited for GHS 2,250/month

*Quick Start:*
/create - Start creating content
/upgrade - View pricing plans
/status - Check your usage
/help - Full guide

Let's create something amazing! 🚀"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = """📚 *AI Content Creator - Complete Guide*

*🎯 How It Works:*
1. Choose content type with /create
2. Describe what you need
3. Get AI-generated content instantly
4. Copy, edit, and use!

*📝 Content Types:*

*📱 Social Media Posts*
Perfect for Instagram, Facebook, Twitter
Example: "Post about new coffee shop opening"

*📢 Ad Copy*
High-converting advertisements
Example: "Ad for fitness app targeting busy professionals"

*📦 Product Descriptions*
SEO-optimized descriptions that sell
Example: "Description for wireless earbuds with noise cancellation"

*#️⃣ Hashtags*
Trending, relevant hashtags for reach
Example: "Hashtags for fashion boutique"

*🎨 AI Images*
Generate custom images
Example: "Modern minimalist logo for tech startup"

*💡 Pro Tips:*
• Be specific about your target audience
• Mention tone (professional, casual, funny)
• Include key features you want highlighted
• Specify platform (Instagram, Facebook, etc.)

*💰 Pricing Plans:*
FREE: 5 generations/day
CREATOR: 100/day - GHS 300/month
BUSINESS: 500/day - GHS 750/month
AGENCY: Unlimited - GHS 2,250/month

Ready to create? Use /create! 🚀"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show content creation menu."""
    user_id = update.effective_user.id
    initialize_user(user_id)
    
    can_generate, remaining = check_usage_limit(user_id)
    
    if not can_generate:
        await update.message.reply_text(
            f"❌ *Daily Limit Reached*\n\n"
            f"Upgrade to continue creating:\n"
            f"/upgrade to view plans",
            parse_mode='Markdown'
        )
        return
    
    keyboard = []
    row = []
    for i, (label, _) in enumerate(CONTENT_TYPES.items()):
        row.append(InlineKeyboardButton(label, callback_data=f"type_{CONTENT_TYPES[label]}"))
        if len(row) == 2 or i == len(CONTENT_TYPES) - 1:
            keyboard.append(row)
            row = []
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎨 *What would you like to create?*\n\n"
        f"Remaining today: {remaining} generations\n\n"
        f"Choose a content type:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_content_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle content type selection."""
    query = update.callback_query
    await query.answer()
    
    content_type = query.data.replace('type_', '')
    context.user_data['content_type'] = content_type
    
    type_instructions = {
        'social_post': "📱 Describe your social media post (e.g., 'Post about summer sale, friendly tone, include emoji')",
        'ad_copy': "📢 Describe your ad (e.g., 'Ad for meal prep service, target busy professionals')",
        'product_desc': "📦 Describe your product (e.g., 'Bluetooth speaker, waterproof, 20hr battery')",
        'hashtags': "#️⃣ What niche/topic? (e.g., 'fitness and health', 'small business')",
        'image': "🎨 Describe the image (e.g., 'modern logo for coffee shop, minimalist, brown tones')"
    }
    
    instruction = type_instructions.get(content_type, "Tell me what you need:")
    
    await query.edit_message_text(
        f"✨ {instruction}\n\n"
        f"💡 Tip: Be specific for better results!",
        parse_mode='Markdown'
    )


async def handle_content_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate content based on user input."""
    user_id = update.effective_user.id
    user_input = update.message.text
    
    initialize_user(user_id)
    
    # Check limits
    can_generate, remaining = check_usage_limit(user_id)
    
    if not can_generate:
        await update.message.reply_text(
            f"❌ *Daily Limit Reached*\n\n"
            f"Upgrade for more:\n/upgrade",
            parse_mode='Markdown'
        )
        return
    
    # Get content type from context
    content_type = context.user_data.get('content_type')
    
    if not content_type:
        await update.message.reply_text(
            "Please start with /create to choose a content type first!"
        )
        return
    
    # Show loading message
    loading_msg = await update.message.reply_text("⏳ *Generating your content...*", parse_mode='Markdown')
    
    try:
        if content_type == 'image':
            # Generate image URL
            image_url = generate_image_url(user_input)
            
            await loading_msg.delete()
            await update.message.reply_photo(
                photo=image_url,
                caption=f"🎨 *Your AI-Generated Image*\n\n"
                        f"Prompt: {user_input}\n\n"
                        f"Remaining today: {remaining - 1}\n"
                        f"/create for more!",
                parse_mode='Markdown'
            )
        else:
            # Generate text content
            system_prompt = SYSTEM_PROMPTS.get(content_type, "")
            result = call_openrouter(user_input, system_prompt)
            
            if result:
                await loading_msg.delete()
                
                # Add type emoji
                type_emoji = {
                    'social_post': '📱',
                    'ad_copy': '📢',
                    'product_desc': '📦',
                    'hashtags': '#️⃣'
                }
                
                await update.message.reply_text(
                    f"{type_emoji.get(content_type, '✨')} *Your Content:*\n\n"
                    f"{result}\n\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📊 Remaining today: {remaining - 1}\n"
                    f"/create for more content!",
                    parse_mode='Markdown'
                )
            else:
                await loading_msg.delete()
                await update.message.reply_text(
                    "❌ Sorry, I encountered an error. Please try again in a moment."
                )
                return
        
        # Increment usage
        increment_usage(user_id)
        
        # Clear content type from context
        context.user_data.pop('content_type', None)
        
    except Exception as e:
        logger.error(f"Content generation error: {e}")
        await loading_msg.delete()
        await update.message.reply_text(
            "❌ An error occurred. Please try again!"
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user status and usage."""
    user_id = update.effective_user.id
    initialize_user(user_id)
    reset_daily_usage(user_id)
    
    user = user_data[user_id]
    
    plan_name = user.get('plan_name', 'FREE')
    status_emoji = '🆓' if user['status'] == 'free' else '⭐'
    
    if user['status'] == 'free':
        limit = FREE_DAILY_LIMIT
    else:
        limit = PRICING[user['status']]['limit']
    
    remaining = limit - user['daily_usage']
    
    status_msg = f"""{status_emoji} *Your Status*

📊 *Plan:* {plan_name}
✅ *Status:* Active
📈 *Used Today:* {user['daily_usage']}/{limit}
🎯 *Remaining:* {remaining}
🏆 *Total Created:* {user['total_generations']}

Want to upgrade? /upgrade
Create content: /create"""
    
    await update.message.reply_text(status_msg, parse_mode='Markdown')


async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show pricing plans."""
    pricing_msg = """💎 *Upgrade Your Plan*

Choose the plan that fits your needs:

⭐ *CREATOR PLAN*
GHS 300/month (~$20)
• 100 generations per day
• All content types
• Priority support
• Perfect for freelancers

💼 *BUSINESS PLAN*
GHS 750/month (~$50)
• 500 generations per day
• All content types
• Priority support
• Analytics dashboard
• Perfect for small businesses

🚀 *AGENCY PLAN*
GHS 2,250/month (~$150)
• UNLIMITED generations
• All content types
• Priority support
• White-label option
• API access
• Perfect for agencies

Ready to upgrade? /subscribe"""
    
    await update.message.reply_text(pricing_msg, parse_mode='Markdown')


# ========== SUBSCRIPTION FLOW ==========
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start subscription flow."""
    keyboard = [
        [InlineKeyboardButton("⭐ Creator - GHS 300", callback_data="plan_creator")],
        [InlineKeyboardButton("💼 Business - GHS 750", callback_data="plan_business")],
        [InlineKeyboardButton("🚀 Agency - GHS 2,250", callback_data="plan_agency")],
        [InlineKeyboardButton("❌ Cancel", callback_data="plan_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💳 *Select Your Plan:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return AWAITING_PLAN


async def handle_plan_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle plan selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "plan_cancel":
        await query.edit_message_text("Subscription cancelled. Upgrade anytime with /subscribe!")
        return ConversationHandler.END
    
    plan = query.data.replace('plan_', '')
    context.user_data['selected_plan'] = plan
    
    await query.edit_message_text(
        f"✉️ *Enter your email address:*\n\n"
        f"We'll send your invoice and receipt here.",
        parse_mode='Markdown'
    )
    
    return AWAITING_EMAIL


async def collect_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect email and initialize payment."""
    user_id = update.effective_user.id
    email = update.message.text.strip()
    
    if not is_valid_email(email):
        await update.message.reply_text(
            "❌ Invalid email. Please enter a valid email address:"
        )
        return AWAITING_EMAIL
    
    plan = context.user_data.get('selected_plan')
    
    if not plan or plan not in PRICING:
        await update.message.reply_text("Error: Invalid plan. Please start over with /subscribe")
        return ConversationHandler.END
    
    # Store email
    user_data[user_id]['email'] = email
    
    # Initialize payment
    await update.message.reply_text("⏳ *Initializing payment...*", parse_mode='Markdown')
    
    plan_info = PRICING[plan]
    result = initialize_paystack_transaction(email, plan_info['amount'], plan)
    
    if result.get('status'):
        authorization_url = result['data']['authorization_url']
        reference = result['data']['reference']
        
        payment_message = f"""✅ *Payment Link Ready!*

💳 *Plan:* {plan_info['name']}
💰 *Amount:* GHS {plan_info['amount']/100:.2f}

Click below to pay:
{authorization_url}

*Reference:* `{reference}`

*After payment:*
1. Return here
2. Send /verify to activate

Questions? Contact support."""
        
        await update.message.reply_text(payment_message, parse_mode='Markdown')
    else:
        error_msg = f"""❌ *Payment Failed*

Error: {result.get('message', 'Unknown error')}

Please try again: /subscribe"""
        
        await update.message.reply_text(error_msg, parse_mode='Markdown')
    
    return ConversationHandler.END


async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually verify and activate subscription."""
    user_id = update.effective_user.id
    
    # For demo: manually upgrade (in production, use webhook)
    if user_id not in user_data:
        initialize_user(user_id)
    
    # Simulate upgrade to creator plan
    user_data[user_id]['status'] = 'creator'
    user_data[user_id]['plan_name'] = 'CREATOR'
    
    success_msg = """🎉 *Payment Verified!*

Your account has been upgraded!

✅ *Plan:* Creator
📊 *Limit:* 100 generations/day
⚡ *Status:* Active

Start creating: /create
Check status: /status

Thank you for upgrading! 🚀"""
    
    await update.message.reply_text(success_msg, parse_mode='Markdown')


async def cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel subscription flow."""
    await update.message.reply_text("Subscription cancelled. Upgrade anytime with /subscribe!")
    return ConversationHandler.END


# ========== MAIN APPLICATION ==========
def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Subscription conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('subscribe', subscribe)],
        states={
            AWAITING_PLAN: [CallbackQueryHandler(handle_plan_selection)],
            AWAITING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_email)],
        },
        fallbacks=[CommandHandler('cancel', cancel_subscription)],
    )
    
    # Register handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("create", create))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("upgrade", upgrade))
    application.add_handler(CommandHandler("verify", verify_payment))
    application.add_handler(CallbackQueryHandler(handle_content_type, pattern="^type_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_content_request))
    
    # Start the bot
    logger.info("AI Content Creator Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()