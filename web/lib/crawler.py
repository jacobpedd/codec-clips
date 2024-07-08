import feedparser
import requests
from bs4 import BeautifulSoup
from django.conf import settings


def crawl_itunes_podcast_links(itunes_genre_url: str) -> list:
    response = requests.get(itunes_genre_url, timeout=5)
    response.raise_for_status()
    content = BeautifulSoup(response.content, "html.parser")
    podcast_links = content.find("div", class_="grid3-column")
    if podcast_links:
        return [link.get("href") for link in podcast_links.findAll("a")]
    else:
        return []


def crawl_itunes_ratings(itunes_podcast_link: str) -> None:
    # Fetch the podcast page
    response = requests.get(
        "https://scraping.narf.ai/api/v1/",
        params={
            "api_key": settings.SCRAPING_FISH_API_KEY,
            "url": itunes_podcast_link,
        },
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    # Extract total ratings
    rating_element = soup.select_one("figcaption.we-rating-count")
    if rating_element:
        rating_text = rating_element.text.strip()
        rating_parts = rating_text.split("•")
        if len(rating_parts) == 2:
            ratings_text = rating_parts[1].strip().split()[0]
            # Parse ratings text, handling 'K' and 'M' suffixes
            if "M" in ratings_text:
                total_ratings = int(float(ratings_text.replace("M", "")) * 1_000_000)
            elif "K" in ratings_text:
                total_ratings = int(float(ratings_text.replace("K", "")) * 1_000)
            else:
                total_ratings = int(ratings_text.replace(",", ""))
            return total_ratings
    return 0


def itunes_podcast_lookup(podcast_id: str) -> tuple:
    # Extract other podcast information as before
    lookup_url = f"https://itunes.apple.com/lookup?id={podcast_id}&entity=podcast"
    lookup_response = requests.get(lookup_url, timeout=5)
    lookup_response.raise_for_status()
    podcast_data = lookup_response.json()

    if podcast_data["resultCount"] == 0:
        raise ValueError(f"No podcast data found for ID {podcast_id}")

    podcast = podcast_data["results"][0]
    feed_url = podcast["feedUrl"]

    return feed_url, podcast["trackName"]


def crawl_rss_feed(rss_feed_url: str) -> list:
    # Crawl the RSS feed
    rss_feed = feedparser.parse(rss_feed_url)

    feed_data = {
        "title": rss_feed.feed.title,
        "description": rss_feed.feed.description,
    }

    # Get the first entry
    entry = rss_feed.entries[0]

    entry_data = {
        "title": entry.get("title", "Untitled"),
        "summary": entry.get("summary", ""),
        "audio_url": entry.get("enclosures", [{}])[0].get("href", None),
        "published_parsed": entry.published_parsed,
        "itunes_duration": entry.get("itunes_duration", "0:00"),
    }

    return feed_data, entry_data
