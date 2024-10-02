import requests
import os
import shutil
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import urllib.parse
import argparse
import concurrent.futures
from urllib.parse import urljoin

# Load environment variables from .env file
load_dotenv()

# Replace the course IDs with the ones you want to download
COURSE_ID_NAME_MAPPING = {
    14220: "EE-556",
    13734: "CS-450",
    15989: "HUM-401"
}

COURSE_NAME_ID_MAPPING = {v: k for k, v in COURSE_ID_NAME_MAPPING.items()}

MOODLE_URL = "https://moodle.epfl.ch"
TEQUILA_LOGIN = f"{MOODLE_URL}/login/index.php"
TEQUILA_LOGIN_POST = "https://tequila.epfl.ch/cgi-bin/tequila/login"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_tequila_login_session(username, password):
    session = requests.session()
    login_page = session.get(TEQUILA_LOGIN)

    if login_page.status_code != 200:
        raise ValueError(f"Failed to access login page. Status code: {login_page.status_code}")

    soup = BeautifulSoup(login_page.content, 'html.parser')
    request_key = soup.find('input', {'name': 'requestkey'})['value']
    login_payload = {
        'username': username,
        'password': password,
        'requestkey': request_key
    }

    response = session.post(TEQUILA_LOGIN_POST, verify=True, data=login_payload)

    soup = BeautifulSoup(response.text, 'html.parser')

    error = soup.find('font', color='red', size='+1')
    if error:
        print(error)

    if response.status_code != 200 or "Login failed" in response.text:
        print("Login failed. Please check your credentials.")
        return None
    print("Login successful!")

    return session

def save_file(response, filepath, path, filename):
    if response.status_code == 200:
        with open(filepath, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded {filename} to {path}")
    else:
        print(f"Failed to download {filename}. Status code: {response.status_code}")

def download_file(session, href, course_folder):
    try:
        if "https://moodle.epfl.ch/mod/resource/view.php?id=" in href:
            # Download the file in the course folder
            file_response = session.get(f"{href}&redirect=1", stream=True)
            content_disposition = file_response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')
            else:
                # Fallback to URL parsing
                filename = os.path.basename(urllib.parse.urlparse(href).path)
            filepath = os.path.join(course_folder, filename)
            save_file(file_response, filepath, course_folder, filename)

        elif "https://moodle.epfl.ch/mod/folder/view.php?id=" in href:
            # Download the folder as a zip file, extract it and remove the zip file
            folder_id = href.split("id=")[1]
            download_url = f"https://moodle.epfl.ch/mod/folder/download_folder.php?id={folder_id}"
            file_response = session.get(download_url)
            content_disposition = file_response.headers.get('Content-Disposition', '')
            if "filename*=UTF-8''" in content_disposition:
                filename_encoded = content_disposition.split("filename*=UTF-8''")[-1]
                filename = urllib.parse.unquote(filename_encoded)
            else:
                # Fallback to URL parsing
                filename = f"folder_{folder_id}.zip"

            foldername = filename.split(".zip")[0].split("-")[0]  # Remove date metadata
            folder_path = os.path.join(course_folder, foldername)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
            os.makedirs(folder_path, exist_ok=True)

            filepath = os.path.join(folder_path, filename)
            save_file(file_response, filepath, folder_path, filename)
            if file_response.status_code == 200:
                try:
                    shutil.unpack_archive(filepath, folder_path)
                    os.remove(filepath)
                    print(f"Extracted and removed archive {filename} in {folder_path}")
                except shutil.ReadError:
                    print(f"Failed to extract {filename}. It may not be a zip file.")
    except Exception as e:
        print(f"Error downloading {href}: {e}")

def download_moodle_files(course_id, moodle_url, session, max_workers=5):
    course_page_url = f"{moodle_url}/course/view.php?id={course_id}"
    
    # Access the course page
    course_page = session.get(course_page_url)
    
    if course_page.status_code != 200:
        print(f"Failed to access course page {course_id}. Status code: {course_page.status_code}")
        return
    
    # Create a folder for the course
    course_folder = course_folder = os.path.join(SCRIPT_DIR, str(COURSE_ID_NAME_MAPPING[course_id]))
    if os.path.exists(course_folder):
        shutil.rmtree(course_folder)
    os.makedirs(course_folder, exist_ok=True)

    soup = BeautifulSoup(course_page.content, 'html.parser')
    file_links = soup.find_all('a', href=True)

    # Prepare a list of absolute URLs
    absolute_links = [urljoin(moodle_url, link['href']) for link in file_links]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(download_file, session, href, course_folder)
            for href in absolute_links
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                print(f"Generated an exception: {exc}")

def main():
    parser = argparse.ArgumentParser(description='Download files from Moodle.')
    parser.add_argument('course_names', nargs='*', help='The names of the courses to download files for')
    parser.add_argument('--max-workers', type=int, default=5, help='Maximum number of concurrent download threads')
    args = parser.parse_args()

    moodle_url = "https://moodle.epfl.ch"
    username = os.getenv('MOODLE_USERNAME')
    password = os.getenv('MOODLE_PASSWORD')

    if not username or not password:
        print("Please set MOODLE_USERNAME and MOODLE_PASSWORD in your environment variables.")
        return

    session = get_tequila_login_session(username, password)

    if not session:
        print("Exiting due to failed login.")
        return

    if args.course_names:
        for course_name in args.course_names:
            course_id = COURSE_NAME_ID_MAPPING.get(course_name.upper())
            if course_id:
                print(f"Downloading files for course: {course_name} (ID: {course_id})")
                download_moodle_files(course_id, moodle_url, session, max_workers=args.max_workers)
            else:
                print(f"Course {course_name} not found in the mapping")
    else:
        for course_id in COURSE_ID_NAME_MAPPING:
            course_name = COURSE_ID_NAME_MAPPING[course_id]
            print(f"Downloading files for course: {course_name} (ID: {course_id})")
            download_moodle_files(course_id, moodle_url, session, max_workers=args.max_workers)
    
    print("All downloads completed!")

if __name__ == "__main__":
    main()
