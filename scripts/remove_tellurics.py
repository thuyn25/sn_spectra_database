import numpy as np
from scipy.ndimage import filters
from scipy.interpolate import splrep, splev, interp1d
from scipy.optimize import curve_fit
from pydl.pydlutils import bspline

from loader import Loader
from auxiliary import load_lines
from specload import read_spec
from bspline_fitting import bspline_iterfit

# import matplotlib.pylab as plt
# plt.rc('axes', labelsize=14)
# plt.rc('axes', labelweight='bold')
# plt.rc('figure', titlesize=16)
# plt.rc('figure', titleweight='bold')
# plt.rc('font', family='sans-serif')
# plt.rcParams['errorbar.capsize'] = 3
# opts = {'mec':'k', 'mew': 0.5, 'lw': 1}
# plt.rcParams['figure.figsize'] = (20, 10)
# plt.rcParams['xtick.direction'] = 'out'
# plt.rcParams['ytick.direction'] = 'out'
# plt.rcParams['xtick.top'] = True
# plt.rcParams['ytick.right'] = True
# plt.rcParams['xtick.minor.visible'] = True
# plt.rcParams['ytick.minor.visible'] = True

def gauss(x, mu, sig):
    return np.exp(-(x-mu)**(2.0)/(2*sig**2)) / np.sqrt(2*np.pi*sig**2)

def degrade_telluric(telspec, binnedwav, R=500):
	dwav = 2*(np.max(binnedwav) - np.min(binnedwav))/np.size(binnedwav)
	dwsig = dwav/(2.*np.sqrt(2.*np.log(2.)))
	# Convolve
	flux_conv = filters.gaussian_filter(telspec['flux'], dwsig)
	# Re-bin
	tck = splrep(telspec['wav'], flux_conv)
	flux_rebin = splev(binnedwav, tck)
	w = (binnedwav < telspec['wav'].min()) | (binnedwav > telspec['wav'].max())
	flux_rebin[w] = 1
	# Degrade to our spectrum's rough resolving power
	fwhm = telspec['wav']/R
	G_sig = fwhm/(2.*np.sqrt(2.*np.log(2.)))
	loader = Loader('Degrading telluric spectrum...')
	loader.start()
	G_mat = np.vstack([np.hstack([gauss(lam,mu,sig) for lam in binnedwav]) for mu, sig in zip(binnedwav, G_sig)])
	tel_corr = np.dot(flux_rebin * dwav, G_mat)
	loader.stop()
	tel_corr /= np.median(tel_corr)
	# Filter out extrapolations
	w = (binnedwav < telspec['wav'].min()) | (binnedwav > telspec['wav'].max())
	tel_corr[w] = 1.
    # Get the output telluric spectrum
	detell = []
	for w,t in zip(binnedwav, tel_corr):
		detell.append(np.array((w,t),dtype=[('wav',float),('flux',float)]))
	detell = np.array(detell)
	return detell

def fit_tellspec(tellwav,telluric,senswav2,tellspec2,wav,flux,eflux,minwav,maxwav,chem,z=0.0):
	tellfit=np.ones(np.size(wav))
	finterp=interp1d(tellwav,telluric,fill_value=(1.0,1.0),bounds_error=False)
	tell=finterp(wav)
	w=(wav*(1+z)<np.min(tellwav))|(wav*(1+z)>np.max(tellwav))
	tell[w]=1.0
	wcont=(wav*(1+z)>minwav)&(wav*(1+z)<maxwav)&(tell>=0.995)&np.isfinite(flux)
	wcomp=np.logical_not(wcont)
	tellshift=0.;tellscale=0.
	if np.sum(wcont) >= 4:
		cset=bspline_iterfit(wav[wcont]*(1+z),flux[wcont],kspace=200.,silence=True)
		if isinstance(cset[0],float):
			step=200.
			N=int((maxwav-minwav)/step)+1
			placed=np.linspace(minwav,maxwav,N)
			newplaced=np.array([])
			for j in range(0,len(placed)):
				w = abs(placed[j]-wav[wcomp]*(1+z))<10
				if np.sum(w)==0:
					newplaced=np.append(newplaced,placed[j])
			cset=bspline.iterfit(wav[wcont]*(1+z),flux[wcont],placed=newplaced)
			continuum=cset[0].value(wav*(1+z))[0]
		else:
			continuum=cset[0](wav*(1+z))
		w=np.isfinite(flux)
		if np.sum(w)>10:
			normflux=flux/continuum
			enormflux=eflux/continuum
			wfit=np.isfinite(flux)&(wav*(1+z)>minwav)&(wav*(1+z)<maxwav)
			if np.sum(wfit)>10:
				def model_tell(wavelength,*params):
					shift,scale=params
					finterp=interp1d(senswav2,tellspec2,fill_value=(1.0,1.0),bounds_error=False)
					tell_interp=finterp(wavelength+shift)
					w=(wavelength+shift<np.min(senswav2))|(wavelength+shift>np.max(senswav2))
					tell_interp[w]=1.0
					model=scale*(tell_interp-1)+1
					return model
				#def model_tell(wavelength, *params):
				#	scale=params
				#	finterp=interp1d(senswav2,tellspec2,fill_value=(1.0,1.0),bounds_error=False)
				#	tell_interp=finterp(wavelength)
				#	w=(wavelength<np.min(senswav2))|(wavelength>np.max(senswav2))
				#	tell_interp[w]=1.0
				#	model=scale*(tell_interp-1)+1
				#	return model
				start = [0., 1.] # wavshift, scale
				bounds = ([-np.inf, 0.],[np.inf,np.inf])
				#start=1.
				#bounds=(0.,np.inf)
				popt,pcov=curve_fit(model_tell,wav[wfit]*(1+z),normflux[wfit],sigma=enormflux[wfit],\
										p0=start,bounds=bounds,maxfev=5000)
				#print('scale is', tellscale)
				#print('shift is', tellshift)
				refit=True
				while refit:
					tellfit=model_tell(wav*(1+z),*popt)
					# plt.figure()
					# plt.plot(wav*(1+z),flux,c='k')
					# plt.plot(wav*(1+z),flux/tellfit,ls='--',c='r')
					# plt.show()
					stillcheck=True
					while stillcheck:
						ans=input('adjust Telluric '+chem+' fit (n/y/i)? ')
						if ans.lower()=='i':
							print("Skipping "+chem+" telluric correction!")
							tellfit[:]=1.0
							refit=False
							stillcheck=False
						elif ans.lower()=='y':
							popt[1]=input(f'enter new scale {popt[1]:.4f}): ')
							popt[0]=input(f'enter new shift {popt[0]:.4f}): ')
							stillcheck=False
						elif ans.lower()=='n':
							refit=False
							stillcheck=False
						else:
							print("input not recognized")
		tellshift=popt[0];tellscale=popt[1]
	return tellfit,tellscale,tellshift

