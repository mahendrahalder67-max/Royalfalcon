import logging
import asyncio
import random
import string
import threading
import os
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ==================== FLASK APP FOR RENDER PORT BINDING ====================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Shien Code Selling Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ==================== CONFIGURATION ====================
BOT_TOKEN = '8628096729:AAF-fLYPVVisHgkWEc5K80Iq-KRNqMomM7Q'
ADMIN_USER_ID = 6877228718
USDT_RATE = 96  # <--- CHANGED FROM 94 TO 96
USDT_ADDRESS = "0x40929e138B0AB6b7AB8B7B232B482749918A0112"

# ==================== DYNAMIC PRICE ====================
current_price = 189  # Default price per code (Admin can change with /setprice)

# ==================== CONVERSATION STATES ====================
SUPPORT_STATE = 1

# ==================== DATA STORAGE ====================
pending_payments = {}
approved_orders = []
rejected_orders = []
user_coupon_selection = {}
all_users = set()
support_tickets = {}

# ==================== LOAD EXISTING USERS ====================
def load_existing_users():
    for order in approved_orders:
        all_users.add(order['user_id'])
    print(f"👥 Loaded {len(all_users)} existing users")

# ==================== AUTO PING ====================
async def auto_self_ping(app):
    ping_count = 0
    start_time = datetime.now()
    
    while True:
        try:
            await asyncio.sleep(1800)
            ping_count += 1
            current_time = datetime.now()
            uptime = current_time - start_time
            
            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            
            message = (
                f"🟢 *BOT STATUS UPDATE* 🟢\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🤖 *Bot:* Shien Code Selling Bot\n"
                f"📡 *Status:* ✅ Running Perfectly\n"
                f"🔄 *Ping #:* `{ping_count}`\n"
                f"⏰ *Time:* `{current_time.strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
                f"📊 *Uptime:* `{days}d {hours}h {minutes}m`\n"
                f"👥 *Total Users:* `{len(all_users)}`\n"
                f"💰 *Current Price:* ₹{current_price} per code\n"
                f"💱 *USDT Rate:* 1 USDT = ₹{USDT_RATE}\n\n"
                f"💪 *Bot is active and working!*"
            )
            
            await app.bot.send_message(ADMIN_USER_ID, message, parse_mode='Markdown')
            print(f"[{current_time}] ✅ Status ping #{ping_count} sent to admin")
            
        except Exception as e:
            print(f"❌ Auto-ping error: {e}")
            await asyncio.sleep(60)

# ==================== HELPER FUNCTIONS ====================
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🛒 Buy Now")],
        [KeyboardButton("📜 My History")],
        [KeyboardButton("🆘 Support")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def generate_coupon_code():
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=13))
    return f"SO9{random_part}"

def generate_multiple_codes(quantity):
    codes = []
    for i in range(quantity):
        code = generate_coupon_code()
        codes.append(code)
    return codes

def get_price(quantity=1):
    """Get price based on current_price variable"""
    total_inr = current_price * quantity
    return total_inr, round(total_inr / USDT_RATE, 2)

def get_coupon_details():
    return {
        "name": "🔥 Shien - ₹800 off on ₹1000+",
        "desc": "✅ Yeh coupon shien pe lagega - Works on all products in Shien!",
        "emoji": "👗",
        "price": current_price
    }

