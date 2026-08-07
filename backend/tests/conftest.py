"""Shared pytest fixtures and configuration for SKPL Agent tests."""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file for testing."""
    content = """\"\"\"Sample Python module for testing.\"\"\"

class Calculator:
    \"\"\"A simple calculator.\"\"\"

    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b

def main():
    calc = Calculator()
    print(calc.add(1, 2))

if __name__ == "__main__":
    main()
"""
    file_path = temp_dir / "sample.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_typescript_file(temp_dir):
    """Create a sample TypeScript file for testing."""
    content = """interface User {
    id: string;
    name: string;
}

class UserService {
    private users: User[] = [];

    async getUser(id: string): Promise<User | null> {
        return this.users.find(u => u.id === id) ?? null;
    }
}

const MAX_USERS = 100;
export { UserService, MAX_USERS };
"""
    file_path = temp_dir / "sample.ts"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_sensitive_file(temp_dir):
    """Create a sample file with sensitive content for testing."""
    content = """# Configuration
API_KEY = "sk-1234567890abcdefghijklmnopqrstuv"
DATABASE_URL = "postgres://user:password@localhost:5432/db"
DEBUG = True
"""
    file_path = temp_dir / "config.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_project_dir(temp_dir):
    """Create a sample project directory with multiple files."""
    (temp_dir / "src").mkdir(exist_ok=True)
    (temp_dir / "src" / "main.py").write_text("def main():\n    pass\n")
    (temp_dir / "src" / "utils.py").write_text("def helper():\n    return True\n")
    (temp_dir / "src" / "types.ts").write_text("type ID = string;\n")
    (temp_dir / "README.md").write_text("# Project\n")
    (temp_dir / ".env").write_text("SECRET=xxx")
    (temp_dir / "data.csv").write_text("col1,col2\n1,2")
    return temp_dir