import warnings

import numpy as np
from iminuit import Minuit
from iminuit.cost import LeastSquares
from scipy.stats import norm
from uncertainties import ufloat


def _double_gaussian(x, mu, amp1, sigma1, amp2, sigma2):
    return (amp1 * np.exp(-0.5 * ((x - mu) / sigma1)**2)
            + amp2 * np.exp(-0.5 * ((x - mu) / sigma2)**2))


class DoubleGaussian:
    """A two-component Gaussian mixture sharing a common mean.

    Defined as q * gauss(mean, sigma1) + (1 - q) * gauss(mean, sigma2), where
    q is the core (sigma1) component's share of the total area. A Gaussian's
    integral is amp * sigma * sqrt(2*pi), so amp*sigma -- not amp alone -- is
    proportional to area; the sqrt(2*pi) cancels out of the ratio, leaving
    q = amp1*sigma1 / (amp1*sigma1 + amp2*sigma2).
    """

    def __init__(self, mean, amp1, sigma1, amp2, sigma2):
        self._mean = self._as_ufloat(mean)
        self._amp1 = self._as_ufloat(amp1)
        self._sigma1 = self._as_ufloat(sigma1)
        self._amp2 = self._as_ufloat(amp2)
        self._sigma2 = self._as_ufloat(sigma2)

    @staticmethod
    def _as_ufloat(value):
        if hasattr(value, "nominal_value"):
            return value
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return ufloat(value, 0)

    @classmethod
    def fit(self, hist, fit_range):
        axis = hist.axes[0]
        edges = np.asarray(axis.edges, dtype=np.float64)

        x_vals = 0.5 * (edges[:-1] + edges[1:])
        y_vals = hist.values()
        y_errs = np.sqrt(hist.variances())

        mask = (x_vals >= fit_range[0]) * (x_vals <= fit_range[1])
        x_vals, y_vals, y_errs = x_vals[mask], y_vals[mask], y_errs[mask]

        peak_amp = y_vals.max()
        peak_mu = x_vals[np.argmax(y_vals)]

        ls = LeastSquares(x_vals, y_vals, y_errs, _double_gaussian)
        m = Minuit(
            ls, mu=peak_mu,
            amp1=0.7 * peak_amp, sigma1=3.0,
            amp2=0.3 * peak_amp, sigma2=10.0
        )
        m.limits["sigma1"] = (0, None)
        m.limits["sigma2"] = (0, None)
        m.migrad()
        m.hesse()

        amp1 = ufloat(m.values["amp1"], m.errors["amp1"])
        amp2 = ufloat(m.values["amp2"], m.errors["amp2"])
        mean = ufloat(m.values["mu"], m.errors["mu"])
        sigma1 = ufloat(m.values["sigma1"], m.errors["sigma1"])
        sigma2 = ufloat(m.values["sigma2"], m.errors["sigma2"])

        # Force sigma1 < sigma2 (i.e. sigma1 is the core)
        if sigma1.nominal_value > sigma2.nominal_value:
            sigma1, sigma2 = sigma2, sigma1
            amp1, amp2 = amp2, amp1

        chi2 = m.fmin.reduced_chi2
        return DoubleGaussian(mean, amp1, sigma1, amp2, sigma2), chi2

    @property
    def mean(self):
        return self._mean.nominal_value

    @property
    def mean_err(self):
        return self._mean.std_dev

    @property
    def amp1(self):
        return self._amp1.nominal_value

    @property
    def amp1_err(self):
        return self._amp1.std_dev

    @property
    def sigma1(self):
        return self._sigma1.nominal_value

    @property
    def sigma1_err(self):
        return self._sigma1.std_dev

    @property
    def amp2(self):
        return self._amp2.nominal_value

    @property
    def amp2_err(self):
        return self._amp2.std_dev

    @property
    def sigma2(self):
        return self._sigma2.nominal_value

    @property
    def sigma2_err(self):
        return self._sigma2.std_dev

    @property
    def _q_ufloat(self):
        area1 = self._amp1 * self._sigma1
        area2 = self._amp2 * self._sigma2
        return area1 / (area1 + area2)

    @property
    def q(self):
        """Fraction of total area under the core Gaussian."""
        return self._q_ufloat.nominal_value

    @property
    def q_err(self):
        return self._q_ufloat.std_dev

    def sample(self, x):
        return _double_gaussian(x, self.mean, self.amp1, self.sigma1, self.amp2, self.sigma2)

    def cdf(self, x):
        return (self.q * norm.cdf(x, self.mean, self.sigma1)
                + (1 - self.q) * norm.cdf(x, self.mean, self.sigma2))

    def inverse_cdf(self, p, pad_factor=8.0, n_grid=4000):
        """Numerically inverts cdf() via interpolation, since a two-component
        Gaussian mixture has no closed-form inverse. pad_factor sets how many
        multiples of sigma2 (the wider component) to grid out to on each side
        of mean -- too narrow and the cdf never reaches ~0/~1, so p near 0 or
        1 gets silently clipped to the grid edge instead of extrapolated."""
        pad = pad_factor * self.sigma2
        x_grid = np.linspace(self.mean - pad, self.mean + pad, n_grid)
        cdf_grid = self.cdf(x_grid)
        return np.interp(p, cdf_grid, x_grid)