def remove_tellurics(obs,tell,z=0.0):
	wav=np.copy(obs['wav']);flux=np.copy(obs['flux']);eflux=np.copy(obs['eflux'])
	tellwav=np.copy(tell['wav']);telluric=np.copy(tell['flux'])
	wo2=((tell['wav']>=6245)&(tell['wav']<=6350)|\
	     (tell['wav']>=6844)&(tell['wav']<=6973)|\
	     (tell['wav']>=7568)&(tell['wav']<=7728))
	wh2o=np.logical_not(wo2)
	tello2=np.ones(np.size(tellwav));tellh2o=np.ones(np.size(tellwav))
	tello2[wo2]=telluric[wo2];tellh2o[wh2o]=telluric[wh2o]
	wtell=(wav*(1+z)>=np.min(tellwav))&(wav*(1+z)<=np.max(tellwav))
	#O2 lines
	senswav2=np.copy(tellwav)
	tellspec2=np.copy(tello2)
	minwav=6500.
	maxwav=8000.
	tellfit,o2tellscale,o2tellshift=fit_tellspec(tellwav,telluric,senswav2,tellspec2,wav,flux,eflux,\
						       minwav,maxwav,chem='O2',z=z)
	tellfit1=np.copy(tellfit)
	flux[wtell]/=tellfit[wtell]
	# H2O lines
	senswav2=np.copy(tellwav)
	tellspec2=np.copy(tellh2o)
	minwav=5500.
	if np.max(wav)>1e4:
		maxwav=10000.
	else:
		maxwav=np.max(wav)
	#h2otellshift,
	tellfit,h2otellscale,h2otellshift=fit_tellspec(tellwav,telluric,senswav2,tellspec2,wav,flux,eflux,\
							   minwav,maxwav,chem='H2O',z=z)
	tellfit2=np.copy(tellfit)
	flux[wtell]/=tellfit[wtell]
	tellfit=tellfit1*tellfit2
	dtype=[('wav',float),('flux',float),('eflux',float)]
	corrspec=[]
	for w,f,e in zip(wav,flux,eflux):
		corrspec.append(np.array((w,f,e),dtype=dtype))
	corrspec=np.array(corrspec)
	return corrspec,o2tellscale,o2tellshift,h2otellscale,h2otellshift



if __name__ == '__main__':
	lines = load_lines()
	sp, isest = read_spec('/home/mbaer/data/spec/newtemp/SN2013fs_2013-10-07_00-00-00_NOT_ALFOSC_iPTF.dat')
	zguess = 0.011855
	sp['eflux'] /= np.median(sp['flux'])
	sp['flux'] /= np.median(sp['flux'])
	ts = np.genfromtxt('/home/mbaer/astr797/telspec/telspec.dat', names='wav,flux')
	binnedwav = np.arange(6000,12000,5)
	tel = degrade_telluric(ts, binnedwav)
	corrspec,o2tellscale,o2tellshift,h2otellscale,h2otellshift = remove_tellurics(sp, tel)
	# fig = plt.figure()
	# plt.plot(sp['wav']/(1+zguess),sp['flux'],'-k')
	# plt.plot(corrspec['wav']/(1+zguess), corrspec['flux'],'--r')
	# plt.show()
