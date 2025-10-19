#!/usr/bin/env python3
"""
Simple script to run the Levi's reviews scraper
Update the config.py file with your BrightData credentials before running
"""

from levis_reviews_scraper import LevisReviewsScraper
import json
import os

def main():
    print("Levi's Reviews Scraper")
    print("=" * 50)

    # Check if BrightData API key is set
    if not os.getenv('BRIGHTDATA_API_KEY'):
        print("💡 To use BrightData, set your API key:")
        print("   export BRIGHTDATA_API_KEY=your_api_key")
        print()

    # Initialize scraper
    scraper = LevisReviewsScraper()

    print(f"Starting to scrape up to 10 pages...")

    # Start scraping
    reviews = scraper.scrape_reviews(
        max_pages=10,
        output_file='levis_reviews.csv'
    )

    if reviews:
        print(f"\n✅ Scraping completed successfully!")
        print(f"📊 Total reviews found: {len(reviews)}")
        print(f"💾 Data saved to: levis_reviews.csv and levis_reviews.json")

        # Show a sample review
        if len(reviews) > 0:
            print(f"\n📝 Sample review:")
            sample = reviews[0]
            print(f"Title: {sample.get('review_title', 'N/A')}")
            print(f"Rating: {sample.get('rating', 'N/A')}")
            print(f"Text: {sample.get('review_text', 'N/A')[:200]}...")
            print(f"Date: {sample.get('review_date', 'N/A')}")
    else:
        print("❌ No reviews found. The page structure may have changed.")
        print("You may need to update the CSS selectors in the scraper.")

if __name__ == "__main__":
    main()