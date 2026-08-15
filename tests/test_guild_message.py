import pytest
from unittest.mock import patch
from pathlib import Path
from Guildmessage import Guild_message


class TestGuildMessage:
    def test_initialization(self):
        msg = Guild_message("TestUser", "Hello world")
        assert msg.name == "TestUser"
        assert msg.content == "Hello world"

    def test_replace_mentions_role(self):
        msg = Guild_message("User", "Hey @commerce check this")
        msg.replace_mentions()
        assert "<@&" in msg.content and ">" in msg.content
        assert "@commerce" not in msg.content

    def test_replace_mentions_user(self):
        msg = Guild_message("User", "Hey @poi")
        msg.replace_mentions()
        assert "<@" in msg.content and ">" in msg.content
        assert "@poi" not in msg.content

    def test_replace_mentions_multiple(self):
        msg = Guild_message("User", "@commerce @tech @dungeons")
        msg.replace_mentions()
        assert msg.content.count("<@&") == 3
        assert msg.content.count(">") == 3
        assert "@commerce" not in msg.content
        assert "@tech" not in msg.content
        assert "@dungeons" not in msg.content

    def test_cleanmessage_removes_everyone_here(self):
        msg = Guild_message("User", "@everyone @here hello")
        msg.cleanmessage()
        assert "@everyone" not in msg.content
        assert "@here" not in msg.content

    def test_cleanmessage_removes_ampersand(self):
        msg = Guild_message("User", "Hello & world")
        msg.cleanmessage()
        assert "&" not in msg.content

    def test_add_emotes_foxspinn(self, mocker):
        msg = Guild_message("User", "Check :foxspinn: this")
        mock_webhook = mocker.MagicMock()
        msg.add_emotes(mock_webhook)
        mock_webhook.add_embed.assert_called_once()
        embed = mock_webhook.add_embed.call_args[0][0]
        assert embed.title == "spin"
        assert "spinn.webp" in embed.image["url"]

    def test_add_emotes_foxspin(self, mocker):
        msg = Guild_message("User", "Check :foxspin: this")
        mock_webhook = mocker.MagicMock()
        msg.add_emotes(mock_webhook)
        mock_webhook.add_embed.assert_called_once()
        embed = mock_webhook.add_embed.call_args[0][0]
        assert embed.title == "spin"
        assert "spin.webp" in embed.image["url"]

    def test_add_emotes_no_emote(self, mocker):
        msg = Guild_message("User", "No emotes here")
        mock_webhook = mocker.MagicMock()
        msg.add_emotes(mock_webhook)
        mock_webhook.add_embed.assert_not_called()

    def test_case_insensitive_emotes(self, mocker):
        msg = Guild_message("User", ":FOXSPINN: and :FoxSpin:")
        mock_webhook = mocker.MagicMock()
        msg.add_emotes(mock_webhook)
        assert mock_webhook.add_embed.call_count == 2

    def test_replace_mentions_missing_config(self, tmp_path):
        """Test replace_mentions when mentions_config.json is missing."""
        # Reset class variable to force reload
        Guild_message._mentions_config = None
        
        with patch.object(Path, "exists", return_value=False):
            msg = Guild_message("User", "Hey @commerce check this")
            msg.replace_mentions()
            # Should not crash and should not replace mentions (empty config)
            assert msg.content == "Hey @commerce check this"

    def test_replace_mentions_empty_config(self):
        """Test replace_mentions with empty config (file exists but empty)."""
        Guild_message._mentions_config = None
        
        with patch("Guildmessage.Path.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "{}"
            msg = Guild_message("User", "Hey @commerce check this")
            msg.replace_mentions()
            # Empty config means no replacements
            assert msg.content == "Hey @commerce check this"