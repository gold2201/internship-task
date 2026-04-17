from decimal import Decimal

from app.services.transaction_analytics_service import (
    get_not_rollbacked_deposit_amount,
    get_not_rollbacked_withdraw_amount,
)


class TestGetNotRollbackedDepositAmount:
    def test_empty_list_returns_zero(self):
        result = get_not_rollbacked_deposit_amount([])
        assert result == Decimal("0.0")

    def test_none_amount_skipped(self):
        data = [(None, "USD")]
        result = get_not_rollbacked_deposit_amount(data)
        assert result == Decimal("0.0")

    def test_none_currency_skipped(self):
        data = [(Decimal("100"), None)]
        result = get_not_rollbacked_deposit_amount(data)
        assert result == Decimal("0.0")

    def test_both_none_skipped(self):
        data = [(None, None)]
        result = get_not_rollbacked_deposit_amount(data)
        assert result == Decimal("0.0")

    def test_single_usd(self):
        data = [(Decimal("100"), "USD")]
        result = get_not_rollbacked_deposit_amount(data)
        assert result == Decimal("100.0")

    def test_single_eur(self):
        data = [(Decimal("100"), "EUR")]
        result = get_not_rollbacked_deposit_amount(data)
        assert result == Decimal("100.0") * Decimal("0.9342")

    def test_multiple_currencies(self):
        data = [
            (Decimal("100"), "USD"),
            (Decimal("200"), "EUR"),
        ]
        result = get_not_rollbacked_deposit_amount(data)
        expected = Decimal("100.0") * Decimal("1") + Decimal("200.0") * Decimal("0.9342")
        assert result == expected

    def test_mixed_with_nones(self):
        data = [
            (Decimal("100"), "USD"),
            (None, "EUR"),
            (Decimal("50"), None),
            (None, None),
            (Decimal("200"), "BTC"),
        ]
        result = get_not_rollbacked_deposit_amount(data)
        expected = Decimal("100.0") * Decimal("1") + Decimal("200.0") * Decimal("100000.0")
        assert result == expected

    def test_decimal_amounts(self):
        data = [(Decimal("99.99"), "USD")]
        result = get_not_rollbacked_deposit_amount(data)
        assert result == Decimal("99.99")

    def test_zero_amount(self):
        data = [(Decimal("0"), "USD")]
        result = get_not_rollbacked_deposit_amount(data)
        assert result == Decimal("0.0")


class TestGetNotRollbackedWithdrawAmount:
    def test_empty_list_returns_zero(self):
        result = get_not_rollbacked_withdraw_amount([])
        assert result == Decimal("0.0")

    def test_none_amount_skipped(self):
        data = [(None, "USD")]
        result = get_not_rollbacked_withdraw_amount(data)
        assert result == Decimal("0.0")

    def test_none_currency_skipped(self):
        data = [(Decimal("100"), None)]
        result = get_not_rollbacked_withdraw_amount(data)
        assert result == Decimal("0.0")

    def test_both_none_skipped(self):
        data = [(None, None)]
        result = get_not_rollbacked_withdraw_amount(data)
        assert result == Decimal("0.0")

    def test_single_usd(self):
        data = [(Decimal("50"), "USD")]
        result = get_not_rollbacked_withdraw_amount(data)
        assert result == Decimal("50.0")
