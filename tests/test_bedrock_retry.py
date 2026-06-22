"""Bedrock client retries transient failures exactly once."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.bedrock_client import _bedrock_config


def test_bedrock_config_allows_one_retry():
    cfg = _bedrock_config()
    # standard mode: max_attempts is TOTAL attempts, so 2 == one retry
    assert cfg.retries["max_attempts"] == 2
    assert cfg.retries["mode"] == "standard"
    assert cfg.read_timeout == 30
    assert cfg.connect_timeout == 10
