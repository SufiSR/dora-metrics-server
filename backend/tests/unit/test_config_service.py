from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.config_schema import ConfigurationSchema
from app.models.app_configuration import AppConfiguration
from app.services import config_service


@dataclass
class _FakeSession:
    app_config: AppConfiguration | None

    def get(self, _model: object, _pk: int) -> AppConfiguration | None:
        return self.app_config


def test_runtime_config_merge_order_defaults_yaml_db_env(monkeypatch) -> None:
    monkeypatch.setattr(
        config_service,
        "_load_yaml_config",
        lambda: {
            "gitlab": {"base_url": "https://yaml.example", "project_paths": ["yaml/path"]},
            "jira": {"ready_for_qa_status_names": ["Ready for test"]},
        },
    )
    monkeypatch.setenv("GITLAB_BASE_URL", "https://env.example")
    monkeypatch.setenv("JIRA_READY_FOR_QA_STATUS_NAMES", "Ready for QA,Ready for test")
    monkeypatch.setenv("CONFIG_ENCRYPTION_KEY", "devops-438-key")

    app_config = AppConfiguration(
        id=1,
        settings_json={
            "gitlab": {"base_url": "https://db.example", "project_paths": ["db/path"]},
            "jira": {"ready_for_qa_status_names": ["DB QA"]},
        },
    )
    runtime = config_service.load_runtime_config(db=_FakeSession(app_config))
    assert runtime.settings.gitlab.base_url == "https://env.example"
    assert runtime.settings.gitlab.project_paths == ["db/path"]
    assert runtime.settings.jira.ready_for_qa_status_names == ["Ready for QA", "Ready for test"]


def test_runtime_tokens_resolve_env_then_db_encrypted(monkeypatch) -> None:
    monkeypatch.setattr(config_service, "_load_yaml_config", lambda: {})
    monkeypatch.setenv("CONFIG_ENCRYPTION_KEY", "devops-438-key")

    gitlab_enc = config_service.encrypt_secret("gitlab-db-token")
    jira_enc = config_service.encrypt_secret("jira-db-token")
    app_config = AppConfiguration(
        id=1,
        settings_json={},
        gitlab_token_enc=gitlab_enc,
        jira_token_enc=jira_enc,
    )
    runtime_from_db = config_service.load_runtime_config(db=_FakeSession(app_config))
    assert runtime_from_db.gitlab_token == "gitlab-db-token"
    assert runtime_from_db.jira_token == "jira-db-token"

    monkeypatch.setenv("GITLAB_TOKEN", "gitlab-env-token")
    monkeypatch.setenv("JIRA_API_TOKEN", "jira-env-token")
    runtime_from_env = config_service.load_runtime_config(db=_FakeSession(app_config))
    assert runtime_from_env.gitlab_token == "gitlab-env-token"
    assert runtime_from_env.jira_token == "jira-env-token"


def test_runtime_config_empty_db_project_paths_keeps_yaml(monkeypatch) -> None:
    """Admin must not persist [] and wipe YAML defaults (empty means inherit)."""
    monkeypatch.setattr(
        config_service,
        "_load_yaml_config",
        lambda: {"gitlab": {"project_paths": ["dev/plunet"]}},
    )
    monkeypatch.setenv("CONFIG_ENCRYPTION_KEY", "devops-438-key")
    app_config = AppConfiguration(
        id=1,
        settings_json={"gitlab": {"project_paths": []}},
    )
    runtime = config_service.load_runtime_config(db=_FakeSession(app_config))
    assert runtime.settings.gitlab.project_paths == ["dev/plunet"]


def test_runtime_config_gitlab_project_path_poc_singular(monkeypatch) -> None:
    """POC YAML uses ``gitlab.project_path``; product uses ``project_paths`` list."""
    monkeypatch.setattr(
        config_service,
        "_load_yaml_config",
        lambda: {"gitlab": {"base_url": "https://gl.example", "project_path": "dev/plunet"}},
    )
    monkeypatch.setenv("CONFIG_ENCRYPTION_KEY", "devops-438-key")
    runtime = config_service.load_runtime_config(db=_FakeSession(None))
    assert runtime.settings.gitlab.project_paths == ["dev/plunet"]
    assert runtime.settings.gitlab.base_url == "https://gl.example"


