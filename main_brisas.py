from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import gspread
import os
import time
import pytz
import schedule
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv

extracted_data = [["Venue", "Date", "Time", "Booked Courts"]]
# Load environment variables from .env file
load_dotenv()

# Replace with your email from the .env file
USER_EMAIL = os.getenv('USER_EMAIL_BRISAS')
USER_PASSWORD = os.getenv('USER_PASSWORD_BRISAS')


# Load Google Sheets credentials from environment variable
google_credentials_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
if not google_credentials_path:
    raise ValueError("The Google Sheets credentials path is not set in the environment variables")

# Set the scope and credentials for Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(google_credentials_path, scope)
client = gspread.authorize(creds)

# Open the Google Spreadsheet by title
sheet_url = "https://docs.google.com/spreadsheets/d/1ImUhNYctOUVSLtdktvzsnd8zkpzVDedPYhSix7CRg8c/edit?usp=sharing"
spreadsheet = client.open_by_url(sheet_url)

def delete_file(file_path):
    # Check if file exists
    if os.path.exists(file_path):
        # Delete the file
        os.remove(file_path)
        print(f"File {file_path} has been deleted.")
    else:
        print(f"The file {file_path} does not exist.")

def extract():    
    try:
        current_date = datetime.now()
        date_index = current_date.strftime("%Y-%m-%d")
        am_pm = current_date.strftime("%p")
        # Toggle between 'AM' and 'PM'
        hour_index = int(current_date.strftime("%H"))
        hour_with_am_pm = 'PM' if am_pm == 'PM' else 'AM'
        hour_value = hour_index - 12 if am_pm == 'PM' else hour_index
        
        if hour_index == 10:
            hour_value = 10
            hour_with_am_pm = 'PM'
        if hour_index == 11:
            hour_value = hour_index - 12
            hour_with_am_pm = 'PM'
            
        folder_name = f"extracted-brisas-{date_index}"
        
        # Define the file name
        if hour_index < 9:
            file_name = f"Padel Haus {date_index}-(0{str(hour_index)}~0{str(hour_index + 1)}).txt"
        elif hour_index == 9:
            file_name = f"Padel Haus {date_index}-(0{str(hour_index)}~{str(hour_index + 1)}).txt"
        else:
            file_name = f"Padel Haus {date_index}-({str(hour_index)}~{str(hour_index + 1)}).txt"

        # Define the full path (folder + file name)
        full_path = os.path.join(folder_name, file_name)
        delete_file(full_path)
        
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Ensure GUI is off
        chrome_options.add_argument("--window-size=1920,1080")  # Set a window size
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")


        # Initialize the Chrome driver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

        # Open the website
        driver.get("https://book.brisas.us/users/sign_in")
        time.sleep(5)    
        padel_url = 'https://book.brisas.us/book/brisas'

        # Wait for the email field to be loaded
        wait = WebDriverWait(driver, 2)

        email_field = wait.until(EC.visibility_of_element_located((By.ID, "user_email")))
        email_field.send_keys(USER_EMAIL)

        # Wait for the password field to be loaded
        password_field = wait.until(EC.visibility_of_element_located((By.ID, "user_password")))
        password_field.send_keys(USER_PASSWORD)

        # Wait for the login button to be clickable and click it
        login_button = wait.until(EC.element_to_be_clickable((By.NAME, "commit")))
        login_button.click()
        time.sleep(1)        
            
        
        driver.get(padel_url)
        time.sleep(2)
                
        try:
            day_buttons = driver.find_element(By.CLASS_NAME, "flex_mobile_button_container").find_elements(By.TAG_NAME, "button")           
        except Exception as e:
                print(f"An unexpected error occurred5: {e}")  
                time.sleep(2) 
                try:
                    day_buttons = driver.find_element(By.CLASS_NAME, "flex_mobile_button_container").find_elements(By.TAG_NAME, "button")  
                except Exception as e:
                    print(f"An unexpected error occurred6: {e}")  
                    time.sleep(2)  
        date = date_index
        try:
            driver.find_element(By.CLASS_NAME, "flex_mobile_button_container").find_elements(By.TAG_NAME, "button")[0].click()
        except Exception as e:
            print(f"An unexpected error occurred4: {e}")
            time.sleep(2)
            delete_file(full_path)
            driver.quit()
            return extract()
        time.sleep(1)
                
        soup_hour_buttons = BeautifulSoup(driver.page_source, features="html.parser").find(class_='hours_list').find_all('button')
        for index, hour_button in enumerate(soup_hour_buttons):
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            if f"-{str(hour_value + 2)}{hour_with_am_pm}" in soup.find(class_='hours_list').find_all('button')[index].text.upper():
                if index < len(soup.find(class_='hours_list').find_all('button')):
                    class_name = soup.find(class_='hours_list').find_all('button')[index].get('class')
                else:
                    continue
                if "red" in class_name:
                    venue = 'Brisas'
                    hour = soup.find(class_='hours_list').find_all('button')[index].text.replace(' +', '')
                    record = [venue, date, hour, 3]
                    print(record)                
                    extracted_data.append(record)
                    # Define the folder name where you want to save the file
                    folder_name = f"extracted-brisas-{date_index}"

                    # Create the folder if it doesn't exist
                    if not os.path.exists(folder_name):
                        os.makedirs(folder_name)

                    # Define the file name
                    if hour_index < 9:
                        file_name = f"Padel Haus {date_index}-(0{str(hour_index)}~0{str(hour_index + 1)}).txt"
                    elif hour_index == 9:
                        file_name = f"Padel Haus {date_index}-(0{str(hour_index)}~{str(hour_index + 1)}).txt"
                    else:
                        file_name = f"Padel Haus {date_index}-({str(hour_index)}~{str(hour_index + 1)}).txt"

                    # Define the full path (folder + file name)
                    full_path = os.path.join(folder_name, file_name)

                    # Now, write to the file at the specified path
                    with open(full_path, 'a', encoding='utf-8') as file:
                        file.write(', '.join(map(str, record)) + '\n')
                else:
                    try:
                        driver.find_element(By.CLASS_NAME, 'hours_list').find_elements(By.TAG_NAME, "button")[index].click()
                    except TimeoutException as e:
                        time.sleep(1)   
                        try:
                            driver.find_element(By.CLASS_NAME, "flex_mobile_button_container").find_elements(By.TAG_NAME, "button")[0].click()
                            time.sleep(1)   
                            driver.find_element(By.CLASS_NAME, 'hours_list').find_elements(By.TAG_NAME, "button")[index].click()
                        except TimeoutException as e:
                            time.sleep(1)   
                        except Exception as e:
                            print(f"An unexpected error occurred: {e}")  
                            time.sleep(1)    
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")  
                        time.sleep(1)         
                    time.sleep(1)
                    soup = BeautifulSoup(driver.page_source, features="html.parser")
                    courts = soup.find_all(class_='over_flex_mobile_button_container')[1].find_all('button')
                    venue = 'Brisas'
                    hour = soup.find(class_='hours_list').find_all('button')[index].text.replace(' +', '')            
                    booked_count = 3 - len(courts)
                    record = [venue, date, hour, booked_count]
                    extracted_data.append(record)
                    print(record)
                    # Define the folder name where you want to save the file
                    folder_name = f"extracted-brisas-{date_index}"

                    # Create the folder if it doesn't exist
                    if not os.path.exists(folder_name):
                        os.makedirs(folder_name)

                    # Define the file name
                    if hour_index <=8:
                        file_name = f"Padel Haus {date_index}-(0{str(hour_index)}~0{str(hour_index + 1)}).txt"
                    elif hour_index ==9:
                        file_name = f"Padel Haus {date_index}-(0{str(hour_index)}~{str(hour_index + 1)}).txt"
                    else:
                        file_name = f"Padel Haus {date_index}-({str(hour_index)}~{str(hour_index + 1)}).txt"

                    # Define the full path (folder + file name)
                    full_path = os.path.join(folder_name, file_name)

                    # Now, write to the file at the specified path
                    with open(full_path, 'a', encoding='utf-8') as file:
                        file.write(', '.join(map(str, record)) + '\n')
                    
                    if driver.find_element(By.CLASS_NAME, "flex_mobile_button_container").find_elements(By.TAG_NAME, "button")[0]:
                        driver.find_element(By.CLASS_NAME, "flex_mobile_button_container").find_elements(By.TAG_NAME, "button")[0].click() 
                    time.sleep(1)  
            
        time.sleep(1)  # Wait for 2 seconds before clicking the next button

        # Close the browser
        driver.quit()
        save_sheet_to_me()
    except Exception as e:
        print(f"An unexpected error occurred4: {e}")
        time.sleep(2)
        delete_file(full_path)
        driver.quit()
        return extract()
        time.sleep(1)
