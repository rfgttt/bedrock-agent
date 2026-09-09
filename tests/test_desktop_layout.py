from bedrock_agent.desktop_layout import centered_geometry


def test_centered_geometry_fits_low_resolution_screen() -> None:
    geometry = centered_geometry(720, 560, 1024, 600)

    dimensions, x_text, y_text = geometry.split("+")
    parsed_width, parsed_height = [int(value) for value in dimensions.split("x")]

    assert parsed_width <= 1024
    assert parsed_height <= 600
    assert int(x_text) >= 0
    assert int(y_text) >= 0
