# StandaloneScraper

## Description
A multi-page web scraper designed to extract product reviews automatically. Utilizes Selenium (headless Chrome) to navigate pagination and stores each review in a Postgres database. Reviews are then embedded into a Pinecone vector database for similarity analysis and categorization, enabling companies to analyze customer feedback efficiently.

## Skills / Technologies
Python, Selenium, Postgres, Pinecone, API integration, Web Scraping, LLM Sandbox

## Features / Highlights
- Automatically paginates through multiple pages of reviews
- Stores scraped reviews as JSON in Postgres
- Embeds reviews in Pinecone for similarity search and categorization
- Integrates with a dynamic LLM-powered scraping sandbox for flexible website scraping

## Notes
This scraper was integrated into a larger system capable of dynamically generating scraping scripts for any website using LLM sandbox generation.
