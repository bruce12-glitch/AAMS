"""Prevent regressions in the selected no-cost Oracle showcase topology."""
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_oracle_compose_keeps_app_private_and_data_persistent():
    compose = yaml.safe_load((ROOT / 'docker-compose.oracle.yml').read_text())
    app = compose['services']['app']
    caddy = compose['services']['caddy']
    assert 'ports' not in app
    assert app['build']['dockerfile'] == 'Dockerfile.showcase'
    assert 'aams-data:/data' in app['volumes']
    assert caddy['ports'] == ['80:80', '443:443']
    assert './deploy/Caddyfile.oracle:/etc/caddy/Caddyfile:ro' in caddy['volumes']


def test_oracle_runtime_template_contains_no_real_credentials():
    template = (ROOT / 'deploy' / '.env.oracle.example').read_text()
    assert 'AAMS_HOSTNAME=choose-a-unique-name.duckdns.org' in template
    assert 'ADMIN_EMAIL=your.name@srmist.edu.in' in template
    assert 'AAMS_ACCESS_PASSWORD=replace-with-' in template
    assert 'TELEGRAM_BOT_TOKEN=' in template
    assert 'AAMSFORDEIFABLAB' not in template
    assert 'deploy/.env.oracle' in (ROOT / '.gitignore').read_text()


def test_caddy_uses_configured_hostname_and_never_exposes_data_volume():
    caddy = (ROOT / 'deploy' / 'Caddyfile.oracle').read_text()
    assert '{$AAMS_HOSTNAME}' in caddy
    assert 'reverse_proxy app:8000' in caddy
    assert '/data' not in caddy


def test_oracle_deploy_workflow_is_manual_and_uses_host_key_verification():
    workflow = (ROOT / '.github' / 'workflows' / 'deploy-oracle.yml').read_text()
    assert 'workflow_dispatch:' in workflow
    assert 'ORACLE_KNOWN_HOSTS' in workflow
    assert 'StrictHostKeyChecking=no' not in workflow
    assert 'git merge --ff-only origin/main' in workflow
    assert 'docker compose --env-file deploy/.env.oracle -f docker-compose.oracle.yml up --build -d --remove-orphans' in workflow
