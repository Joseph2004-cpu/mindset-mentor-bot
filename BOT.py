import os
import json
import logging
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ====== Logging ======
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== Bot States ======
(
    MSG_1, MSG_2, MSG_3, MSG_4, MSG_5, MSG_6, MSG_7, MSG_8,
    PRODUCT_INTRO, POST_PURCHASE_START, FIRST_INSIGHT,
    FOCUS_AREA, SYSTEM_BUILDING, CHECKIN_RESPONSE
) = range(14)

PAYSTACK_LINK = "https://paystack.com/buy/unleash-your-ultimate-mindset-the-5-step-blueprint-to-uwsyav"


# ============================================================
#                   BOT BLUEPRINT (COMPRESSED)
# ============================================================

class MindsetBot:
    def __init__(self):
        self.db_file = "user_data.json"
        self.user_db = self.load()

    # ========== STORAGE ==========
    def load(self):
        try:
            with open(self.db_file, "r") as f:
                return json.load(f)
        except:
            return {}

    def save(self):
        with open(self.db_file, "w") as f:
            json.dump(self.user_db, f, indent=2)

    def set(self, uid, data):
        uid = str(uid)
        if uid not in self.user_db:
            self.user_db[uid] = {}
        self.user_db[uid].update(data)
        self.save()

    def get(self, uid):
        return self.user_db.get(str(uid), {})

    # ============================================================
    #                      START MESSAGE (UPDATED)
    # ============================================================
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.set(user.id, {"first_name": user.first_name, "started": str(datetime.now())})

        # ----- YOUR REWRITTEN OPENING MESSAGE -----
        await update.message.reply_text(
            f"Hey {user.first_name}! 👋\n\n"
            "I'm really glad you're here. Can I ask you something honest?\n\n"
            "**What's the one thing you wish you could change about how you're showing up right now?**\n\n"
            "(No judgment—just curious what brought you here today.)"
        )

        return MSG_1

    # ============================================================
    #               PRE-SALE FLOW (COMPRESSED)
    # ============================================================

    async def msg_1(self, update, context):
        """Short dynamic emotional reflection"""
        text = update.message.text.lower()
        uid = update.effective_user.id
        self.set(uid, {"initial_concern": text})

        r = None
        if any(k in text for k in ["stuck","plateau","not moving"]):
            r = "That stuck feeling is rough. Do you feel unsure what to do next, or do you know what to do but can’t get yourself to do it?"
        elif any(k in text for k in ["motivat","discipline","lazy"]):
            r = "Motivation isn’t your real issue. What's one thing you ARE consistent with?"
        elif any(k in text for k in ["goal","achieve"]):
            r = "Love that. When you imagine achieving it, do you feel excited or pressured?"
        elif any(k in text for k in ["start","procrast"]):
            r = "When you *do* start, do you always finish, or does resistance show up everywhere?"
        elif any(k in text for k in ["fail","fear"]):
            r = "Fear means you care. What’s one thing you’d try if no one could judge you?"
        else:
            r = "Interesting. If the version of you who solved this was here, what would they say is different about their thinking?"

        await update.message.reply_text(r)
        return MSG_2

    async def msg_2(self, update, context):
        await update.message.reply_text(
            "Let me ask you this—when did you first start noticing this pattern? "
            "Is it recent, or have you felt this way for a long time?"
        )
        return MSG_3

    async def msg_3(self, update, context):
        await update.message.reply_text(
            "Okay. And when you're in that moment where you want to change but you don’t… "
            "what thoughts usually show up first?"
        )
        return MSG_4

    async def msg_4(self, update, context):
        await update.message.reply_text(
            "That makes sense.\n\nIf you could snap your fingers and instantly fix ONE part of this, "
            "which part would change first?"
        )
        return MSG_5

    async def msg_5(self, update, context):
        await update.message.reply_text(
            "Got you.\n\nCan I share something about people who feel the way you feel?"
        )
        return MSG_6

    async def msg_6(self, update, context):
        await update.message.reply_text(
            "Most people think their problem is motivation or discipline.\n\n"
            "But the real issue is **identity conflict** — you're trying to create results with a mindset "
            "that wasn’t built for the life you’re aiming for.\n\n"
            "Want me to show you?"
        )
        return MSG_7

    async def msg_7(self, update, context):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Yes, show me 👀", callback_data="show_intro")]
        ])
        await update.message.reply_text("Ready?", reply_markup=kb)
        return MSG_8

    async def msg_8_button(self, update, context):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "Alright — here’s the truth.\n\n"
            "There’s a 5-step internal blueprint that separates people who stay stuck "
            "from people who transform their identity permanently.\n\n"
            "Let me show you what it looks like."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Show me the blueprint", callback_data="show_product")]
        ])
        await query.message.reply_text("Ready?", reply_markup=kb)
        return PRODUCT_INTRO

    # ============================================================
    #                      PRODUCT INTRO
    # ============================================================

    async def product_intro(self, update, context):
        q = update.callback_query
        await q.answer()

        await q.edit_message_text(
            "**UNLEASH YOUR ULTIMATE MINDSET™**\n\n"
            "A 5-step psychological re-engineering system that helps you:\n"
            "• Build unshakeable identity\n"
            "• Remove old mental patterns\n"
            "• Build discipline without forcing it\n"
            "• Become the version of you who *automatically* wins\n\n"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Get the Blueprint", url=PAYSTACK_LINK)],
            [InlineKeyboardButton("I already paid", callback_data="paid")]
        ])
        await q.message.reply_text("Choose an option:", reply_markup=kb)
        return POST_PURCHASE_START

    # ============================================================
    #                  POST-PURCHASE EXPERIENCE
    # ============================================================

    async def paid(self, update, context):
        q = update.callback_query
        uid = update.effective_user.id
        self.set(uid, {"purchased": True})
        await q.answer()
        await q.edit_message_text(
            "Amazing. Let’s begin.\n\n"
            "First — what was your biggest aha moment from the blueprint?"
        )
        return FIRST_INSIGHT

    async def first_insight(self, update, context):
        await update.message.reply_text(
            "Great.\nWhat’s the #1 area of your life you want to transform first?"
        )
        return FOCUS_AREA

    async def focus_area(self, update, context):
        await update.message.reply_text(
            "Perfect.\nLet’s build your first identity system.\n\n"
            "Describe the future version of you who has already solved this."
        )
        return SYSTEM_BUILDING

    async def system_building(self, update, context):
        await update.message.reply_text(
            "Powerful.\n\nI’ll check in on you daily.\n"
            "What time do you want your mindset check-in?"
        )
        return CHECKIN_RESPONSE

    async def checkin_response(self, update, context):
        await update.message.reply_text(
            "Done! You’ll get your daily check-ins."
        )
        return ConversationHandler.END


# ============================================================
#                 BUILD APPLICATION (COMPRESSED)
# ============================================================

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    bot = MindsetBot()

    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", bot.start)],
        states={
            MSG_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.msg_1)],
            MSG_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.msg_2)],
            MSG_3: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.msg_3)],
            MSG_4: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.msg_4)],
            MSG_5: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.msg_5)],
            MSG_6: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.msg_6)],
            MSG_7: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.msg_7)],
            MSG_8: [CallbackQueryHandler(bot.msg_8_button, pattern="show_intro")],
            PRODUCT_INTRO: [CallbackQueryHandler(bot.product_intro, pattern="show_product")],
            POST_PURCHASE_START: [CallbackQueryHandler(bot.paid, pattern="paid")],
            FIRST_INSIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.first_insight)],
            FOCUS_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.focus_area)],
            SYSTEM_BUILDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.system_building)],
            CHECKIN_RESPONSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.checkin_response)],
        },
        fallbacks=[]
    )

    app.add_handler(conv)
    app.run_polling()


if __name__ == "__main__":
    main()
