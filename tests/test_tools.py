"""Unit tests for all tool modules. No API key required."""
import os
import pytest

from tools.file_tools import append_file, list_directory, read_file, write_file
from tools.code_executor import execute_python_code
from tools.shell_tools import run_shell


class TestFileTools:
    def test_write_and_read(self, tmp_path):
        path = str(tmp_path / "test.txt")
        assert "Wrote" in write_file(path, "hello world")
        assert read_file(path) == "hello world"

    def test_write_creates_parent_dirs(self, tmp_path):
        path = str(tmp_path / "a" / "b" / "c.txt")
        write_file(path, "nested")
        assert read_file(path) == "nested"

    def test_read_nonexistent_returns_error(self):
        result = read_file("/nonexistent/__test_file__.txt")
        assert "Error" in result

    def test_append(self, tmp_path):
        path = str(tmp_path / "append.txt")
        write_file(path, "line1\n")
        append_file(path, "line2")
        assert read_file(path) == "line1\nline2"

    def test_list_directory(self, tmp_path):
        (tmp_path / "file.txt").write_text("x")
        (tmp_path / "subdir").mkdir()
        result = list_directory(str(tmp_path))
        assert "file.txt" in result
        assert "subdir" in result

    def test_list_empty_directory(self, tmp_path):
        result = list_directory(str(tmp_path))
        assert result == "(empty)"


class TestCodeExecutor:
    def test_basic_print(self):
        result = execute_python_code("print('hello')")
        assert result["success"]
        assert "hello" in result["stdout"]

    def test_arithmetic(self):
        result = execute_python_code("print(2 + 2)")
        assert result["success"]
        assert "4" in result["stdout"]

    def test_syntax_error(self):
        result = execute_python_code("def foo(:")
        assert not result["success"]
        assert result["stderr"]

    def test_stderr_captured(self):
        result = execute_python_code("import sys; print('err', file=sys.stderr)")
        assert "err" in result["stderr"]

    def test_timeout(self):
        result = execute_python_code("while True: pass", timeout=1)
        assert not result["success"]
        assert "timed out" in result["stderr"].lower()

    def test_multiline(self):
        code = "total = sum(range(10))\nprint(total)"
        result = execute_python_code(code)
        assert result["success"]
        assert "45" in result["stdout"]


class TestShellTools:
    def test_echo(self):
        result = run_shell("echo hello")
        assert "hello" in result

    def test_python_version(self):
        result = run_shell("python --version")
        assert "Python" in result or "python" in result.lower()

    def test_blocked_rm(self):
        result = run_shell("rm -rf /important")
        assert "blocked" in result.lower() or "Error" in result

    def test_blocked_kill(self):
        result = run_shell("kill -9 1")
        assert "blocked" in result.lower() or "Error" in result

    def test_nonexistent_command(self):
        result = run_shell("nonexistent_command_xyz_abc")
        assert "not found" in result.lower() or "Error" in result

    def test_empty_command(self):
        result = run_shell("")
        assert "Empty" in result or "Error" in result


class TestMemoryStore:
    def test_save_and_recall(self, tmp_path):
        from memory.store import MemoryStore
        store = MemoryStore(str(tmp_path / "mem.json"))
        store.save("name", "Alice")
        assert "Alice" in store.recall("name")

    def test_recall_missing_key(self, tmp_path):
        from memory.store import MemoryStore
        store = MemoryStore(str(tmp_path / "mem.json"))
        assert "No memory" in store.recall("missing")

    def test_list_all(self, tmp_path):
        from memory.store import MemoryStore
        store = MemoryStore(str(tmp_path / "mem.json"))
        store.save("k1", "v1")
        store.save("k2", "v2")
        result = store.list_all()
        assert "k1" in result
        assert "k2" in result

    def test_delete(self, tmp_path):
        from memory.store import MemoryStore
        store = MemoryStore(str(tmp_path / "mem.json"))
        store.save("key", "val")
        store.delete("key")
        assert "No memory" in store.recall("key")

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "mem.json")
        s1 = MemoryStore(path)
        s1.save("persisted", "yes")
        s2 = MemoryStore(path)  # reload
        assert "yes" in s2.recall("persisted")
