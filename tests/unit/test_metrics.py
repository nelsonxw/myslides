"""
Unit tests for slide metrics and quality scoring.
"""
from myslides.analysis.metrics.formatting import calculate_formatting_metrics
from myslides.analysis.metrics.layout import calculate_layout_metrics
from myslides.analysis.metrics.visuals import calculate_visual_metrics
from myslides.analysis.scorer import score_slide


def test_visual_metrics():
    features = {
        "has_chart": True,
        "has_table": False,
        "has_images": True,
        "icon_count": 3,
        "shapes": [],
    }
    m = calculate_visual_metrics(features)
    assert m["visual_diversity"] > 0.5
    assert m["icon_usage"] == 1.0
    assert m["chart_impact"] == 1.0
    assert m["composite_visual_score"] > 0.7


def test_layout_metrics():
    features = {
        "whitespace_ratio": 0.45,
        "title_text": "Executive Q3 Update",
        "font_sizes": [32.0, 16.0, 12.0],
        "shapes": [
            {"type": "text_box", "left_in": 0.8, "top_in": 1.5, "width_in": 3.5, "height_in": 4.5, "is_title": False},
            {"type": "text_box", "left_in": 4.8, "top_in": 1.5, "width_in": 3.5, "height_in": 4.5, "is_title": False},
            {"type": "text_box", "left_in": 8.8, "top_in": 1.5, "width_in": 3.5, "height_in": 4.5, "is_title": False},
        ],
    }
    m = calculate_layout_metrics(features)
    assert m["whitespace"] == 1.0
    assert m["visual_hierarchy"] == 1.0
    assert m["composite_layout_score"] >= 0.7


def test_formatting_metrics():
    features = {
        "fonts": ["Arial", "Arial Nova Light"],
        "colors": ["#0672CB", "#1D2C3B", "#FFFFFF"],
        "shapes": [
            {"type": "text_box", "left_in": 0.8, "is_placeholder": False},
        ],
    }
    m = calculate_formatting_metrics(features)
    assert m["font_choice"] == 1.0
    assert m["color_palette"] == 1.0
    assert m["contrast"] == 1.0
    assert m["composite_formatting_score"] >= 0.8


def test_score_slide():
    features = {
        "whitespace_ratio": 0.4,
        "has_chart": True,
        "icon_count": 2,
        "fonts": ["Arial"],
        "colors": ["#0672CB", "#1D2C3B", "#FFFFFF"],
        "shapes": [
            {"type": "text_box", "left_in": 0.8, "top_in": 1.5, "width_in": 5.5, "height_in": 4.5, "is_title": True},
            {"type": "chart", "left_in": 6.8, "top_in": 1.5, "width_in": 5.5, "height_in": 4.5, "is_title": False},
        ],
        "font_sizes": [28.0, 14.0],
    }
    res = score_slide(features)
    assert "total_score" in res
    assert 0 <= res["total_score"] <= 100
    assert res["total_score"] > 60
