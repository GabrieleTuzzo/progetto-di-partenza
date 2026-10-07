import unittest
from decimal import Decimal
from unittest.mock import patch

import server


class FinbankMcpTests(unittest.TestCase):
    def test_transfer_simulation_reads_accounts_without_mutating_them(self) -> None:
        source = {"balance": "1000.00", "currency": "EUR", "status": "ACTIVE"}
        target = {"balance": "500.00", "currency": "EUR", "status": "ACTIVE"}
        with patch.object(server, "_api_get", side_effect=[source, target]) as api_get:
            result = server.simulate_transfer(1, 2, "125.50")

        self.assertTrue(result["would_succeed"])
        self.assertEqual(result["source"]["balance_after"], "874.50")
        self.assertEqual(result["target"]["balance_after"], "625.50")
        self.assertTrue(result["simulation_only"])
        self.assertEqual(
            [call.args[0] for call in api_get.call_args_list],
            ["/api/accounts/1", "/api/accounts/2"],
        )

    def test_recent_movements_are_capped_by_the_server(self) -> None:
        movements = [
            {
                "id": movement_id,
                "type": "TRANSFER_IN",
                "amount": "1.00",
                "counterpartyAccountId": 2,
                "executedAt": "2026-10-07T10:00:00Z",
                "description": "must not leak",
            }
            for movement_id in range(15)
        ]
        with patch.object(server, "_api_get", return_value=movements):
            result = server.get_recent_movements(1, limit=100)

        self.assertEqual(result["count"], server.MAX_MOVEMENTS)
        self.assertEqual(len(result["movements"]), server.MAX_MOVEMENTS)
        self.assertNotIn("description", result["movements"][0])

    def test_amount_validation_uses_decimal_values(self) -> None:
        self.assertEqual(server._money("12.30"), Decimal("12.30"))
        for invalid_amount in ("0", "-1.00", "1.001", "NaN", "100000000000000000.00"):
            with self.subTest(amount=invalid_amount):
                with self.assertRaises(ValueError):
                    server._money(invalid_amount)

    def test_backend_failure_is_not_converted_to_a_success_shaped_result(self) -> None:
        with patch.object(
            server,
            "_api_get",
            side_effect=RuntimeError("LipariBank backend is unavailable."),
        ):
            with self.assertRaisesRegex(RuntimeError, "backend is unavailable"):
                server.get_account_balance(1)


if __name__ == "__main__":
    unittest.main()
