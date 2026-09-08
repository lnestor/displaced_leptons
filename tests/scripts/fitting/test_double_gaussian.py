from types import SimpleNamespace

import hist
import numpy as np
import pytest
from scipy.stats import norm

import scripts.fitting.double_gaussian as dg
from scripts.fitting.double_gaussian import DoubleGaussian


def _make_hist(mu, amp1, sigma1, amp2, sigma2, lo=-100, hi=100, nbins=400):
    h = hist.Hist(hist.axis.Regular(nbins, lo, hi), storage=hist.storage.Weight())
    edges = np.asarray(h.axes[0].edges, dtype=np.float64)
    x_centers = 0.5 * (edges[:-1] + edges[1:])
    values = DoubleGaussian(mu, amp1, sigma1, amp2, sigma2).sample(x_centers)
    h.view().value = values
    h.view().variance = np.maximum(values, 1e-3)
    return h


def test_fit_recovers_known_parameters():
    truth = dict(mu=1.5, amp1=700.0, sigma1=8.0, amp2=300.0, sigma2=25.0)
    h = _make_hist(**truth)

    dg, chi2 = DoubleGaussian.fit(h, fit_range=(-60, 60))

    assert dg.mean == pytest.approx(truth["mu"], abs=0.05)
    assert dg.amp1 == pytest.approx(truth["amp1"], rel=1e-2)
    assert dg.sigma1 == pytest.approx(truth["sigma1"], rel=1e-2)
    assert dg.amp2 == pytest.approx(truth["amp2"], rel=1e-2)
    assert dg.sigma2 == pytest.approx(truth["sigma2"], rel=1e-2)
    assert chi2 == pytest.approx(0.0, abs=1e-4)


def test_fit_with_fit_range_masks_data_outside_range():
    truth = dict(mu=0.0, amp1=700.0, sigma1=8.0, amp2=300.0, sigma2=25.0)
    fit_range = (-60, 60)

    h_clean = _make_hist(**truth)
    h_with_spike = _make_hist(**truth)

    h_with_spike.view().value[-1] = 1e6
    h_with_spike.view().variance[-1] = 1e6

    dg_clean, _ = DoubleGaussian.fit(h_clean, fit_range)
    dg_spiked, _ = DoubleGaussian.fit(h_with_spike, fit_range)

    assert dg_spiked.mean == pytest.approx(dg_clean.mean, abs=1e-6)
    assert dg_spiked.sigma1 == pytest.approx(dg_clean.sigma1, abs=1e-6)
    assert dg_spiked.sigma2 == pytest.approx(dg_clean.sigma2, abs=1e-6)


def test_fit_orders_sigma1_as_the_narrower_component(monkeypatch):
    class _FakeMinuit:
        def __init__(self, cost, **kwargs):
            # Deliberately "backwards": sigma1 > sigma2
            self.values = {"mu": 2.0, "amp1": 300.0, "sigma1": 25.0, "amp2": 700.0, "sigma2": 8.0}
            self.errors = {"mu": 0.1, "amp1": 5.0, "sigma1": 0.5, "amp2": 5.0, "sigma2": 0.3}
            self.limits = {}
            self.fmin = SimpleNamespace(reduced_chi2=1.0)

        def migrad(self):
            return self

        def hesse(self):
            return self

    monkeypatch.setattr(dg, "Minuit", _FakeMinuit)

    h = _make_hist(mu=2.0, amp1=300.0, sigma1=25.0, amp2=700.0, sigma2=8.0)
    fitted, _ = DoubleGaussian.fit(h, fit_range=(-60, 60))

    assert fitted.sigma1 < fitted.sigma2
    assert fitted.sigma1 == pytest.approx(8.0)
    assert fitted.amp1 == pytest.approx(700.0)
    assert fitted.sigma2 == pytest.approx(25.0)
    assert fitted.amp2 == pytest.approx(300.0)


def test_q_gives_area_fraction_of_core_gaussian():
    dg = DoubleGaussian(0, 100, 5, 10, 10)
    assert dg.q == pytest.approx(500/600, rel=1e-2)


def test_sample_at_mean_equals_sum_of_amplitudes():
    dg = DoubleGaussian(mean=3.0, amp1=100, sigma1=8, amp2=300, sigma2=25)
    assert dg.sample(3.0) == pytest.approx(400.0)


def test_sample_is_symmetric_about_mean():
    dg = DoubleGaussian(mean=3.0, amp1=100, sigma1=8, amp2=300, sigma2=25)
    offsets = np.linspace(0.5, 40, 20)
    np.testing.assert_allclose(dg.sample(3.0 + offsets), dg.sample(3.0 - offsets))


def test_sample_reduces_to_single_gaussian_when_tail_has_zero_amplitude():
    dg = DoubleGaussian(mean=2.0, amp1=100, sigma1=8, amp2=0, sigma2=25)
    x = np.linspace(-60, 60, 25)
    expected = dg.amp1 * dg.sigma1 * np.sqrt(2 * np.pi) * norm.pdf(x, dg.mean, dg.sigma1)
    np.testing.assert_allclose(dg.sample(x), expected)


def test_cdf_at_mean_equals_one_half():
    dg = DoubleGaussian(mean=3.0, amp1=100, sigma1=8, amp2=300, sigma2=25)
    assert dg.cdf(3.0) == pytest.approx(0.5)


def test_cdf_reduces_to_single_gaussian_when_tail_has_zero_amplitude():
    dg = DoubleGaussian(mean=2.0, amp1=100, sigma1=8, amp2=0, sigma2=25)
    x = np.linspace(-60, 60, 25)
    np.testing.assert_allclose(dg.cdf(x), norm.cdf(x, 2.0, 8))


def test_inverse_cdf_of_cdf_is_noop():
    dg = DoubleGaussian(mean=3.0, amp1=100, sigma1=8, amp2=300, sigma2=25)
    x = np.linspace(-60, 60, 25)
    np.testing.assert_allclose(dg.inverse_cdf(dg.cdf(x)), x, atol=0.5)


def test_inverse_cdf_at_one_half_equals_mean():
    dg = DoubleGaussian(mean=-4.0, amp1=100, sigma1=8, amp2=300, sigma2=25)
    assert dg.inverse_cdf(0.5) == pytest.approx(-4.0, abs=1e-3)


def test_inverse_cdf_reduces_to_single_gaussian_when_tail_has_zero_amplitude():
    dg = DoubleGaussian(mean=2.0, amp1=100, sigma1=8, amp2=0, sigma2=25)
    p = np.linspace(0.05, 0.95, 25)
    np.testing.assert_allclose(dg.inverse_cdf(p), norm.ppf(p, 2.0, 8), atol=1e-3)