def test_runtime_jira_user_email_env_then_db(monkeypatch) -> None:
    monkeypatch.setattr(config_service, "_load_yaml_config", lambda: {})
    monkeypatch.setenv("CONFIG_ENCRYPTION_KEY", "devops-438-key")
    monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
    app_config = AppConfiguration(
        id=1,
        settings_json={"jira": {"api_user_email": "  stored@example.test  "}},
    )
    runtime = config_service.load_runtime_config(db=_FakeSession(app_config))
    assert runtime.jira_user_email == "stored@example.test"

    monkeypatch.setenv("JIRA_USER_EMAIL", " env@example.test ")
    runtime_env = config_service.load_runtime_config(db=_FakeSession(app_config))
    assert runtime_env.jira_user_email == "env@example.test"


def test_mask_secret_hint_masks_value() -> None:
    assert config_service.mask_secret_hint("glpat-1234567890") == "glpat****7890"


def test_env_sync_cron_hour_zero_not_falsy_fallback(monkeypatch) -> None:
    monkeypatch.setenv("DORA_SYNC_CRON_HOUR", "0")
    cfg = config_service._apply_env_overrides(ConfigurationSchema())
    assert cfg.backend.sync_cron_hour == 0


def test_env_backend_port_zero_not_falsy_fallback(monkeypatch) -> None:
    monkeypatch.setenv("DORA_BACKEND_PORT", "0")
    cfg = config_service._apply_env_overrides(ConfigurationSchema())
    assert cfg.backend.port == 0


def test_merge_dict_nested_merge() -> None:
    out = config_service._merge_dict(
        {"a": {"x": 1}, "b": 2},
        {"a": {"y": 2}, "b": 3},
    )
    assert out == {"a": {"x": 1, "y": 2}, "b": 3}


def test_load_yaml_config_missing_path_returns_empty(monkeypatch, tmp_path) -> None:
    p = tmp_path / "nope.yml"
    monkeypatch.setenv("DORA_CONFIG_PATH", str(p))
    assert config_service._load_yaml_config() == {}


def test_load_yaml_config_non_dict_payload(tmp_path, monkeypatch) -> None:
    f = tmp_path / "c.yml"
    f.write_text("- not\n- a\n- dict\n", encoding="utf-8")
    monkeypatch.setenv("DORA_CONFIG_PATH", str(f))
    assert config_service._load_yaml_config() == {}


def test_coerce_gitlab_not_dict() -> None:
    merged: dict = {"gitlab": "bad"}
    config_service._coerce_gitlab_project_paths_from_poc_shape(merged)
    assert merged["gitlab"] == "bad"


def test_coerce_paths_list_pops_singular() -> None:
    merged: dict = {"gitlab": {"project_paths": ["a"], "project_path": "x"}}
    config_service._coerce_gitlab_project_paths_from_poc_shape(merged)
    assert "project_path" not in merged["gitlab"]


def test_split_csv_and_env_helpers(monkeypatch) -> None:
    assert config_service._split_csv(None) == []
    assert config_service._split_csv(" a ,  b ") == ["a", "b"]
    monkeypatch.delenv("X_N", raising=False)
    assert config_service._env_text("X_N") is None
    assert config_service._env_int("X_N") is None
    monkeypatch.setenv("X_P", "nope")
    assert config_service._env_int("X_P") is None
    assert config_service._env_bool("X_P") is None
    monkeypatch.setenv("X_T", "true")
    assert config_service._env_bool("X_T") is True
    monkeypatch.setenv("X_F", "no")
    assert config_service._env_bool("X_F") is False


