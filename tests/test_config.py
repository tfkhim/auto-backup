import pytest

from auto_backup import Config


@pytest.fixture
def config_file(tmpdir):
    content = """
        [XMPP]
        account    = "sender@test-server.net"
        password   = "my-password"
        recipient  = "recipient@test-server.net"

        [[tasks]]
        type       = "rclone"
        name       = "First task"
        tags       = []
    """
    config = tmpdir.join("test_config.toml")
    config.write(content)
    return config


@pytest.fixture
def config(config_file):
    return Config(config_file)


def test_notify_has_sender_set(config):
    assert config.notify.sender == "sender@test-server.net"


def test_notify_has_password_set(config):
    assert config.notify.password == "my-password"


def test_notify_has_recipient_set(config):
    assert config.notify.recipient == "recipient@test-server.net"


def test_task_one_has_type_rclone(config):
    assert config.tasks[0].type == "rclone"


def test_task_one_has_correct_name(config):
    assert config.tasks[0].name == "First task"
