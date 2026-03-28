import telebot
import requests
import threading
import os
from flask import Flask
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import generate_image
import generate_pdf

user_data_store = {}

# आप Replit में Secrets (Environment Variables) का इस्तेमाल भी कर सकते हैं
API_TOKEN = os.environ.get('BOT_TOKEN', '8380156635:AAH_jCEH_bGUbUsmWmX0ZrUWP0T5ZC4vRnE')

bot = telebot.TeleBot(API_TOKEN)

def get_final_score(url):
    try:
        # असली ब्राउज़र जैसा दिखने के लिए उन्नत हेडर्स
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'Upgrade-Insecure-Requests': '1'
        }

        # URL को साफ़ करें
        clean_url = url.strip().replace('//per', '/per').split('#')[0]
        
        response = session.get(clean_url, headers=headers, timeout=30)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            return f"❌ Error: वेबसाइट ने जवाब नहीं दिया। (Code: {response.status_code})", None

        soup = BeautifulSoup(response.text, 'html.parser')

        # बैनर इमेज निकालें
        banner_img = soup.find('img')
        banner_url = ""
        if banner_img and banner_img.has_attr('src'):
            banner_url = urljoin(url, banner_img['src'])

        # छात्र की फोटो निकालें
        tds = soup.find_all('td')
        photo_b64 = ""
        photo_url = ""
        for i, td in enumerate(tds):
            if "Application Photograph" in td.get_text() or "Candidate Photograph" in td.get_text():
                img = td.find('img')
                if not img and i + 1 < len(tds):
                    img = tds[i+1].find('img')
                if img and img.has_attr('src'):
                    src = img['src']
                    if src.startswith('data:image'):
                        photo_b64 = src
                    else:
                        photo_url = urljoin(url, src)
                break

        # छात्र की जानकारी निकालें
        user_info = {}
        first_table = soup.find('table')
        if first_table:
            tds = first_table.find_all('td')
            for i in range(len(tds) - 1):
                key = tds[i].get_text(strip=True)
                val = tds[i+1].get_text(strip=True)
                user_info[key] = val
        
        exam_name = user_info.get('Subject', 'N/A')
        reg_no = user_info.get('Registration Number', 'N/A')
        roll_no = user_info.get('Roll Number', 'N/A')
        cand_name = user_info.get('Candidate Name', 'N/A')
        community = user_info.get('Community', 'N/A')
        test_date = user_info.get('Test Date', 'N/A')
        test_time = user_info.get('Test Time', 'N/A')
        test_center = user_info.get('Test Centre Name', 'N/A')

        section_results = []
        overall_total = 0
        overall_correct = 0
        overall_incorrect = 0
        overall_not_answered = 0

        # सवाल ढूँढने के लिए सबसे लचीला तरीका, सेक्शन-वाइज़
        sections = soup.find_all('div', class_='section-cntnr')
        if not sections:
            sections = [soup]

        for sec in sections:
            sec_lbl = sec.find('div', class_='section-lbl') if hasattr(sec, 'find') else None
            sec_name = sec_lbl.get_text(strip=True).replace("Section :", "").strip() if sec_lbl else "Part A"
            
            all_tables = sec.find_all('table') if hasattr(sec, 'find_all') else []
            question_blocks = []
            
            for table in all_tables:
                if "Question ID :" in table.get_text():
                    if table.find('table', class_='menu-tbl'):
                        question_blocks.append(table)
                        
            if not question_blocks and hasattr(sec, 'find_all'):
                question_blocks = sec.find_all('table', class_='question-pnl')

            if not question_blocks:
                continue
                
            sec_total = len(question_blocks)
            sec_correct = 0
            sec_incorrect = 0
            sec_not_answered = 0

            for q in question_blocks:
                correct_opt = None
                ans_td = q.find('td', class_='rightAns')
                if ans_td:
                    ans_text = ans_td.get_text().strip()
                    match_c = re.search(r'^([A-Za-z0-9])\.', ans_text)
                    if match_c:
                        correct_opt = match_c.group(1).upper()

                chosen_opt = None
                menu_tbl = q.find('table', class_='menu-tbl')
                if menu_tbl:
                    menu_text = menu_tbl.get_text()
                    match_ch = re.search(r'Chosen\s*Option\s*:\s*([A-Za-z0-9])', menu_text)
                    if match_ch:
                        chosen_opt = match_ch.group(1).upper()
                    elif "ChosenOption:--" in menu_text.replace(" ", "") or "ChosenOption:None" in menu_text.replace(" ", ""):
                        chosen_opt = "--"

                if chosen_opt == "--" or chosen_opt is None:
                    sec_not_answered += 1
                elif correct_opt and str(chosen_opt) == str(correct_opt):
                    sec_correct += 1
                else:
                    sec_incorrect += 1
                    
            sec_marks = sec_correct - (sec_incorrect * 0.33)
            section_results.append({
                'name': sec_name,
                'total': sec_total,
                'na': sec_not_answered,
                'right': sec_correct,
                'wrong': sec_incorrect,
                'marks': round(sec_marks, 2)
            })

            overall_total += sec_total
            overall_correct += sec_correct
            overall_incorrect += sec_incorrect
            overall_not_answered += sec_not_answered

        if overall_total == 0:
            return "❌ Error: कोई सवाल नहीं मिले। कृपया सुनिश्चित करें कि यह सही HTML रिस्पॉन्स शीट है。", None

        overall_attempted = overall_correct + overall_incorrect
        overall_score = overall_correct - (overall_incorrect * 0.33)

        res = (
            f"🎓 Exam: {exam_name}\n"
            f"🔢 Registration Number: {reg_no}\n"
            f"🎫 Roll Number: {roll_no}\n"
            f"👤 Candidate Name: {cand_name}\n"
            f"🏛️ Community: {community}\n"
            f"🏫 Test Center Name: {test_center}\n"
            f"📅 Exam Date: {test_date}\n"
            f"⏰ Exam Time: {test_time}\n"
            f"📚 Subject: {exam_name}\n\n"
        )
        
        if len(section_results) > 1:
            res += "📑 Section-wise Score:\n-------------------\n"
            for s in section_results:
                res += f"🔹 {s['name']}\n"
                answered = s['right'] + s['wrong']
                res += f"  Total: {s['total']} | Answered: {answered} | Right: {s['right']} | Wrong: {s['wrong']} | Not Answered: {s['na']} | Marks: {s['marks']} |\n\n"

        res += (
            "🏆 Overall Scorecard\n"
            "----------------------\n"
            f"📝 Total Questions: {overall_total}\n"
            f"🎯 Attempted: {overall_attempted}\n"
            f"⚪ Skipped: {overall_not_answered}\n"
            "\n"
            f"✅ Total Correct Answers: {overall_correct}\n"
            f"❌ Total Incorrect Answers: {overall_incorrect}\n"
            "\n"
            f"🏅 Total Score: {round(overall_score, 2)}"
        )
        
        parsed_data = {
            'cand_name': cand_name,
            'roll_no': roll_no,
            'test_date': test_date,
            'exam_name': exam_name,
            'community': community,
            'overall_total': overall_total,
            'overall_attempted': overall_attempted,
            'overall_correct': overall_correct,
            'overall_incorrect': overall_incorrect,
            'overall_not_answered': overall_not_answered,
            'overall_score': round(overall_score, 5),
            'banner_url': banner_url,
            'photo_b64': photo_b64,
            'photo_url': photo_url,
            'sections': section_results,
            'reg_no': reg_no,
            'test_center': test_center,
            'test_time': test_time
        }
        return res, parsed_data

    except Exception as e:
        return f"⚠️ Error: {str(e)}", None

