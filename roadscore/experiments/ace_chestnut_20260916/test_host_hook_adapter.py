import unittest
import weakref
import tempfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from host_hook_adapter import continuation_inputs, finish_capture, release_preparation_decoder, PreparationOnlyDecoder, HostHookAdapter
from test_hook_planning import fake_prepare, request


class PrefixTests(unittest.TestCase):
    def test_thread_capture_requires_completion_expected_error_and_valid_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            req = request()
            fake_prepare(req, {}, output)
            expected = SimpleNamespace(success=False, error="'outputs'")
            finish_capture(True, expected, req, {}, output)
            finish_capture(True, None, req, {}, output)
            for complete, result in ((False, expected), (True, SimpleNamespace(success=False, error='unrelated failure')),
                                     (True, SimpleNamespace(success=True, error=None))):
                with self.assertRaises(RuntimeError):
                    finish_capture(complete, result, req, {}, output)
            (output / 'context_latents.npy').unlink()
            with self.assertRaises(FileNotFoundError):
                finish_capture(True, expected, req, {}, output)

    def test_preparation_only_releases_weights_but_keeps_capture_dispatch(self):
        class Decoder: pass
        handler = SimpleNamespace(use_mlx_dit=True, mlx_decoder=Decoder(), model=SimpleNamespace(decoder=None))
        reference = weakref.ref(handler.mlx_decoder)
        release_preparation_decoder(handler)
        self.assertIsNone(reference())
        self.assertIsInstance(handler.mlx_decoder, PreparationOnlyDecoder)
        self.assertTrue(handler.use_mlx_dit)
        with self.assertRaises(RuntimeError): handler.mlx_decoder(None)

    def test_release_cannot_mask_failed_conversion_or_torch_fallback(self):
        for use_mlx, decoder, torch_decoder in [(False, object(), None), (True, None, None), (True, object(), object())]:
            handler = SimpleNamespace(use_mlx_dit=use_mlx, mlx_decoder=decoder, model=SimpleNamespace(decoder=torch_decoder))
            with self.assertRaises(RuntimeError): release_preparation_decoder(handler)
        self.assertFalse(HostHookAdapter('/unused').preparation_only)

    def test_exactprefix_only_future_hints_survive(self):
        context = np.arange(1 * 1125 * 128, dtype=np.float32).reshape(1, 1125, 128)
        original = context.copy()
        prefix = np.ones((1, 200, 64), np.float16) * 3
        result, source, mask = continuation_inputs(context, prefix)
        np.testing.assert_array_equal(context, original)
        np.testing.assert_array_equal(result[:, :200, :64], prefix)
        np.testing.assert_array_equal(result[:, 200:, :64], original[:, 200:, :64])
        np.testing.assert_array_equal(source[:, :200], prefix)
        self.assertFalse(mask[:, :200].any())
        self.assertTrue(mask[:, 200:].all())

    def test_wholepreviousresult_or_badprefix_rejected(self):
        context = np.zeros((1, 1125, 128), np.float16)
        with self.assertRaises(ValueError):
            continuation_inputs(context, np.zeros((1, 900, 64), np.float16))
        prefix = np.zeros((1, 200, 64), np.float16)
        prefix[0, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            continuation_inputs(context, prefix)


if __name__ == '__main__':
    unittest.main()