# ==================== SET PRICE (ADMIN ONLY) ====================
async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change coupon price per code (Admin only)"""
    global current_price
    
    user = update.effective_user
    
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ Unauthorized! Only admin can use this command.")
        return
    
    args = context.args
    
    if not args:
        await update.message.reply_text(
            f"❌ *Usage:* `/setprice <amount>`\n\n"
            f"Current price: ₹{current_price} per code\n"
            f"Example: `/setprice 150`",
            parse_mode='Markdown'
        )
        return
    
    try:
        new_price = int(args[0])
        
        if new_price <= 0:
            await update.message.reply_text("❌ Price must be a positive number!")
            return
        
        old_price = current_price
        current_price = new_price
        new_usdt = round(current_price / USDT_RATE, 2)
        
        await update.message.reply_text(
            f"✅ *Price Updated Successfully!* ✅\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Old Price: ₹{old_price} per code\n"
            f"💰 New Price: ₹{current_price} per code\n"
            f"🪙 USDT Price: ~{new_usdt} USDT (1 USDT = ₹{USDT_RATE})\n\n"
            f"✅ All future purchases will use the new price!",
            parse_mode='Markdown'
        )
        
        for order in approved_orders:
            all_users.add(order['user_id'])
        
        if all_users:
            broadcast_msg = (
                f"📢 *PRICE UPDATE* 📢\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🆕 *New Price: ₹{current_price}* per code\n"
                f"📉 Old Price: ₹{old_price}\n\n"
                f"🛍️ Shien - ₹800 off on ₹1000+\n"
                f"✅ Shien pe lagega!\n\n"
                f"Grab your codes now! 🔥"
            )
            
            sent = 0
            for uid in list(all_users)[:50]:
                try:
                    await context.bot.send_message(uid, broadcast_msg, parse_mode='Markdown')
                    sent += 1
                    await asyncio.sleep(0.1)
                except:
                    pass
            await update.message.reply_text(f"📢 Price update broadcast sent to {sent} users.")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid price! Please enter a valid number.")

# ==================== BROADCAST ====================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ Unauthorized! Only admin can use this command.")
        return
    
    message_text = " ".join(context.args)
    
    if not message_text:
        await update.message.reply_text(
            "❌ *Usage:* `/msgtosend Your message here`\n\n"
            "Example: `/msgtosend New offer available!`",
            parse_mode='Markdown'
        )
        return
    
    for order in approved_orders:
        all_users.add(order['user_id'])
    
    if not all_users:
        await update.message.reply_text("📭 No users found to broadcast.")
        return
    
    sent_count = 0
    failed_count = 0
    
    for user_id in all_users:
        try:
            await context.bot.send_message(user_id, message_text, parse_mode='Markdown')
            sent_count += 1
            await asyncio.sleep(0.2)
        except Exception as e:
            failed_count += 1
            print(f"Failed to send to {user_id}: {e}")
    
    await update.message.reply_text(
        f"✅ *Broadcast Complete!*\n\n"
        f"📤 Sent to: `{sent_count}` users\n"
        f"❌ Failed: `{failed_count}` users\n"
        f"👥 Total users: `{len(all_users)}`",
        parse_mode='Markdown'
    )

# ==================== TICKET REPLY ====================
async def ticket_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ Unauthorized! Only admin can use this command.")
        return
    
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text(
            "❌ *Usage:* `/ticket @username Your reply message here`\n\n"
            "Example: `/ticket @rajkumar Your issue has been resolved.`",
            parse_mode='Markdown'
        )
        return
    
    target_username = args[0].replace('@', '')
    reply_text = " ".join(args[1:])
    
    if not reply_text:
        await update.message.reply_text("❌ Please provide a message to send.")
        return
    
    target_user_id = None
    
    for uid in all_users:
        try:
            chat = await context.bot.get_chat(uid)
            if chat.username and chat.username.lower() == target_username.lower():
                target_user_id = uid
                break
        except:
            continue
    
    if not target_user_id:
        for payment in pending_payments.values():
            if payment.get('username', '').lower() == target_username.lower():
                target_user_id = payment['user_id']
                break
    
    if not target_user_id:
        await update.message.reply_text(f"❌ User @{target_username} not found.")
        return
    
    try:
        await context.bot.send_message(
            target_user_id,
            f"📩 *REPLY FROM SUPPORT* 📩\n━━━━━━━━━━━━━━━━━━━━\n\n{reply_text}\n\n"
            f"📌 *From:* Admin Support Team",
            parse_mode='Markdown'
        )
        await update.message.reply_text(f"✅ Reply sent to @{target_username}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send reply: {e}")

# ==================== START COMMAND ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    all_users.add(user.id)
    print(f"👤 New user: {user.first_name} (ID: {user.id}) - Total: {len(all_users)}")
    
    if user.id == ADMIN_USER_ID:
        await update.message.reply_text(
            f"👑 *Welcome Admin!* 👑\n\n"
            f"✅ Order notifications with Approve/Reject buttons.\n"
            f"🟢 Status update every 30 minutes.\n"
            f"📢 `/msgtosend Your message` - Broadcast\n"
            f"📩 `/ticket @username Your reply` - Reply to user\n"
            f"💰 `/setprice 150` - Change coupon price\n"
            f"👥 Total users: `{len(all_users)}`\n"
            f"💰 Current price: ₹{current_price} per code\n"
            f"💱 USDT Rate: 1 USDT = ₹{USDT_RATE}\n\n"
            f"🚀 *Bot is ready!*",
            parse_mode='Markdown'
        )
        return
    
    welcome_msg = (
        f"👑 *Welcome to Shien Code Selling Bot, {user.first_name}!* 👑\n\n"
        "✨ *Your one-stop destination for premium Shien coupon codes!* ✨\n\n"
        "💎 *Why Choose Us?*\n"
        "✅ Instant Delivery After Payment Verification\n"
        "✅ Secure Blockchain Payments (USDT BEP20)\n"
        "✅ 24/7 Customer Support\n\n"
        "🛍️ *Available Coupon:*\n"
        "• Shien - ₹800 off on ₹1000+ (✅ Shien pe lagega)\n\n"
        f"💰 *Price:* ₹{current_price} per code\n\n"
        f"💱 *Exchange Rate:* 1 USDT = ₹{USDT_RATE}\n\n"
        "👇 *Use the buttons below!*"
    )
    await update.message.reply_text(welcome_msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

# ==================== SUPPORT CONVERSATION ====================
async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *SUPPORT* 🆘\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Please describe your problem in detail.\n"
        "Our support team will assist you within 24 hours.\n\n"
        "📝 *Type your message below:*",
        parse_mode='Markdown'
    )
    return SUPPORT_STATE

async def support_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    problem_text = update.message.text
    
    support_tickets[user.id] = {
        'user_id': user.id,
        'username': user.username or str(user.id),
        'first_name': user.first_name,
        'last_name': user.last_name or '',
        'message': problem_text,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    await update.message.reply_text(
        "✅ *Support Request Received!* ✅\n\n"
        "We have forwarded your request to our support team.\n"
        "You will receive a reply within 24 hours.\n\n"
        "📌 *Ticket ID:* `#" + str(user.id)[:6] + "`\n\n"
        "Thank you for your patience! 🙏",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )
    
    admin_msg = (
        f"🆕 *NEW SUPPORT TICKET* 🆕\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *CUSTOMER DETAILS:*\n"
        f"├ 🏷️ Name: {user.first_name} {user.last_name or ''}\n"
        f"├ 🆔 Telegram ID: `{user.id}`\n"
        f"├ 📝 Username: @{user.username or 'N/A'}\n"
        f"└ 🔗 Profile: [Click Here](tg://user?id={user.id})\n\n"
        f"📝 *MESSAGE:*\n"
        f"{problem_text}\n\n"
        f"⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *To reply:* `/ticket @{user.username or str(user.id)} Your reply here`"
    )
    
    try:
        await context.bot.send_message(ADMIN_USER_ID, admin_msg, parse_mode='Markdown')
        print(f"📩 Support ticket from {user.first_name} sent to admin")
    except Exception as e:
        print(f"❌ Failed to send support ticket: {e}")
    
    return ConversationHandler.END

# ==================== MESSAGE HANDLERS ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🛒 Buy Now":
        await show_coupon(update)
    elif text == "📜 My History":
        await show_user_history(update)
    elif text == "🆘 Support":
        await support_start(update, context)
        return SUPPORT_STATE
    else:
        await update.message.reply_text("❓ Please use the buttons below:", reply_markup=get_main_keyboard(), parse_mode='Markdown')
    return ConversationHandler.END

# ==================== COUPON FUNCTIONS ====================
async def show_coupon(update: Update):
    details = get_coupon_details()
    
    text = (
        f"{details['emoji']} *{details['name']}*\n\n"
        f"📝 *Description:* {details['desc']}\n\n"
        f"💰 *Price:* ₹{details['price']} per code\n\n"
        f"👇 *Select Quantity (1-10):*"
    )
    
    quantity_buttons = []
    for i in range(1, 11):
        quantity_buttons.append(InlineKeyboardButton(f"{i}", callback_data=f'qty_{i}'))
    
    keyboard = []
    for i in range(0, len(quantity_buttons), 5):
        keyboard.append(quantity_buttons[i:i+5])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_user_history(update: Update):
    user_id = update.effective_user.id
    user_approved = [order for order in approved_orders if order['user_id'] == user_id]
    user_rejected = [order for order in rejected_orders if order['user_id'] == user_id]
    
    if not user_approved and not user_rejected:
        await update.message.reply_text(
            "📜 *Your Purchase History*\n\n"
            "📭 *No orders found*\n\n"
            "You haven't made any purchases yet.\n"
            "Click '🛒 Buy Now' to start shopping! 🛍️",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        return
    
    history_text = "📜 *YOUR PURCHASE HISTORY*\n━━━━━━━━━━━━━━━━━━\n\n"
    
    if user_approved:
        history_text += "✅ *Approved Orders:*\n"
        for order in user_approved[-5:]:
            history_text += (
                f"┌ 📅 {order['timestamp']}\n"
                f"├ 🏷️ {order['coupon_name']}\n"
                f"├ 🔢 Qty: {order['quantity']} code(s)\n"
                f"├ 💰 ₹{order['inr_amount']}\n"
                f"├ 🎫 Codes: \n"
            )
            for idx, code in enumerate(order['coupon_codes'], 1):
                history_text += f"│  {idx}. `{code}`\n"
            history_text += f"└ 📌 Status: ✅ Approved\n\n"
    
    if user_rejected:
        history_text += "❌ *Rejected Orders:*\n"
        for order in user_rejected[-3:]:
            history_text += (
                f"┌ 📅 {order['timestamp']}\n"
                f"├ 🏷️ {order['coupon_name']}\n"
                f"├ 🔢 Qty: {order['quantity']}\n"
                f"├ 💰 ₹{order['inr_amount']}\n"
                f"└ 📌 Status: ❌ Rejected\n\n"
            )
    
    await update.message.reply_text(history_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

# ==================== BUTTON CALLBACKS ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'back_to_main':
        await show_main_menu(query)
    elif data.startswith('qty_'):
        await handle_quantity_selection(query, context)
    elif data == 'paid':
        await confirm_payment(query, context)
    elif data == 'cancel_payment':
        await cancel_payment(query)
    elif data == 'copy_address':
        await query.answer(f"Address copied: {USDT_ADDRESS}", show_alert=True)
    elif data.startswith('approve_'):
        await handle_admin_approve(query, context)
    elif data.startswith('reject_'):
        await handle_admin_reject(query, context)

async def show_main_menu(query):
    await query.edit_message_text(
        "👑 *Shien Code Selling Bot - Main Menu*\n\n"
        "Use the buttons below to navigate:",
        parse_mode='Markdown'
    )
    await query.message.reply_text("👇 *Available Options:*", reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def handle_quantity_selection(query, context):
    quantity = int(query.data.split('_')[1])
    inr_total, usdt_total = get_price(quantity)
    context.user_data['pending_payment'] = {'quantity': quantity, 'inr': inr_total, 'usdt': usdt_total}
    await show_payment_screen(query, inr_total, usdt_total, quantity)

async def show_payment_screen(query, inr_total, usdt_total, quantity):
    details = get_coupon_details()
    
    text = (
        f"💳 *PAYMENT REQUIRED*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛍️ *Order Summary:*\n"
        f"├ {details['emoji']} {details['name']}\n"
        f"├ 🔢 Quantity: {quantity} code(s)\n"
        f"├ 💰 Price: ₹{details['price']} each\n"
        f"└ 💰 Total (INR): ₹{inr_total}\n\n"
        f"💎 *Payment Details:*\n"
        f"├ Currency: USDT (BEP20)\n"
        f"├ Amount: {usdt_total} USDT\n"
        f"├ Rate: 1 USDT = ₹{USDT_RATE}\n"
        f"└ Network: BEP20\n\n"
        f"📤 *Send Payment To:*\n"
        f"`{USDT_ADDRESS}`\n\n"
        f"⚠️ *Important:*\n"
        f"• Send EXACT {usdt_total} USDT\n"
        f"• Use BEP20 network only\n"
        f"• You will receive {quantity} coupon code(s)\n\n"
        f"✅ *After sending, click the button below*"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ I HAVE PAID", callback_data='paid'),
         InlineKeyboardButton("❌ CANCEL", callback_data='cancel_payment')],
        [InlineKeyboardButton("📋 Copy Address", callback_data='copy_address')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def confirm_payment(query, context):
    user = query.from_user
    payment_info = context.user_data.get('pending_payment')
    if not payment_info:
        await query.edit_message_text("❌ No pending payment found.", parse_mode='Markdown')
        return
    
    payment_id = random.randint(100000, 999999)
    details = get_coupon_details()
    
    pending_payments[payment_id] = {
        'payment_id': payment_id,
        'user_id': user.id,
        'username': user.username or str(user.id),
        'first_name': user.first_name,
        'last_name': user.last_name or '',
        'quantity': payment_info['quantity'],
        'inr_amount': payment_info['inr'],
        'usdt_amount': payment_info['usdt'],
        'coupon_name': details['name'],
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'status': 'pending'
    }
    
    admin_notification = (
        f"🆕 *🧾 NEW ORDER #{payment_id}* 🆕\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *👨‍💼 CUSTOMER DETAILS:*\n"
        f"├ 🏷️ Name: {user.first_name} {user.last_name or ''}\n"
        f"├ 🆔 Telegram ID: `{user.id}`\n"
        f"├ 📝 Username: @{user.username or 'N/A'}\n"
        f"└ 🔗 Profile: [Click Here](tg://user?id={user.id})\n\n"
        f"🛍️ *📦 ORDER DETAILS:*\n"
        f"├ 🏷️ Product: {details['name']}\n"
        f"├ 🔢 Quantity: {payment_info['quantity']} code(s)\n"
        f"├ 💰 INR Amount: ₹{payment_info['inr']}\n"
        f"└ 🪙 USDT Amount: {payment_info['usdt']} USDT\n\n"
        f"💰 *💳 PAYMENT INFO:*\n"
        f"├ 📤 USDT Address: `{USDT_ADDRESS[:20]}...`\n"
        f"├ 💱 Rate: 1 USDT = ₹{USDT_RATE}\n"
        f"├ 🌐 Network: BEP20\n"
        f"└ ⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ *📌 ACTION REQUIRED:*"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ APPROVE ORDER ✅", callback_data=f'approve_{payment_id}'),
         InlineKeyboardButton("❌ REJECT ORDER ❌", callback_data=f'reject_{payment_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(ADMIN_USER_ID, admin_notification, reply_markup=reply_markup, parse_mode='Markdown')
        print(f"✅ Order #{payment_id} notification sent to admin")
    except Exception as e:
        print(f"❌ Failed to send admin notification: {e}")
    
    await query.edit_message_text(
        "🔄 *✅ PAYMENT VERIFICATION INITIATED*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🧾 *Order ID:* `#{payment_id}`\n\n"
        "✅ Your payment is being verified on the blockchain.\n"
        "⏰ This may take 2-5 minutes.\n\n"
        f"📌 You will receive {payment_info['quantity']} coupon code(s) once approved by admin.\n\n"
        "🙏 Thank you for shopping with Shien Code Selling Bot! 👑",
        parse_mode='Markdown'
    )
    
    context.user_data.pop('pending_payment', None)

async def cancel_payment(query):
    await query.edit_message_text(
        "❌ *PAYMENT CANCELLED*\n\n"
        "Your transaction has been cancelled.\n"
        "You can start a new purchase anytime.\n\n"
        "Have a great day! 🌟",
        parse_mode='Markdown'
    )

# ==================== ADMIN ACTIONS ====================
async def handle_admin_approve(query, context):
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return
    
    payment_id = int(query.data.split('_')[1])
    payment = pending_payments.get(payment_id)
    if not payment:
        await query.edit_message_text("❌ Order not found or already processed.")
        return
    
    codes = generate_multiple_codes(payment['quantity'])
    codes_text = ""
    for idx, code in enumerate(codes, 1):
        codes_text += f"{idx}. `{code}`\n"
    
    try:
        await context.bot.send_message(
            payment['user_id'],
            f"✅ *✅ PAYMENT APPROVED!* ✅\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎉 *Congratulations {payment['first_name']}!*\n\n"
            f"🛍️ *Order Details:*\n"
            f"├ 🧾 Order ID: `#{payment_id}`\n"
            f"├ 🏷️ Product: {payment['coupon_name']}\n"
            f"├ 🔢 Quantity: {payment['quantity']} code(s)\n"
            f"└ 💰 Amount: ₹{payment['inr_amount']}\n\n"
            f"🎫 *Your Coupon Code(s):*\n"
            f"{codes_text}\n"
            f"📌 *How to Use:*\n"
            f"• Shien Coupon: ✅ Shien pe lagega - Works on all products\n\n"
            f"💫 *Valid for 30 days from today*\n\n"
            f"🙏 Thank you for choosing Shien Code Selling Bot! 👑",
            parse_mode='Markdown'
        )
        
        approved_orders.append({
            'user_id': payment['user_id'],
            'coupon_name': payment['coupon_name'],
            'quantity': payment['quantity'],
            'inr_amount': payment['inr_amount'],
            'coupon_codes': codes,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        all_users.add(payment['user_id'])
        
        admin_confirm_msg = (
            f"✅ *ORDER #{payment_id} APPROVED* ✅\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *👨‍💼 CUSTOMER DETAILS:*\n"
            f"├ 🏷️ Name: {payment['first_name']} {payment['last_name']}\n"
            f"├ 🆔 Telegram ID: `{payment['user_id']}`\n"
            f"├ 📝 Username: @{payment['username'] if payment['username'] != str(payment['user_id']) else 'N/A'}\n"
            f"└ 🔗 Profile: [Click Here](tg://user?id={payment['user_id']})\n\n"
            f"🛍️ *📦 ORDER DETAILS:*\n"
            f"├ 🏷️ Product: {payment['coupon_name']}\n"
            f"├ 🔢 Quantity: {payment['quantity']} code(s)\n"
            f"└ 💰 Amount: ₹{payment['inr_amount']}\n\n"
            f"🎫 *Codes Sent:*\n{codes_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Coupon codes delivered successfully to @{payment['username'] if payment['username'] != str(payment['user_id']) else 'N/A'}"
        )
        
        await query.edit_message_text(admin_confirm_msg, parse_mode='Markdown')
        pending_payments.pop(payment_id, None)
        print(f"✅ Order #{payment_id} approved - User: {payment['first_name']}")
        
    except Exception as e:
        print(f"Error: {e}")
        await query.edit_message_text(f"⚠️ Error sending coupon: {e}")

async def handle_admin_reject(query, context):
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return
    
    payment_id = int(query.data.split('_')[1])
    payment = pending_payments.get(payment_id)
    if not payment:
        await query.edit_message_text("❌ Order not found or already processed.")
        return
    
    try:
        await context.bot.send_message(
            payment['user_id'],
            f"❌ *❌ PAYMENT REJECTED* ❌\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Dear {payment['first_name']},\n\n"
            f"Your payment for Order #{payment_id} has been rejected.\n\n"
            f"🛍️ *Order Details:*\n"
            f"├ 🧾 Order ID: `#{payment_id}`\n"
            f"├ 🏷️ Product: {payment['coupon_name']}\n"
            f"├ 🔢 Quantity: {payment['quantity']} code(s)\n"
            f"└ 💰 Amount: ₹{payment['inr_amount']}\n\n"
            f"📌 *Reason for Rejection:*\n"
            f"• Payment not received\n"
            f"• Transaction not found on blockchain\n"
            f"• Incorrect amount sent\n\n"
            f"💰 *Refund Policy:*\n"
            f"If amount was deducted from your wallet, you will receive a FULL refund within 3 hours.\n\n"
            f"📞 *For support, click the Support button.*\n\n"
            f"Sorry for the inconvenience. 🙏",
            parse_mode='Markdown'
        )
        
        rejected_orders.append({
            'user_id': payment['user_id'],
            'coupon_name': payment['coupon_name'],
            'quantity': payment['quantity'],
            'inr_amount': payment['inr_amount'],
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        admin_reject_msg = (
            f"❌ *ORDER #{payment_id} REJECTED* ❌\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *👨‍💼 CUSTOMER DETAILS:*\n"
            f"├ 🏷️ Name: {payment['first_name']} {payment['last_name']}\n"
            f"├ 🆔 Telegram ID: `{payment['user_id']}`\n"
            f"├ 📝 Username: @{payment['username'] if payment['username'] != str(payment['user_id']) else 'N/A'}\n"
            f"└ 🔗 Profile: [Click Here](tg://user?id={payment['user_id']})\n\n"
            f"🛍️ *📦 ORDER DETAILS:*\n"
            f"├ 🏷️ Product: {payment['coupon_name']}\n"
            f"├ 🔢 Quantity: {payment['quantity']} code(s)\n"
            f"└ 💰 Amount: ₹{payment['inr_amount']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 User has been notified about the rejection."
        )
        
        await query.edit_message_text(admin_reject_msg, parse_mode='Markdown')
        pending_payments.pop(payment_id, None)
        print(f"❌ Order #{payment_id} rejected - User: {payment['first_name']}")
        
    except Exception as e:
        print(f"Error: {e}")
        await query.edit_message_text(f"⚠️ Error sending rejection: {e}")

# ==================== MAIN FUNCTION ====================
def main():
    load_existing_users()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ==================== CONVERSATION HANDLER FOR SUPPORT ====================
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^🆘 Support$'), support_start),
        ],
        states={
            SUPPORT_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, support_receive),
            ]
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex('^🛒 Buy Now$'), handle_message),
            MessageHandler(filters.Regex('^📜 My History$'), handle_message),
        ]
    )
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("msgtosend", broadcast))
    app.add_handler(CommandHandler("ticket", ticket_reply))
    app.add_handler(CommandHandler("setprice", set_price))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Start auto-ping
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(auto_self_ping(app))
    
    print("=" * 60)
    print("🤖 Shien Code Selling Bot is running...")
    print(f"👑 Admin ID: {ADMIN_USER_ID}")
    print(f"👥 Total Users: {len(all_users)}")
    print("🟢 Status ping: Every 30 minutes")
    print("📢 Broadcast: /msgtosend")
    print("📩 Support reply: /ticket @username")
    print("💰 Set price: /setprice 150")
    print(f"✅ Current price: ₹{current_price} per code")
    print(f"💱 USDT Rate: 1 USDT = ₹{USDT_RATE}")
    print("=" * 60)
    
    app.run_polling()

if __name__ == '__main__':
    main()