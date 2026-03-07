import requests
import csv
import time
import re
import os
import urllib.parse

def search_and_download(base_url, input_csv="goodreads_to_get.csv", output_csv="downloaded_books.csv", download_dir="downloads"):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": base_url
    }

    results = []
    
    # Check if output_csv exists to resume or start fresh
    file_exists = os.path.isfile(output_csv)

    try:
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            books = list(reader)
    except FileNotFoundError:
        print(f"Error: {input_csv} not found.")
        return

    print(f"Starting Anna's Archive scraper using: {base_url}")
    print(f"Found {len(books)} books to process.")

    with open(output_csv, 'a', newline='', encoding='utf-8') as out_f:
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
            print(f"\nSearching for: {query}")
            
            try:
                # 1. Search for the book
                response = requests.get(search_url, headers=headers, timeout=15)
                if response.status_code != 200:
                    print(f"Search failed (Status {response.status_code})")
                    continue
                
                html = response.text
                
                # 2. Look for results with epub or mobi
                # Regex to find result links: look for href="/md5/xxxx"
                # And try to find entries that mention epub/mobi nearby
                # This is a heuristic search
                matches = re.findall(r'href="(/md5/[a-f0-9]+)"', html)
                
                if not matches:
                    print("No results found on Anna's Archive.")
                    writer.writerow({'Title': title, 'Author': author, 'Status': 'Not Found', 'Filepath': ''})
                    continue

                # Just take the first match for simplicity in this script
                target_md5_path = matches[0]
                book_page_url = base_url.rstrip('/') + target_md5_path
                
                print(f"Found match: {book_page_url}")
                
                # 3. Visit the book page to find download links
                time.sleep(2) # Delay
                book_page_res = requests.get(book_page_url, headers=headers, timeout=15)
                if book_page_res.status_code != 200:
                    print("Could not access book page.")
                    continue
                
                # Check for format in the page
                page_content = book_page_res.text
                if not re.search(r'epub|mobi', page_content, re.I):
                    print("Desired format (epub/mobi) not explicitly found on the first match page.")
                    # We'll continue anyway and try to find a link
                
                # 4. Attempt to find a "Slow Partner Server" or similar direct-ish link
                # Anna's Archive usually has multiple mirrors. 
                # Scrapers usually have a hard time with the "Slow" links because of wait times.
                # We will look for anything that looks like a direct download link.
                
                # Heuristic: look for <a> tags with text containing "Slow" or "Fast" or "Partner"
                # and grabbing their hrefs.
                download_links = re.findall(r'href="(https?://[^"]+)"[^>]*>.*?Download.*?</a>', page_content, re.I)
                
                # Also check relative links that might be internal proxies
                internal_links = re.findall(r'href="(/get/[^"]+)"', page_content)
                
                found_download = False
                for link in internal_links:
                    download_url = base_url.rstrip('/') + link
                    print(f"Attempting download from: {download_url}")
                    
                    # Try to download
                    dl_res = requests.get(download_url, headers=headers, stream=True, timeout=30)
                    if dl_res.status_code == 200:
                        # Extract filename from header if possible
                        cd = dl_res.headers.get('content-disposition')
                        if cd and 'filename=' in cd:
                            filename = re.findall('filename="?([^"]+)"?', cd)[0]
                        else:
                            # Fallback filename
                            ext = ".epub" if "epub" in page_content.lower() else ".mobi"
                            filename = f"{title}_{author}".replace(" ", "_")[:50] + ext
                        
                        filename = "".join([c for c in filename if c.isalnum() or c in ('.', '_')]).strip()
                        filepath = os.path.join(download_dir, filename)
                        
                        with open(filepath, 'wb') as f_dl:
                            for chunk in dl_res.iter_content(chunk_size=8192):
                                f_dl.write(chunk)
                        
                        print(f"Successfully downloaded: {filename}")
                        writer.writerow({'Title': title, 'Author': author, 'Status': 'Success', 'Filepath': filepath})
                        found_download = True
                        break
                
                if not found_download:
                    print("Failed to find a direct download link. It might require manual captcha or wait-timer.")
                    writer.writerow({'Title': title, 'Author': author, 'Status': 'Manual Required', 'Filepath': ''})

            except Exception as e:
                print(f"Error processing {title}: {e}")
                writer.writerow({'Title': title, 'Author': author, 'Status': f'Error: {str(e)}', 'Filepath': ''})
            
            out_f.flush()
            time.sleep(5) # Respectful delay between books

if __name__ == "__main__":
    # Example usage:
    # python3 aa_downloader.py https://annas-archive.org
    import sys
    if len(sys.argv) > 1:
        site = sys.argv[1]
        search_and_download(site)
    else:
        print("Usage: python3 aa_downloader.py [Anna's Archive URL]")
