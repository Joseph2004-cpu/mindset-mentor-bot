import os
import logging
from datetime import datetime, timedelta, timezone
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
from telegram.error import TelegramError, BadRequest, NetworkError
import json
from typing import Optional, Dict, Any
import re

# Conversation states
PRE_PURCHASE_QUESTION, WAITING_FOR_PURCHASE, POST_PURCHASE_FEEDBACK, FOCUS_AREA, SYSTEM_BUILDING, CHECKIN_RESPONSE = range(6)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# SECURITY: Use environment variable for token (recommended for production)
# Fallback to hardcoded token for development/testing only
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8342995076:AAH9TosXOwx_1KF3Kb5TwrKEcVlWqUmPEBI')

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found!")

PAYSTACK_LINK = "https://paystack.com/buy/unleash-your-ultimate-mindset-the-5-step-blueprint-to-uwsyav"


class MindsetBot:
    def __init__(self):
        self.user_data_file = "user_data.json"
        self.jobs_data_file = "jobs_data.json"
        self.load_user_data()
        self.load_jobs_data()
        
        # Base questions (to be formatted dynamically)
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
    
    def load_user_data(self) -> None:
        """Load user data with error handling"""
        try:
            with open(self.user_data_file, 'r') as f:
                self.user_db = json.load(f)
            logger.info(f"Loaded {len(self.user_db)} user records")
        except FileNotFoundError:
            self.user_db = {}
            logger.info("No existing user data file, starting fresh")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing user data: {e}")
            # Backup corrupted file
            if os.path.exists(self.user_data_file):
                backup_name = f"{self.user_data_file}.backup.{int(datetime.now().timestamp())}"
                os.rename(self.user_data_file, backup_name)
                logger.warning(f"Corrupted file backed up to {backup_name}")
            self.user_db = {}
        except Exception as e:
            logger.error(f"Unexpected error loading user data: {e}")
            self.user_db = {}
    
    def load_jobs_data(self) -> None:
        """Load scheduled jobs data"""
        try:
            with open(self.jobs_data_file, 'r') as f:
                self.jobs_db = json.load(f)
            logger.info(f"Loaded {len(self.jobs_db)} scheduled jobs")
        except FileNotFoundError:
            self.jobs_db = {}
            logger.info("No existing jobs data file")
        except Exception as e:
            logger.error(f"Error loading jobs data: {e}")
            self.jobs_db = {}
    
    def save_user_data(self) -> bool:
        """Save user data with error handling"""
        try:
            # Write to temporary file first
            temp_file = f"{self.user_data_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.user_db, f, indent=2)
            
            # Replace original file
            os.replace(temp_file, self.user_data_file)
            return True
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
            return False
    
    def save_jobs_data(self) -> bool:
        """Save jobs data with error handling"""
        try:
            with open(self.jobs_data_file, 'w') as f:
                json.dump(self.jobs_db, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving jobs data: {e}")
            return False
    
    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Get user data safely"""
        return self.user_db.get(str(user_id), {})
    
    def update_user_data(self, user_id: int, data: Dict[str, Any]) -> bool:
        """Update user data with validation"""
        try:
            user_id_str = str(user_id)
            if user_id_str not in self.user_db:
                self.user_db[user_id_str] = {}
            self.user_db[user_id_str].update(data)
            return self.save_user_data()
        except Exception as e:
            logger.error(f"Error updating user data for {user_id}: {e}")
            return False
    
    def format_question(self, question_index: int, user_data: Dict[str, Any]) -> str:
        """Format questions with actual user responses"""
        question = self.mindset_questions[question_index]
        responses = user_data.get('responses', [])
        
        # Extract key terms from previous responses
        replacements = {
            'outcome': responses[0][:50] if len(responses) > 0 else 'your goal',
            'blocker': responses[1][:50] if len(responses) > 1 else 'the challenge',
            'inner_issue': responses[2][:50] if len(responses) > 2 else 'that',
            'difference': responses[5][:50] if len(responses) > 5 else 'what changed'
        }
        
        # Replace placeholders
        for key, value in replacements.items():
            question = question.replace(f'{{{key}}}', value)
        
        return question
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        # Limit length
        return text[:2000]
    
    async def safe_send_message(self, context, chat_id: int, text: str, **kwargs) -> bool:
        """Send message with error handling"""
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
            return True
        except BadRequest as e:
            logger.error(f"Bad request sending message to {chat_id}: {e}")
            return False
        except NetworkError as e:
            logger.error(f"Network error sending message to {chat_id}: {e}")
            return False
        except TelegramError as e:
            logger.error(f"Telegram error sending message to {chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message to {chat_id}: {e}")
            return False
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start command handler - works at any point in conversation"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "there"
            user_data = self.get_user_data(user_id)
            
            # Log user interaction
            logger.info(f"User {user_id} ({first_name}) used /start command")
            
            # Handle returning purchased users
            if user_data.get('purchased'):
                # Check if they completed the PDF
                if user_data.get('pdf_completed'):
                    await update.message.reply_text(
                        f"Hey {first_name}! Welcome back! 🙌\n\n"
                        "Ready to keep building? What's on your mind?\n\n"
                        "Or use:\n"
                        "/checkin - Update me on your progress\n"
                        "/help - See all commands"
                    )
                    return CHECKIN_RESPONSE
                else:
                    # Purchased but haven't done /done yet
                    await update.message.reply_text(
                        f"Hey {first_name}! 👋\n\n"
                        "Have you finished reading the PDF?\n\n"
                        "• If yes → Type /done to build your system\n"
                        "• If not yet → Take your time, I'll be here!\n"
                        "• Need the link again? Check your email or let me know"
                    )
                    return ConversationHandler.END
            
            # Handle users in progress (not purchased)
            question_count = user_data.get('question_count', 0)
            
            if question_count > 0 and question_count < 10:
                # User was in the middle of questions
                keyboard = [
                    [InlineKeyboardButton("✅ Yes, let's continue", callback_data="continue_questions")],
                    [InlineKeyboardButton("🔄 Start fresh", callback_data="restart_fresh")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"Hey {first_name}! 👋\n\n"
                    f"I see you were in the middle of our conversation (question {question_count}/10).\n\n"
                    "Want to pick up where we left off, or start fresh?",
                    reply_markup=reply_markup
                )
                return WAITING_FOR_PURCHASE
            
            elif question_count >= 10:
                # User completed questions but didn't purchase
                await update.message.reply_text(
                    f"Welcome back, {first_name}! 👋\n\n"
                    "You completed the questions. Ready to take the next step?"
                )
                return await self.show_sales_pitch(update, context)
            
            # Brand new user
            await update.message.reply_text(
                f"Hey {first_name}! 👋\n\n"
                "I'm glad you're here. I want to ask you something real:\n\n"
                "**What's the one thing about yourself right now that you want to change?**"
            )
            
            self.update_user_data(user_id, {
                'first_name': first_name,
                'username': update.effective_user.username,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'question_count': 0,
                'responses': [],
                'last_interaction': datetime.now(timezone.utc).isoformat()
            })
            
            return PRE_PURCHASE_QUESTION
        
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text(
                "Oops! Something went wrong. Please try /start again."
            )
            return ConversationHandler.END
    
    async def pre_purchase_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle pre-purchase questions"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "there"
            user_response = self.sanitize_input(update.message.text)
            
            if not user_response:
                await update.message.reply_text("I didn't catch that. Can you share more?")
                return PRE_PURCHASE_QUESTION
            
            user_data = self.get_user_data(user_id)
            question_count = user_data.get('question_count', 0)
            responses = user_data.get('responses', [])
            
            responses.append(user_response)
            question_count += 1
            
            self.update_user_data(user_id, {
                'question_count': question_count,
                'responses': responses,
                'last_interaction': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"User {user_id} answered question {question_count}")
            
            # Continue with questions
            if question_count < 10:
                next_question = self.format_question(question_count, user_data)
                await update.message.reply_text(next_question)
                return PRE_PURCHASE_QUESTION
            else:
                # Show sales pitch
                return await self.show_sales_pitch(update, context)
        
        except Exception as e:
            logger.error(f"Error in pre_purchase_question: {e}")
            await update.message.reply_text(
                "Sorry, something went wrong. Let's continue—tell me more."
            )
            return PRE_PURCHASE_QUESTION
    
    async def show_sales_pitch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show sales pitch with purchase options"""
        try:
            first_name = update.effective_user.first_name or "there"
            
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
                [InlineKeyboardButton("I have a question", callback_data="ask_question")],
                [InlineKeyboardButton("Let me think about it", callback_data="think_about_it")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(sales_pitch, reply_markup=reply_markup)
            else:
                await update.message.reply_text(sales_pitch, reply_markup=reply_markup)
            
            return WAITING_FOR_PURCHASE
        
        except Exception as e:
            logger.error(f"Error showing sales pitch: {e}")
            return WAITING_FOR_PURCHASE
    
    async def waiting_for_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle purchase flow callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            first_name = query.from_user.first_name or "there"
            
            # Handle continue/restart from /start command
            if query.data == "continue_questions":
                user_data = self.get_user_data(user_id)
                question_count = user_data.get('question_count', 0)
                
                if question_count < 10:
                    next_question = self.format_question(question_count, user_data)
                    await query.edit_message_text(
                        f"Great! Let's continue where we left off.\n\n{next_question}"
                    )
                    return PRE_PURCHASE_QUESTION
                else:
                    return await self.show_sales_pitch(update, context)
            
            elif query.data == "restart_fresh":
                # Reset question count
                self.update_user_data(user_id, {
                    'question_count': 0,
                    'responses': [],
                    'restarted_at': datetime.now(timezone.utc).isoformat()
                })
                
                await query.edit_message_text(
                    f"No problem, {first_name}! Starting fresh. 🔄\n\n"
                    "**What's the one thing about yourself right now that you want to change?**"
                )
                return PRE_PURCHASE_QUESTION
            
            # Original purchase flow handlers
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
                
                self.update_user_data(user_id, {
                    'payment_link_sent': datetime.now(timezone.utc).isoformat()
                })
                
                return WAITING_FOR_PURCHASE
            
            elif query.data == "ask_question":
                await query.edit_message_text(
                    "What's your question? I'll answer honestly, then you can decide.\n\n"
                    "Reply with your question, and I'll get back to the purchase options after."
                )
                # Store that user is asking a question
                self.update_user_data(user_id, {'asking_question': True})
                return WAITING_FOR_PURCHASE
            
            elif query.data == "think_about_it":
                await query.edit_message_text(
                    f"No rush, {first_name}. Take your time.\n\n"
                    "Type /start whenever you're ready to continue.\n\n"
                    "**Real talk:** If nothing changes, where are you in 6 months?"
                )
                
                self.update_user_data(user_id, {
                    'deferred_purchase': datetime.now(timezone.utc).isoformat()
                })
                
                return ConversationHandler.END
            
            elif query.data == "confirm_payment":
                self.update_user_data(user_id, {
                    'purchased': True,
                    'purchase_date': datetime.now(timezone.utc).isoformat()
                })
                
                logger.info(f"User {user_id} confirmed purchase")
                
                await query.edit_message_text(
                    f"🎉 You're in, {first_name}!\n\n"
                    "Check your email for the PDF. Read it whenever you're ready—no rush.\n\n"
                    "When you're done, use the link at the end of the PDF (or type /done).\n\n"
                    "That's when we build YOUR system. 💪"
                )
                return ConversationHandler.END
            
            elif query.data == "back_to_purchase":
                # Return to sales pitch from question
                return await self.show_sales_pitch(update, context)
            
            return WAITING_FOR_PURCHASE
        
        except Exception as e:
            logger.error(f"Error in waiting_for_purchase: {e}")
            return WAITING_FOR_PURCHASE
    
    async def handle_question_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle user's question during purchase flow"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "there"
            question = self.sanitize_input(update.message.text)
            
            # Log the question
            user_data = self.get_user_data(user_id)
            questions = user_data.get('pre_purchase_questions', [])
            questions.append({
                'question': question,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            self.update_user_data(user_id, {
                'pre_purchase_questions': questions,
                'asking_question': False
            })
            
            # Generic helpful response
            await update.message.reply_text(
                f"Great question, {first_name}.\n\n"
                "The framework works because it's not theory—it's a step-by-step system "
                "built on what actually changes behavior: clarity, belief, experimentation, "
                "design, and momentum.\n\n"
                "Plus, you get me checking in every 3 days to keep you accountable.\n\n"
                "Most programs give you info and leave you alone. This builds YOUR system with you."
            )
            
            # Return to purchase options
            keyboard = [
                [InlineKeyboardButton("🔥 I'm ready now", callback_data="show_payment")],
                [InlineKeyboardButton("Another question", callback_data="ask_question")],
                [InlineKeyboardButton("Let me think", callback_data="think_about_it")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("What do you think?", reply_markup=reply_markup)
            
            return WAITING_FOR_PURCHASE
        
        except Exception as e:
            logger.error(f"Error handling question response: {e}")
            return WAITING_FOR_PURCHASE
    
    async def done_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /done command after PDF reading"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "there"
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
            
            self.update_user_data(user_id, {
                'pdf_completed': datetime.now(timezone.utc).isoformat()
            })
            
            return POST_PURCHASE_FEEDBACK
        
        except Exception as e:
            logger.error(f"Error in done_command: {e}")
            await update.message.reply_text("Let's try that again. What part of the PDF resonated most?")
            return POST_PURCHASE_FEEDBACK
    
    async def post_purchase_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle post-purchase feedback"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "there"
            user_response = self.sanitize_input(update.message.text)
            
            if not user_response:
                await update.message.reply_text("Take your time. What part really hit home?")
                return POST_PURCHASE_FEEDBACK
            
            self.update_user_data(user_id, {
                'pdf_feedback': user_response,
                'feedback_timestamp': datetime.now(timezone.utc).isoformat()
            })
            
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
                "Type the letter (A, B, C, D, or E) or the full word (like 'belief')."
            )
            
            await update.message.reply_text(reply)
            return FOCUS_AREA
        
        except Exception as e:
            logger.error(f"Error in post_purchase_feedback: {e}")
            return POST_PURCHASE_FEEDBACK
    
    async def focus_area(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle focus area selection"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "there"
            choice = self.sanitize_input(update.message.text).upper().strip()
            
            # Map full words to letters
            word_mapping = {
                'CLARITY': 'A',
                'BELIEF': 'B',
                'FAILURE': 'C',
                'FAIL': 'C',
                'SYSTEMS': 'D',
                'SYSTEM': 'D',
                'MOMENTUM': 'E'
            }
            
            # Check if user typed full word
            for word, letter in word_mapping.items():
                if word in choice:
                    choice = letter
                    break
            
            # Extract just the letter if user typed "A)" or similar
            if len(choice) > 1:
                choice = choice[0]
            
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
                self.update_user_data(user_id, {
                    'focus_area': choice,
                    'focus_area_timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                logger.info(f"User {user_id} selected focus area: {choice}")
                
                await update.message.reply_text(exercises[choice])
                return SYSTEM_BUILDING
            else:
                reply = (
                    "I didn't catch that. Just reply with the letter or word:\n\n"
                    "**A** or 'Clarity'\n"
                    "**B** or 'Belief'\n"
                    "**C** or 'Failure'\n"
                    "**D** or 'Systems'\n"
                    "**E** or 'Momentum'"
                )
                await update.message.reply_text(reply)
                return FOCUS_AREA
        
        except Exception as e:
            logger.error(f"Error in focus_area: {e}")
            return FOCUS_AREA
    
    async def system_building(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle system building exercise response"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "there"
            user_input = self.sanitize_input(update.message.text)
            
            if not user_input:
                await update.message.reply_text("Take your time. What's your answer?")
                return SYSTEM_BUILDING
            
            self.update_user_data(user_id, {
                'exercise_response': user_input,
                'last_interaction': datetime.now(timezone.utc).isoformat(),
                'exercise_completed': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"User {user_id} completed exercise")
            
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
            
            # Schedule check-in with error handling
            try:
                job_queue = context.application.job_queue
                chat_id = update.effective_chat.id
                
                # Remove existing jobs for this user
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
                
                # Persist job data
                self.jobs_db[str(user_id)] = {
                    'chat_id': chat_id,
                    'next_checkin': (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
                    'check_in_count': 0
                }
                self.save_jobs_data()
                
                logger.info(f"Scheduled check-in for user {user_id}")
            
            except Exception as e:
                logger.error(f"Error scheduling check-in for user {user_id}: {e}")
            
            return ConversationHandler.END
        
        except Exception as e:
            logger.error(f"Error in system_building: {e}")
            return SYSTEM_BUILDING
    
    async def send_checkin(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send scheduled check-in message"""
        try:
            job_data = context.job.data
            user_id = job_data['user_id']
            chat_id = job_data['chat_id']
            
            user_data = self.get_user_data(user_id)
            first_name = user_data.get('first_name', 'there')
            check_in_count = user_data.get('check_in_count', 0)
            
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
            
            # Select message based on check-in count
            message = messages[min(check_in_count, len(messages) - 1)]
            
            # Send message
            success = await self.safe_send_message(context, chat_id, message)
            
            if success:
                # Update user data
                self.update_user_data(user_id, {
                    'check_in_count': check_in_count + 1,
                    'last_checkin': datetime.now(timezone.utc).isoformat()
                })
                
                # Schedule next check-in
                context.application.job_queue.run_once(
                    self.send_checkin,
                    when=timedelta(days=3),
                    data=job_data,
                    name=f"checkin_{user_id}"
                )
                
                # Update jobs database
                if str(user_id) in self.jobs_db:
                    self.jobs_db[str(user_id)]['next_checkin'] = (
                        datetime.now(timezone.utc) + timedelta(days=3)
                    ).isoformat()
                    self.jobs_db[str(user_id)]['check_in_count'] = check_in_count + 1
                    self.save_jobs_data()
                
                logger.info(f"Check-in sent to user {user_id}, count: {check_in_count + 1}")
            else:
                logger.warning(f"Failed to send check-in to user {user_id}")
        
        except Exception as e:
            logger.error(f"Error in send_checkin: {e}")
    
    async def checkin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle manual check-in command"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "there"
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
            
            self.update_user_data(user_id, {
                'last_manual_checkin': datetime.now(timezone.utc).isoformat()
            })
            
            return CHECKIN_RESPONSE
        
        except Exception as e:
            logger.error(f"Error in checkin_command: {e}")
            return ConversationHandler.END
    
    async def checkin_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle check-in response"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "there"
            user_message = self.sanitize_input(update.message.text).lower()
            
            if not user_message:
                await update.message.reply_text("I'm listening. What's going on?")
                return CHECKIN_RESPONSE
            
            # Sentiment analysis based on keywords
            positive_words = ['great', 'good', 'working', 'progress', 'better', 'awesome', 'amazing', 'excellent', 'succeeding']
            struggle_words = ['stuck', 'struggling', 'hard', 'difficult', 'failing', 'blocked', 'frustrated', 'confused']
            quit_words = ['quit', 'give up', 'stop', 'done', 'tired', 'can\'t', 'impossible']
            
            if any(word in user_message for word in positive_words):
                reply = (
                    f"YES, {first_name}! 🔥\n\n"
                    "Keep riding that momentum.\n\n"
                    "**Next level:** What would make this even better? Don't settle—keep pushing."
                )
            elif any(word in user_message for word in quit_words):
                reply = (
                    f"Hold up, {first_name}.\n\n"
                    "What would you tell someone you love if they were here right now?\n\n"
                    "I bet: 'Keep going. One more shot.'\n\n"
                    "So: Give me one more experiment. One more MVE.\n\n"
                    "Most people quit right before breakthrough. You're not most people.\n\n"
                    "You in?"
                )
            elif any(word in user_message for word in struggle_words):
                reply = (
                    f"Thanks for being real, {first_name}.\n\n"
                    "Struggle = you're pushing boundaries. That's good.\n\n"
                    "Let's troubleshoot:\n"
                    "• Goal too big? Break it smaller (MVE style)\n"
                    "• Missing system? Add an If-Then\n"
                    "• Doubt creeping in? Evidence Inventory again\n\n"
                    "Which resonates? Let's fix it."
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
            
            self.update_user_data(user_id, {
                'last_interaction': datetime.now(timezone.utc).isoformat(),
                'checkin_responses': user_data.get('checkin_responses', []) + [{
                    'message': user_message[:500],
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }]
            })
            
            logger.info(f"User {user_id} checked in")
            
            return ConversationHandler.END
        
        except Exception as e:
            logger.error(f"Error in checkin_response: {e}")
            return ConversationHandler.END
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle help command"""
        try:
            help_text = (
                "**Commands:**\n\n"
                "/start - Begin or continue\n"
                "/done - Finished reading PDF\n"
                "/checkin - Check in anytime\n"
                "/help - This menu\n"
                "/cancel - End current conversation\n\n"
                "Or just message me. I'm here. 💪"
            )
            await update.message.reply_text(help_text)
            return ConversationHandler.END
        
        except Exception as e:
            logger.error(f"Error in help_command: {e}")
            return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle cancel command"""
        try:
            first_name = update.effective_user.first_name or "there"
            await update.message.reply_text(
                f"No worries, {first_name}!\n\n"
                "When you're ready, type /start.\n\n"
                "Best time to start was yesterday. Second best is now. 💪"
            )
            return ConversationHandler.END
        
        except Exception as e:
            logger.error(f"Error in cancel: {e}")
            return ConversationHandler.END
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
        
        try:
            if isinstance(update, Update) and update.effective_message:
                await update.effective_message.reply_text(
                    "Oops! Something went wrong. Let's try again.\n\n"
                    "Type /start to continue."
                )
        except Exception as e:
            logger.error(f"Error in error_handler: {e}")


def main():
    """Main function to run the bot"""
    try:
        # Build application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        bot = MindsetBot()
        
        # Conversation handler with proper state management
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', bot.start),
            ],
            states={
                PRE_PURCHASE_QUESTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, bot.pre_purchase_question),
                    CommandHandler('start', bot.start)  # Allow restart at any time
                ],
                WAITING_FOR_PURCHASE: [
                    CallbackQueryHandler(bot.waiting_for_purchase),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_question_response),
                    CommandHandler('start', bot.start)  # Allow restart at any time
                ],
                POST_PURCHASE_FEEDBACK: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, bot.post_purchase_feedback),
                    CommandHandler('start', bot.start)  # Allow restart at any time
                ],
                FOCUS_AREA: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, bot.focus_area),
                    CommandHandler('start', bot.start)  # Allow restart at any time
                ],
                SYSTEM_BUILDING: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, bot.system_building),
                    CommandHandler('start', bot.start)  # Allow restart at any time
                ],
                CHECKIN_RESPONSE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, bot.checkin_response),
                    CommandHandler('start', bot.start)  # Allow restart at any time
                ],
            },
            fallbacks=[
                CommandHandler('start', bot.start),  # Critical: Allow restart from anywhere
                CommandHandler('cancel', bot.cancel),
                CommandHandler('checkin', bot.checkin_command),
                CommandHandler('done', bot.done_command),
                CommandHandler('help', bot.help_command),
            ],
            allow_reentry=True,
            name="mindset_conversation",
            persistent=False
        )
        
        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler('help', bot.help_command))
        
        # Global /start handler as backup (processes before conversation handler)
        # This ensures /start ALWAYS works, even if conversation handler has issues
        global_start_handler = CommandHandler('start', bot.start)
        application.add_handler(global_start_handler, group=0)
        
        # Add error handler
        application.add_error_handler(bot.error_handler)
        
        # Restore scheduled jobs on startup
        logger.info("Restoring scheduled jobs...")
        for user_id_str, job_data in bot.jobs_db.items():
            try:
                next_checkin = datetime.fromisoformat(job_data['next_checkin'])
                now = datetime.now(timezone.utc)
                
                if next_checkin > now:
                    # Schedule future check-in
                    time_until = next_checkin - now
                    application.job_queue.run_once(
                        bot.send_checkin,
                        when=time_until,
                        data={'user_id': int(user_id_str), 'chat_id': job_data['chat_id']},
                        name=f"checkin_{user_id_str}"
                    )
                    logger.info(f"Restored check-in for user {user_id_str}")
                else:
                    # Past due - schedule for 1 hour from now
                    application.job_queue.run_once(
                        bot.send_checkin,
                        when=timedelta(hours=1),
                        data={'user_id': int(user_id_str), 'chat_id': job_data['chat_id']},
                        name=f"checkin_{user_id_str}"
                    )
                    logger.info(f"Rescheduled overdue check-in for user {user_id_str}")
            except Exception as e:
                logger.error(f"Error restoring job for user {user_id_str}: {e}")
        
        # Start bot
        logger.info("🚀 Mindset Bot Starting...")
        logger.info(f"✅ Loaded {len(bot.user_db)} users")
        logger.info(f"✅ Restored {len(bot.jobs_db)} scheduled jobs")
        logger.info("✅ All systems operational")
        
        print("\n" + "="*50)
        print("🚀 MINDSET BOT RUNNING")
        print("="*50)
        print(f"✅ Users in database: {len(bot.user_db)}")
        print(f"✅ Scheduled jobs: {len(bot.jobs_db)}")
        print("✅ Error handling: Active")
        print("✅ Job persistence: Active")
        print("✅ Ready for interactions")
        print("="*50 + "\n")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print("\n❌ ERROR: Please set TELEGRAM_BOT_TOKEN environment variable")
        print("Example: export TELEGRAM_BOT_TOKEN='your-token-here'")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ FATAL ERROR: {e}")


if __name__ == '__main__':
    main()