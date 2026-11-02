import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.config.styles import STYLE_CONFIGS, get_style_params


def test_style_params():
    for style_key in ["google", "amazon", "meta", "general"]:
        params = get_style_params(style_key)
        assert params is not None
        assert params.max_follow_ups_per_stage >= 2
        assert len(params.tone) > 0
        total_weight = (
            params.optimal_approach_weight
            + params.edge_cases_weight
            + params.correctness_weight
            + params.communication_weight
            + params.time_mgmt_weight
        )
        assert abs(total_weight - 1.0) < 1e-4

    # Fallback to general
    unknown = get_style_params("non_existent_style")
    assert unknown.tone == "neutral"
