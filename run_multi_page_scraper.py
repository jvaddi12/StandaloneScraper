#!/usr/bin/env python3
"""
Simple script to run the multi-page Levi's reviews scraper
This version uses Selenium to automatically navigate through multiple pages
"""

from levis_reviews_scraper_multi_page import LevisReviewsScraperMultiPage
import os

def main():
    print("🚀 Levi's Reviews Multi-Page Scraper")
    print("=" * 50)
    print("This scraper uses Chrome browser automation to navigate through multiple pages")
    print()

    # Check requirements
    print("📋 Checking requirements...")

    # Check if ChromeDriver is available
    try:
        import selenium
        print("✅ Selenium is installed")
    except ImportError:
        print("❌ Selenium not found. Please install: pip install selenium")
        return

    # Check if BrightData API key is set
    if os.getenv('BRIGHTDATA_API_KEY'):
        print("✅ BrightData API key found")
        use_brightdata = True
    else:
        print("💡 BrightData API key not set (optional)")
        print("   To use: export BRIGHTDATA_API_KEY=your_api_key")
        use_brightdata = False

    print()

    # Get user preferences
    try:
        max_pages = int(input("How many pages to scrape? (default 5): ") or "5")
    except ValueError:
        max_pages = 5

    print(f"\n🎯 Starting scraper with settings:")
    print(f"   • Max pages: {max_pages}")
    print(f"   • BrightData: {'Enabled' if use_brightdata else 'Disabled'}")
    print(f"   • Output files: levis_reviews_all_pages.csv & .json")
    print()

    # Initialize and run scraper
    scraper = LevisReviewsScraperMultiPage(use_brightdata=use_brightdata)

    try:
        reviews = scraper.scrape_all_reviews(
            max_pages=max_pages,
            output_file='levis_reviews_all_pages.csv'
        )

        if reviews:
            print(f"\n🎉 Success! Scraped {len(reviews)} reviews")
            print(f"📁 Files saved:")
            print(f"   • levis_reviews_all_pages.csv")
            print(f"   • levis_reviews_all_pages.json")

            # Show stats
            pages_scraped = len(set(r['page_number'] for r in reviews))
            print(f"\n📊 Stats:")
            print(f"   • Total reviews: {len(reviews)}")
            print(f"   • Pages scraped: {pages_scraped}")
            print(f"   • Avg reviews per page: {len(reviews) / pages_scraped:.1f}")

        else:
            print("❌ No reviews found")

    except KeyboardInterrupt:
        print("\n⏹️  Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()