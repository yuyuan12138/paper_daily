from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from config import QueryConfig
from fetcher import ArXivFetcher
from models import PaperStatus


@pytest.mark.asyncio
async def test_fetch_papers_by_keywords():
    """Test fetching papers by keywords."""
    query_config = QueryConfig(
        keywords=["transformer", "attention"],
        max_results=10,
    )
    fetcher = ArXivFetcher(query_config)

    # Mock arxiv.Client
    with patch("fetcher.arxiv.Client") as mock_client:
        mock_results = [
            type("Result", (), {
                "entry_id": "http://arxiv.org/abs/2401.12345",
                "title": "Test Paper",
                "summary": "Test abstract",
                "published": datetime(2024, 1, 1, 12, 0, 0),
                "categories": ["cs.AI"],
                "authors": [type("Author", (), {"name": "Test Author"})()],
                "pdf_url": "http://arxiv.org/pdf/2401.12345.pdf",
            })()
        ]
        mock_client_instance = MagicMock()
        mock_client_instance.results.return_value = mock_results
        mock_client.return_value = mock_client_instance

        papers = await fetcher.fetch()

    assert len(papers) == 1
    assert papers[0].arxiv_id == "2401.12345"
    assert papers[0].title == "Test Paper"
    assert papers[0].authors == ["Test Author"]
    assert papers[0].status == PaperStatus.discovered


@pytest.mark.asyncio
async def test_fetch_with_categories():
    """Test fetching papers with category filter."""
    query_config = QueryConfig(
        keywords=["machine learning"],
        categories=["cs.AI", "cs.LG"],
        max_results=5,
    )
    fetcher = ArXivFetcher(query_config)

    with patch("fetcher.arxiv.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.results.return_value = []

        papers = await fetcher.fetch()

    assert isinstance(papers, list)


@pytest.mark.asyncio
async def test_fetch_empty_results():
    """Test handling empty search results."""
    query_config = QueryConfig(keywords=["nonexistent"], max_results=10)
    fetcher = ArXivFetcher(query_config)

    with patch("fetcher.arxiv.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.results.return_value = []

        papers = await fetcher.fetch()

    assert papers == []


@pytest.mark.asyncio
async def test_extract_arxiv_id():
    """Test extracting arXiv ID from various URL formats."""
    fetcher = ArXivFetcher(QueryConfig(keywords=["test"]))

    assert fetcher._extract_arxiv_id("http://arxiv.org/abs/2401.12345v1") == "2401.12345"
    assert fetcher._extract_arxiv_id("http://arxiv.org/abs/2401.12345") == "2401.12345"
    assert fetcher._extract_arxiv_id("2401.12345v1") == "2401.12345"
