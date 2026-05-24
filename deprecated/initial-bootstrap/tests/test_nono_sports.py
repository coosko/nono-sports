from nono_sports.integrator import DataIntegrator
from nono_sports.normalizer import DataNormalizer


def test_normalize_activity():
    raw = {"id": 1, "name": "Test Run", "distance": 5000, "elapsed_time": 1500, "type": "Run"}
    normalized = DataNormalizer.normalize_activity(raw)

    assert normalized["id"] == 1
    assert normalized["distance_m"] == 5000
    assert normalized["elapsed_time_s"] == 1500
    assert normalized["type"] == "Run"


def test_integrator_deduplicates():
    dataset = [
        {"id": 1, "name": "A"},
        {"id": 1, "name": "A duplicate"},
        {"id": 2, "name": "B"},
    ]
    result = DataIntegrator.deduplicate_by_id(dataset)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["id"] == 2
