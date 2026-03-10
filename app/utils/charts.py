from typing import List


def bar_chart_data(labels: List[str], values: List[float], label: str = "Data") -> dict:
    """Return a Chart.js bar chart configuration dict."""
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": label,
                    "data": values,
                    "backgroundColor": [
                        "rgba(59, 130, 246, 0.7)" for _ in values
                    ],
                    "borderColor": [
                        "rgba(59, 130, 246, 1)" for _ in values
                    ],
                    "borderWidth": 1,
                }
            ],
        },
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {"display": True},
                "tooltip": {"enabled": True},
            },
            "scales": {
                "y": {"beginAtZero": True},
            },
        },
    }
