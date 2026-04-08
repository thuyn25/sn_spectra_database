'''
author:        thuyn25 <thuyn27@lsu.edu>
date:          2026-03-30 11:22:35
Copyright © YourCompanyName All rights reserved
'''
import os
import glob
import numpy as np
from scipy.interpolate import interp1d
from sgfilter import sgfilter2
from specload import read_spec

import matplotlib.pylab as plt
plt.rc('axes', labelsize=14)
plt.rc('axes', labelweight='bold')
plt.rc('figure', titlesize=16)
plt.rc('figure', titleweight='bold')
plt.rc('font', family='sans-serif')
plt.rcParams['errorbar.capsize'] = 3
opts = {'mec':'k', 'mew': 0.5, 'lw': 1}
plt.rcParams['figure.figsize'] = (20, 10)
plt.rcParams['xtick.direction'] = 'out'
plt.rcParams['ytick.direction'] = 'out'
plt.rcParams['xtick.top'] = True
plt.rcParams['ytick.right'] = True
plt.rcParams['xtick.minor.visible'] = True
plt.rcParams['ytick.minor.visible'] = True

def smooth_template(template, newwav, cspacing, isok, lowwav=None, highwav=None, redshift=0.0, **kwargs):
    w = (template['wav']>=newwav.min())&(template['wav']<=newwav.max())
    tspec = template[w]
    isok=isok[w]
    tspec['wav'] = tspec['wav'] / (1+redshift)
    nwav=np.size(tspec['wav'])

    if 'res' in kwargs:
        res = kwargs['res']
    else: res = 100

    if 'order' in kwargs:
        order=kwargs['order']
    else: order = 4

    if lowwav is None:
        lowwav = np.min(tspec['wav'])
    if highwav is None: 
        highwav = np.max(tspec['wav'])

    # identify gaps in coverage
    dwav = tspec['wav'][1:]-tspec['wav'][:-1]
    res = np.median(newwav/cspacing)
    w = np.argwhere(dwav>tspec['wav'][:-1]/res).flatten()
    nw=np.size(w)
    isgap = np.zeros(np.size(newwav))
    for i in range(0, nw):
        if np.size(tspec['wav'][w[i]])==0:
            continue
        wgap=(newwav >= np.min(tspec['wav'][w[i]]))&(newwav <= np.max(tspec['wav'][w[i]]))
        ngap = np.sum(wgap)
        if np.any(wgap):
            cspacing[wgap] = np.max(newwav[wgap]) - np.min(newwav[wgap])
            isgap[wgap] = 1

    wgap = isgap==1
    ngap=np.sum(wgap)
    dwav = np.median(tspec['wav'][1:] - tspec['wav'][:-1])
    datares = np.median(tspec['wav'][:-1] / (tspec['wav'][1:] - tspec['wav'][:-1]))
    if lowwav is None:
        lowwav = np.min(tspec['wav'])
    if highwav is None: 
        highwav = np.min(tspec['wav'])

    use_eflux = np.median(tspec['eflux']) > 0 

    dtype=[('wav',float),('flux',float),('eflux',float)]
    # Smooth the spectrum
    if datares < 300 or not use_eflux:
        print('input data are low resolution (R='+str(datares)+')...no smoothing applied!')
        finterp = interp1d(tspec['wav'],tspec['flux'],bounds_error=False)
        newflux = finterp(newwav)
        finterp = interp1d(tspec['wav'],tspec['eflux'],bounds_error=False)
        neweflux = finterp(newwav)
        wfin=np.isfinite(newflux)&np.isfinite(neweflux)
        
        if not np.any(wfin):
            return np.array([], dtype=dtype)
        
        smoothspec=[]
        for l,f,e in zip(newwav[wfin],newflux[wfin],neweflux[wfin]):
            smoothspec.append(np.array((l,f,e),dtype=dtype))
        smoothspec=np.array(smoothspec)
    else:
        pull=0
        nlast=0
        nuse=nwav
        niter=0
        while nlast != nuse:
            if not pull:
                wuse=isok==1
                nuse=np.sum(wuse)
            else:
                wuse=(isok==1)&(np.logical_not(np.isfinite(pull))|np.abs(pull)<3.0)
                nuse=np.sum(wuse)
            
            if nuse < 4:
                print('too few points to smooth! Returning empty array.')
                return np.array([], dtype = dtype)
            print('smoothing data...', niter)
            smoothspec = sgfilter2(tspec[wuse], newwav, cspacing=cspacing, res=res, order=order)
            smoothspec['eflux'][wgap]=smoothspec['flux'][wgap]
            wfin=np.isfinite(smoothspec['flux'])&np.isfinite(smoothspec['eflux'])
            smoothspec=smoothspec[wfin]
            finterp=interp1d(smoothspec['wav'],smoothspec['flux'],kind='cubic',fill_value='extrapolate')
            smoothed=finterp(tspec['wav'])
            diff=tspec['flux']-smoothed
            diff-=np.median(diff)
            # Test the standard deviations
            iwavstep=100*dwav
            ntest=int(np.floor((np.max(tspec['wav'])-np.min(tspec['wav']))/iwavstep))
            testwav=np.empty(ntest);teststd=np.empty(ntest)
            testwav[:]=np.nan;teststd[:]=np.nan
            wavstep=(np.max(tspec['wav'])-np.min(tspec['wav']))/ntest
            for i in range(ntest):
                w=(isok==1)&np.isfinite(diff)&(tspec['wav']>=np.min(tspec['wav'])+i*wavstep)&(tspec['wav']<=np.min(tspec['wav'])+(i+1)*wavstep)
                nw=np.sum(w)
                if nw<5:
                    continue
                testwav[i]=np.median(tspec['wav'][w])
                teststd[i]=np.std(diff[w])
            w=np.isfinite(teststd)
            if np.sum(w)==0:
                print('encountered NAN error in smooth_template!...ignoring!')
                break
            finterp=interp1d(testwav,teststd,bounds_error=False)
            pull=diff/finterp(tspec['wav'])
            nlast=nuse
    if smoothspec.size == 0:
        print('smoothspec.size == 0. Returning empty array.')
        return np.array([], dtype=dtype)
    wok=(smoothspec['wav']>=lowwav)&(smoothspec['wav']<=highwav)
    return smoothspec[wok]

