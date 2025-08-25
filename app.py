import time
from bs4 import BeautifulSoup
import cloudscraper
from ebooklib import epub

# Config
start_url = ""
novel_title = ""
delay_seconds = 2  
retry_delay_seconds = 5  
max_retries = 5  

# Create scraper
scraper = cloudscraper.create_scraper()

# EPUB setup
book = epub.EpubBook()
book.set_title(novel_title)
book.set_language("en")
book.add_author("Unknown")  # You can set the author if known

chapter_number = 1
chapters = []
current_url = start_url

while current_url:
    retries = 0
    while retries < max_retries:
        print(f"Scraping Chapter {chapter_number} (Attempt {retries+1}) -> {current_url}")
        html = scraper.get(current_url).text
        soup = BeautifulSoup(html, "html.parser")

        # Get content
        content_div = soup.find("div", id="chr-content")
        if not content_div:
            print(f"Could not find chapter content. Retrying in {retry_delay_seconds} seconds...")
            retries += 1
            time.sleep(retry_delay_seconds)
            continue  # retry same chapter

        # Remove unwanted ads/scripts
        for tag in content_div.find_all(["script", "div"], {"id": lambda x: x and x.startswith("pf-")}):
            tag.decompose()

        chapter_text = content_div.get_text(separator="\n", strip=True)

        # Create EPUB chapter
        c = epub.EpubHtml(title=f"Chapter {chapter_number}", file_name=f"chap_{chapter_number}.xhtml", lang="en")
        c.content = f"<h1>Chapter {chapter_number}</h1><p>{chapter_text.replace('\n', '<br/>')}</p>"
        book.add_item(c)
        chapters.append(c)

        # Find next chapter link
        next_link_tag = soup.find("a", id="next_chap")
        if next_link_tag and next_link_tag.get("href"):
            next_href = next_link_tag.get("href").strip()

            # Check for invalid URLs like 'null'
            if not next_href or next_href.lower() == "null":
                print("Next chapter link is invalid. Ending scrape.")
                break

            # Avoid double-prefix issue
            if next_href.startswith("http://") or next_href.startswith("https://"):
                current_url = next_href
            elif next_href.startswith("/"):
                current_url = "https://novelbin.com" + next_href
            else:
                current_url = "https://novelbin.com/" + next_href

            chapter_number += 1
            time.sleep(delay_seconds)
        else:
            print("No more chapters found.")
            current_url = None
        break  # Exit retry loop if successful
    else:
        print(f"Failed to fetch Chapter {chapter_number} after {max_retries} retries. Stopping.")
        break

# Finalize EPUB
book.toc = tuple(chapters)
book.spine = ["nav"] + chapters
book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())

# Save file
file_name = f"{novel_title}.epub"
epub.write_epub(file_name, book, {})
print(f"EPUB saved as '{file_name}'")
