from app.services.table_analytics import analyze_table


def test_grouped_sum_and_ranking():
    rows = [
        {"city": "Mumbai", "forecast": 100},
        {"city": "Hyderabad", "forecast": 80},
        {"city": "Mumbai", "forecast": 50},
    ]
    result = analyze_table(rows=rows, metric="forecast", dimension="city", aggregation="sum", sort="desc", limit=2)
    assert result["data"] == [
        {"label": "Mumbai", "value": 150.0},
        {"label": "Hyderabad", "value": 80.0},
    ]


def test_filter_and_average():
    rows = [
        {"category": "A", "value": 10},
        {"category": "A", "value": 20},
        {"category": "B", "value": 100},
    ]
    result = analyze_table(rows=rows, metric="value", aggregation="average", filters={"category": "A"})
    assert result["data"][0]["value"] == 15.0