@bot.message_handler(commands=['start'])
def welcome(message):
    welcome_text = (
        "👋 **Scorecard Calculator Bot में आपका स्वागत है!** 🎯\n\n"
        "यह बॉट आपको आपकी **Railway (RRB)** और **SSC** परीक्षाओं की Answer Key का लिंक भेजने पर एक शानदार और 100% एक्यूरेट Scorecard बनाकर देता है। \n\n"
        "👇 **कदम (How to use):**\n"
        "1️⃣ Menu से `/scorecard` कमांड चुनें।\n"
        "2️⃣ अपनी Official Answer Key का लिंक (URL) चैट में पेस्ट (Paste) करके भेज दें।\n"
        "3️⃣ कुछ ही सेकंड्स में अपना स्कोरकार्ड *PDF और Image* दोनों में पाएँ!\n\n"
        "🔗 *आप चाहें तो डायरेक्ट अभी भी अपना लिंक (URL) भेज सकते हैं...*"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['scorecard'])
def ask_for_url(message):
    bot.reply_to(
        message, 
        "🔗 **कृपया अपनी Answer Key का वेब लिंक (URL) नीचे भेजें!**\n\nलिंक भेजते ही मैं तुरंत आपके लिए Image और PDF में स्कोरकार्ड तैयार कर दूँगा।", 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: True)
