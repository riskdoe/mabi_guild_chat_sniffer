import pytest
from unittest.mock import MagicMock, patch, AsyncMock, call
import queue
import threading
import asyncio
from message_normalizer import (
    normalize_discord_message,
    extract_discord_emotes,
    clean_username,
    normalize_message_chunks,
)
from to_client_worker import (
    type_message,
    ToClientWorker,
)
from discord_client import (
    ToClientConfig,
    DiscordClient,
    ToClientBotThread,
)
import discord


class TestNormalizeDiscordMessage:
    def test_removes_invisible_chars(self):
        msg = "hello​world"
        result = normalize_discord_message(msg)
        assert "​" not in result
        assert result == "helloworld"

    def test_replaces_custom_emotes(self):
        msg = "Hello <:smile:123456> world"
        result = normalize_discord_message(msg)
        assert ":smile:" in result

    def test_removes_unicode_emojis(self):
        msg = "Hello 😀 world"
        result = normalize_discord_message(msg)
        assert "😀" not in result
        assert "*" in result

    def test_removes_mentions(self):
        msg = "Hello <@123456> and <@&789012>"
        result = normalize_discord_message(msg)
        assert "[mention]" in result

    def test_removes_channel_mentions(self):
        msg = "Check <#123456>"
        result = normalize_discord_message(msg)
        assert "[channel]" in result

    def test_removes_everyone_here(self):
        msg = "@everyone @here hello"
        result = normalize_discord_message(msg)
        assert "@everyone" not in result
        assert "@here" not in result

    def test_preserves_spacing(self):
        msg = "hello    world"
        result = normalize_discord_message(msg)
        assert result == "hello world"

    def test_truncates_long_messages(self):
        msg = "a" * 100
        result = normalize_discord_message(msg, max_length=50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_custom_emote_replacement_format(self):
        msg = "<a:animated:987654>"
        result = normalize_discord_message(msg, emote_replacement="[{name}]")
        assert result == "[animated]"

    def test_custom_emoji_replacement(self):
        msg = "😀"
        result = normalize_discord_message(msg, emoji_replacement="[emoji]")
        assert result == "[emoji]"

    def test_keep_markdown_when_false(self):
        msg = "**bold** *italic*"
        result = normalize_discord_message(msg, remove_markdown=False)
        assert "**" in result
        assert "*" in result

    def test_remove_markdown_when_true(self):
        msg = "**bold** *italic*"
        result = normalize_discord_message(msg, remove_markdown=True)
        assert "**" not in result
        assert "*" not in result


class TestExtractDiscordEmotes:
    def test_extracts_single_emote(self):
        msg = "Hello <:smile:123456> world"
        result = extract_discord_emotes(msg)
        assert result == [("smile", "123456")]

    def test_extracts_animated_emote(self):
        msg = "Hello <a:dance:789012> world"
        result = extract_discord_emotes(msg)
        assert result == [("dance", "789012")]

    def test_extracts_multiple_emotes(self):
        msg = "<:a:1> <:b:2> <:c:3>"
        result = extract_discord_emotes(msg)
        assert result == [("a", "1"), ("b", "2"), ("c", "3")]

    def test_returns_empty_list(self):
        msg = "No emotes here"
        result = extract_discord_emotes(msg)
        assert result == []


class TestCleanUsername:
    def test_removes_emojis(self):
        name = "User😀Name"
        result = clean_username(name)
        assert "😀" not in result

    def test_removes_invisible_chars(self):
        name = "User​Name"
        result = clean_username(name)
        assert "​" not in result

    def test_removes_markdown(self):
        name = "**User**"
        result = clean_username(name)
        assert "*" not in result

    def test_truncates_long_names(self):
        name = "a" * 20
        result = clean_username(name, max_length=10)
        assert len(result) == 10

    def test_strips_whitespace(self):
        name = "  User Name  "
        result = clean_username(name)
        assert result == "User Name"


class TestNormalizeMessageChunks:
    def test_single_chunk_under_limit(self):
        msg = "Short message"
        result = normalize_message_chunks(msg, chunk_size=50)
        assert result == ["Short message"]

    def test_splits_by_words(self):
        msg = "This is a longer message that should be split"
        result = normalize_message_chunks(msg, chunk_size=20)
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= 20

    def test_splits_long_word(self):
        msg = "supercalifragilisticexpialidocious"
        result = normalize_message_chunks(msg, chunk_size=10)
        assert len(result) > 1

    def test_respects_kwargs(self):
        msg = "Hello <:smile:123> world"
        result = normalize_message_chunks(msg, chunk_size=50, emote_replacement="[{name}]")
        assert "[smile]" in result[0]


class TestTypeMessage:
    """Test the type_message function."""

    @patch("to_client_worker.os.system")
    @patch("to_client_worker.subprocess.run")
    @patch("to_client_worker.time.sleep")
    def test_type_message_calls_xdotool(self, mock_sleep, mock_run, mock_system):
        type_message("test message", 0.01)
        
        # Check xdotool search and activate
        mock_system.assert_any_call('xdotool search --name "Mabinogi" windowactivate')
        # Check key presses
        assert mock_system.call_count >= 3  # activate, Return, Return, Return
        # Check subprocess.run for typing
        mock_run.assert_called_once_with(["xdotool", "type", "test message"], check=False)
        # Check sleep calls
        assert mock_sleep.call_count >= 4


class TestToClientWorker:
    """Test the ToClientWorker class."""

    def test_initialization(self):
        worker = ToClientWorker(queue_maxsize=100, delay_seconds=0.05)
        assert worker._queue.maxsize == 100
        assert worker._delay_seconds == 0.05
        assert worker._thread is None

    def test_start_creates_thread(self):
        worker = ToClientWorker(queue_maxsize=10, delay_seconds=0.01)
        worker.start()
        assert worker._thread is not None
        assert worker._thread.is_alive()
        assert worker._thread.daemon is True
        worker.stop()

    def test_start_idempotent(self):
        worker = ToClientWorker(queue_maxsize=10, delay_seconds=0.01)
        worker.start()
        first_thread = worker._thread
        worker.start()  # Should not create new thread
        assert worker._thread is first_thread
        worker.stop()

    def test_stop_joins_thread(self):
        worker = ToClientWorker(queue_maxsize=10, delay_seconds=0.01)
        worker.start()
        worker.stop()
        assert not worker._thread.is_alive()  # type: ignore[union-attr]

    def test_stop_when_not_running(self):
        worker = ToClientWorker(queue_maxsize=10, delay_seconds=0.01)
        # Should not raise
        worker.stop()

    def test_enqueue_adds_to_queue(self):
        worker = ToClientWorker(queue_maxsize=10, delay_seconds=0.01)
        worker.start()
        worker.enqueue("test message")
        assert worker._queue.qsize() == 1
        worker.stop()

    def test_enqueue_full_queue_logs_warning(self, caplog):
        worker = ToClientWorker(queue_maxsize=2, delay_seconds=0.01)
        worker.start()
        worker.enqueue("msg1")
        worker.enqueue("msg2")
        worker.enqueue("msg3")  # Should be dropped
        assert "queue full, dropping message" in caplog.text
        worker.stop()

    def test_queue_qsize(self):
        worker = ToClientWorker(queue_maxsize=10, delay_seconds=0.01)
        assert worker._queue.qsize() == 0
        worker.start()
        worker.enqueue("msg1")
        assert worker._queue.qsize() == 1
        worker.stop()

    def test_queue_maxsize(self):
        worker = ToClientWorker(queue_maxsize=100, delay_seconds=0.01)
        assert worker._queue.maxsize == 100

    @patch("to_client_worker.type_message")
    def test_loop_processes_messages(self, mock_type_message):
        worker = ToClientWorker(queue_maxsize=10, delay_seconds=0.01)
        worker.start()
        worker.enqueue("msg1")
        worker.enqueue("msg2")
        # Wait for processing
        import time
        time.sleep(0.1)
        worker.stop()
        assert mock_type_message.call_count == 2

    @patch("to_client_worker.type_message")
    def test_loop_handles_exception(self, mock_type_message, caplog):
        mock_type_message.side_effect = Exception("Test error")
        worker = ToClientWorker(queue_maxsize=10, delay_seconds=0.01)
        worker.start()
        worker.enqueue("msg1")
        import time
        time.sleep(0.1)
        worker.stop()
        assert "ToClientWorker error" in caplog.text

    def test_shutdown_signal(self):
        worker = ToClientWorker(queue_maxsize=10, delay_seconds=0.01)
        worker.start()
        worker._queue.put(None)  # Poison pill
        worker._thread.join(timeout=1)  # type: ignore[union-attr]
        assert not worker._thread.is_alive()  # type: ignore[union-attr]


class TestToClientConfig:
    """Test the ToClientConfig dataclass."""

    def test_config_creation(self):
        config = ToClientConfig(
            discord_token="test_token",
            target_channel_id=123456,
            guild_id=789,
            delay_seconds=0.05
        )
        assert config.discord_token == "test_token"
        assert config.target_channel_id == 123456
        assert config.guild_id == 789
        assert config.delay_seconds == 0.05

    def test_config_defaults(self):
        config = ToClientConfig(
            discord_token="test_token",
            target_channel_id=123456
        )
        assert config.guild_id is None
        assert config.delay_seconds == 0.02


class TestDiscordClient:
    """Test the DiscordClient class."""

    @pytest.fixture
    def config(self):
        return ToClientConfig(
            discord_token="test_token",
            target_channel_id=123456
        )

    @pytest.fixture
    def config_with_guild(self):
        return ToClientConfig(
            discord_token="test_token",
            target_channel_id=123456,
            guild_id=789
        )

    @pytest.fixture
    def worker(self):
        return ToClientWorker(queue_maxsize=10, delay_seconds=0.01)

    @pytest.fixture
    def intents(self):
        intents = discord.Intents.default()
        intents.message_content = True
        return intents

    @pytest.mark.asyncio
    async def test_client_initialization(self, config, worker, intents):
        client = DiscordClient(config=config, worker=worker, intents=intents)
        assert client._config == config
        assert client._worker == worker
        assert hasattr(client, "tree")
        assert client.scheduled_tasks == {}

    @pytest.mark.asyncio
    async def test_setup_hook_no_guild(self, config, worker, intents):
        client = DiscordClient(config=config, worker=worker, intents=intents)
        client.tree.sync = AsyncMock()
        await client.setup_hook()
        client.tree.sync.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_setup_hook_with_guild(self, config_with_guild, worker, intents):
        client = DiscordClient(config=config_with_guild, worker=worker, intents=intents)
        client.tree.copy_global_to = MagicMock()
        client.tree.sync = AsyncMock()
        await client.setup_hook()
        client.tree.copy_global_to.assert_called_once()
        client.tree.sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_ready_starts_worker(self, config, worker, intents):
        client = DiscordClient(config=config, worker=worker, intents=intents)
        # user is a read-only property, but we can mock it
        with patch.object(type(client), "user", new_callable=MagicMock) as mock_user:
            mock_user.__str__ = MagicMock(return_value="TestBot#1234")
            await client.on_ready()
        assert worker._thread is not None
        assert worker._thread.is_alive()
        worker.stop()

    @pytest.mark.asyncio
    async def test_on_message_ignores_webhook(self, config, worker, intents):
        client = DiscordClient(config=config, worker=worker, intents=intents)
        message = MagicMock()
        message.webhook_id = 123
        message.author.bot = False
        message.channel.id = config.target_channel_id
        message.content = "test"
        
        await client.on_message(message)
        assert worker._queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_on_message_ignores_bot(self, config, worker, intents):
        client = DiscordClient(config=config, worker=worker, intents=intents)
        message = MagicMock()
        message.webhook_id = None
        message.author.bot = True
        message.channel.id = config.target_channel_id
        message.content = "test"
        
        await client.on_message(message)
        assert worker._queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_on_message_wrong_channel(self, config, worker, intents):
        client = DiscordClient(config=config, worker=worker, intents=intents)
        message = MagicMock()
        message.webhook_id = None
        message.author.bot = False
        message.channel.id = 999999  # Different channel
        message.content = "test"
        
        await client.on_message(message)
        assert worker._queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_on_message_ignores_commands(self, config, worker, intents):
        client = DiscordClient(config=config, worker=worker, intents=intents)
        message = MagicMock()
        message.webhook_id = None
        message.author.bot = False
        message.channel.id = config.target_channel_id
        message.content = "!command"
        
        await client.on_message(message)
        assert worker._queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_on_message_processes_valid(self, config, worker, intents):
        client = DiscordClient(config=config, worker=worker, intents=intents)
        message = MagicMock()
        message.webhook_id = None
        message.author.bot = False
        message.author.display_name = "TestUser"
        message.channel.id = config.target_channel_id
        message.content = "Hello world"
        
        await client.on_message(message)
        assert worker._queue.qsize() > 0
        worker.stop()

    @pytest.mark.asyncio
    async def test_on_message_empty_content(self, config, worker, intents):
        client = DiscordClient(config=config, worker=worker, intents=intents)
        message = MagicMock()
        message.webhook_id = None
        message.author.bot = False
        message.author.display_name = "TestUser"
        message.channel.id = config.target_channel_id
        message.content = ""
        
        await client.on_message(message)
        assert worker._queue.qsize() > 0
        worker.stop()


class TestToClientBotThread:
    """Test the ToClientBotThread class."""

    @pytest.fixture
    def config(self):
        return ToClientConfig(
            discord_token="test_token",
            target_channel_id=123456
        )

    def test_initialization(self, config):
        thread = ToClientBotThread(config)
        assert thread._config == config
        assert thread._client is None
        assert thread.daemon is True

    def test_stop_before_start(self, config):
        thread = ToClientBotThread(config)
        # Should not raise
        thread.stop()

    @patch("discord_client.DiscordClient")
    @patch("discord_client.ToClientWorker")
    def test_run_creates_client_and_worker(self, mock_worker_class, mock_client_class, config):
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_client = MagicMock()
        mock_client.run = MagicMock()
        mock_client_class.return_value = mock_client
        
        thread = ToClientBotThread(config)
        thread.run()
        
        mock_worker_class.assert_called_once_with(delay_seconds=config.delay_seconds)
        mock_client_class.assert_called_once()
        mock_client.run.assert_called_once_with(config.discord_token, log_handler=None)
        assert thread._client is mock_client

    def test_stop_closes_client(self, config):
        thread = ToClientBotThread(config)
        mock_client = MagicMock()
        mock_client.loop = MagicMock()
        mock_client.loop.is_closed.return_value = False
        mock_client.close = AsyncMock()
        thread._client = mock_client
        
        thread.stop()
        
        mock_client.loop.call_soon_threadsafe.assert_called_once()

    def test_stop_with_no_client(self, config):
        thread = ToClientBotThread(config)
        # Should not raise
        thread.stop()

    def test_stop_with_closed_loop(self, config):
        thread = ToClientBotThread(config)
        mock_client = MagicMock()
        mock_client.loop = MagicMock()
        mock_client.loop.is_closed.return_value = True
        thread._client = mock_client
        
        thread.stop()
        # Should not call call_soon_threadsafe