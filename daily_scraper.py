from datetime import datetime
from typing import Tuple
import os
import hashlib
import difflib
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup


def get_url_hash(url: str) -> str:
    """Generate a unique hash for the URL to use as filename"""
    return hashlib.md5(url.encode()).hexdigest()


def setup_selenium():
    """Set up and return a configured Chrome WebDriver using webdriver-manager"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Remove this line if you want to see the browser
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # Automatically download and use the correct chromedriver
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def fetch_page(url: str) -> str | None:
    print(f"🌐 Fetching page content from {url}")
    driver = None
    try:
        driver = setup_selenium()
        driver.get(url)

        # Wait for the page to load with a fixed delay
        print("Waiting 5 seconds for page to load and JavaScript to execute...")
        time.sleep(5)

        # Get the page source after JavaScript execution
        html_content = driver.page_source
        print("Page fetched successfully with Selenium")
        return html_content

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def save_html(url: str, html_content: str) -> None:
    """Save HTML content to a file"""
    if not html_content:
        return

    # Create html_storage directory if it doesn't exist
    os.makedirs('html_storage', exist_ok=True)

    # Generate filename from URL
    filename = f"html_storage/{get_url_hash(url)}.html"

    # Save the HTML content
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Saved HTML for {url} to {filename}")


def extract_text(html: str) -> str:
    """Extract user-visible text content from HTML with structured line breaks"""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove non-visible elements
    for tag in soup(['script', 'style']):
        tag.decompose()

    # Get text with line breaks between blocks
    text = soup.get_text(separator='\n')  # This is the key change

    # Normalize whitespace and remove empty lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return '\n'.join(lines)


def get_text_diff(old_text: str, new_text: str) -> str:
    """Generate a simple unified diff between two cleaned HTML text contents"""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile='old.html',
        tofile='new.html',
        lineterm='',
        n=3  # Show 3 lines of context
    )

    return '\n'.join(diff)


def has_html_changed(url: str, new_html: str) -> Tuple[bool, str]:
    """Check if the HTML content has changed from the stored version and return diff if changed"""
    filename = f"html_storage/{get_url_hash(url)}.html"

    # If file doesn't exist, it's considered changed
    if not os.path.exists(filename):
        return True, "No previous version found"

    # Read stored HTML
    with open(filename, 'r', encoding='utf-8') as f:
        stored_html = f.read()

    # Extract text from both versions
    stored_text = extract_text(stored_html)
    current_text = extract_text(new_html)

    # Compare extracted text
    if stored_text != current_text:
        if stored_text.strip() or current_text.strip():
            diff = get_text_diff(stored_text, current_text)
            return True, diff

    return False, ""


def append_to_markdown(results: list[tuple[str, bool, str]]) -> None:
    """Add change status for multiple URLs to the top of the markdown log file with a single timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Create new content to add at the top
    new_content = f"\n## {timestamp}\n\n"

    # Check if any URLs have changes
    has_any_changes = any(has_changes for _, has_changes, _ in results)

    if has_any_changes:
        # Only show URLs that have changes
        for url, has_changes, diff in results:
            if has_changes:
                new_content += f"### [{url}]({url})\n\n"  # Use markdown link format
                new_content += "**Changes detected!**\n\n"
                new_content += "```diff\n"
                new_content += diff
                new_content += "\n```\n"
                new_content += "\n---\n"
    else:
        # If no changes detected for any URL, show a single message
        new_content += "**No changes for today**\n\n---\n"

    # Read existing content (if any)
    try:
        with open('changes.md', 'r', encoding='utf-8') as f:
            existing_content = f.read()
    except FileNotFoundError:
        existing_content = ""

    # Write new content followed by existing content
    with open('changes.md', 'w', encoding='utf-8') as f:
        f.write(new_content + existing_content)


def process_urls(urls: list[str]) -> None:
    """Process URLs and store their HTML content"""
    results = []

    for url in urls:
        print(f"\nProcessing URL: {url}")
        if html_content := fetch_page(url):
            has_changed, diff = has_html_changed(url, html_content)
            if has_changed:
                print(f"Changes detected for {url}")
                save_html(url, html_content)
            else:
                print(f"No changes detected for {url}")

            results.append((url, has_changed, diff))
        else:
            print(f"Failed to fetch content from {url}")
            results.append((url, False, "Failed to fetch content"))

    # Append all results with a single timestamp
    append_to_markdown(results)


def main():
    urls = [
        "https://optiver.com/working-at-optiver/career-opportunities/?_gl=1*x7c8ib*_up*MQ..*_ga*MTA5OTMxMjk3Mi4xNzQ1NjQxMDk2*_ga_YMLN3CLJVE*MTc0NTY0MTA5NS4xLjEuMTc0NTY0MTA5OC4wLjAuMA..&numberposts=10&paged=1&office=singapore&level=internship",
        "https://stripe.com/jobs/search?office_locations=Asia+Pacific--Singapore&tags=University",
        "https://www.google.com/about/careers/applications/jobs/results/?src=Online%2FGoogle%20Website%2FByF&utm_source=Online%20&utm_medium=careers_site%20&utm_campaign=ByF&distance=50&employment_type=INTERN&company=Fitbit&company=Google&location=Singapore",
        "https://www.janestreet.com/join-jane-street/open-roles/?type=internship&location=new-york"
    ]

    process_urls(urls)
    print("\nHTML storage and comparison completed. Check changes.md for the log.")

if __name__ == "__main__":
    main()