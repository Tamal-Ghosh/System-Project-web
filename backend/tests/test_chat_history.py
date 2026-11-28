import tempfile
from pathlib import Path
import unittest
from assistant.history import ChatHistory


class HistoryTests(unittest.TestCase):
    def test_isolation_feedback_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'history.sqlite'
            store = ChatHistory(path)
            identity = store.add('case-a', 'Question', {'answer': 'Evidence'})
            self.assertEqual(store.list('case-b'), [])
            with self.assertRaises(LookupError):
                store.rate('case-b', identity, 'helpful')
            store.rate('case-a', identity, 'helpful')
            self.assertEqual(ChatHistory(path).list('case-a')[0]['id'], identity)
