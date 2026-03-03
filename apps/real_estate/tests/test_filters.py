from decimal import Decimal

import pytest

from apps.real_estate.templatetags.real_estate_filters import cad


class TestCadFilter:
    def test_whole_number(self):
        assert cad(Decimal("1234")) == "$1,234"

    def test_with_cents(self):
        assert cad(Decimal("1234.56")) == "$1,234.56"

    def test_large_number(self):
        assert cad(Decimal("1000000")) == "$1,000,000"

    def test_zero(self):
        assert cad(Decimal("0")) == "$0"

    def test_none(self):
        assert cad(None) == ""

    def test_string_number(self):
        assert cad("5000") == "$5,000"

    def test_decimal_with_trailing_zeros(self):
        assert cad(Decimal("500.00")) == "$500"

    def test_negative_number(self):
        assert cad(Decimal("-1234")) == "$-1,234"

    @pytest.mark.parametrize("value", ["abc", object(), []])
    def test_invalid_values(self, value):
        assert cad(value) == ""
