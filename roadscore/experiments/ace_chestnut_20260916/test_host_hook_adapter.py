import unittest
import numpy as np
from host_hook_adapter import continuation_inputs


class PrefixTests(unittest.TestCase):
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
