# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from backend.diet.vision import _extract_error_from_opencode_response


class TestDietVisionOpenCodeError(unittest.TestCase):
    def test_extracts_message_from_response_body_json(self) -> None:
        data = {
            "info": {
                "error": {
                    "name": "APIError",
                    "data": {
                        "statusCode": 403,
                        "message": "Provider returned error",
                        "responseBody": '{"error":{"message":"Free tier exhausted","code":"AllocationQuota.FreeTierOnly"}}',
                    },
                }
            },
            "parts": [],
        }

        msg = _extract_error_from_opencode_response(data)
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("APIError", msg)
        self.assertIn("403", msg)
        self.assertIn("Free tier exhausted", msg)


if __name__ == "__main__":
    unittest.main()