def process_templates(inbase, outbase):
    files = glob.glob(inbase+'*/*/*.dat')

    dz = 0.001
    step = np.log10(1+dz)   #logarithmic wavelength binning                   
    logwav = np.arange(3.0, 4.0+step, step)
    newwav=np.power(10, logwav)
    res=100
    order = 4
    counter_unk = 0
    total_files = 0
    counter_success = 0
    for file in files:
        print(file)
        total_files += 1
        f = open(file, 'r')
        header = f.readline()
        header += f.readline()
        parts = f.readline().split("=")
        redshift=float(parts[1])
        parts = f.readline().split("=")
        sn_type = parts[1].strip()
        parts = f.readline().split("=")
        phase = float(parts[1])

        parts = file.split('/')
        filename = parts[-1]
        atype = parts[-2]
        sn_name = filename.split('.')[0]
        outdir = os.path.join(outbase, atype)
        # print(outdir)
        os.makedirs(outdir, exist_ok=True)
        outname = os.path.join(outdir, filename)
        # print(outname, '\n')

        spec, isest = read_spec(file)
        if (np.min(spec['wav'])>np.max(newwav)) or (np.max(spec['wav'])<np.min(newwav)):
            print('Spectrum does not cover the wavelength range of interest. Skip the event.\n')
            counter_unk += 1
            continue
        
        fnorm = 1. / np.median(spec['flux'])
        spec['flux'] *= fnorm
        spec['eflux'] *= fnorm

        minwav=np.min(spec['wav'])
        maxwav=np.max(spec['wav'])
        wavrange=maxwav-minwav
        cspacing=newwav/res

        # extra smoothing on ends
        margin=0.1
        w=newwav<minwav+margin*wavrange
        c=np.polyfit([0,margin*wavrange],[2,1],1)
        cspacing[w]*=np.polyval(c,newwav[w]-minwav)
        w=newwav>maxwav-margin*wavrange
        c=np.polyfit([wavrange,wavrange-margin*wavrange],[2,1],1)
        cspacing[w]*=np.polyval(c,newwav[w]-minwav)
        
        # Clip galaxy emissions
        if (atype=="SNIIn") or (atype=="SLSN-IIn") or (atype=="SNIa-CSM"):
            # Increase resolution around H-alpha/beta
            w=((newwav>6516)&(newwav<6628))|((newwav>4825)&(newwav<4921))
            cspacing[w]=newwav[w]/200.
        gallines=np.array([2795.528, # Mg II
                        2802.704, # Mg II
                        3726.1, # [O II]
                        3728.8, # [O II]
                        3933.66, # Ca-II K
                        3968.47, # Ca-II H
                        3970.075, # H-epsilon
                        4101.734, #H-delta
                        4340.472, #H-gamma
                        4861.35, #H-beta
                        4958.911, # [O III]
                        5006.843, # [O III]
                        5891.94, # Na I
                        6548.05, # [N II]
                        6562.79, # H-alpha
                        6583.45]) # [N II]
        galwinds = gallines / 500.
        for lin,win in zip(gallines, galwinds):
            wclip = (spec['wav']>=lin-win/2.)&(spec['wav']<=lin+win/2.)
            spec['eflux'][wclip] =np.inf
        isok=np.ones(len(spec['wav']))
        lowwav = np.min(spec['wav'])
        highwav = np.max(spec['wav'])

        median_eflux = np.median(spec['eflux'])

        if median_eflux > 0:
            w2 = spec['eflux']/np.median(spec['eflux'])<10
            if np.any(w2):
                if np.min(spec['wav'][w2]) >= lowwav:
                    lowwav = np.min(spec['wav'][w2])
                if np.max(spec['wav'][w2]) <= highwav:
                    highwav = np.max(spec['wav'][w2])
        else:
            print(f'This {filename} has zero/fake eflux. Skipping eflux filtering.')                    
        # w2 = spec['eflux']/np.median(spec['eflux'])<10
        # if np.min(spec['wav'][w2]) >= lowwav:
        #     lowwav = np.min(spec['wav'][w2])
        # if np.max(spec['wav'][w2]) <= highwav:
        #     highwav = np.max(spec['wav'][w2])
        
        temspec = smooth_template(spec, newwav, cspacing, isok, lowwav=lowwav, highwav=highwav,res=res, order=order)
        if temspec.size == 0:
            print(f'this {filename} is empty.')
        header += f'starting wavelength: {lowwav:.3f} A\n'
        header += f'ending wavelength: {highwav:.3f} A\n'
        header += '\n'
        header += "wav\tflux\teflux\n"
        np.savetxt(outname, temspec, header=header)
        counter_success += 1
        plt.figure()
        plt.plot(spec['wav'], spec['flux'], label=f'original {filename}')
        plt.plot(temspec['wav'], temspec['flux'], label='smoothed', linestyle='--', color='r')
        plt.xlim(2000, 10000)
        plt.ylim(-5, 5)
        plt.title(sn_name)
        plt.legend()
        plt.savefig(outname.replace('.dat', '.png'), dpi=300)
        plt.close()
    
    print(f'Total files processed: {total_files}')
    print(f'Successfully processed files: {counter_success}')
    print(f'Files skipped due to wavelength coverage issues: {counter_unk}')
    return 

if __name__ == '__main__':

    inbase = "../data/processed2"
    outbase = "../data/templates2"

    process_templates(inbase, outbase)