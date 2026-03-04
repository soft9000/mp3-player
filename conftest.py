# MISSION: Create a remote-controller music player.
# STATUS: Research.
# VERSION: 0.0.1
# NOTES: Tweaking a fumbled CoPilot attempt.
# DATE: 2026-03-04 06:44:37
# FILE: conftest.py
# AUTHOR: Randall Nagy
#
import pytest
import tempfile
import os

@pytest.fixture
def temp_db():
    test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    test_db.close()
    yield test_db.name
    if os.path.exists(test_db.name):
        os.remove(test_db.name)

@pytest.fixture
def temp_dir():
    test_dir = tempfile.mkdtemp()
    yield test_dir
    for root, dirs, files in os.walk(test_dir, topdown=False):
        for file in files:
            os.remove(os.path.join(root, file))
        for dir in dirs:
            os.rmdir(os.path.join(root, dir))
    os.rmdir(test_dir)
