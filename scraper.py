import os
import requests
from bs4 import BeautifulSoup
import ddddocr
import base64
from urllib.parse import urljoin

# Initialize the free AI Captcha Solver
ocr = ddddocr.DdddOcr(show_ad=False)

# Configuration from GitHub Secrets
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Keywords to match Singanallur and its surrounding feeding stations
TARGET_KEYWORDS = ["uppilipalayam", "singanallur", "g.v.residency"]
BASE_URL = "https://www.tnebltd.gov.in/outages/viewshutdown.xhtml"

def scrape_tneb():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    })
    
    try:
        print("Connecting to TNEB Portal...")
        response = session.get(BASE_URL, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        view_state_tag = soup.find('input', {'name': 'javax.faces.ViewState'})
        if not view_state_tag:
            print("Error: Could not find javax.faces.ViewState.")
            return
        view_state = view_state_tag['value']
        
        captcha_img = (
            soup.find('img', id=lambda x: x and 'capimg' in x.lower()) or 
            soup.find('img', src=lambda x: x and 'captcha' in x.lower()) or
            soup.find('img', id=lambda x: x and 'j_idt' in x and 'cap' in x.lower())
        )
        
        if not captcha_img:
            print("Could not find the captcha image tag.")
            return
            
        img_path = captcha_img['src']
        captcha_url = urljoin(BASE_URL, img_path)
        print(f"Downloading captcha from: {captcha_url}")
        
        img_response = session.get(captcha_url, headers={"Referer": BASE_URL}, timeout=10)
        img_bytes = img_response.content

        # Use AI to read the text in the captcha image
        solved_captcha = ocr.classification(img_bytes).strip()
        print(f"AI Decoded Captcha: {solved_captcha}")
        
        payload = {
            "j_idt5": "j_idt5",
            "j_idt5:appcat_focus": "",
            "j_idt5:appcat_input": "0435", 
            "j_idt5:cap": solved_captcha,  
            "j_idt5:submit3": "",
            "javax.faces.ViewState": view_state
        }
        
        print("Submitting verification payload...")
        post_response = session.post(BASE_URL, data=payload, timeout=15)
        final_soup = BeautifulSoup(post_response.text, 'html.parser')
        
        table_rows = final_soup.find_all('tr')
        alerts_found = 0
        
        # Hyper-focused keywords to match your doorstep
        TARGET_KEYWORDS = ["uppilipalayam", "singanallur", "g.v.residency"]
        
        for row in table_rows:
            cols = [ele.text.strip() for ele in row.find_all('td')]
            
            # Match the exact 8-column layout found in image_6cc746.png
            if cols and len(cols) >= 8:
                location_text = cols[4].lower()
                
                # Check if your specific neighborhood is targeted
                if any(keyword in location_text for keyword in TARGET_KEYWORDS):
                    date_val = cols[0]
                    substation_val = cols[2]
                    feeder_val = cols[3]
                    areas_val = cols[4]
                    work_details = cols[5]
                    from_time = cols[6]
                    to_time = cols[7]

                    # Custom brutal warning message with exact time windows
                    alert_message = (
                        f"⚡ **🚨 FIX YOUR SHT AND PREPARE!** ⚡\n\n"
                        f"TNEB is coming for your grid, Paari! Don't you dare get caught with flat batteries. 🔌\n\n"
                        f"📅 **Date:** `{date_val}`\n"
                        f"🏢 **Substation / Feeder:** `{substation_val} ({feeder_val})`\n"
                        f"⏰ **Timing:** `{from_time} AM to {to_time} PM`\n"
                        f"🔧 **Work Type:** `{work_details}`\n\n"
                        f"📍 **Hit Zone Areas:** {areas_val}\n"
                    )
                    send_telegram(alert_message)
                    alerts_found += 1
                    
        if alerts_found == 0:
            hype_message = (
                f"✨ **HELL YEAH, PAARI!** ✨\n\n"
                f"The Singanallur grid refreshed like it just had the best f*cking night of its life! "
                f"No power cuts detected for your doorstep. Now go break some hearts! 🏍️💨"
            )
            send_telegram(hype_message)
            print("Scan complete: No outages. Hype message sent!")
            
    except Exception as e:
        print(f"An error occurred: {e}")
def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: Telegram credentials are missing from environment variables.")
        return
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(telegram_url, json=payload, timeout=10)
        print("Alert message sent successfully to Telegram!")
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")

if __name__ == "__main__":
    scrape_tneb()
