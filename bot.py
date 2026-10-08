import sqlite3
import telebot
from telebot import types

TOKEN = '8902568217:AAHDC5J_3_r1jMA0Ys1cOpbeawyJvynOi2k'
bot = telebot.TeleBot(TOKEN)

GROUP_CHAT_ID = -1004317508437
MESSAGE_THREAD_ID = 30         # Առաջադրանքների Topic-ի ID-ն
CALCULATOR_THREAD_ID = 0       # Այստեղ գրէ՛ք Ձեր 3D Հաշւիչի Topic-ի ID-ն (օրինակ՝ 45)
CALCULATOR_URL = "https://celebrated-palmier-2b00cd.netlify.app/"

commands = [
    telebot.types.BotCommand("start", "Գլխաւոր ցանկ"),
    telebot.types.BotCommand("calculator", "3D Տպագրութեան հաշւարկ"),
    telebot.types.BotCommand("newtask", "Ստեղծել նոր յանձնարարութիւն"),
    telebot.types.BotCommand("help", "Օգնութիւն")
]
bot.set_my_commands(commands)

def init_db():
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            message_id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            task_text TEXT,
            status TEXT,
            assignee TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

user_states = {}

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for member in message.new_chat_members:
        user_name = f"@{member.username}" if member.username else member.first_name
        user_id = member.id
        
        welcome_text = (
            f"Բարի գալուստ Technolab-ի համայնքային զրոյց! 🚀\n\n"
            f"👤 Յարգելի {user_name}\n"
            f"🆔 ID: {user_id}\n\n"
            f"Այս հարթակը նախատեսուած է մեր աշխատանքային ընթացքը եւ պատուէրները քննարկելու համար։"
        )
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            pass
            
        bot.send_message(chat_id=message.chat.id, text=welcome_text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_calc = types.InlineKeyboardButton("🖨 3D Հաշւիչ (Բացել Topic-ում)", callback_data="send_calculator_to_topic")
    btn_new_task = types.InlineKeyboardButton("➕ Ստեղծել նոր յանձնարարութիւն", callback_data="menu_new_task")
    markup.add(btn_calc, btn_new_task)

    welcome_text = (
        "🤖 Technolab Task Manager\n\n"
        "Սեղմեցէք ստորեւ նշուած կոճակը կամ օգտագործէք /calculator հրամանը:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.message_handler(commands=['calculator'])
def calculator_command(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    send_calculator_to_topic(message.chat.id)

def send_calculator_to_topic(chat_id):
    markup = types.InlineKeyboardMarkup()
    btn_calc = types.InlineKeyboardButton("🖨 Բացել 3D Հաշւիչը", url=CALCULATOR_URL)
    markup.add(btn_calc)

    calc_text = (
        "🖨 **Technolab 3D Տպագրութեան Հաշւիչ**\n\n"
        "Սեղմեցէք ստորեւ նշուած կոճակը՝ 3D տպագրութեան գինն ու ժամանակը հաշւելու համար:"
    )
    
    target_chat = GROUP_CHAT_ID if GROUP_CHAT_ID else chat_id
    kwargs = {
        "chat_id": target_chat,
        "text": calc_text,
        "parse_mode": "Markdown",
        "reply_markup": markup
    }
    
    if CALCULATOR_THREAD_ID and GROUP_CHAT_ID:
        kwargs["message_thread_id"] = CALCULATOR_THREAD_ID

    bot.send_message(**kwargs)

@bot.message_handler(commands=['newtask'])
def create_task_command(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    task_text = message.text.replace('/newtask', '').strip()
    if not task_text:
        return
    save_and_send_task(message.chat.id, task_text)

def save_and_send_task(chat_id, task_text):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_take = types.InlineKeyboardButton("⏳ Կը վերցնեմ", callback_data="take_task")
    btn_cancel = types.InlineKeyboardButton("❌ Ազատել", callback_data="cancel_task")
    btn_done = types.InlineKeyboardButton("✅ Կատարուած է", callback_data="done_task")
    markup.add(btn_take, btn_cancel, btn_done)

    msg_body = (
        f"📌 ՆՈՐ ՅԱՆՁՆԱՐԱՐՈՒԹԻՒՆ\n\n"
        f"• Անելիք՝ {task_text}\n"
        f"• Վիճակ՝ 🟢 Ազատ է\n"
        f"• Կատարող՝ ➖ (Տակաւին վերցուած չէ)"
    )

    target_chat = GROUP_CHAT_ID if GROUP_CHAT_ID else chat_id
    
    kwargs = {
        "chat_id": target_chat,
        "text": msg_body,
        "reply_markup": markup
    }
    
    if MESSAGE_THREAD_ID and GROUP_CHAT_ID:
        kwargs["message_thread_id"] = MESSAGE_THREAD_ID

    sent_msg = bot.send_message(**kwargs)
    
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (message_id, chat_id, task_text, status, assignee) VALUES (?, ?, ?, ?, ?)",
        (sent_msg.message_id, sent_msg.chat.id, task_text, "🟢 Ազատ է", None)
    )
    conn.commit()
    conn.close()

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "waiting_for_task")
def process_task_text(message):
    user_id = message.from_user.id
    task_text = message.text.strip()
    user_states[user_id] = None
    
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    if not task_text:
        return

    save_and_send_task(message.chat.id, task_text)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    message = call.message
    user_id = call.from_user.id
    
    if call.from_user.username:
        user_name = f"@{call.from_user.username}"
    else:
        user_name = call.from_user.first_name

    if call.data == "open_calculator_to_topic":
        bot.answer_callback_query(call.id, "🖨 Հաշւիչը ուղարկուեց իր նախատեսուած թեմա (Topic):")
        send_calculator_to_topic(message.chat.id)
        return

    if call.data == "menu_new_task":
        user_states[user_id] = "waiting_for_task"
        bot.answer_callback_query(call.id)
        bot.send_message(message.chat.id, "✍️ Ուղարկեցէք յանձնարարութեան գրութիւնը հաղորդագրութեամբ:")
        return

    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute("SELECT task_text, status, assignee FROM tasks WHERE message_id = ?", (message.message_id,))
    row = cursor.fetchone()

    if not row:
        bot.answer_callback_query(call.id, "⚠️ Յանձնարարութիւնը չգտնուեցաւ տուեալների բազայում:")
        conn.close()
        return

    task_text, status, assignee = row

    if call.data == "take_task":
        new_status = "⏳ Կատարման ընթացքին է"
        new_text = (
            f"📌 ՆՈՐ ՅԱՆՁՆԱՐԱՐՈՒԹԻՒՆ\n\n"
            f"• Անելիք՝ {task_text}\n"
            f"• Վիճակ՝ {new_status}\n"
            f"• Կատարող՝ {user_name}"
        )
        cursor.execute("UPDATE tasks SET status = ?, assignee = ? WHERE message_id = ?", (new_status, user_name, message.message_id))
        conn.commit()
        bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=new_text, reply_markup=message.reply_markup)
        bot.answer_callback_query(call.id, f"Դուք վերցրིք այս գործը ({user_name})։")

    elif call.data == "cancel_task":
        new_status = "🟢 Ազատ է"
        new_text = (
            f"📌 ՆՈՐ ՅԱՆՁՆԱՐԱՐՈՒԹԻՒՆ\n\n"
            f"• Անելիք՝ {task_text}\n"
            f"• Վիճակ՝ {new_status}\n"
            f"• Կատարող՝ ➖ (Տակաւին վերցուած չէ)"
        )
        cursor.execute("UPDATE tasks SET status = ?, assignee = ? WHERE message_id = ?", (new_status, None, message.message_id))
        conn.commit()
        bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=new_text, reply_markup=message.reply_markup)
        bot.answer_callback_query(call.id, "Յանձնարարութիւնը ազատուեցաւ:")

    elif call.data == "done_task":
        current_assignee = assignee if assignee else user_name
        new_text = (
            f"📌 ՆՈՐ ՅԱՆՁՆԱՐԱՐՈՒԹԻՒՆ\n\n"
            f"• Անելիք՝ {task_text}\n"
            f"• Վիճակ՝ ✅ Աւարտուած է\n"
            f"• Կատարող՝ {current_assignee}"
        )
        cursor.execute("UPDATE tasks SET status = ? WHERE message_id = ?", ("✅ Աւարտուած է", message.message_id))
        conn.commit()
        bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=new_text)
        bot.answer_callback_query(call.id, "Յանձնարարութիւնը նշուեցաւ որպէս կատարուած։")

    conn.close()

print("Բոտը աշխատում է առանձին թեմաներով (Topics)...")
bot.infinity_polling()
