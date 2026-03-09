import requests
import csv
import time
import re

def scrape_goodreads_shelf_expanded(user_id, shelf_name="to-get", output_file="goodreads_to_get.csv", max_books=1001):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    all_books = []
    page = 1
    
    print(f"Starting expanded scrape for shelf: {shelf_name} (Goal: {max_books} books)")
    
    while len(all_books) < max_books:
        # RSS feed supports pagination via &page=X
        rss_url = f"https://www.goodreads.com/review/list_rss/{user_id}?shelf={shelf_name}&page={page}"
        print(f"Fetching page {page}...")
        
        try:
            response = requests.get(rss_url, headers=headers)
            if response.status_code != 200:
                print(f"Error fetching RSS page {page}: Status {response.status_code}")
                break
                
            xml_content = response.text
            items = re.findall(r'<item>(.*?)</item>', xml_content, re.DOTALL)
            
            if not items:
                print("No more items found.")
                break
                
            for item in items:
                if len(all_books) >= max_books:
                    break
                    
                title_match = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
                author_match = re.search(r'<author_name>(.*?)</author_name>', item, re.DOTALL)
                
                if title_match:
                    t = title_match.group(1).replace('<![CDATA[', '').replace(']]>', '').strip()
                    a = author_match.group(1).replace('<![CDATA[', '').replace(']]>', '').strip() if author_match else "Unknown"
                    
                    all_books.append({
                        "Title": t,
                        "Author": a
                    })
            
            print(f"Total books collected so far: {len(all_books)}")
            
            # If we got fewer than 100 items (standard Goodreads RSS page size), we're likely at the end
            if len(items) < 20: # RSS usually gives 30-100, but checking for a low number to be safe
                break
                
            page += 1
            time.sleep(1.5) # Modest delay to avoid rate limiting
            
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    if all_books:
        keys = ["Title", "Author"]
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_books)
        print(f"Successfully saved {len(all_books)} books to {output_file}")
    else:
        print("No books found.")

if __name__ == "__main__":
    import sys
    print("\n--- Goodreads Shelf Scraper ---")
    print("This script scrapes books from a Goodreads shelf and saves them to a CSV file.")

    user_id = input("\nEnter your Goodreads user ID (found in your profile URL, e.g., 25519145): ").strip()
    if not user_id:
        print("Goodreads user ID cannot be empty. Exiting.")
        sys.exit(1)

    shelf = input("Enter the shelf name to scrape (default: to-get): ").strip() or "to-get"
    output_file = input("Enter the output CSV filename (default: goodreads_to_get.csv): ").strip() or "goodreads_to_get.csv"

    scrape_goodreads_shelf_expanded(user_id, shelf_name=shelf, output_file=output_file, max_books=1001)
