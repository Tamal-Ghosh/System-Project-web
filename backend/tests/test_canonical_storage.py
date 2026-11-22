import unittest
from unittest.mock import MagicMock, patch

from database import AnalysisMismatch, save_explanation_snapshot


class CanonicalStorageTests(unittest.TestCase):
    def test_mismatched_explanation_is_not_linked(self):
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = None
        manager = MagicMock()
        manager.__enter__.return_value = connection
        result = {'model_version': 'model-v2', 'input_hash': 'b' * 64}
        with patch('database._database_url', return_value='test'), \
             patch('database.psycopg.connect', return_value=manager):
            with self.assertRaises(AnalysisMismatch):
                save_explanation_snapshot('analysis', 'explanation', result)
        self.assertIs(manager.__exit__.call_args.args[0], AnalysisMismatch)


if __name__ == '__main__':
    unittest.main()
