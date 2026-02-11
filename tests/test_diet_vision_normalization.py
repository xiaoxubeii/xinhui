# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from backend.diet.models import DietVisionRawResult
from backend.diet.vision import _normalize_parsed


class TestDietVisionNormalization(unittest.TestCase):
    def test_warnings_string_and_totals_aliases(self) -> None:
        parsed = {
            "items": [],
            "totals": {
                "calories": 0,
                "protein": 0,
                "carbohydrates": 0,
                "fat": 0,
                "fiber": 0,  # should be ignored
            },
            "warnings": "无法识别图片中的食物，请提供清晰图片。",
        }

        known = _normalize_parsed(parsed)
        self.assertIsInstance(known["warnings"], list)
        self.assertEqual(known["warnings"], ["无法识别图片中的食物，请提供清晰图片。"])
        self.assertIn("totals", known)
        self.assertEqual(known["totals"]["calories_kcal"], 0.0)
        self.assertEqual(known["totals"]["protein_g"], 0.0)
        self.assertEqual(known["totals"]["carbs_g"], 0.0)
        self.assertEqual(known["totals"]["fat_g"], 0.0)

        result = DietVisionRawResult.model_validate(known)
        self.assertEqual(result.warnings, ["无法识别图片中的食物，请提供清晰图片。"])

    def test_items_aliases_and_warning_key(self) -> None:
        parsed = {
            "foods": [
                {
                    "food": "米饭",
                    "weight": "200g",
                    "calories": "260",
                    "protein": "5g",
                    "carbohydrates": "57g",
                    "fat": "1.0g",
                    "confidence": 80,  # percent
                }
            ],
            "warning": ["test"],
        }

        known = _normalize_parsed(parsed)
        result = DietVisionRawResult.model_validate(known)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].name, "米饭")
        self.assertEqual(result.items[0].grams, 200.0)
        self.assertEqual(result.items[0].calories_kcal, 260.0)
        self.assertEqual(result.items[0].protein_g, 5.0)
        self.assertEqual(result.items[0].carbs_g, 57.0)
        self.assertEqual(result.items[0].fat_g, 1.0)
        self.assertEqual(result.items[0].confidence, 0.8)
        self.assertEqual(result.warnings, ["test"])


if __name__ == "__main__":
    unittest.main()

