"""Regression tests for the cleaning and business-analysis layer."""

import unittest

from src.analysis import business_answers, kpis, performance_by
from src.data_pipeline import build_data_bundle


class HospitalityPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = build_data_bundle()
        cls.transactions = cls.bundle.transactions

    def test_stay_level_dataset_is_unique_and_complete(self):
        self.assertEqual(len(self.transactions), self.transactions["transaction_id"].nunique())
        self.assertTrue(self.transactions["sales"].ge(0).all())
        self.assertTrue(self.transactions["estimated_profit"].notna().all())

    def test_sales_reconcile_to_revenue_components(self):
        components = self.transactions[["Room_Revenue", "Food_Revenue", "Spa_Revenue", "Other_Revenue"]].sum(axis=1)
        self.assertTrue(self.transactions["sales"].equals(components))

    def test_kpis_and_requested_answers_are_generated(self):
        summary = kpis(self.transactions)
        answers = business_answers(self.transactions)
        self.assertGreater(summary["total_sales"], 0)
        self.assertGreater(summary["orders"], 0)
        self.assertEqual(len(answers), 25)

    def test_category_performance_contains_calculated_margin(self):
        category = performance_by(self.transactions, "category")
        self.assertFalse(category.empty)
        self.assertTrue(category["profit_margin"].between(-1, 1).all())


if __name__ == "__main__":
    unittest.main()
