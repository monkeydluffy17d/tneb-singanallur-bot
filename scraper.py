import os
import requests
from bs4 import BeautifulSoup
import ddddocr

# Initialize the free AI Captcha Solver
ocr = ddddocr.DdddOcr(show_ad=False)

# Configuration from GitHub Secrets
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Keywords to match Singanallur and its surrounding feeding stations
TARGET_KEYWORDS = ["singanallur", "kallimadai", "ondipudur", "trichy road"]

BASE_URL = "https://www.tnebltd.gov.in/outages/viewshutdown.xhtml"

def scrape_tneb():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    })
    
    try:
        # Step 1: Initial load to establish cookies and extract hidden variables
        print("Connecting to TNEB Portal...")
        response = session.get(BASE_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Pull the required dynamic view state token
        view_state = soup.find('input', {'name': 'javax.faces.ViewState'})['value']
        
        # Step 2: Grab the dynamic Captcha Image URL
        # Java frameworks typically generate an image component with 'capimg' or within the ID structure
        captcha_img = soup.find('img', id=lambda x: x and 'capimg' in x.lower()) or soup.find('img', src=lambda x: x and 'captcha' in x.lower())
        
        if not captcha_img:
            print("Could not find the captcha image tag. Trying fallback submission...")
            return
            
        # Ensures a forward slash exists between the domain and the image path
        img_path = captcha_img['src']
        if not img_path.startswith('/'):
            img_path = '/' + img_path
            captcha_url = "https://www.tnebltd.gov.in" + img_path
        
        # Download the dynamic captcha image bytes
        img_bytes = session.get(captcha_url).content
        
        # Use AI to read the text in the captcha image
        solved_captcha = ocr.classification(img_bytes).strip()
        print(f"AI Decoded Captcha: {solved_captcha}")
        
        # Step 3: Build the exact payload you extracted from the network logs
        payload = {
            "j_idt5": "j_idt5",
            "j_idt5:appcat_focus": "",
            "j_idt5:appcat_input": "0435", # Kept your tested circle code 
            "j_idt5:cap": solved_captcha,  # AI-generated answer goes here
            "j_idt5:submit3": "",
            "javax.faces.ViewState": view_state
        }
        
        # Step 4: Submit form to unlock the data table
        post_response = session.post(BASE_URL, data=payload)
        final_soup = BeautifulSoup(post_response.text, 'html.parser')
        
        # Step 5: Parse the resulting table for Singanallur zones
        table_rows = final_soup.find_all('tr')
        alerts_found = 0
        
        for row in table_rows:
            cols = [ele.text.strip() for ele in row.find_all('td')]
            if cols and len(cols) >= 6:
                full_row_text = " ".join(cols).lower()
                
                # Verify if any local zone keyword hits
                if any(keyword in full_row_text for keyword in TARGET_KEYWORDS):
                    alert_message = (
                        f"⚠️ **TNEB SHUTDOWN NOTICE: SINGANALLUR**\n\n"
                        f"📅 **Date:** {cols[0]}\n"
                        f"🏢 **Substation:** {cols[2]}\n"
                        f"📍 **Affected Areas:** {cols[3]}\n"
                        f"⏰ **Timing:** {cols[5]} to {cols[6]}\n"
                        f"🔧 **Type:** {cols[4]}"
                    )
                    send_telegram(alert_message)
                    alerts_found += 1
                    
        if alerts_found == 0:
            print("Scan complete: No upcoming power cuts posted for your grid.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

def send_telegram(message):
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(telegram_url, json=payload)

if __name__ == "__main__":
    scrape_tneb()
