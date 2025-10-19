import requests
import json
import time
import os
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

class LevisReviewsScraperMultiPage:
    def __init__(self, use_brightdata=False):
        """
        Initialize the scraper with optional BrightData proxy configuration

        Args:
            use_brightdata (bool): Whether to use BrightData proxy
        """
        self.base_url = "https://levis.pissedconsumer.com"
        self.start_url = "https://levis.pissedconsumer.com/review.html"
        self.use_brightdata = use_brightdata
        self.driver = None

        # Set up Chrome options
        self.chrome_options = Options()
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)

        # Add user agent
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

        # Set up BrightData proxy if requested
        if use_brightdata:
            api_key = os.getenv('BRIGHTDATA_API_KEY')
            if api_key:
                # BrightData proxy configuration for Selenium
                # Format: username-session-<random>:password@endpoint
                proxy_endpoint = "brd.superproxy.io:22225"  # Default BrightData endpoint
                proxy_user = f"brd-customer-{api_key}-session-{int(time.time())}"
                proxy_pass = api_key

                proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_endpoint}"

                # Configure Chrome with BrightData proxy
                self.chrome_options.add_argument(f'--proxy-server={proxy_url}')
                print(f"✅ BrightData proxy configured: {proxy_endpoint}")
            else:
                print("No BrightData API key found")

    def setup_driver(self):
        """Initialize the Chrome WebDriver"""
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("Chrome driver initialized successfully")
            return True
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            print("Make sure ChromeDriver is installed and in your PATH")
            return False

    def parse_review(self, review_element):
        """
        Parse individual review data from BeautifulSoup review element
        """
        try:
            review_data = {}

            # Extract review text from the specific container
            review_text_elem = review_element.find('div', class_='f-component-text review_text_container review-track')
            if review_text_elem:
                # Get all paragraph text within the container
                paragraphs = review_text_elem.find_all('p')
                if paragraphs:
                    review_text = ' '.join([p.get_text(strip=True) for p in paragraphs])
                else:
                    review_text = review_text_elem.get_text(strip=True)
                review_data['review_text'] = review_text
            else:
                review_data['review_text'] = "N/A"

            # Extract rating and date from the mb24px-desktop row
            date_rating_elem = review_element.find('div', class_='row-inline mb24px-desktop')
            if date_rating_elem:
                date_rating_text = date_rating_elem.get_text(strip=True)

                # Extract date (format like "Aug 01, 2025")
                import re
                date_match = re.search(r'([A-Za-z]{3} \d{1,2}, \d{4})', date_rating_text)
                review_data['review_date'] = date_match.group(1) if date_match else "N/A"

                # Extract rating - the text is like "Aug 01, 20252.0Rating Details..."
                # So we look for year followed by rating
                rating_match = re.search(r'(\d{4})(\d+\.\d+)', date_rating_text)
                if rating_match:
                    review_data['rating'] = float(rating_match.group(2))
                else:
                    # Fallback: look for any decimal number that could be a rating (1.0-5.0)
                    rating_numbers = re.findall(r'\d+\.\d+', date_rating_text)
                    for num in rating_numbers:
                        try:
                            rating_val = float(num)
                            # Ratings should be between 1.0 and 5.0
                            if 1.0 <= rating_val <= 5.0:
                                review_data['rating'] = rating_val
                                break
                        except ValueError:
                            continue
                    else:
                        review_data['rating'] = "N/A"
            else:
                review_data['review_date'] = "N/A"
                review_data['rating'] = "N/A"

            # Extract reviewer name from avatar-name span
            name_elem = review_element.find('span', class_='avatar-name')
            if name_elem:
                reviewer_name = name_elem.get_text(strip=True)
            else:
                # Fallback: look for other name patterns
                name_elem = review_element.find('span', class_=lambda x: x and 'author' in x if x else False)
                reviewer_name = name_elem.get_text(strip=True) if name_elem else "Anonymous"

            review_data['reviewer_name'] = reviewer_name

            # Extract title from f-component-info-header if available
            title_elem = review_element.find('div', class_='f-component-info-header')
            if title_elem:
                review_data['review_title'] = title_elem.get_text(strip=True)[:100]  # Limit title length
            else:
                review_data['review_title'] = "N/A"

            # Extract user recommendation if available
            recommendation_elem = review_element.find('p', class_='word-break-break-word')
            if recommendation_elem:
                rec_text = recommendation_elem.get_text(strip=True)
                if 'recommendation' in rec_text.lower():
                    review_data['user_recommendation'] = rec_text
                else:
                    review_data['user_recommendation'] = "N/A"
            else:
                review_data['user_recommendation'] = "N/A"

            return review_data

        except Exception as e:
            print(f"Error parsing review: {e}")
            return None

    def find_reviews_on_page(self, soup):
        """
        Find all review elements on the page using the correct selectors for PissedConsumer
        """
        # Look for divs with class 'review-item' which contain the actual reviews
        review_items = soup.find_all('div', class_='review-item')

        # Filter out any empty or invalid review items
        valid_reviews = []
        for review in review_items:
            # Check if it has a review text container
            text_container = review.find('div', class_='f-component-text review_text_container review-track')
            if text_container and text_container.get_text(strip=True):
                valid_reviews.append(review)

        print(f"Found {len(valid_reviews)} valid review items on the page")
        return valid_reviews

    def click_next_page(self):
        """
        Click the next page button and return True if successful, False if no more pages
        """
        try:
            print("Looking for pagination elements...")

            # Wait a moment for page to fully load
            time.sleep(1)

            # First, scroll down a bit to make sure pagination is visible
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.8);")
            time.sleep(1)

            next_button = None
            current_url = self.driver.current_url

            # Strategy 1: Look for specific pagination containers
            pagination_containers = [
                ".pagination",
                ".paging",
                ".page-navigation",
                "[class*='pagination']",
                "[class*='paging']",
                "[class*='page-nav']"
            ]

            for container_selector in pagination_containers:
                try:
                    container = self.driver.find_element(By.CSS_SELECTOR, container_selector)
                    links = container.find_elements(By.TAG_NAME, "a")

                    print(f"Found pagination container with {len(links)} links")

                    for link in links:
                        text = link.get_attribute('textContent').strip().lower()
                        href = link.get_attribute('href') or ""

                        # Skip unwanted links
                        if any(skip in href.lower() for skip in ['customer-service', 'contact', 'help', 'about']):
                            continue

                        # Look for next indicators
                        if text in ['next', '>', '›', '»', 'more'] or 'next' in text:
                            print(f"Found next button in container: '{text}' -> {href[:60]}...")
                            next_button = link
                            break

                    if next_button:
                        break

                except NoSuchElementException:
                    continue

            # Strategy 2: Look for numbered pagination and find the next number
            if not next_button:
                print("Trying numbered pagination strategy...")

                # Get current page number from URL
                import re
                current_page_match = re.search(r'RT-P\.html\?page=(\d+)', current_url)
                if current_page_match:
                    current_page = int(current_page_match.group(1))
                    next_page = current_page + 1
                    print(f"Current page: {current_page}, looking for page: {next_page}")
                else:
                    # If on first page, look for page 2
                    next_page = 2
                    print(f"On first page, looking for page: {next_page}")

                # Look for link with next page number
                page_links = self.driver.find_elements(By.XPATH, f"//a[text()='{next_page}']")
                for link in page_links:
                    href = link.get_attribute('href') or ""
                    if 'levis.pissedconsumer.com' in href:
                        print(f"Found numbered next page link: {next_page}")
                        next_button = link
                        break

            # Strategy 3: Look for any "next" text or arrows
            if not next_button:
                print("Trying broader next button search...")

                xpath_selectors = [
                    "//a[contains(translate(text(), 'NEXT', 'next'), 'next')]",
                    "//a[text()='>']",
                    "//a[text()='›']",
                    "//a[text()='»']",
                    "//a[contains(@class, 'next')]",
                    "//a[contains(@title, 'next')]",
                    "//a[contains(@title, 'Next')]"
                ]

                for xpath in xpath_selectors:
                    try:
                        buttons = self.driver.find_elements(By.XPATH, xpath)
                        for button in buttons:
                            href = button.get_attribute('href') or ""
                            # Make sure it's a Levi's page and not an external link
                            if ('levis.pissedconsumer.com' in href and
                                not any(skip in href.lower() for skip in ['customer-service', 'contact', 'help'])):
                                print(f"Found next button via XPath: {xpath}")
                                next_button = button
                                break
                        if next_button:
                            break
                    except NoSuchElementException:
                        continue

            # Strategy 4: Look for "Load More" or similar buttons
            if not next_button:
                print("Looking for load more buttons...")

                load_more_selectors = [
                    "//button[contains(text(), 'Load')]",
                    "//button[contains(text(), 'More')]",
                    "//a[contains(text(), 'Load')]",
                    "//a[contains(text(), 'More')]",
                    "//*[contains(@class, 'load-more')]",
                    "//*[contains(@class, 'show-more')]"
                ]

                for selector in load_more_selectors:
                    try:
                        button = self.driver.find_element(By.XPATH, selector)
                        if button.is_displayed() and button.is_enabled():
                            print(f"Found load more button: {selector}")
                            next_button = button
                            break
                    except NoSuchElementException:
                        continue

            if not next_button:
                print("No next page button found after all strategies")

                # Debug: Show all visible links
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                visible_links = [link for link in all_links if link.is_displayed()]
                print(f"Total visible links on page: {len(visible_links)}")

                for i, link in enumerate(visible_links[:15]):  # Show first 15
                    text = link.get_attribute('textContent').strip()[:40]
                    href = link.get_attribute('href') or ""
                    print(f"  {i+1}. '{text}' -> {href[:60]}...")

                return False

            # Check if button is disabled
            button_class = next_button.get_attribute('class') or ""
            if 'disabled' in button_class.lower():
                print("Next button is disabled - reached last page")
                return False

            # Scroll to button and make sure it's visible
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(1)

            print(f"Attempting to click: '{next_button.get_attribute('textContent').strip()}'")

            # Try JavaScript click first (more reliable)
            try:
                self.driver.execute_script("arguments[0].click();", next_button)
                print("Used JavaScript click")
            except Exception as js_error:
                print(f"JavaScript click failed: {js_error}, trying regular click")
                next_button.click()

            # Wait for navigation with longer timeout
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda driver: driver.current_url != current_url
                )
                print(f"✅ Successfully navigated to: {self.driver.current_url}")
                time.sleep(2)  # Wait for content to load
                return True

            except TimeoutException:
                print("❌ Page didn't change after click - might be end of results")
                return False

        except Exception as e:
            print(f"❌ Error during pagination: {e}")
            return False

    def scrape_all_reviews(self, max_pages=10, output_file='levis_reviews_all_pages.csv'):
        """
        Scrape reviews from multiple pages using Selenium
        """
        if not self.setup_driver():
            return []

        all_reviews = []
        page_count = 0

        try:
            print(f"Starting to scrape reviews from: {self.start_url}")
            self.driver.get(self.start_url)

            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "review-item"))
            )

            while page_count < max_pages:
                print(f"\n=== Scraping page {page_count + 1} ===")
                print(f"Current URL: {self.driver.current_url}")

                # Get page source and parse with BeautifulSoup
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')

                # Find reviews on current page
                review_elements = self.find_reviews_on_page(soup)

                # Parse each review
                page_reviews = []
                for review_elem in review_elements:
                    review_data = self.parse_review(review_elem)
                    if review_data and review_data['review_text'] != "N/A":
                        review_data['page_number'] = page_count + 1
                        review_data['source_url'] = self.driver.current_url
                        page_reviews.append(review_data)

                print(f"Successfully parsed {len(page_reviews)} reviews from page {page_count + 1}")
                all_reviews.extend(page_reviews)

                # Try to go to next page
                if not self.click_next_page():
                    print("No more pages or failed to navigate to next page")
                    break

                page_count += 1

        except Exception as e:
            print(f"Error during scraping: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                print("Browser closed")

        print(f"\n=== SCRAPING COMPLETE ===")
        print(f"Total reviews scraped: {len(all_reviews)}")
        print(f"Total pages scraped: {page_count}")

        # Save to files
        if all_reviews:
            self.save_to_csv(all_reviews, output_file)
            self.save_to_json(all_reviews, output_file.replace('.csv', '.json'))

        return all_reviews

    def save_to_csv(self, reviews, filename):
        """
        Save reviews to CSV file
        """
        if not reviews:
            print("No reviews to save")
            return

        fieldnames = ['review_title', 'review_text', 'rating', 'reviewer_name', 'review_date', 'user_recommendation', 'page_number', 'source_url']

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for review in reviews:
                writer.writerow(review)

        print(f"Reviews saved to {filename}")

    def save_to_json(self, reviews, filename):
        """
        Save reviews to JSON file
        """
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(reviews, jsonfile, indent=2, ensure_ascii=False)

        print(f"Reviews saved to {filename}")


def main():
    print("Levi's Reviews Multi-Page Scraper (with Selenium)")
    print("=" * 60)

    # Check if BrightData API key is set
    if not os.getenv('BRIGHTDATA_API_KEY'):
        print("💡 To use BrightData, set your API key:")
        print("   export BRIGHTDATA_API_KEY=your_api_key")
        print()

    # Initialize scraper
    use_brightdata = bool(os.getenv('BRIGHTDATA_API_KEY'))
    scraper = LevisReviewsScraperMultiPage(use_brightdata=use_brightdata)

    # Start scraping
    max_pages = int(input("How many pages to scrape? (default 5): ") or "5")

    print(f"\nStarting to scrape up to {max_pages} pages...")
    print("This will use Chrome browser automation to navigate through pages.")

    reviews = scraper.scrape_all_reviews(
        max_pages=max_pages,
        output_file='levis_reviews_all_pages.csv'
    )

    if reviews:
        print(f"\n✅ Scraping completed successfully!")
        print(f"📊 Total reviews found: {len(reviews)}")
        print(f"💾 Data saved to: levis_reviews_all_pages.csv and levis_reviews_all_pages.json")

        # Show a sample review
        if len(reviews) > 0:
            print(f"\n📝 Sample review:")
            sample = reviews[0]
            print(f"Title: {sample.get('review_title', 'N/A')}")
            print(f"Rating: {sample.get('rating', 'N/A')}")
            print(f"Text: {sample.get('review_text', 'N/A')[:200]}...")
            print(f"Date: {sample.get('review_date', 'N/A')}")
            print(f"Reviewer: {sample.get('reviewer_name', 'N/A')}")
    else:
        print("❌ No reviews found.")


if __name__ == "__main__":
    main()