def test_apply_env_extras_branches(monkeypatch) -> None:
    c = ConfigurationSchema()
    monkeypatch.setenv("DORA_ENVIRONMENT", "stg")
    monkeypatch.setenv("DORA_BACKEND_HOST", "0.0.0.0")
    monkeypatch.setenv("DORA_LOOKBACK_DAYS", "365")
    monkeypatch.setenv("GITLAB_NON_CUSTOMER_RELEASE_MARKERS", "alpha,beta")
    monkeypatch.setenv("GITLAB_EXCLUDE_RELEASE_ONLY_MRS_FROM_LEAD_TIME", "1")
    monkeypatch.setenv("GITLAB_RELEASE_MR_TITLE_MARKERS", "A,B")
    monkeypatch.setenv("GITLAB_RELEASE_MR_SOURCE_BRANCH_MARKERS", "C,D")
    monkeypatch.setenv("JIRA_EXCLUDED_PROJECTS", "P1, P2")
    monkeypatch.setenv("JIRA_PRODUCTION_BUG_INDICATOR_CF_IDS", "1,2")
    monkeypatch.setenv("JIRA_MTTR_ALPHA_PRIORITIES", "High")
    out = config_service._apply_env_overrides(c)
    assert out.environment == "stg"
    assert out.backend.lookback_days == 365
    assert "alpha" in [m.lower() for m in out.gitlab.non_customer_release_markers]
    assert out.gitlab.exclude_release_only_mrs_from_lead_time is True
    assert out.jira.excluded_projects == ["P1", "P2"]


def test_normalize_fernet_key_falls_back_to_sha256() -> None:
    # Not a valid raw Fernet key, triggers digest path
    b = config_service._normalize_fernet_key("short-invalid-key-not-fernet-like-at-all")
    assert len(b) == 44


def test_get_fernet_none_without_key(monkeypatch) -> None:
    monkeypatch.delenv("CONFIG_ENCRYPTION_KEY", raising=False)
    assert config_service._get_fernet() is None


def test_encrypt_decrypt_require_key(monkeypatch) -> None:
    monkeypatch.delenv("CONFIG_ENCRYPTION_KEY", raising=False)
    with pytest.raises(RuntimeError, match="CONFIG_ENCRYPTION_KEY"):
        config_service.encrypt_secret("x")
    with pytest.raises(RuntimeError, match="CONFIG_ENCRYPTION_KEY"):
        config_service.decrypt_secret(b"x")


def test_decrypt_invalid_token(monkeypatch) -> None:
    monkeypatch.setenv("CONFIG_ENCRYPTION_KEY", "devops-438-key")
    with pytest.raises(RuntimeError, match="Failed to decrypt"):
        config_service.decrypt_secret(b"not-encrypted-ciphertext!!")


def test_to_string_list() -> None:
    assert config_service._to_string_list("x") == []
    assert config_service._to_string_list([1, "  y ", 0]) == ["1", "y", "0"]


def test_resolve_jira_user_email_from_db_only(monkeypatch) -> None:
    monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
    app_config = AppConfiguration(
        id=1,
        settings_json={"jira": {}},
    )
    assert config_service._resolve_jira_user_email(app_config) == ""


def test_resolve_db_tokens_no_app() -> None:
    assert config_service._resolve_db_tokens(None) == (None, None)


def test_apply_db_overrides_flat_gitlab_paths(monkeypatch) -> None:
    monkeypatch.setattr(config_service, "_load_yaml_config", lambda: {})
    base: dict = {"foo": 1}
    ac = AppConfiguration(
        id=1,
        settings_json={"gitlab_project_paths": ["a/b", "c/d"]},
    )
    out = config_service._apply_db_overrides(base, ac)
    assert isinstance(out.get("gitlab"), dict)
    assert "a/b" in out["gitlab"]["project_paths"]


def test_apply_db_overrides_empty_paths_no_base_gitlab() -> None:
    base: dict = {}
    ac = AppConfiguration(
        id=1,
        settings_json={"gitlab": {"project_paths": []}},
    )
    out = config_service._apply_db_overrides(base, ac)
    assert "gitlab" not in out or out.get("gitlab", {}).get("project_paths", None) in (None, [])


def test_mask_secret_edge_cases() -> None:
    assert config_service.mask_secret_hint("") is None
    assert config_service.mask_secret_hint("   ") is None
    assert config_service.mask_secret_hint("12345678") == "********"


def test_load_runtime_config_without_db(monkeypatch) -> None:
    monkeypatch.setattr(config_service, "_load_yaml_config", lambda: {})
    r = config_service.load_runtime_config(db=None)
    assert r.settings is not None
