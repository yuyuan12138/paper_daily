from datetime import datetime
from pathlib import Path
import pytest
import json
from src.models import Paper, PaperStatus
from src.state_manager import StateManager


def test_state_manager_init(tmp_path):
    """Test StateManager initialization."""
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)
    assert manager.state_file == state_file
    assert manager.state == {"last_run": None, "papers": {}}


def test_get_paper_status_not_found():
    """Test getting status for non-existent paper."""
    manager = StateManager(Path("/tmp/test_state.json"))
    status = manager.get_paper_status("2401.99999")
    assert status is None


def test_update_paper_status():
    """Test updating paper status."""
    manager = StateManager(Path("/tmp/test_state.json"))
    manager.update_paper_status(
        arxiv_id="2401.12345",
        status=PaperStatus.downloaded,
        pdf_path=Path("/data/pdfs/2401.12345.pdf"),
    )
    paper_state = manager.get_paper_status("2401.12345")
    assert paper_state["status"] == "downloaded"
    assert paper_state["pdf_path"] == "/data/pdfs/2401.12345.pdf"
    assert paper_state["error"] is None


def test_update_paper_with_error():
    """Test updating paper status with error."""
    manager = StateManager(Path("/tmp/test_state.json"))
    manager.update_paper_status(
        arxiv_id="2401.12345",
        status=PaperStatus.failed,
        error="Download failed: 404",
    )
    paper_state = manager.get_paper_status("2401.12345")
    assert paper_state["status"] == "failed"
    assert paper_state["error"] == "Download failed: 404"


def test_is_paper_processed():
    """Test checking if paper is already processed."""
    manager = StateManager(Path("/tmp/test_state.json"))
    assert manager.is_paper_processed("2401.12345") is False

    manager.update_paper_status("2401.12345", PaperStatus.summarized)
    assert manager.is_paper_processed("2401.12345") is True


def test_save_and_load_state(tmp_path):
    """Test saving and loading state from file."""
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)

    manager.update_last_run()
    manager.update_paper_status("2401.12345", PaperStatus.downloaded)
    manager.save()

    # Load state in new manager
    manager2 = StateManager(state_file)
    manager2.load()
    assert manager2.state["last_run"] is not None
    assert manager2.get_paper_status("2401.12345")["status"] == "downloaded"


def test_get_papers_by_status():
    """Test getting papers filtered by status."""
    manager = StateManager(Path("/tmp/test_state.json"))
    manager.update_paper_status("2401.11111", PaperStatus.downloaded)
    manager.update_paper_status("2401.22222", PaperStatus.failed)
    manager.update_paper_status("2401.33333", PaperStatus.summarized)

    failed = manager.get_papers_by_status(PaperStatus.failed)
    assert failed == ["2401.22222"]

    downloaded = manager.get_papers_by_status(PaperStatus.downloaded)
    assert set(downloaded) == {"2401.11111"}
