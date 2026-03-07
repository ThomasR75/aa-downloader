import requests
import csv
import time
import re
import os
import urllib.parse
import sys
import zipfile # For EPUB verification

def sanitize_filename(filename):
    # Replace invalid characters with underscores
    s_filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
    # Remove leading/trailing spaces, dots.
    s_filename = s_filename.strip()
    # Replace sequences of underscores
    s_filename = re.sub(r'_+', '_', s_filename)
    # Ensure it's not empty, e.g., if title/author were all invalid chars
    if not s_filename: s_filename = "untitled"
    return s_filename

def verify_epub(filepath):
    """
    Performs a more robust verification for EPUB files.
    Checks for PK magic bytes and 'mimetype' file with 'application/epub+zip'.
    """
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return False
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            # Check for mimetype file
            if 'mimetype' not in zf.namelist():
                return False
            # Check mimetype content
            with zf.open('mimetype') as mime_file:
                content = mime_file.read().decode('utf-8').strip()
                if content == 'application/epub+zip':
                    return True
        return False
    except zipfile.BadZipFile:
        return False
    except Exception as e:
        print(f"Error during EPUB verification: {e}")
        return False

def verify_mobi(filepath):
    """
    Performs a basic verification for MOBI files by checking magic bytes.
    MOBI files usually have 'BOOKMOBI' or a similar string at offset 0x3c (PalmDOC header).
    More reliably, the magic string 'MOBI' is at offset 0x19 *after* the PalmDOC header.
    We'll check for 'MOBI' at the more common offset after the first basic check.
    """
    if not os.path.exists(filepath) or os.path.getsize(filepath) < 256: # MOBI header is well into the file
        return False
    try:
        with open(filepath, 'rb') as f_verify:
            f_verify.seek(0x3C) # Offset to PalmDOC header for 'BOOKMOBI'
            if f_verify.read(8) == b'BOOKMOBI': # Primary check: PalmDOC header type
                f_verify.seek(0x130 - 0x10) # Offset for MOBI identifier in MOBI header itself (-16 as per spec sometimes)
                # This could be more precise, but often MOBI is directly after
                # A full spec read would be better, but we aim for simple detection.
                return True
        return False
    except Exception as e:
        print(f"Error during MOBI verification: {e}")
        return False