def save_sheet_to_me():
    try:
        # Get the worksheet by name
        worksheet_name = "Sheet1"
        worksheet = spreadsheet.get_worksheet(2)

        # If the worksheet is not found, create a new one
        if worksheet is None:
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="100", cols="20")

        # Define the header names
        header_names = ["Venue", "Date", "Time", "Booked Courts"]
        # Check if the worksheet is empty (no header row) and add headers if needed
        existing_headers = worksheet.row_values(1)
        if not existing_headers:
            worksheet.insert_row(header_names, index=1)
        
        current_date = datetime.now()
        date_index = current_date.strftime("%Y-%m-%d")
        hour_index = int(current_date.strftime("%H"))
        # Define the folder name where you want to save the file
        folder_name = f"extracted-brisas-{date_index}"

        # Create the folder if it doesn't exist
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        # Define the file name
        if hour_index <=8:
            file_name = f"Padel Haus {date_index}-(0{str(hour_index)}~0{str(hour_index + 1)}).txt"
        elif hour_index ==9:
            file_name = f"Padel Haus {date_index}-(0{str(hour_index)}~{str(hour_index + 1)}).txt"
        else:
            file_name = f"Padel Haus {date_index}-({str(hour_index)}~{str(hour_index + 1)}).txt"

        # Define the full path (folder + file name)
        full_path = os.path.join(folder_name, file_name) 

        # Check if the file is a text file
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as file:
                # Read each line in the file
                for line in file:
                    # Split the line by ', ' and strip any whitespace or newline characters
                    record = [element.strip() for element in line.split(', ')]
                    worksheet.append_row(record)
                    time.sleep(1)
            
        print('Data has been written to the spreadsheet.')
    except Exception as e:
        print(f"An unexpected error occurred: {e}")  
        time.sleep(1)
        return save_sheet_to_me()    

schedule.every().day.at("06:50").do(extract)


schedule.every().day.at("07:50").do(extract)

schedule.every().day.at("08:50").do(extract)


schedule.every().day.at("09:50").do(extract)


schedule.every().day.at("10:50").do(extract)


schedule.every().day.at("11:50").do(extract)


schedule.every().day.at("12:50").do(extract)


schedule.every().day.at("13:50").do(extract)


schedule.every().day.at("14:50").do(extract)


schedule.every().day.at("15:50").do(extract)


schedule.every().day.at("16:50").do(extract)


schedule.every().day.at("17:50").do(extract)


schedule.every().day.at("18:50").do(extract)


schedule.every().day.at("19:50").do(extract)


schedule.every().day.at("20:50").do(extract)


while True:
    schedule.run_pending()
    time.sleep(1)