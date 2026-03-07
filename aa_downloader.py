import requests
import csv
import time
import re
import os
import urllib.parse
import sys

def search_and_download(base_url, input_csv_path, output_csv_filename="downloaded_books.csv", download_folder_name="downloads"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    download_dir = os.path.join(os.getcwd(), download_folder_name)

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # You might need to add specific cookies if your access to fast downloads
    # depends on being logged into Anna's Archive (e.g., from your browser).
    # headers = {
    #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    #     "Referer": base_url,
    #     "Cookie": "your_cookie_string_here" # example: "session=abcdef; csrftoken=12345"
    # }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": base_url
    }


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
            
            search_url = f"{base_url.rstrip('/')}/search?q={safe_query}"
            print(f"\\nSearching for: {query}")
            
            try:
                response = requests.get(search_url, headers=headers, timeout=15)
                if response.status_code != 200:
                    print(f"Search failed (Status {response.status_code})")
                    writer.writerow({'Title': title, 'Author': author, 'Status': f'Search Failed ({response.status_code})', 'Filepath': ''})
                    continue
                
                html = response.text
                
                # Extract MD5 link from search results. This still picks the first one found.
                # A more robust solution would involve proper HTML parsing to associate MD5 link with format on search results.
                # For now, we assume the first MD5 link leads to the correct book's detail page.
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
                
                # --- MODIFICATION START: Prioritize /fast_download/ links ---
                
                # 1. Extract relative /fast_download/ links
                # Updated regex to be more specific to ensure it captures these
                fast_download_links_raw = re.findall(r'href=\"(/fast_download/[a-f0-9/]+)\"', page_content)
                fast_download_links_absolute = [base_url.rstrip('/') + link for link in fast_download_links_raw]

                # 2. Extract relative /get/ links (existing)
                get_links_raw = re.findall(r'href=\"(/get/[a-zA-Z0-9/.\-]+)\"', page_content)
                get_links_absolute = [base_url.rstrip('/') + link for link in get_links_raw]
                
                # 3. Extract any other absolute HTTP/HTTPS links from the text (existing, broad)
                # Keep this as a fallback but note its broader scope
                other_absolute_links = re.findall(r'https?://(?:[a-zA-Z0-9$-_@.&+]|[!*(),/]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', page_content)

                # Combine all possible download URLs, prioritizing fast downloads from the details page
                all_possible_download_urls = []
                all_possible_download_urls.extend(fast_download_links_absolute) # Prioritize fast downloads
                all_possible_download_urls.extend(get_links_absolute)
                all_possible_download_urls.extend(other_absolute_links)
                
                # Remove duplicates while preserving order
                temp_urls = []
                [temp_urls.append(x) for x in all_possible_download_urls if x not in temp_urls]
                all_possible_download_urls = temp_urls

                found_download_url = None
                # Iterate through prioritized URLs to find EPUB/MOBI
                for dl_url in all_possible_download_urls:
                    if "format=epub" in dl_url.lower() or dl_url.lower().endswith('.epub') or '.epub?' in dl_url.lower():
                        found_download_url = dl_url
                        break
                    if "format=mobi" in dl_url.lower() or dl_url.lower().endswith('.mobi') or '.mobi?' in dl_url.lower():
                        found_download_url = dl_url
                        break
                
                # Fallback: if no specific format found but there are fast download links, just take the first fast one
                if not found_download_url and fast_download_links_absolute:
                    found_download_url = fast_download_links_absolute[0]
                    print(f"No explicit EPUB/MOBI fast download link found, trying first fast download link: {found_download_url}")
                # Fallback: If still no URL, but other URLs exist, take the first one
                elif not found_download_url and all_possible_download_urls:
                    found_download_url = all_possible_download_urls[0]
                    print(f"No specific format found in fast downloads, trying first available download link from any source: {found_download_url}")


                if found_download_url:
                    print(f"Attempting download from: {found_download_url}")
                    
                    try:
                        dl_res = requests.get(found_download_url, headers=headers, stream=True, timeout=30)
                        dl_res.raise_for_status() # Check for HTTP errors

                        cd = dl_res.headers.get('content-disposition', '')
                        if 'filename=' in cd:
                            filename = re.findall('filename=\"?([^\"]+)\"?', cd)[0]
                        else:
                            parsed_url = urllib.parse.urlparse(found_download_url)
                            path_segments = parsed_url.path.split('/')
                            filename = path_segments[-1] if path_segments[-1] else f"{title}_{author}.epub"
                            # Ensure filename has a valid extension if not found
                            if not (filename.lower().endswith(('.epub', '.mobi', '.pdf', '.zip', '.rar', '.azw', '.azw3'))):
                                # Heuristic: derive extension from the URL if possible
                                if any(ext in found_download_url.lower() for ext in ['epub', 'mobi', 'pdf', 'zip', 'rar', 'azw', 'azw3']):
                                    filename = f"{filename}.{next((ext for ext in ['epub', 'mobi', 'pdf', 'zip', 'rar', 'azw', 'azw3'] if ext in found_download_url.lower()), 'epub')}"
                                else:
                                     filename = f"{filename}.epub" # Default fallback
                        
                        # Sanitize filename (existing logic)
                        filename = "".join(c for c in filename if c.isalnum() or c in ('.', '_', '-')).strip()
                        if filename.startswith('.'): filename = filename[1:]
                        if not filename: filename = f"{title}_{author}.epub" # Final fallback

                        filepath = os.path.join(download_dir, filename)
                        
                        with open(filepath, 'wb') as f_dl:
                            for chunk in dl_res.iter_content(chunk_size=8192):
                                f_dl.write(chunk)
                        
                        print(f"Successfully downloaded: {filename}")
                        writer.writerow({'Title': title, 'Author': author, 'Status': 'Success', 'Filepath': filepath})
                    except requests.exceptions.HTTPError as http_err:
                        # Specifically catch HTTP 403 Forbidden for membership requirement
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