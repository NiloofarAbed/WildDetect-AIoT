from telethon import TelegramClient, events, Button
import sqlite3
import time
from datetime import datetime
import requests
import re
import os
import signal
import asyncio
import subprocess
import adafruit_dht
import board
from gpiozero import LED, Buzzer, OutputDevice
import shutil
import zipfile

# Kill any libgpiod_pulsei process to avoid conflicts with DHT sensor in New version of Raspberry Pi OS
try:
    pid_output = subprocess.check_output("ps -A | grep libgpiod_pulsei | awk '{print $1}'", shell=True).strip()
    if pid_output:
        pid = int(pid_output)
        os.kill(pid, signal.SIGTERM)
        print(f"Process with PID {pid} has been killed.")
    else:
        print("Process libgpiod_pulsei not found.")
except subprocess.CalledProcessError:
    print("Error occurred while retrieving process.")

# Telegram API credentials
api_id = '' # Your API ID
api_hash = '' # Your API Hash
bot_token = '' # Your Bot Token from BotFather
client = TelegramClient('VAR', api_id, api_hash)

# Paths
DB_PATH = "data/users.db"
STATSDB_PATH = "data/stats.db"
BACKUP_FOLDER = "./backup"
PHOTO_PATH = "../ngl"

# Ensure directories exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)

# Initialize sensor and GPIO devices
dht_device = adafruit_dht.DHT11(board.D21)
LED1_PIN = OutputDevice(17)
LED2_PIN = OutputDevice(18)
buzzer1 = Buzzer(22)
buzzer2 = Buzzer(27)

# Current datetime
current_datetime = datetime.now().strftime("%d/%m/%Y %H:%M")

# Updated regex patterns
phone_pattern = re.compile(r'^[5-9]\d{9}$')  # Indian mobile numbers start with 5-9
name_pattern = re.compile(r'^[A-Z][a-z]+$')
password_pattern = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$.!]).{5,14}$')

# Database functions
def db_query(query, params=(), fetchone=False, commit=False):
    """Execute a database query with parameters"""
    try:
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            if commit:
                connection.commit()
            return cursor.fetchone() if fetchone else cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        # Return appropriate default values
        return None if fetchone else []

