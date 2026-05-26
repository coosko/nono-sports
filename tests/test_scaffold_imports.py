import importlib

SCAFFOLD_MODULES = [
    "nono_sports.cli",
    "nono_sports.core.config",
    "nono_sports.core.paths",
    "nono_sports.core.logging",
    "nono_sports.core.errors",
    "nono_sports.auth.strava_oauth",
    "nono_sports.auth.token_store",
    "nono_sports.strava.client",
    "nono_sports.strava.endpoints",
    "nono_sports.strava.sync",
    "nono_sports.strava.rate_limits",
    "nono_sports.storage.raw_store",
    "nono_sports.storage.consolidated_store",
    "nono_sports.storage.normalized_store",
    "nono_sports.storage.state_store",
    "nono_sports.storage.manifest",
    "nono_sports.domain.source",
    "nono_sports.domain.activity",
    "nono_sports.domain.athlete",
    "nono_sports.domain.stream",
    "nono_sports.normalization.strava_activity",
    "nono_sports.normalization.strava_athlete",
    "nono_sports.normalization.strava_dataset",
    "nono_sports.normalization.strava_stream",
    "nono_sports.consolidation.single_source",
    "nono_sports.validation.checks",
    "nono_sports.validation.reports",
]


def test_scaffold_modules_import() -> None:
    for module_name in SCAFFOLD_MODULES:
        assert importlib.import_module(module_name) is not None
