import pytest

from src import narrate_book_f5


def test_validate_speed_accepts_positive_values() -> None:
    assert narrate_book_f5.validate_speed(1.0) == 1.0
    assert narrate_book_f5.validate_speed("0.8") == 0.8


@pytest.mark.parametrize("value", [0, 0.0, -0.1, "0", "-1", "nan", "inf", "bad"])
def test_validate_speed_rejects_invalid_values(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        narrate_book_f5.validate_speed(value)