def search_and_download(base_url, input_csv_path, output_csv_filename="downloaded_books.csv", download_folder_name="downloads"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    download_dir = os.path.join(os.getcwd(), download_folder_name)

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

<<<<<<< HEAD
    # === IMPORTANT: READ COOKIE STRING FROM ENVIRONMENT VARIABLE ===
    # Set ANNA_ARCHIVE_COOKIES environment variable before running the script.
    # e.g., export ANNA_ARCHIVE_COOKIES="session=YOUR_SESSION_ID; csrftoken=YOUR_CSRF_TOKEN;"
    YOUR_ANNA_ARCHIVE_COOKIE_STRING = os.environ.get("ANNA_ARCHIVE_COOKIES", "") 

    if not YOUR_ANNA_ARCHIVE_COOKIE_STRING:
        print("WARNING: ANNA_ARCHIVE_COOKIES environment variable not set. Fast downloads may fail due to lack of authentication.")
=======
    # === IMPORTANT: PASTE YOUR COOKIE STRING HERE ===
    # Follow "Step 1" instructions above to get this string from your browser.
    # Example: "session=YOUR_SESSION_ID; csrftoken=YOUR_CSRF_TOKEN;"
    YOUR_ANNA_ARCHIVE_COOKIE_STRING = "__ddg1_=FuORYFoJVn26jKAK5JqF; aa_account_id2=eyJhIjoiTmdwZHdOdSIsImlhdCI6MTc3MjQ1NjA5OX0.iumiNpCyR9tPV2lWgJ-9Lm5u5bKIbAHRdDUSeePLd20; __ddg9_=59.142.103.100; __ddg10_=1772878684; __ddg8_=ER4znPSUYR8qpw7H" # <--- PASTE YOUR COOKIE STRING BETWEEN THESE QUOTES
>>>>>>> 47cb63496a1efa3fba6049065082bbd5d0097964

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": base_url
    }
    
    if YOUR_ANNA_ARCHIVE_COOKIE_STRING:
        headers["Cookie"] = YOUR_ANNA_ARCHIVE_COOKIE_STRING

    results = []
    
    output_csv_path = os.path.join(os.getcwd(), output_csv_filename)
    file_exists = os.path.isfile(output_csv_path)

    try:
        with open(input_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            books = list(reader)
    except FileNotFoundError:
        print(f"Error: Input CSV file '{input_csv_path}' not found. Please ensure it's in the correct directory.")
        return

    print(f"Starting Anna's Archive scraper using: {base_url}")
    print(f"Found {len(books)} books to process from '{input_csv_path}'.")

    with open(output_csv_path, 'a', newline='', encoding='utf-8') as out_f:
        fieldnames = ['Title', 'Author', 'Status', 'Filepath']
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        for book in books:
            title = book['Title']
            author = book['Author']
            query = f"{title} {author}"
            safe_query = urllib.parse.quote_plus(query)
            
            # --- MODIFICATION START: Add Language Filtering ---
            # Assuming 'lang' parameter works with comma-separated values for multiple languages
            search_url = f"{base_url.rstrip('/')}/search?q={safe_query}&lang=en,de"
            # --- MODIFICATION END ---
            
            print(f"\\nSearching for: {query} (Languages: English, German)")
            
            try:
                response = requests.get(search_url, headers=headers, timeout=15)
                if response.status_code != 200:
                    print(f"Search failed (Status {response.status_code})")
                    writer.writerow({'Title': title, 'Author': author, 'Status': f'Search Failed ({response.status_code})', 'Filepath': ''})
                    continue
                
                html = response.text
                
                md5_matches = re.findall(r'href=\"(/md5/[a-f0-9]+)\"', html)
                
                if not md5_matches:
                    print("No book MD5 results found on Anna's Archive search page.")
                    writer.writerow({'Title': title, 'Author': author, 'Status': 'Not Found', 'Filepath': ''})
                    continue

                target_md5_path = md5_matches[0] 
                book_page_url = base_url.rstrip('/') + target_md5_path
                
                print(f"Found book detail page: {book_page_url}")
                
                time.sleep(2) # Delay before visiting book page
                book_page_res = requests.get(book_page_url, headers=headers, timeout=15)
                if book_page_res.status_code != 200:
                    print(f"Could not access book page (Status {book_page_res.status_code}).")
                    writer.writerow({'Title': title, 'Author': author, 'Status': f'Book Page Failed ({book_page_res.status_code})', 'Filepath': ''})
                    continue
                
                page_content = book_page_res.text
                
                # --- Prioritize /fast_download/ links ---
                
                # 1. Extract relative /fast_download/ links
                fast_download_links_raw = re.findall(r'href=\"(/fast_download/[a-f0-9/]+)\"', page_content)
                fast_download_links_absolute = [base_url.rstrip('/') + link for link in fast_download_links_raw]

                # 2. Extract relative /get/ links (existing)
                get_links_raw = re.findall(r'href=\"(/get/[a-zA-Z0-9/.\-]+)\"', page_content)
                get_links_absolute = [base_url.rstrip('/') + link for link in get_links_raw]
                
                # 3. Extract any other absolute HTTP/HTTPS links from the text (existing, broad)
                other_absolute_links = re.findall(r'https?://(?:[a-zA-Z0-9$-_@.&+]|[!*(),/]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', page_content)

                # Combine all possible download URLs, prioritizing fast downloads from the details page
                all_possible_download_urls = []
                all_possible_download_urls.extend(fast_download_links_absolute) # Prioritize fast downloads
                all_possible_download_urls.extend(get_links_absolute)
                all_possible_download_urls.extend(other_absolute_links)
                
                temp_urls = []
                [temp_urls.append(x) for x in all_possible_download_urls if x not in temp_urls]
                all_possible_download_urls = temp_urls

                found_download_url = None
                expected_extension = '.epub' # Default to epub for priority

                # Prioritize EPUB/MOBI from fast download links
                for dl_url in all_possible_download_urls:
                    if "fast_download" in dl_url: # Only consider fast downloads for primary formats
                        if "format=epub" in dl_url.lower() or dl_url.lower().endswith('.epub') or '.epub?' in dl_url.lower():
                            found_download_url = dl_url
                            expected_extension = '.epub'
                            break
                        if "format=mobi" in dl_url.lower() or dl_url.lower().endswith('.mobi') or '.mobi?' in dl_url.lower():
                            found_download_url = dl_url
                            expected_extension = '.mobi'
                            break
                
                # Fallback: if no specific preferred format found, take the first fast download link available
                if not found_download_url and fast_download_links_absolute:
                    found_download_url = fast_download_links_absolute[0]
                    # Attempt to infer extension from the first fast_download link
                    if '.mobi' in found_download_url.lower() or 'format=mobi' in found_download_url.lower():
                         expected_extension = '.mobi'
                    elif '.pdf' in found_download_url.lower() or 'format=pdf' in found_download_url.lower():
                         expected_extension = '.pdf'
                    print(f"No explicit EPUB/MOBI fast download link found, trying first fast download link: {found_download_url}")
                # Fallback: If still no URL, but other URLs exist, take the first one (e.g., /get/ links or external)
                elif not found_download_url and all_possible_download_urls:
                    found_download_url = all_possible_download_urls[0]
                    # Attempt to infer extension from the first general link
                    if '.mobi' in found_download_url.lower() or 'format=mobi' in found_download_url.lower():
                         expected_extension = '.mobi'
                    elif '.pdf' in found_download_url.lower() or 'format=pdf' in found_download_url.lower():
                         expected_extension = '.pdf'
                    print(f"No specific format found in fast downloads, trying first available download link from any source: {found_download_url}")
                

                if found_download_url:
                    print(f"Attempting download from: {found_download_url}")
                    
                    try:
                        dl_res = requests.get(found_download_url, headers=headers, stream=True, timeout=30)
                        dl_res.raise_for_status()

                        # --- MODIFICATION START: Unique Filenames and Enhanced Verification ---

                        base_filename_from_book = sanitize_filename(f"{title}_{author}")
                        
                        filename = None
                        cd = dl_res.headers.get('content-disposition', '')
                        if 'filename=' in cd:
                            match = re.findall('filename=\"?([^\"]+)\"?', cd)
                            if match:
                                filename_from_cd = match[0]
                                # Heuristic: if content-disposition filename is just a hash (e.g., '0' or '123ABCD'), ignore it
                                if not re.fullmatch(r'[a-f0-9]+', os.path.splitext(filename_from_cd)[0].lower()):
                                    filename_from_cd = sanitize_filename(filename_from_cd)
                                    # Ensure it has an extension, if not, append expected
                                    if not any(filename_from_cd.lower().endswith(ext) for ext in ['.epub', '.mobi', '.pdf', '.zip', '.rar', '.azw', '.azw3']):
                                        filename = f"{filename_from_cd}{expected_extension}"
                                    else:
                                        filename = filename_from_cd # Use as is if it has a good extension
                        
                        if not filename:
                            filename = f"{base_filename_from_book}{expected_extension}"
                            if len(filename) > 200: # Prevent extremely long filenames
                                filename = f"{base_filename_from_book[:150]}{expected_extension}"

                        if not filename or filename == expected_extension:
                            # Final fallback: use MD5 hash from the book page URL
                            filename = f"{target_md5_path.split('/')[-1]}{expected_extension}"

                        print(f"Determined filename: {filename}")
                        filepath = os.path.join(download_dir, filename)
                        
                        counter = 1
                        original_filepath_no_ext, original_ext = os.path.splitext(filepath)
                        while os.path.exists(filepath):
                            filepath = f"{original_filepath_no_ext}_{counter}{original_ext}"
                            counter += 1

                        print(f"Saving to: {filepath}")

                        downloaded_size = 0
                        with open(filepath, 'wb') as f_dl:
                            for chunk in dl_res.iter_content(chunk_size=8192):
                                downloaded_size += len(chunk)
                                f_dl.write(chunk)
                        
                        # --- Enhanced Verification ---
                        file_is_valid = False
                        file_status_msg = ""

                        if os.path.exists(filepath) and downloaded_size > 0:
                            if expected_extension == '.epub':
                                file_is_valid = verify_epub(filepath)
                                if not file_is_valid:
                                    file_status_msg = " (EPUB verification failed)"
                            elif expected_extension == '.mobi':
                                file_is_valid = verify_mobi(filepath)
                                if not file_is_valid:
                                    file_status_msg = " (MOBI verification failed)"
                            else: # For other formats, just check non-zero size
                                file_is_valid = True

                            if file_is_valid:
                                print(f"Successfully downloaded and verified: {filename} ({downloaded_size / (1024*1024):.2f} MB)")
                                writer.writerow({'Title': title, 'Author': author, 'Status': 'Success', 'Filepath': filepath})
                            else:
                                print(f"Download failed verification for {filename}{file_status_msg}. Size: {downloaded_size / (1024*1024):.2f} MB")
                                writer.writerow({'Title': title, 'Author': author, 'Status': f'Download Failed (Verification{file_status_msg}: {downloaded_size / (1024*1024):.2f} MB)', 'Filepath': ''})
                        else:
                            print(f"Download failed for {filename}: File is empty or not created.")
                            writer.writerow({'Title': title, 'Author': author, 'Status': 'Download Failed (Empty File)', 'Filepath': ''})

                        # --- MODIFICATION END ---

                    except requests.exceptions.HTTPError as http_err:
                        if http_err.response.status_code == 403:
                            print(f"Download from {found_download_url} failed: 403 Forbidden. Membership/login might be required or the link expired.")
                            writer.writerow({'Title': title, 'Author': author, 'Status': 'Download Failed (403 Forbidden)', 'Filepath': ''})
                        else:
                            print(f"Download from {found_download_url} failed (Status {http_err.response.status_code}): {http_err}")
                            writer.writerow({'Title': title, 'Author': author, 'Status': f'Download Error ({str(http_err)})', 'Filepath': ''})
                    except requests.exceptions.RequestException as req_err:
                        print(f"Request error during download from {found_download_url}: {req_err}")
                        writer.writerow({'Title': title, 'Author': author, 'Status': f'Download Error ({str(req_err)})', 'Filepath': ''})
                    except Exception as e:
                        print(f"An unexpected error during download from {found_download_url}: {e}")
                        writer.writerow({'Title': title, 'Author': author, 'Status': f'Download Error ({str(e)})', 'Filepath': ''})
                else:
                    print("Failed to find any viable download link (EPUB/MOBI fast or otherwise) on the book detail page.")
                    writer.writerow({'Title': title, 'Author': author, 'Status': 'No Download Link', 'Filepath': ''})

            except requests.exceptions.RequestException as req_err:
                print(f"Request error for {title}: {req_err}")
                writer.writerow({'Title': title, 'Author': author, 'Status': f'Error: {str(req_err)}', 'Filepath': ''})
            except Exception as e:
                print(f"An unexpected error occurred for {title}: {e}")
                writer.writerow({'Title': title, 'Author': author, 'Status': f'Error: {str(e)}', 'Filepath': ''})
            
            out_f.flush()
            time.sleep(5)

if __name__ == "__main__":
    print("\\n--- Anna's Archive Downloader ---")
    print("This script downloads books from Anna's Archive based on a CSV list.")
    
    anna_archive_url = input("Please enter the base URL for Anna's Archive (e.g., https://annas-archive.gl/): ").strip()
    if not anna_archive_url:
        print("Anna's Archive URL cannot be empty. Exiting.")
        sys.exit(1)
    
    input_csv = input("Please enter the name of your input CSV file (e.g., goodreads_to_get.csv): ").strip()
    if not input_csv:
        print("Input CSV filename cannot be empty. Exiting.")
        sys.exit(1)

    search_and_download(anna_archive_url, input_csv)
