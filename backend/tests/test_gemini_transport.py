import unittest
from unittest.mock import patch
import httpx
from assistant.gemini import GeminiTextClient, GeminiUnavailable


def success():
    return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'Hello'}]}}]})


class GeminiTransportTests(unittest.TestCase):
    def setup_client(self,responses):
        environment=patch.dict('os.environ',{'GEMINI_API_KEY':'synthetic-test-key','GEMINI_CHAT_FALLBACK_MODELS':''})
        environment.start(); self.addCleanup(environment.stop)
        factory=patch('assistant.gemini.httpx.Client'); client=factory.start().return_value.__enter__.return_value
        self.addCleanup(factory.stop); client.post.side_effect=responses
        sleep=patch('assistant.gemini.time.sleep'); sleep.start(); self.addCleanup(sleep.stop)
        jitter=patch('assistant.gemini.random.uniform',return_value=0); jitter.start(); self.addCleanup(jitter.stop)
        return client

    def test_temporary_503_is_retried(self):
        http=self.setup_client([httpx.Response(503),success()])
        self.assertEqual(GeminiTextClient().generate('Hello','Reply briefly'),'Hello')
        self.assertEqual(http.post.call_count,2)

    def test_retry_count_is_bounded(self):
        http=self.setup_client([httpx.Response(503)]*3)
        with self.assertRaisesRegex(GeminiUnavailable,'HTTP 503'):
            GeminiTextClient().generate('Hello','Reply briefly')
        self.assertEqual(http.post.call_count,3)

    def test_credentials_errors_are_not_retried_or_leaked(self):
        http=self.setup_client([httpx.Response(401,json={'error':'synthetic-sensitive-content'})])
        with self.assertRaises(GeminiUnavailable) as caught:
            GeminiTextClient().generate('Hello','Reply briefly')
        self.assertEqual(http.post.call_count,1)
        self.assertNotIn('sensitive',str(caught.exception))
        self.assertNotIn('synthetic-test-key',str(caught.exception))

    def test_long_retry_after_is_not_ignored(self):
        http=self.setup_client([httpx.Response(429,headers={'Retry-After':'120'})])
        with self.assertRaisesRegex(GeminiUnavailable,'HTTP 429'):
            GeminiTextClient().generate('Hello','Reply briefly')
        self.assertEqual(http.post.call_count,1)

    def test_response_schema_is_forwarded(self):
        http=self.setup_client([success()])
        schema={'type':'object','properties':{'answer':{'type':'string'}}}
        GeminiTextClient().generate('Hello','Reply',json_mode=True,response_schema=schema)
        self.assertEqual(http.post.call_args.kwargs['json']['generationConfig']['responseJsonSchema'],schema)

    def test_timeout_is_retried_and_json_mode_sent(self):
        http=self.setup_client([httpx.ReadTimeout('synthetic timeout'),success()])
        self.assertEqual(GeminiTextClient().generate('Hello','Reply briefly',json_mode=True),'Hello')
        payload=http.post.call_args.kwargs['json']
        self.assertEqual(payload['generationConfig']['responseMimeType'],'application/json')
        self.assertNotIn('thinkingConfig',payload['generationConfig'])


class GeminiFallbackTests(unittest.TestCase):
    setup_client = GeminiTransportTests.setup_client
    def test_explicit_fallback_after_overload(self):
        http=self.setup_client([httpx.Response(503),success()])
        with patch.dict('os.environ',{'GEMINI_CHAT_FALLBACK_MODELS':'gemini-flash-lite-latest'}):
            self.assertEqual(GeminiTextClient(model='primary-model').generate('Hi','Brief'),'Hello')
        self.assertIn('/primary-model:',http.post.call_args_list[0].args[0])
        self.assertIn('/gemini-flash-lite-latest:',http.post.call_args_list[1].args[0])

    def test_rate_limit_does_not_switch_models(self):
        http=self.setup_client([httpx.Response(429),success()])
        with patch.dict('os.environ',{'GEMINI_CHAT_FALLBACK_MODELS':'fallback-model'}):
            GeminiTextClient(model='primary-model').generate('Hi','Brief')
        self.assertTrue(all('/primary-model:' in call.args[0] for call in http.post.call_args_list))


if __name__=='__main__': unittest.main()
