"""Functions for doing decorrelation analysis


"""
import numpy as np
import pandas as pd
from sklearn import isotonic
from scipy.optimize import curve_fit
from statsmodels.tsa import stattools

from . import NotEquilibratedError


def split_around(sig, thresh):
    """Split *sig* around the first occurence of *thresh*

    Works on rising signals

    Parameters
    ----------
    sig : pd.Series
      timeseries to split
    thresh : float
      value to trigger the split

    Returns
    -------
    before, after : pd.Series
      sections of sig from before and after the threshold value
    """
    split = sig[sig > thresh].index[0]

    return sig.loc[:split].iloc[:-1], sig.loc[split:]


def check_flat(sig, max_drift=5):
    """Check a portion of signal is flat, else raise error

    Flat defined as not drifting more than 5% of mean
    """
    x0, c = np.polyfit(sig.index, sig.values, 1)

    y0 = c + x0 * sig.index[0]
    y1 = c + x0 * sig.index[-1]

    totdrift = 100 * abs((y1 - y0) / sig.mean())

    # if x0 is very small, dont calculate drift and assume flat
    # fixes issue with very long time series
    return (x0 > 1e-4) and (totdrift > max_drift)


def find_eq(signal):
    """Given a timeseries, figure out where it became equilibrated

    Parameters
    ----------
    signal : pd.Series
      total combined raw signal from a given parallel_id

    Returns
    -------
    eq : int
      index of the step at which equilibrium is reached

    Raises
    ------
    NotEquilibratedError
      if the back half of the signal has over 5% drift
    """
    back = signal.tail(len(signal) // 2)

    # raises NotEquilibratedError if not flat
    #if not check_flat(back):
    #    raise NotEquilibratedError

    ir = isotonic.IsotonicRegression()
    ir_fit = pd.Series(ir.fit_transform(signal.index, signal.values),
                       index=signal.index)
    # find first point that we hit one "wiggle" below the max value
    eq = ir_fit[ir_fit >= (ir_fit.iloc[-1] - back.std())].index[0]

    return eq


def grab_until(sig, thresh):
    """Works on falling signals"""
    # find index where signal is first below value
    cut = sig[sig < thresh].index[0]

    return sig[:cut].iloc[:-1]  # return signal up to cut, excluding cut


def grab_after(sig, thresh):
    """Works on falling signals"""
    cut = sig[sig < thresh].index[0]

    return sig.loc[cut:]


def exp_fit(x, tau):
    return np.exp(-x/tau)


def do_exp_fit(sig, thresh=0.1):
    """Fit an exponential up to thresh

    Single exponential::
      y = exp(-x/tau)

    Parameters
    ----------
    sig : pd.Series
      timeseries of the signal
    thresh : float, optional
      value at which to cut off the signal when fitting

    Returns
    -------
    result : float
      coefficient for tau
    """
    sig = grab_until(sig, thresh)
    # grab sig up to where it first goes below threshhold

    x, y = sig.index, sig.values
    return curve_fit(exp_fit, x, y, p0=10000)[0][0]


def find_g(signal, tmax=5000000, thresh=0.1):
    """Given the equilibrated portion of a signal, calculate the stat. ineff.

    Parameters
    ----------
    signal : pd.Series
      equilibrated portion of the results from a given parallel_id
    tmax : int
      maximum number of MC steps to look ahead in the timeseries to
      look for decorrelation
    thresh : float
      value of autocorrelation to truncate the exponential fitting
      procedure

    Returns
    -------
    g : int
      the statistical inefficiency of this data series.  Ie the number of steps
      required between samples.
    """
    # find how many rows of sig we will use
    # the signal won't start at t=0, therefore find the offset and adjust
    t0 = signal.index[0]
    nlags = len(signal.loc[:t0 + tmax])  # this then finds
    acf = stattools.acf(signal, fft=True, nlags=nlags)
    # (nlags + 1) as acf at zero is returned
    acf = pd.Series(acf, signal.index[:nlags + 1] - t0)

    return int(do_exp_fit(acf, thresh=thresh))
