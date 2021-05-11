from scipy.stats import zscore
from scipy import signal
import numpy as np
from numpy.random import Generator, MT19937
from functools import lru_cache


gen = Generator(MT19937(6))


@lru_cache
def make_sos_filter(order, low, high, btype, fs):
    sos = signal.butter(order, [low, high], btype=btype, output='sos', fs=fs)
    return sos


def bandpass(sig, low, high, fs=1250, order=4):
    sos = make_sos_filter(order, low, high, 'bandpass', fs)
    filtered = signal.sosfiltfilt(sos, sig)
    return filtered


def lowpass(sig, cut, fs=1250, order=4):
    sos = signal.butter(order, cut, btype='lowpass', output='sos', fs=fs)
    filtered = signal.sosfiltfilt(sos, sig)
    return filtered


def downsample(raw_sig, factor=16):
    # This is the slowest part of it all
    dwn = signal.decimate(raw_sig, factor, ftype='fir')  # FIR is slower than IIR
    return dwn


def get_band_power(raw_sig, low, high, fs=20000, factor=16, order=4):
    dwn_sig = downsample(raw_sig, factor)
    dwn_fs = int(fs // factor)
    f_sig = bandpass(dwn_sig, low, high, dwn_fs, order)
    h_transf = signal.hilbert(f_sig)
    power = np.abs(h_transf) ** 2
    return power


def delta_theta(lfp, low_delta, high_delta, low_theta, high_theta, fs=20000):
    theta_power = get_band_power(lfp, low_theta, high_theta, fs)
    delta_power = get_band_power(lfp, low_delta, high_delta, fs)
    ratio = zscore(theta_power) / zscore(delta_power)
    return ratio


def speed(acc_sig, factor=16, fs=20000):
    motion = downsample(acc_sig)
    dwn_fs = fs / factor
    n_pts = len(motion)
    end_time = n_pts / dwn_fs
    t = np.linspace(0, end_time, n_pts)
    d_motion = np.gradient(motion, t)
    return d_motion


def is_sleeping(lfp, acc, low_delta=.1, high_delta=3, low_theta=4, high_theta=10, fs=20000):
    ratio = delta_theta(lfp, low_delta, high_delta, low_theta, high_theta, fs=fs)
    motion = speed(acc, fs=fs)
    return ratio, motion


def generate_data(dur=60, fs=20000, noise=1):
    """
    Generates fake data to test analysis functions
    Noise during first third, then delta + theta for a third, then noise
    Accelaration is noise during first fourth, then activity during second 1/4th, then just noise
    during next  1/4 then activity again
    LFP: ____----____
    ACC: ___---___---
    REM: 000000100000

    Parameters
    ----------
    dur: int
        Duration in seconds
        Defaut to 60
    fs: int
        Sampling rate in Hz
        Defaults to 20000 Hz
    noise: float
        Scale of noise

    Returns
    -------

    """
    n_pts = dur * fs
    end_time = n_pts / fs
    t = np.linspace(0, end_time, n_pts)
    delta = np.zeros(n_pts)
    theta = np.zeros(n_pts)
    acc = np.zeros(n_pts) + gen.normal(scale=noise, size=(n_pts,))
    third = n_pts // 3
    fourth = n_pts // 4
    # delta
    for f in gen.uniform(low=1, high=3, size=(5, )):
        delta[third:2*third] += np.sin(2*np.pi*f*t[third:2*third])
    # theta
    for f in gen.uniform(low=4, high=7, size=(5, )):
        theta[third:2*third] += np.sin(2*np.pi*f*t[third:2*third])
    acc[fourth:2*fourth] = gen.normal(loc=3, size=(fourth, ))
    acc[3*fourth:] = gen.normal(loc=3, size=(fourth, ))

    lfp = delta + theta + gen.normal(scale=noise, size=(n_pts,))
    return lfp, acc


if __name__ == '__main__':
    fake_lfp, fake_acc = generate_data(dur=5)
    for _ in range(10):
        is_sleeping(fake_lfp, fake_acc)
