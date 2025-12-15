def pytest_configure(config):
    # Block ruff plugin to avoid requiring the ruff binary in CI/unit runs
    config.pluginmanager.set_blocked("ruff")
    config.pluginmanager.set_blocked("pytest_ruff")