def ensure_tables_exist():
    """Ensure necessary tables exist in the databases"""
    # Create user table if not exists
    db_query('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY,
            step TEXT,
            phone TEXT,
            temp_phone TEXT,
            name TEXT,
            password TEXT,
            autologin TEXT,
            lightsen TEXT,
            buzzersen TEXT,
            role TEXT
        )
    ''', commit=True)
    
    # Create stats table in stats.db if not exists
    try:
        with sqlite3.connect(STATSDB_PATH) as conn:
            cursor = conn.cursor()
            # Check if stats table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stats'")
            if not cursor.fetchone():
                # Create the stats table with all needed columns
                cursor.execute('''
                    CREATE TABLE stats (
                        Name TEXT PRIMARY KEY,
                        Bull INTEGER DEFAULT 0,
                        Nilgai INTEGER DEFAULT 0,
                        Pig INTEGER DEFAULT 0,
                        Peacock INTEGER DEFAULT 0,
                        Squirrel INTEGER DEFAULT 0,
                        Jackal INTEGER DEFAULT 0,
                        Cat INTEGER DEFAULT 0,
                        Dog INTEGER DEFAULT 0,
                        Goat INTEGER DEFAULT 0,
                        Mouse INTEGER DEFAULT 0,
                        Insect INTEGER DEFAULT 0,
                        Person INTEGER DEFAULT 0,
                        Elephant INTEGER DEFAULT 0,
                        Monkey INTEGER DEFAULT 0,
                        Bird INTEGER DEFAULT 0,
                        Unknown INTEGER DEFAULT 0
                    )
                ''')
                # Insert the necessary rows
                cursor.execute("INSERT INTO stats (Name) VALUES ('Detected')")
                cursor.execute("INSERT INTO stats (Name) VALUES ('Correct')")
                cursor.execute("INSERT INTO stats (Name) VALUES ('Incorrect')")
                cursor.execute("INSERT INTO stats (Name) VALUES ('None')")
                conn.commit()
    except sqlite3.Error as e:
        print(f"Stats DB error: {e}")

def id_exist(user_id):
    """Check if a user exists in the database"""
    result = db_query("SELECT COUNT(*) FROM user WHERE id = ?", (user_id,), fetchone=True)
    return result and result[0] > 0

def login_check(phone, password):
    """Verify login credentials"""
    user = db_query("SELECT * FROM user WHERE phone = ? AND password = ?", (phone, password), fetchone=True)
    return user is not None

def get_user_column(user_id, column):
    """Get a specific column value for a user"""
    result = db_query(f"SELECT {column} FROM user WHERE id = ?", (user_id,), fetchone=True)
    return result[0] if result else None

def update_user_column(user_id, column, value):
    """Update a specific column for a user"""
    db_query(f"UPDATE user SET {column} = ? WHERE id = ?", (value, user_id), commit=True)

def all_farmer():
    """Get all user IDs with autologin enabled"""
    user_ids = db_query("SELECT id FROM user WHERE autologin = 'on'")
    return [int(row[0]) for row in user_ids if row and row[0]]

def role(chat_id):
    """Get user role"""
    return get_user_column(chat_id, "role")

# Sensor functions
def temp():
    """Read temperature from DHT sensor"""
    try:
        temperature = dht_device.temperature
        return temperature
    except Exception as error:
        print(f"Error reading temperature: {error}")
        return "Error"

def humid():
    """Read humidity from DHT sensor"""
    try:
        humidity = dht_device.humidity
        return humidity
    except Exception as error:
        print(f"Error reading humidity: {error}")
        return "Error"

# Backup functions
def get_next_entry_number():
    """Get the next entry number for backup details"""
    details_file_path = os.path.join(BACKUP_FOLDER, "details.txt")
    
    if os.path.exists(details_file_path):
        try:
            with open(details_file_path, "r") as details_file:
                lines = details_file.readlines()
                if lines:
                    last_line = lines[-1]
                    match = re.search(r'\[(\d+)\]', last_line)
                    if match:
                        last_number = int(match.group(1))
                        return last_number + 1
        except Exception as e:
            print(f"Error reading details file: {e}")
    
    return 1

def backup_photo(photo_path, detected_name):
    """Backup a detected photo with details"""
    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)

    try:
        temperature = temp()
        formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        entry_number = get_next_entry_number()
        new_filename = f"{entry_number}_{detected_name}_{formatted_datetime}"
        backup_file_path = os.path.join(BACKUP_FOLDER, new_filename)
        
        # Copy the file to the backup directory
        shutil.copy(photo_path, backup_file_path)
        
        # Record details
        details = f"[{entry_number}] Detected: {detected_name}, Time: {formatted_datetime}, Temperature: {temperature}\n"
        details_file_path = os.path.join(BACKUP_FOLDER, "details.txt")
        
        with open(details_file_path, "a") as details_file:
            details_file.write(details)
            
        return True
    except Exception as e:
        print(f"Error backing up photo: {e}")
        return False

def backup_folder_to_zip(zip_filename):
    """Create a zip backup of the backup folder"""
    if not os.path.exists(BACKUP_FOLDER):
        print(f"Error: The folder '{BACKUP_FOLDER}' does not exist.")
        return False

    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(BACKUP_FOLDER):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, BACKUP_FOLDER))
        
        print(f"Backup completed! The folder is saved as '{zip_filename}'.")
        return True
    except Exception as e:
        print(f"Error creating zip backup: {e}")
        return False

# Bot command handlers
@client.on(events.NewMessage(incoming=True, pattern="/start"))
async def start(event):
    """Handle /start command"""
    await event.delete()
    chat_id = event.chat_id

    if not id_exist(chat_id):
        await event.reply("Welcome to IOT test bot😊\nChoose your option:", buttons=[
            [Button.inline("Sign Up/Login", data="sign_login_btn")],
            [Button.inline("❓ About Us", data="about_us")]
        ])
        db_query('INSERT INTO user (id, step, phone, temp_phone, name, password, autologin, lightsen, buzzersen, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                 (chat_id, 'none', 'none', 'none', 'none', 'none', 'off', 'off', 'off', 'none'), commit=True)
    elif get_user_column(chat_id, "autologin") == "off":
        update_user_column(chat_id, 'step', 'none')
        await event.reply("Welcome to IOT test bot😊\nChoose your option:", buttons=[
            [Button.inline("Sign Up/Login", data="sign_login_btn")],
            [Button.inline("❓ About Us", data="about_us")]
        ])
    else:
        lightstats = get_user_column(chat_id, "lightsen")
        buzzerstats = get_user_column(chat_id, "buzzersen")
        await event.reply("🎛️ Welcome to panel:", buttons=[
            [Button.inline("ℹ️ Info", data="info")],
            [Button.inline("💡 Light", data="lightswitch"), Button.inline(lightstats, data="lightswitch")],
            [Button.inline("🔊 Buzzer", data="buzzerswitch"), Button.inline(buzzerstats, data="buzzerswitch")],
            [Button.inline("🔃 Refresh", data="refresh"), Button.inline("📩 Logout", data="logout")]
        ])
        update_user_column(chat_id, 'step', 'panel')

@client.on(events.CallbackQuery(data="sign_login_btn"))
async def sign_login_btn(event):
    """Handle sign up/login button"""
    await event.edit("You want to sign up or login?🤔", buttons=[
        [Button.inline("✏️ Sign Up", data="sign_up")],
        [Button.inline("🔑 Login", data="login")],
        [Button.inline("back", data="back_menu")]
    ])

@client.on(events.CallbackQuery(data="back_menu"))
async def back_menu(event):
    """Handle back to main menu button"""
    update_user_column(event.chat_id, 'step', 'none')
    update_user_column(event.chat_id, 'temp_phone', 'none')
    await event.edit("Welcome to IOT test bot😊\nChoose your option:", buttons=[
        [Button.inline("Sign Up/Login", data="sign_login_btn")],
        [Button.inline("❓ About Us", data="about_us")]
    ])

@client.on(events.CallbackQuery(data="about_us"))
async def about_us(event):
    """Handle about us button"""
    await event.edit("Beta version of VAR IoT", buttons=[
        [Button.inline("🔙", data="back_menu")]
    ])

@client.on(events.CallbackQuery(data="back_panel"))
async def back_panel(event):
    """Handle back to panel button"""
    chat_id = event.chat_id
    update_user_column(chat_id, 'step', 'panel')
    lightstats = get_user_column(chat_id, "lightsen")
    buzzerstats = get_user_column(chat_id, "buzzersen")
    await event.edit("🎛️ Welcome to panel:", buttons=[
        [Button.inline("ℹ️ Info", data="info")],
        [Button.inline("💡 Light", data="lightswitch"), Button.inline(lightstats, data="lightswitch")],
        [Button.inline("🔊 Buzzer", data="buzzerswitch"), Button.inline(buzzerstats, data="buzzerswitch")],
        [Button.inline("🔃 Refresh", data="refresh"), Button.inline("📩 Logout", data="logout")]
    ])

@client.on(events.CallbackQuery(data="sign_up"))
async def sign_up1(event):
    """Handle sign up button"""
    chat_id = event.chat_id
    if get_user_column(chat_id, "phone") == "none":
        update_user_column(chat_id, 'step', 'phone')
        await event.edit("📞 Send your phone number (10 digits starting with 5-9):", buttons=[
            [Button.inline("back", data="back_menu")]
        ])

@client.on(events.NewMessage)
async def handle_message(event):
    """Handle all incoming messages based on user step"""
    chat_id = event.chat_id
    step = get_user_column(chat_id, 'step')
    message = event.message.text

    if not step:
        return  # Ignore if no step is set or user doesn't exist

    if step == 'phone' and phone_pattern.match(message):
        update_user_column(chat_id, 'phone', message)
        reply_message = await event.reply("✅ Your phone submitted.", buttons=[[Button.inline("back", data="back_menu")]])
        await asyncio.sleep(2)
        await reply_message.edit("👤 What is your name? (First letter capital, rest lowercase)", buttons=[[Button.inline("back", data="back_menu")]])
        update_user_column(chat_id, 'step', 'name')
    
    elif step == 'name' and name_pattern.match(message):
        update_user_column(chat_id, 'name', message)
        reply_message = await event.reply("✅ Your name submitted.", buttons=[[Button.inline("back", data="back_menu")]])
        await asyncio.sleep(2)
        await reply_message.edit("🔐 Enter your password (5-14 chars with lowercase, uppercase, digit, and @$.!):", buttons=[[Button.inline("back", data="back_menu")]])
        update_user_column(chat_id, 'step', 'pass')
    
    elif step == 'pass' and password_pattern.match(message):
        update_user_column(chat_id, 'password', message)
        reply_message = await event.reply("✅ Your password submitted.", buttons=[[Button.inline("back", data="back_menu")]])
        await asyncio.sleep(2)
        lightstats = get_user_column(chat_id, "lightsen")
        buzzerstats = get_user_column(chat_id, "buzzersen")
        await reply_message.edit("🎛️ Welcome to panel:", buttons=[
            [Button.inline("ℹ️ Info", data="info")],
            [Button.inline("💡 Light", data="lightswitch"), Button.inline(lightstats, data="lightswitch")],
            [Button.inline("🔊 Buzzer", data="buzzerswitch"), Button.inline(buzzerstats, data="buzzerswitch")],
            [Button.inline("🔃 Refresh", data="refresh"), Button.inline("📩 Logout", data="logout")]
        ])
        update_user_column(chat_id, 'step', 'panel')
        update_user_column(chat_id, 'autologin', 'on')
    
    elif step == 'log_phone':
        # Validate phone number for login
        if phone_pattern.match(message):
            update_user_column(chat_id, 'temp_phone', message)
            reply_message = await event.reply("✅ Your phone checked.", buttons=[[Button.inline("back", data="back_menu")]])
            await asyncio.sleep(2)
            await reply_message.edit("🔐 Enter your password:", buttons=[[Button.inline("back", data="back_menu")]])
            update_user_column(chat_id, 'step', 'log_pass')
        else:
            await event.reply("❌ Invalid phone number. Please enter a 10-digit number starting with 5-9.", buttons=[[Button.inline("back", data="back_menu")]])
    
    elif step == 'log_pass':
        # Validate the password and perform login
        temp_phone = get_user_column(chat_id, 'temp_phone')
        if password_pattern.match(message) and login_check(temp_phone, message):
            reply_message = await event.reply("✅ Your password checked.")
            lightstats = get_user_column(chat_id, "lightsen")
            buzzerstats = get_user_column(chat_id, "buzzersen")
            await reply_message.edit("🎛️ Welcome to panel:", buttons=[
                [Button.inline("ℹ️ Info", data="info")],
                [Button.inline("💡 Light", data="lightswitch"), Button.inline(lightstats, data="lightswitch")],
                [Button.inline("🔊 Buzzer", data="buzzerswitch"), Button.inline(buzzerstats, data="buzzerswitch")],
                [Button.inline("🔃 Refresh", data="refresh"), Button.inline("📩 Logout", data="logout")]
            ])
            update_user_column(chat_id, 'temp_phone', 'none')
            update_user_column(chat_id, 'step', 'panel')
            update_user_column(chat_id, 'autologin', 'on')
        else:
            await event.reply("❌ Invalid password or phone number. Please try again.", buttons=[[Button.inline("back", data="back_menu")]])

@client.on(events.CallbackQuery(data="login"))
async def login_num(event):
    """Handle login button"""
    if get_user_column(event.chat_id, "autologin") == "off":
        update_user_column(event.chat_id, 'step', 'log_phone')
        await event.edit("📞 Enter your phone number:", buttons=[[Button.inline("back", data="back_menu")]])

@client.on(events.CallbackQuery(data="info"))
async def panel(event):
    """Handle info button"""
    chat_id = event.chat_id
    if get_user_column(chat_id, "autologin") == "on":
        phone = get_user_column(chat_id, "phone")
        temperature = temp()
        humidity = humid()
        await event.edit(f"🪪 ID: {chat_id}\n📞 Phone Number: {phone}",
                buttons=[
            [Button.inline("🌡️ Temperature", data=b""), Button.inline(f"{temperature}°C", data=b"")],
            [Button.inline("🌫️ Humidity", data=b""), Button.inline(f"{humidity}%", data=b"")],
            [Button.inline("back", data="back_panel")]
        ])

@client.on(events.CallbackQuery(data="refresh"))
async def refresh_panel(event):
    """Handle refresh button"""
    try:
        chat_id = event.chat_id
        lightstats = get_user_column(chat_id, "lightsen")
        buzzerstats = get_user_column(chat_id, "buzzersen")
        
        for i in range(3):
            await event.edit("🔃 Wait please" + '.' * (i + 1))
            await asyncio.sleep(0.1)
            
        await event.edit("🎛️ Welcome to panel:", buttons=[
            [Button.inline("ℹ️ Info", data="info")],
            [Button.inline("💡 Light", data="lightswitch"), Button.inline(lightstats, data="lightswitch")],
            [Button.inline("🔊 Buzzer", data="buzzerswitch"), Button.inline(buzzerstats, data="buzzerswitch")],
            [Button.inline("🔃 Refresh", data="refresh"), Button.inline("📩 Logout", data="logout")]
        ])
        update_user_column(chat_id, 'step', 'panel')
    except Exception as e:
        print(f"Error in refresh: {e}")
        await event.edit("❌ Login Expired\nStart again with /start")

@client.on(events.CallbackQuery(data="logout"))
async def logout(event):
    """Handle logout button"""
    update_user_column(event.chat_id, "autologin", "off")
    await event.edit("Welcome to IOT test bot😊\nChoose your option:", buttons=[
        [Button.inline("Sign Up/Login", data="sign_login_btn")],
        [Button.inline("❓ About Us", data="about_us")]
    ])
    update_user_column(event.chat_id, 'step', 'none')

@client.on(events.CallbackQuery(data="lightswitch"))
async def light_switch(event):
    """Handle light switch button"""
    chat_id = event.chat_id
    lightstats = get_user_column(chat_id, "lightsen")
    
    try:
        if lightstats == "off":
            LED1_PIN.on()
            LED2_PIN.on()
            update_user_column(chat_id, "lightsen", "on")
            await event.answer("✅ Lights are now on!", alert=True)
        else:
            LED1_PIN.off()
            LED2_PIN.off()
            update_user_column(chat_id, "lightsen", "off")
            await event.answer("❌ Lights are now off!", alert=True)
            
        await event.edit(buttons=[
            [Button.inline("ℹ️ Info", data="info")],
            [Button.inline("💡 Light", data="lightswitch"), Button.inline(get_user_column(chat_id, "lightsen"), data="lightswitch")],
            [Button.inline("🔊 Buzzer", data="buzzerswitch"), Button.inline(get_user_column(chat_id, "buzzersen"), data="buzzerswitch")],
            [Button.inline("🔃 Refresh", data="refresh"), Button.inline("📩 Logout", data="logout")]
        ])
    except Exception as e:
        print(f"Error toggling lights: {e}")
        await event.answer("❌ Error toggling lights!", alert=True)

@client.on(events.CallbackQuery(data="buzzerswitch"))
async def buzzer_switch(event):
    """Handle buzzer switch button"""
    chat_id = event.chat_id
    buzzer_status = get_user_column(chat_id, "buzzersen")

    try:
        if buzzer_status == "off":
            buzzer1.on()
            buzzer2.on()
            update_user_column(chat_id, "buzzersen", "on")
            await event.answer("✅ Buzzer is now on!", alert=True)
        else:
            buzzer1.off()
            buzzer2.off()
            update_user_column(chat_id, "buzzersen", "off")
            await event.answer("❌ Buzzer is now off!", alert=True)

        await event.edit(buttons=[
            [Button.inline("ℹ️ Info", data="info")],
            [Button.inline("💡 Light", data="lightswitch"), Button.inline(get_user_column(chat_id, "lightsen"), data="lightswitch")],
            [Button.inline("🔊 Buzzer", data="buzzerswitch"), Button.inline(get_user_column(chat_id, "buzzersen"), data="buzzerswitch")],
            [Button.inline("🔃 Refresh", data="refresh"), Button.inline("📩 Logout", data="logout")]
        ])
    except Exception as e:
        print(f"Error toggling buzzer: {e}")
        await event.answer("❌ Error toggling buzzer!", alert=True)

# Directory monitoring functions
async def monitor_directory(path):
    """Monitor a directory for new files and yield their paths"""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
        
    existing_files = {f: os.path.getmtime(os.path.join(path, f)) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))}

    while True:
        await asyncio.sleep(1)  # Check every second
        try:
            current_files = {f: os.path.getmtime(os.path.join(path, f)) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))}

            # Find newly added or modified files
            added_files = {
                f for f in current_files
                if f not in existing_files or current_files[f] > existing_files[f]
            }

            for file_name in added_files:
                file_path = os.path.join(path, file_name)
                if os.path.isfile(file_path):
                    yield file_path  # Yield the detected file

            # Update the existing file dictionary
            existing_files = current_files

        except Exception as e:
            print(f"Error reading the directory: {e}")
            await asyncio.sleep(1)  # Backoff in case of an error

def extract_filename(filepath):
    """Extract the base filename without extension"""
    filename_without_extension = os.path.splitext(os.path.basename(filepath))[0]
    return filename_without_extension.split('\\')[-1]

async def send_detection_photo_to_all(photo_path, chat_ids):
    """Send detection notification to all users and handle responses"""
    if not os.path.exists(photo_path):
        print(f"Photo path doesn't exist: {photo_path}")
        return
        
    detected_name = extract_filename(photo_path)
    formatted_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message_info = {}

    # Send to all users
    for chat_id in chat_ids:
        try:
            message = await client.send_file(
                chat_id, photo_path,
                caption=f"🕵🏻‍♂️ Detected as: {detected_name} \n📆 Time and Date: {formatted_datetime} \n️⚠️ Is this information correct?",
                buttons=[
                    Button.inline("❌ No", data=f"incorrect_{detected_name}"),
                    Button.inline("✅ Yes", data=f"correct_{detected_name}")
                ]
            )
            message_info[message.id] = chat_id  # Track message_id and chat_id
        except Exception as e:
            print(f"Error sending file to {chat_id}: {e}")

    # Update detection stats
    try:
        with sqlite3.connect(STATSDB_PATH) as conn:
            cursor = conn.cursor()
            # Check if the column exists
            cursor.execute(f"PRAGMA table_info(stats)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if detected_name in columns:
                cursor.execute(f"UPDATE stats SET {detected_name} = {detected_name} + 1 WHERE Name = 'Detected'")
            else:
                print(f"Column {detected_name} doesn't exist in stats table")
    except sqlite3.Error as e:
        print(f"Database error while updating stats: {e}")
    
    # Backup photo
    backup_photo(photo_path, detected_name)
    
    # Wait for 60 seconds for responses
    await asyncio.sleep(60)
    
    # Handle responses and message deletion
    for message_id, chat_id in message_info.items():
        try:
            # Fetch the message
            message = await client.get_messages(chat_id, ids=message_id)
                     
            # Check if the message has no responses (buttons clicked)
            if message and hasattr(message, 'button_count') and message.button_count > 0:
                try:
                    with sqlite3.connect(STATSDB_PATH) as conn:
                        cursor = conn.cursor()
                        # Check if the column exists
                        cursor.execute(f"PRAGMA table_info(stats)")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        if detected_name in columns:
                            cursor.execute(f"UPDATE stats SET {detected_name} = {detected_name} + 1 WHERE Name = 'None'")
                except sqlite3.Error as e:
                    print(f"Database error while updating None stats: {e}")

                await client.delete_messages(chat_id, message_id)
                await client.send_message(chat_id, "⚠️ We did a detection, but you didn't choose if it's correct or not.")
        except Exception as e:
            print(f"Error handling message response for {chat_id}: {e}")

@client.on(events.CallbackQuery(data=re.compile(b"(correct|incorrect)_")))
async def detection_result(event):
    """Handle detection confirmation callbacks"""
    try:
        data = event.data.decode("utf-8")
        confirmation, detected_name = data.split("_", 1)
        
        # Update stats more efficiently with parameter substitution
        with sqlite3.connect(STATSDB_PATH) as conn:
            cursor = conn.cursor()
            # Validate column exists before updating
            cursor.execute("PRAGMA table_info(stats)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if detected_name in columns:
                status = 'Correct' if confirmation == "correct" else 'Incorrect'
                cursor.execute(f"UPDATE stats SET {detected_name} = {detected_name} + 1 WHERE Name = ?", (status,))
                conn.commit()
            else:
                print(f"Warning: Column {detected_name} not found in stats table")
        
        # Send confirmation to user
        await event.answer(f"Thank you for confirming this detection as {confirmation}!", alert=True)
        await event.delete()
    except Exception as e:
        print(f"Error in detection callback: {e}")
        await event.answer("An error occurred processing your response", alert=True)

# More efficient tracking with class-based approach
class DetectionTracker:
    def __init__(self):
        self.last_processed = {
            "Bull": 0, "Nilgai": 0, "Pig": 0, "Peacock": 0,
            "Squirrel": 0, "Jackal": 0, "Cat": 0, "Dog": 0,
            "Goat": 0, "Mouse": 0, "Insect": 0, "Person": 0,
            "Elephant": 0, "Monkey": 0, "Bird": 0, "Unknown": 0
        }
        # Targeting animals that require action
        self.target_animals = {"Nilgai", "Pig", "Jackal", "Person"}

tracker = DetectionTracker()

# Simplified ultrasonic function for future implementation
def activate_ultrasonic(frequency, duration=1):
    """Function to activate ultrasonic device (placeholder for implementation)"""
    print(f"Activating ultrasonic at {frequency}kHz for {duration}s")

async def action_per_detection():
    """Monitor detection stats and trigger appropriate actions"""
    while True:
        try:
            await asyncio.sleep(20)  # Check every 20 seconds
            
            with sqlite3.connect(STATSDB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM stats WHERE Name = "Detected"')
                detected_row = cursor.fetchone()
                
                if not detected_row:
                    continue
                    
                # Map column indices to animal names for readability
                cursor.execute("PRAGMA table_info(stats)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Process only animals that have new detections
                for i, animal_count in enumerate(detected_row[1:], 1):
                    if i >= len(columns):
                        break
                        
                    animal_name = columns[i]
                    if not animal_count or tracker.last_processed.get(animal_name, 0) == animal_count:
                        continue
                        
                    # Update the tracking counter first to prevent duplicate actions
                    tracker.last_processed[animal_name] = animal_count
                    
                    # Take action based on detected animal
                    if animal_name in ("Nilgai", "Pig", "Jackal"):
                        print(f"Taking deterrent action for {animal_name}")
                        # Cycle through deterrent methods
                        LED1_PIN.on()
                        buzzer1.on()
                        await asyncio.sleep(2)
                        buzzer1.off()
                        await asyncio.sleep(1)
                        LED1_PIN.off()
                        
                    elif animal_name == "Person":
                        print(f"Person detected - activating lights")
                        LED1_PIN.on()
                        LED2_PIN.on()
                        await asyncio.sleep(5)
                        LED1_PIN.off()
                        LED2_PIN.off()
                        
        except sqlite3.Error as db_err:
            print(f"Database error in action monitoring: {db_err}")
        except Exception as e:
            print(f"Error in action monitoring: {e}")
            await asyncio.sleep(30)  # Longer sleep on error to prevent rapid retries

# Admin command handlers optimized for better error handling and performance
@client.on(events.NewMessage(incoming=True, pattern="/help"))
async def admin_help(event):
    """Handle admin help command"""
    if role(event.chat_id) == "admin":
        help_text = (
            "🆘 Admin Help Commands:\n"
            " /user_db - Export users database\n"
            " /stats_db - Export detection statistics database\n"
            " /export - Export photo backups with detection details\n"
            " /analysis - Export statistical charts and analysis\n"
            " /backup - Create and send a backup of all system data"
        )
        await event.reply(help_text)

@client.on(events.NewMessage(incoming=True, pattern="/user_db"))
async def export_user_db(event):
    """Export user database for admin"""
    if role(event.chat_id) != "admin":
        return
        
    try:
        await client.send_file(
            event.chat_id, 
            DB_PATH,
            caption=f"🕵🏻‍♂️ Users Database\n📆 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
    except Exception as e:
        await event.reply(f"❌ Error exporting users database: {e}")

@client.on(events.NewMessage(incoming=True, pattern="/stats_db"))
async def export_stats_db(event):
    """Export detection statistics database for admin"""
    if role(event.chat_id) != "admin":
        return
        
    try:
        await client.send_file(
            event.chat_id, 
            STATSDB_PATH,
            caption=f"🕵🏻‍♂️ Detection Statistics Database\n📆 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
    except Exception as e:
        await event.reply(f"❌ Error exporting stats database: {e}")

@client.on(events.NewMessage(incoming=True, pattern="/analysis"))
async def generate_analysis(event):
    """Generate and send statistical analysis charts for admin"""
    if role(event.chat_id) != "admin":
        return
        
    try:
        # Notify user that processing has started
        processing_msg = await event.reply("📊 Generating analysis charts... Please wait.")
        
        # Run the data analysis script
        result = subprocess.run(['python', "data.py"], capture_output=True, text=True)
        
        if result.returncode != 0:
            await processing_msg.edit(f"❌ Error generating charts: {result.stderr}")
            return
            
        # Current timestamp for all captions
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # Send all charts with appropriate captions
        chart_files = [
            ("data/all_conditions_charts.png", "📊 All conditions chart"),
            ("data/Detected_charts.png", "📊 Detected animals chart"),
            ("data/Correct_charts.png", "📊 Correctly identified animals chart"),
            ("data/Incorrect_charts.png", "📊 Incorrectly identified animals chart"),
            ("data/None_charts.png", "📊 No-response detection chart")
        ]
        
        for file_path, caption in chart_files:
            if os.path.exists(file_path):
                await client.send_file(
                    event.chat_id,
                    file_path,
                    caption=f"{caption}\n📆 {timestamp}"
                )
            else:
                await event.reply(f"⚠️ Chart file not found: {file_path}")
                
        await processing_msg.delete()
    except Exception as e:
        await event.reply(f"❌ Error in analysis: {e}")

@client.on(events.NewMessage(incoming=True, pattern="/export"))
async def export_backup(event):
    """Export photo backups and detection data for admin"""
    if role(event.chat_id) != "admin":
        return
        
    try:
        # Notify user that processing has started
        processing_msg = await event.reply("📦 Creating backup archive... Please wait.")
        
        # Generate backup with timestamp to prevent overwrites
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f'backup_{timestamp}.zip'
        
        if backup_folder_to_zip(zip_filename):
            await client.send_file(
                event.chat_id,
                zip_filename,
                caption=f"🕵🏻‍♂️ Photo and detection backup\n📆 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            # Clean up the zip file after sending
            try:
                os.remove(zip_filename)
            except OSError:
                pass
        else:
            await event.reply("❌ Failed to create backup archive.")
            
        await processing_msg.delete()
    except Exception as e:
        await event.reply(f"❌ Error creating backup: {e}")

async def monitor_task():
    """Monitor directory for new detection photos and notify users"""
    while True:
        try:
            # Fetch chat IDs periodically to ensure we have the current list
            chat_ids = all_farmer()
            
            # No need to continue if no users to notify
            if not chat_ids:
                await asyncio.sleep(10)
                continue
                
            async for photo_path in monitor_directory(PHOTO_PATH):
                try:
                    if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
                        await send_detection_photo_to_all(photo_path, chat_ids)
                    else:
                        print(f"Skipping invalid file: {photo_path}")
                except Exception as e:
                    print(f"Error processing photo {photo_path}: {e}")
                    
        except Exception as e:
            print(f"Error in monitor task: {e}")
            await asyncio.sleep(30)  # Back off on errors

async def main():
    """Main function to run the bot and monitoring tasks"""
    try:
        # Ensure database tables exist
        ensure_tables_exist()
        
        # Start the monitoring and action tasks
        monitor = asyncio.create_task(monitor_task())
        action = asyncio.create_task(action_per_detection())
        
        # Run the bot until disconnected
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        # Clean up resources
        LED1_PIN.off()
        LED2_PIN.off()
        buzzer1.off()
        buzzer2.off()
        print("Resources cleaned up")

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())