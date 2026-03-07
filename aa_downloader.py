import requests
import csv
import time
import re
import os
import urllib.parse
import sys

def search_and_download(base_url, input_csv_path, output_csv_filename="downloaded_books.csv", download_folder_name="downloads"):
    # Determine the directory where the script is run from
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Use the current working directory for the download folder, or a subfolder within it
    # if the user runs the script from a different path, it will create a 'downloads' folder there.
    download_dir = os.path.join(os.getcwd(), download_folder_name)

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": base_url # Helps with some site policies
    }

    results = []
    
    # Path for the output CSV, relative to the current working directory
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
        if not file_exists: # Write header only if file is new
            writer.writeheader()

        for book in books:
            title = book['Title']
            author = book['Author']
            query = f"{title} {author}"
            safe_query = urllib.parse.quote_plus(query)
            
            search_url = f"{base_url.rstrip('/')}/search?q={safe_query}"
            print(f"\nSearching for: {query}")
            
            try:
                response = requests.get(search_url, headers=headers, timeout=15)
                if response.status_code != 200:
                    print(f"Search failed (Status {response.status_code})")
                    writer.writerow({'Title': title, 'Author': author, 'Status': f'Search Failed ({response.status_code})', 'Filepath': ''})
                    continue
                
                html = response.text
                
                matches = re.findall(r'href="(/md5/[a-f0-9]+)"', html)
                
                if not matches:
                    print("No direct results found on Anna's Archive.")
                    writer.writerow({'Title': title, 'Author': author, 'Status': 'Not Found', 'Filepath': ''})
                    continue

                target_md5_path = matches[0]
                book_page_url = base_url.rstrip('/') + target_md5_path
                
                print(f"Found match: {book_page_url}")
                
                time.sleep(2) # Delay before visiting book page
                book_page_res = requests.get(book_page_url, headers=headers, timeout=15)
                if book_page_res.status_code != 200:
                    print(f"Could not access book page (Status {book_page_res.status_code}).")
                    writer.writerow({'Title': title, 'Author': author, 'Status': f'Book Page Failed ({book_page_res.status_code})', 'Filepath': ''})
                    continue
                
                page_content = book_page_res.text
                
                # Corrected regex to find download links (prioritizing epub/mobi, but taking any direct link)
                # The issue was an unescaped quote in the regex pattern itself.
                download_links = re.findall(r'(https?://(?:[a-zA-Z0-9$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)', page_content)
                # Also check relative links that might be internal proxies, but less reliable for direct download
                internal_links_raw = re.findall(r'href="(/get/[a-zA-Z0-9/.-]+)"', page_content)
                internal_links = [base_url.rstrip('/') + link for link in internal_links_raw]
                
                all_possible_download_urls = download_links + internal_links
                
                found_download = False
                for dl_url in all_possible_download_urls:
                    # Heuristic check for file extension
                    if not (dl_url.endswith('.epub') or dl_url.endswith('.mobi') or ".epub?" in dl_url or ".mobi?" in dl_url or "format=epub" in dl_url or "format=mobi" in dl_url):
                        continue # Skip if not desired format

                    print(f"Attempting download from: {dl_url}")
                    
                    try:
                        dl_res = requests.get(dl_url, headers=headers, stream=True, timeout=30)
                        if dl_res.status_code == 200:
                            cd = dl_res.headers.get('content-disposition')
                            if cd and 'filename=' in cd:
                                filename = re.findall('filename="?([^"]+)"?', cd)[0]
                            else:
                                # Fallback filename based on URL or generic
                                parsed_url = urllib.parse.urlparse(dl_url)
                                path_segments = parsed_url.path.split('/')
                                filename = path_segments[-1] if path_segments[-1] else f"{title}_{author}.epub"
                                if not (filename.endswith('.epub') or filename.endswith('.mobi')):
                                     filename = f"{title}_{author}.epub" # Default to epub if unsure
                            
                            # Sanitize filename
                            filename = "".join(c for c in filename if c.isalnum() or c in ('.', '_', '-')).strip()
                            # Ensure it doesn't start with a dot from scrubbing, or is empty
                            if filename.startswith('.'): filename = filename[1:]
                            if not filename: filename = f"{title}_{author}.epub"

                            filepath = os.path.join(download_dir, filename)
                            
                            with open(filepath, 'wb') as f_dl:
                                for chunk in dl_res.iter_content(chunk_size=8192):
                                    f_dl.write(chunk)
                            
                            print(f"Successfully downloaded: {filename}")
                            writer.writerow({'Title': title, 'Author': author, 'Status': 'Success', 'Filepath': filepath})
                            found_download = True
                            break # Move to next book once one is downloaded
                        else:
                            print(f"Download attempt from {dl_url} failed (Status {dl_res.status_code})")
                    except requests.exceptions.RequestException as req_err:
                        print(f"Request error during download from {dl_url}: {req_err}")
                    except Exception as e:
                        print(f"An unexpected error during download from {dl_url}: {e}")
                
                if not found_download:
                    print("Failed to find a direct download link for desired format. Manual intervention might be required.")
                    writer.writerow({'Title': title, 'Author': author, 'Status': 'Manual Required', 'Filepath': ''})

            except requests.exceptions.RequestException as req_err:
                print(f"Request error for {title}: {req_err}")
                writer.writerow({'Title': title, 'Author': author, 'Status': f'Error: {str(req_err)}', 'Filepath': ''})
            except Exception as e:
                print(f"An unexpected error occurred for {title}: {e}")
                writer.writerow({'Title': title, 'Author': author, 'Status': f'Error: {str(e)}', 'Filepath': ''})
            
            out_f.flush() # Ensure data is written to disk after each book
            time.sleep(5) # Respectful delay between books

if __name__ == "__main__":
    print("\n--- Anna's Archive Downloader ---")
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
