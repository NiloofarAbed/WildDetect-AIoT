# 🐾 WildDetect-AIoT  
**Smart AI + IoT Animal Detection System for Farmers**

Welcome to **WildDetect-AIoT** – a Raspberry Pi-powered AI bot that detects wild animals using **YOLOv8**, alerts the farmer via **Telegram**, and scares them off with a **buzzer + light combo**!  
Control everything from an **admin panel** and go fully **auto-mode** after confirming detections.  
Peace of mind for your crops, powered by AI.

---

## ✨ Features

| Feature | Description |
|--------|-------------|
| 🧠 YOLOv8 Detection | Real-time animal detection using camera feed and YOLOv8 |
| 📲 Telegram Bot | Instant alerts and image notifications via Telegram |
| 🛠️ Admin Panel | Sign up, sign in, and control devices remotely |
| 🔔 Buzzer & Light | Scare off animals with GPIO-controlled hardware |
| ✅ Manual Review | Farmer confirms detection accuracy |
| 🤖 Auto Mode | Automatically triggers hardware for future detections |

---

## ⚙️ Hardware Requirements

- Raspberry Pi (with GPIO support) (Already tested on Raspberry pi 5,4)
- Camera module (Pi Cam)
- Buzzer module
- Light module (LED or spotlight)
- Internet connection (for bot communication)

---

## 💻 Software Requirements

- Python 3.7+
- [YOLOv8 (Ultralytics)](https://github.com/ultralytics/ultralytics)
- Telethon
- OpenCV
- Pic2cam
- PyTorch

Install all required Python packages:

```bash
pip install -r requirements.txt



---

## 🚀 Getting Started
	1.	Clone this repo:

git clone https://github.com/NiloofarAbed/WildDetect-AIoT.git
cd WildDetect-AIoT

	2.	Create Telegram Bot:
	•	Chat with @BotFather
	•	Save the Bot Token
	•	Get API ID and API Hash from my.telegram.org
	3.	Update bot.py:
	•	Fill in your bot token, API ID, API Hash, and user settings
	4.	Start the bot:

python bot.py



---

## 🧪 How It Works

graph TD;
    A[Camera captures live feed] --> B[YOLOv8 detects animal];
    B --> C[Send image to farmer via Telegram];
    C --> D[Farmer confirms if detection is correct];
    D -->|Correct| E[Enable Auto-Mode];
    E --> F[Future detections trigger buzzer & light];
    D -->|Incorrect| G[No action taken];



---

## 🛡 Admin Panel

Access your web panel to:
	•	✅ Sign In / Sign Up
	•	💡 Toggle Light
	•	🔔 Toggle Buzzer
	•	📸 View Detected Images
	•	⚙️ Information of Account

---

## 📁 Project Structure

WildDetect-AIoT/
├── bot/                        # Telegram bot and admin logic
│   ├── bot.py                  # Main Telegram bot logic (everything lives here!)
│   ├── data.py                 # Generates charts and processes DB data
│   ├── req.txt                 # Bot-specific Python requirements
│   ├── data/           # Contains local database and historical data
│
├── camera/                     # Camera + YOLO module
│   ├── camera.py               # Handles camera input and image capture
│   ├── epoch200               # Trained YOLOv8 model weights
│
├── ngl/                        # Photo relay system between camera and bot
│   ├── [takes captured images and sends them to the bot]



---

## 🖼️ Screenshots

!(Workflow)[images/main.png]
!(Bot Screen)[images/screen.png]
!(Admin Panel Screen)[images/admin.png]

---

## 📝 License

This project is open-source and available for use under the terms of the MIT License.

**However**, if you use, modify, or build upon this project in any academic, research, or commercial setting,  
**you must cite the following publication**:

> **Citation DOI**: [https://doi.org/10.1016/j.atech.2025.100829](https://doi.org/10.1016/j.atech.2025.100829)

Give credit where it's due — it helps support the work and keeps the community strong!



⸻