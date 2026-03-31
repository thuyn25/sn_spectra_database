import numpy as np
from auxiliary import polyval
from scipy.optimize import curve_fit

def sgfilter(spec, outwav, res=100, order=2):
    """
    Smooth a spectrum using the generalized Savitzky-Golay method.

    `spec` is a numpy structured array
           spec['wav'] --> wavelengths of the input spectrum
           spec['flux'] --> flux densities of the input spectrum
           spec['eflux'] --> [optional] flux uncertainties

    `outwav` is a numpy array provideing the wavelengths at which to
           compute the output, smoothed spectrum.

    `res` is the smoothing parameter

    `order` is the order for the polynomials fit at each output wavelength
    """

    start = [1 for x in range(order + 1)]

    outspec = np.zeros( len(outwav), dtype=spec.dtype)
    outspec['wav'] = outwav
    outspec['flux'] = np.nan
    for i, wav in enumerate(outwav):
        if wav <= np.min(spec['wav']) or wav >= np.max(spec['wav']):
            continue
        # which data are we fitting?
        dwav = wav / res
        w = np.isfinite(spec['flux']) & (np.abs(spec['wav'] - wav) <= dwav)

        # do we have enough data points to fit the given order?
        if w.sum() < (order + 1):
            continue

        # fit the polynomial
        meanwav = np.mean(spec['wav'][w])
        meanflux = np.mean(spec['flux'][w])
        if 'eflux' in outspec.dtype.names:
            sigma = spec['eflux'][w]
        else:
            sigma = None

        try:
            popt, pcov = curve_fit(polyval,
                                   spec['wav'][w] - meanwav,
                                   spec['flux'][w] - meanflux,
                                   sigma=sigma,
                                   p0=start,
                                   maxfev=10000)
            # get the polynomial value at wav
            outspec['flux'][i] = np.polyval(popt, wav - meanwav) + meanflux
        except RuntimeError as e:
            print(f'Warning: curve_fit failed at wav={wav:.2f} A with error: {e}')
            outspec['flux'][i] = meanflux
            continue

        # get the uncertainty at wav
        if 'eflux' in outspec.dtype.names:
            outspec['eflux'][i] = np.sqrt(np.sum([((wav - meanwav)**(order - i))**2 * var
                                                  for i, var in enumerate(np.diag(pcov))]))

        # reset the starting guess for next time
        start = popt

    return outspec


def sgfilter2(spec, outwav, cspacing=None, res=100, order=2):
    """
    Smooth a spectrum using the generalized Savitzky-Golay method.

    `spec` is a numpy structured array
           spec['wav'] --> wavelengths of the input spectrum
           spec['flux'] --> flux densities of the input spectrum
           spec['eflux'] --> [optional] flux uncertainties

    `outwav` is a numpy array provideing the wavelengths at which to
           compute the output, smoothed spectrum.

    `res` is the smoothing parameter

    `order` is the order for the polynomials fit at each output wavelength
    """
    if cspacing is None:
        cspacing=outwav/res
    if not isinstance(cspacing,np.ndarray) or (np.size(cspacing)!=np.size(outwav)):
        print("SGFILTER2: Error with cspacing array, defaulting to newwav/R")
        cspacing=outwav/res

    start = [1 for x in range(order + 1)]

    outspec = np.zeros( len(outwav), dtype=spec.dtype)
    outspec['wav'] = outwav
    outspec['flux'] = np.nan
    for i, wav in enumerate(outwav):
        if wav <= np.min(spec['wav']) or wav >= np.max(spec['wav']):
            continue
        # which data are we fitting?
        dwav = cspacing[i]
        w = np.isfinite(spec['flux']) & (np.abs(spec['wav'] - wav) <= dwav)

        # do we have enough data points to fit the given order?
        if w.sum() < (order + 1):
            continue

        # fit the polynomial
        meanwav = np.mean(spec['wav'][w])
        meanflux = np.mean(spec['flux'][w])
        if 'eflux' in outspec.dtype.names:
            sigma = spec['eflux'][w]
        else:
            sigma = None

        try:
            popt, pcov = curve_fit(polyval,
                               spec['wav'][w] - meanwav,
                               spec['flux'][w] - meanflux,
                               sigma=sigma,
                               p0=start,
                               maxfev=10000)

            # get the polynomial value at wav
            outspec['flux'][i] = np.polyval(popt, wav - meanwav) + meanflux
        except RuntimeError as e:
            print(f'Warning: curve_fit failed at wav={wav:.2f} A with error: {e}')
            outspec['flux'][i] = meanflux
            continue

        # get the uncertainty at wav
        if 'eflux' in outspec.dtype.names:
            outspec['eflux'][i] = np.sqrt(np.sum([((wav - meanwav)**(order - i))**2 * var
                                                  for i, var in enumerate(np.diag(pcov))]))

        # reset the starting guess for next time
        start = popt

    return outspec
