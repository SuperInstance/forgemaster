#!/usr/bin/env python3
"""
tests/test_plato_room_ide.py — Tests for PLATO Agentic IDE (20+ tests)
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure we can import the module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from plato_room_ide import (
    HistoryEntry, RoomHistory, FileSnapshot, DiffResult, RoomDiff,
    ShellConfig, AgentShell, AgentRoom, RoomCheckpoint,
    RoomTask, TaskStatus, RoomIDE, RoomIDEHandler,
    SANDBOX_BASE,
)


# ---------------------------------------------------------------------------
# RoomHistory Tests
# ---------------------------------------------------------------------------

class TestRoomHistory(unittest.TestCase):

    def setUp(self):
        self.history = RoomHistory()

    def test_log_and_scroll(self):
        """Test logging entries and scrolling."""
        self.history.log("execute", "test prompt")
        self.history.log("agent_response", "test response")
        entries = self.history.scroll(10)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].action, "execute")
        self.assertEqual(entries[1].action, "agent_response")

    def test_scroll_formatted(self):
        """Test formatted scroll output."""
        self.history.log("execute", "hello world")
        formatted = self.history.scroll_formatted(10)
        self.assertEqual(len(formatted), 1)
        self.assertIn("execute", formatted[0])
        self.assertIn("hello world", formatted[0])

    def test_scroll_limit(self):
        """Test scroll respects N limit."""
        for i in range(50):
            self.history.log("action", f"entry {i}")
        entries = self.history.scroll(10)
        self.assertEqual(len(entries), 10)
        # Should be the last 10 entries
        self.assertEqual(entries[0].summary, "entry 40")

    def test_search(self):
        """Test searching history entries."""
        self.history.log("execute", "write a function")
        self.history.log("execute", "read a file")
        self.history.log("agent_response", "here is the function")
        results = self.history.search("function")
        self.assertEqual(len(results), 2)

    def test_since(self):
        """Test getting entries since a timestamp."""
        self.history.log("old", "before")
        cutoff = time.time()
        time.sleep(0.01)
        self.history.log("new", "after")
        recent = self.history.since(cutoff)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].summary, "after")

    def test_count(self):
        """Test entry count."""
        self.assertEqual(self.history.count, 0)
        self.history.log("test", "entry")
        self.assertEqual(self.history.count, 1)

    def test_entry_format(self):
        """Test HistoryEntry format string."""
        entry = HistoryEntry(action="execute", summary="test prompt")
        formatted = entry.format()
        self.assertIn("[", formatted)
        self.assertIn("execute", formatted)
        self.assertIn("test prompt", formatted)


# ---------------------------------------------------------------------------
# RoomDiff Tests
# ---------------------------------------------------------------------------

class TestRoomDiff(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.differ = RoomDiff(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_snapshot_empty_dir(self):
        """Test snapshot of empty directory."""
        snap = self.differ.snapshot()
        self.assertEqual(len(snap), 0)

    def test_snapshot_with_files(self):
        """Test snapshot captures files."""
        (self.tmpdir / "test.txt").write_text("hello")
        snap = self.differ.snapshot()
        self.assertIn("test.txt", snap)
        self.assertEqual(snap["test.txt"].size, 5)

    def test_checkpoint_and_diff_no_changes(self):
        """Test diff with no changes returns empty."""
        (self.tmpdir / "file.txt").write_text("original")
        self.differ.save_checkpoint("cp1")
        diff = self.differ.diff("cp1")
        self.assertFalse(diff.has_changes)

    def test_diff_detects_added_files(self):
        """Test diff detects new files."""
        self.differ.save_checkpoint("cp1")
        (self.tmpdir / "new_file.py").write_text("print('hello')")
        diff = self.differ.diff("cp1")
        self.assertIn("new_file.py", diff.files_added)
        self.assertTrue(diff.has_changes)

    def test_diff_detects_modified_files(self):
        """Test diff detects changed files."""
        (self.tmpdir / "data.txt").write_text("version 1")
        self.differ.save_checkpoint("cp1")
        (self.tmpdir / "data.txt").write_text("version 2 changed")
        diff = self.differ.diff("cp1")
        self.assertIn("data.txt", diff.files_modified)
        self.assertIn("data.txt", diff.content_diffs)

    def test_diff_detects_removed_files(self):
        """Test diff detects deleted files."""
        fp = self.tmpdir / "temp.txt"
        fp.write_text("temporary")
        self.differ.save_checkpoint("cp1")
        fp.unlink()
        diff = self.differ.diff("cp1")
        self.assertIn("temp.txt", diff.files_removed)

    def test_diff_with_nested_files(self):
        """Test diff handles nested directory structure."""
        self.differ.save_checkpoint("cp1")
        subdir = self.tmpdir / "src" / "lib"
        subdir.mkdir(parents=True)
        (subdir / "module.py").write_text("# module code")
        diff = self.differ.diff("cp1")
        self.assertTrue(any("module.py" in f for f in diff.files_added))

    def test_multiple_checkpoints(self):
        """Test tracking multiple checkpoints."""
        self.differ.save_checkpoint("cp1")
        (self.tmpdir / "file1.txt").write_text("one")
        self.differ.save_checkpoint("cp2")
        (self.tmpdir / "file2.txt").write_text("two")
        diff1 = self.differ.diff("cp1")
        diff2 = self.differ.diff("cp2")
        self.assertGreaterEqual(len(diff1.files_added), 2)
        self.assertGreaterEqual(len(diff2.files_added), 1)


# ---------------------------------------------------------------------------
# ShellConfig Tests
# ---------------------------------------------------------------------------

class TestShellConfig(unittest.TestCase):

    def test_default_config(self):
        """Test default shell configuration."""
        config = ShellConfig()
        self.assertEqual(config.shell_type, "seed-mini")
        self.assertIn("Seed", config.model)

    def test_custom_shell_type(self):
        """Test custom shell type maps to correct model."""
        config = ShellConfig(shell_type="hermes-70b")
        self.assertIn("Hermes", config.model)

    def test_custom_shell_unknown(self):
        """Test unknown shell type uses default model."""
        config = ShellConfig(shell_type="unknown-type")
        # Should fallback to seed-mini since not in SHELL_MODELS
        self.assertEqual(config.model, "")


# ---------------------------------------------------------------------------
# AgentShell Tests (mocked API calls)
# ---------------------------------------------------------------------------

class TestAgentShell(unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_execute_returns_response(self, mock_urlopen):
        """Test execute returns agent response."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Hello from agent!"}}]
        }).encode()
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        shell = AgentShell(ShellConfig(shell_type="seed-mini"))
        result = shell.execute("Say hello")
        self.assertEqual(result, "Hello from agent!")

    @patch("urllib.request.urlopen")
    def test_conversation_tracking(self, mock_urlopen):
        """Test that conversation history is tracked."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "response"}}]
        }).encode()
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        shell = AgentShell()
        self.assertEqual(shell.conversation_length, 0)
        shell.execute("prompt 1")
        self.assertEqual(shell.conversation_length, 2)  # user + assistant

    def test_swap_shell(self):
        """Test swapping shell type."""
        shell = AgentShell(ShellConfig(shell_type="seed-mini"))
        shell.swap_shell("hermes-70b")
        self.assertIn("Hermes", shell.config.model)

    def test_clear_conversation(self):
        """Test clearing conversation history."""
        shell = AgentShell()
        shell._conversation.append({"role": "user", "content": "test"})
        shell.clear_conversation()
        self.assertEqual(shell.conversation_length, 0)

    @patch("urllib.request.urlopen", side_effect=Exception("connection refused"))
    def test_execute_error_handling(self, mock_urlopen):
        """Test execute handles API errors gracefully."""
        shell = AgentShell()
        result = shell.execute("test")
        self.assertIn("Shell Error", result)


# ---------------------------------------------------------------------------
# AgentRoom Tests
# ---------------------------------------------------------------------------

class TestAgentRoom(unittest.TestCase):

    def setUp(self):
        self.room = AgentRoom(name="test-room", shell_type="seed-mini")

    def tearDown(self):
        self.room.destroy()

    def test_room_creation(self):
        """Test room is created with correct attributes."""
        self.assertEqual(self.room.name, "test-room")
        self.assertTrue(self.room.sandbox_dir.exists())
        self.assertEqual(self.room.history.count, 1)  # room_created entry

    def test_write_and_read_file(self):
        """Test writing and reading files in sandbox."""
        self.room.write_file("test.py", "print('hello')")
        content = self.room.read_file("test.py")
        self.assertEqual(content, "print('hello')")

    def test_write_nested_file(self):
        """Test writing nested directory files."""
        self.room.write_file("src/lib/utils.py", "def helper(): pass")
        content = self.room.read_file("src/lib/utils.py")
        self.assertEqual(content, "def helper(): pass")

    def test_read_nonexistent_file(self):
        """Test reading non-existent file returns None."""
        result = self.room.read_file("nope.txt")
        self.assertIsNone(result)

    def test_list_files(self):
        """Test listing files in sandbox."""
        self.room.write_file("a.txt", "aaa")
        self.room.write_file("b.txt", "bbb")
        files = self.room.list_files()
        names = [f["name"] for f in files]
        self.assertIn("a.txt", names)
        self.assertIn("b.txt", names)

    def test_scroll_history(self):
        """Test scrolling room history."""
        self.room.write_file("test.txt", "content")
        self.room.history.log("execute", "test prompt")
        entries = self.room.scroll(10)
        self.assertGreater(len(entries), 1)

    def test_checkpoint(self):
        """Test creating a checkpoint."""
        self.room.write_file("data.txt", "initial")
        cp = self.room.checkpoint("v1")
        self.assertEqual(cp, "v1")
        self.assertIn("v1", self.room._checkpoints)

    def test_diff_after_changes(self):
        """Test diff detects changes after checkpoint."""
        self.room.checkpoint("base")
        self.room.write_file("new_file.py", "# new code")
        diff = self.room.diff("base")
        self.assertIn("new_file.py", diff.files_added)

    def test_set_and_get_env(self):
        """Test room environment variables."""
        self.room.set_env("LANGUAGE", "python")
        self.assertEqual(self.room.get_env("LANGUAGE"), "python")

    def test_room_to_dict(self):
        """Test room serialization."""
        d = self.room.to_dict()
        self.assertIn("room_id", d)
        self.assertIn("name", d)
        self.assertEqual(d["name"], "test-room")

    def test_execute_logs_history(self):
        """Test that execute logs to history (mocked shell)."""
        with patch.object(self.room.shell, 'execute', return_value="response"):
            self.room.execute("test prompt")
        # Should have execute + agent_response entries
        actions = [e.action for e in self.room.history.all_entries()]
        self.assertIn("execute", actions)
        self.assertIn("agent_response", actions)

    def test_destroy_cleanup(self):
        """Test destroy removes sandbox directory."""
        sandbox = self.room.sandbox_dir
        self.assertTrue(sandbox.exists())
        self.room.destroy()
        self.assertFalse(sandbox.exists())


# ---------------------------------------------------------------------------
# RoomTask Tests
# ---------------------------------------------------------------------------

class TestRoomTask(unittest.TestCase):

    def setUp(self):
        self.room = AgentRoom(name="task-room", shell_type="seed-mini")

    def tearDown(self):
        self.room.destroy()

    @patch.object(AgentShell, 'execute')
    def test_task_completes_on_done_signal(self, mock_execute):
        """Test task completes when DONE signal received."""
        mock_execute.return_value = "DONE - Task completed successfully"
        task = RoomTask(room=self.room, prompt="Do something", max_iterations=5)
        status = task.run(background=False)
        self.assertEqual(status.status, "done")
        self.assertEqual(status.current_iteration, 1)

    @patch.object(AgentShell, 'execute')
    def test_task_runs_max_iterations(self, mock_execute):
        """Test task runs until max_iterations."""
        mock_execute.return_value = "Still working..."
        task = RoomTask(room=self.room, prompt="Do something", max_iterations=3)
        status = task.run(background=False)
        self.assertEqual(status.status, "done")
        self.assertEqual(status.current_iteration, 3)
        self.assertEqual(len(status.results), 3)

    @patch.object(AgentShell, 'execute')
    def test_task_handles_error(self, mock_execute):
        """Test task handles exceptions."""
        mock_execute.side_effect = RuntimeError("API down")
        task = RoomTask(room=self.room, prompt="Do something", max_iterations=5)
        status = task.run(background=False)
        self.assertEqual(status.status, "failed")
        self.assertIn("API down", status.error)

    @patch.object(AgentShell, 'execute')
    def test_task_kill(self, mock_execute):
        """Test killing a running task."""
        import threading
        barrier = threading.Barrier(2, timeout=5)

        def slow_execute(*args, **kwargs):
            barrier.wait()  # Block until kill test is ready
            time.sleep(2)
            return "Done"

        mock_execute.side_effect = slow_execute
        task = RoomTask(room=self.room, prompt="Do something", max_iterations=100)
        task.run(background=True)
        time.sleep(0.2)
        barrier.wait()  # Ensure execute is running
        task.kill()
        time.sleep(0.3)
        self.assertIn(task.status().status, ("killed", "done"))

    @patch.object(AgentShell, 'execute', return_value="DONE")
    def test_task_status_dict(self, mock_execute):
        """Test task status serialization."""
        task = RoomTask(room=self.room, prompt="Test", max_iterations=1)
        task.run(background=False)
        d = task.to_dict()
        self.assertIn("task_id", d)
        self.assertEqual(d["status"], "done")


# ---------------------------------------------------------------------------
# RoomIDE Tests
# ---------------------------------------------------------------------------

class TestRoomIDE(unittest.TestCase):

    def setUp(self):
        self.ide = RoomIDE()

    def tearDown(self):
        for room_id in list(self.ide._rooms.keys()):
            self.ide.destroy_room(room_id)

    def test_create_room(self):
        """Test creating a room."""
        room = self.ide.create_room("research", "seed-mini")
        self.assertEqual(room.name, "research")
        self.assertIn(room.room_id, self.ide._rooms)

    def test_list_rooms(self):
        """Test listing rooms."""
        self.ide.create_room("room1")
        self.ide.create_room("room2")
        rooms = self.ide.list_rooms()
        self.assertEqual(len(rooms), 2)

    def test_enter_and_leave(self):
        """Test entering and leaving a room."""
        room = self.ide.create_room("test")
        result = self.ide.enter(room.room_id)
        self.assertIsNotNone(result)
        self.assertEqual(self.ide.current_room_id, room.room_id)
        old = self.ide.leave()
        self.assertEqual(old, room.room_id)
        self.assertIsNone(self.ide.current_room_id)

    def test_enter_nonexistent_room(self):
        """Test entering a non-existent room returns None."""
        result = self.ide.enter("nope")
        self.assertIsNone(result)

    @patch.object(AgentShell, 'execute', return_value="mocked response")
    def test_prompt_sends_to_current_room(self, mock_exec):
        """Test prompt sends to the currently entered room."""
        room = self.ide.create_room("test")
        self.ide.enter(room.room_id)
        result = self.ide.prompt("hello")
        self.assertEqual(result, "mocked response")

    def test_prompt_without_room(self):
        """Test prompt with no current room returns None."""
        result = self.ide.prompt("hello")
        self.assertIsNone(result)

    def test_scroll_without_room(self):
        """Test scroll with no current room returns empty list."""
        result = self.ide.scroll()
        self.assertEqual(result, [])

    def test_diff_without_room(self):
        """Test diff with no current room returns None."""
        result = self.ide.diff()
        self.assertIsNone(result)

    def test_destroy_room(self):
        """Test destroying a room cleans up."""
        room = self.ide.create_room("doomed")
        sandbox = room.sandbox_dir
        self.assertTrue(sandbox.exists())
        self.ide.enter(room.room_id)
        self.ide.destroy_room(room.room_id)
        self.assertFalse(sandbox.exists())
        self.assertIsNone(self.ide.current_room_id)

    def test_destroy_nonexistent_room(self):
        """Test destroying non-existent room returns False."""
        result = self.ide.destroy_room("nope")
        self.assertFalse(result)

    @patch.object(AgentShell, 'execute', return_value="DONE - complete")
    def test_dispatch_task(self, mock_exec):
        """Test dispatching a room on a task."""
        room = self.ide.create_room("worker")
        task = self.ide.dispatch(room.room_id, "Do the thing", max_iterations=5, background=False)
        self.assertIsNotNone(task)
        self.assertEqual(task.status().status, "done")

    def test_dispatch_nonexistent_room(self):
        """Test dispatching to non-existent room returns None."""
        result = self.ide.dispatch("nope", "Do something")
        self.assertIsNone(result)

    @patch.object(AgentShell, 'execute', return_value="DONE")
    def test_check_task(self, mock_exec):
        """Test checking task status for a room."""
        room = self.ide.create_room("worker")
        self.ide.dispatch(room.room_id, "Work", background=False)
        status = self.ide.check(room.room_id)
        self.assertIsNotNone(status)
        self.assertEqual(status["status"], "done")

    @patch.object(AgentShell, 'execute', return_value="DONE")
    def test_kill_task(self, mock_exec):
        """Test killing a task by task ID."""
        room = self.ide.create_room("worker")
        task = self.ide.dispatch(room.room_id, "Work", background=False)
        result = self.ide.kill_task(task.task_id)
        self.assertTrue(result)

    def test_kill_nonexistent_task(self):
        """Test killing non-existent task returns False."""
        result = self.ide.kill_task("nope")
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# DiffResult Tests
# ---------------------------------------------------------------------------

class TestDiffResult(unittest.TestCase):

    def test_empty_diff_no_changes(self):
        """Test empty DiffResult reports no changes."""
        diff = DiffResult()
        self.assertFalse(diff.has_changes)

    def test_diff_with_additions(self):
        """Test DiffResult with added files."""
        diff = DiffResult(files_added=["new.py"])
        self.assertTrue(diff.has_changes)

    def test_diff_serialization(self):
        """Test DiffResult to_dict."""
        diff = DiffResult(files_added=["a.py"], files_modified=["b.py"])
        d = diff.to_dict()
        self.assertEqual(d["files_added"], ["a.py"])
        self.assertEqual(d["files_modified"], ["b.py"])


# ---------------------------------------------------------------------------
# Integration Test
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):
    """Integration test: create room, write files, checkpoint, diff."""

    def setUp(self):
        self.ide = RoomIDE()

    def tearDown(self):
        for room_id in list(self.ide._rooms.keys()):
            self.ide.destroy_room(room_id)

    def test_full_workflow(self):
        """Test complete workflow: create → write → checkpoint → modify → diff."""
        # Create room
        room = self.ide.create_room("workflow-test", "seed-mini")
        self.ide.enter(room.room_id)

        # Write initial files
        room.write_file("README.md", "# Workflow Test\nInitial version.")
        room.write_file("main.py", "def main():\n    pass")
        room.checkpoint("v1")

        # Modify files
        room.write_file("main.py", "def main():\n    print('hello')")
        room.write_file("utils.py", "def helper():\n    return True")

        # Diff
        diff = room.diff("v1")
        self.assertIn("main.py", diff.files_modified)
        self.assertIn("utils.py", diff.files_added)
        self.assertEqual(len(diff.files_removed), 0)

        # Scroll
        entries = room.scroll(20)
        self.assertGreater(len(entries), 3)

        # Leave room
        self.ide.leave()
        self.assertIsNone(self.ide.current_room_id)

        # Room still exists
        self.assertIn(room.room_id, self.ide._rooms)

    @patch.object(AgentShell, 'execute', return_value="Analysis complete. DONE")
    def test_prompt_and_scroll(self, mock_exec):
        """Test prompting a room and scrolling results."""
        room = self.ide.create_room("analysis", "seed-mini")
        self.ide.enter(room.room_id)
        response = self.ide.prompt("Analyze the constraint matrix")
        self.assertIn("Analysis complete", response)

        entries = self.ide.scroll()
        self.assertGreater(len(entries), 0)

        # Search history
        room.history.log("execute", "Analyze the constraint matrix")
        found = room.history.search("constraint")
        self.assertGreater(len(found), 0)


if __name__ == "__main__":
    unittest.main()
