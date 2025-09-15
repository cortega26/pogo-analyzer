import json

import pytest

from pogo_analyzer import social


@pytest.fixture()
def tmp_paths(tmp_path):
    session = tmp_path / "session.json"
    leaderboard = tmp_path / "leaderboard.json"
    return session, leaderboard


def sample_result():
    return {
        "title": "Raid Scoreboard Top 3",
        "share_url": "https://example.com/chart.png",
        "top_entries": [
            {"name": "Shadow Giratina", "form": "Origin", "score": 95.2, "tier": "S"},
            {"name": "Mega Gengar", "form": "Mega", "score": 92.1, "tier": "S"},
            {"name": "Shadow Machamp", "form": "Shadow", "score": 90.0, "tier": "A"},
        ],
    }


def test_share_results_twitter_format():
    payload = sample_result()
    message = social.share_results(payload, "twitter")
    assert "Raid Scoreboard Top 3" in message
    assert payload["share_url"] in message
    assert len(message) <= 280


def test_share_results_discord_block():
    payload = sample_result()
    message = social.share_results(payload, "discord")
    assert "```" in message
    assert "Shadow Giratina" in message
    assert payload["share_url"] in message


def test_share_results_reddit_markdown():
    payload = sample_result()
    message = social.share_results(payload, "reddit")
    assert message.startswith("## Raid Scoreboard Top 3")
    assert "[View chart]" in message


def test_share_results_invalid_platform():
    with pytest.raises(ValueError):
        social.share_results(sample_result(), "myspace")


def test_login_and_record_score(tmp_paths):
    session, leaderboard = tmp_paths
    user = social.login("Spark", session_path=session)
    assert user == "Spark"
    entry = social.record_score(
        94.6,
        label="Raid Scoreboard",
        details="Shadow Giratina",
        session_path=session,
        leaderboard_path=leaderboard,
    )
    assert entry["user"] == "Spark"
    assert entry["score"] == pytest.approx(94.6, rel=1e-6)
    data = json.loads(leaderboard.read_text())
    assert data[0]["user"] == "Spark"

    social.login("Candela", session_path=session)
    social.record_score(
        97.2,
        label="Raid Scoreboard",
        details="Mega Gengar",
        session_path=session,
        leaderboard_path=leaderboard,
    )
    board = social.load_leaderboard(leaderboard_path=leaderboard)
    assert board[0]["user"] == "Candela"
    assert board[0]["score"] == pytest.approx(97.2, rel=1e-6)


def test_record_score_requires_login(tmp_paths):
    session, leaderboard = tmp_paths
    with pytest.raises(ValueError):
        social.record_score(88.0, session_path=session, leaderboard_path=leaderboard)