def process_link(message):
    url = message.text.strip()
    if "digialm.com" in url:
        progress_msg = bot.reply_to(message, "Generating Your 📝 Scorecard....")
        res_text, parsed_data = get_final_score(url)
        
        try:
            bot.delete_message(message.chat.id, progress_msg.message_id)
        except:
            pass
            
        if parsed_data:
            user_data_store[message.chat.id] = parsed_data
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton("🖼️ Download Image", callback_data="dl_image"),
                telebot.types.InlineKeyboardButton("📄 Download PDF", callback_data="dl_pdf")
            )
            sent_msg = bot.send_message(message.chat.id, res_text, reply_markup=markup)
        else:
            sent_msg = bot.send_message(message.chat.id, res_text)

        # ऑटो रिएक्शन दें (अगर लाइब्रेरी सपोर्ट करती है)
        try:
            from telebot.types import ReactionTypeEmoji
            bot.set_message_reaction(message.chat.id, sent_msg.message_id, [ReactionTypeEmoji('🎉')], is_big=True)
        except Exception:
            pass

    else:
        bot.reply_to(message, "❌ कृपया सही Answer Key का लिंक भेजें।")

@bot.callback_query_handler(func=lambda call: call.data in ["dl_image", "dl_pdf"])
def handle_download(call):
    chat_id = call.message.chat.id
    if chat_id in user_data_store:
        data = user_data_store[chat_id]
        
        if call.data == "dl_image":
            bot.answer_callback_query(call.id)
            prog_msg = bot.send_message(chat_id, "Generating Your Scorecard 🖼️ IMAGE....")
            
            img_bytes = generate_image.create_scorecard_image(data)
            
            cand_name = data.get('cand_name', 'Student')
            exam_name = str(data.get('exam_name', 'Exam'))
            safe_exam_name = exam_name.replace("/", "_").replace("\\", "_").replace(":", "-").replace("*", "")
            img_bytes.name = f"{safe_exam_name} {cand_name} SCORECARD.png"
            
            # send_document preserves the filename exactly like PDF and prevents extreme Telegram compression
            bot.send_document(chat_id, document=img_bytes, caption="यह रहा आपके शानदार Scorecard का 🖼️ Image 🏆")
            
            try:
                bot.delete_message(chat_id, prog_msg.message_id)
            except:
                pass
            
        elif call.data == "dl_pdf":
            bot.answer_callback_query(call.id)
            prog_msg = bot.send_message(chat_id, "Generating Your Scorecard 📄 PDF....")
            
            pdf_bytes = generate_pdf.create_scorecard_pdf(data)
            
            # Name the file
            cand_name = data.get('cand_name', 'Student')
            exam_name = str(data.get('exam_name', 'Exam'))
            # Clean for safe filenames
            safe_exam_name = exam_name.replace("/", "_").replace("\\", "_").replace(":", "-").replace("*", "")
            pdf_bytes.name = f"{safe_exam_name} {cand_name} SCORECARD.pdf"
            
            bot.send_document(chat_id, document=pdf_bytes, caption="यह रहा आपके शानदार Scorecard का 📄PDF 🏆")
            
            try:
                bot.delete_message(chat_id, prog_msg.message_id)
            except:
                pass
            
    else:
        bot.answer_callback_query(call.id, "❌ डेटा नहीं मिला। कृपया अपना लिंक फिर से भेजें।", show_alert=True)

if __name__ == '__main__':
    try:
        commands = [
            telebot.types.BotCommand("/start", "Start The Bot"),
            telebot.types.BotCommand("/scorecard", "Start Generating Scorecard PDF & Image")
        ]
        bot.set_my_commands(commands)
    except Exception as e:
        pass
        
    print("Bot शुरू हो गया है...")
    
    # Render.com Free Web Service के लिए डमी वेब सर्वर
    app = Flask(__name__)
    @app.route('/')
    def home():
        return "Scorecard Bot is Running 24/7!"
        
    def run_flask():
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port)
        
    # वेब सर्वर को अलग थ्रेड (Thread) में चलाएं
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
