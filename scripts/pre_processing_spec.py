'''
author:        thuyn25 <thuyn27@lsu.edu>
date:          2026-03-25 13:25:57
Copyright © YourCompanyName All rights reserved
'''
import os
import glob 
from auxiliary import load_lines
import numpy as np
from specload import read_spec
from remove_tellurics import remove_tellurics, degrade_telluric
from astropy.time import Time

def setup_new_templates(inbase, outbase, sndata, remtels=None, telspec=None):
    infiles = glob.glob(inbase+"/*")
    lines = load_lines()
    # /Users/beehuynh/Developer/test_suites/sn_spectra_database/data/raw/osc_raw_data_20260325/2010hy_2010-09-16.dat
    for file in infiles:
        unkflag1 = False     # for 'unknown' max_date, use discovery_date
        unkflag2 = False     # for 'unknown' max_date and discovery_date
        filename=file.split("/")[-1]
        sn_name = filename.split('_')[0]

        print(filename)

        w = sndata['name'] == sn_name   # sndata from SNlist.txt
        # print(w)
        sntype = sndata['type'][w][0]
        redshift = sndata['redshift'][w][0]
        maxdate = sndata['max_date'][w][0]
        
        if maxdate == 'unknown':
            maxdate=sndata['discovery_date'][w][0]
            unkflag1=True
            if maxdate == 'unknown':    # both max_date and disdate = unknown
                continue
            else:
                unkflag2=True
        # print(maxdate)

        maxtime = Time(maxdate, format='isot', scale='utc')
        # Get observation time
        obs_datestr = filename.split('_')[1]
        obs_datestr = obs_datestr.split('.')[0]
        # print(obs_datestr)
        obstime = Time(obs_datestr, format='isot', scale='utc')

        phase = obstime.jd - maxtime.jd
        if phase==0:
            ph='max'
        elif phase < 0:
            ph=f'm{abs(round(phase)):04d}'
        elif phase > 0:
            ph=f'p{abs(round(phase)):04d}'
        
        outname = "sn"+sn_name+'.'+ph+'.dat'

        tspec, isest = read_spec(file, silence=True)
        if remtels is not None:
            if outname in remtels:
                corrspec, o2tellscale, o2tellshift, h2otellscale, h2otellshift = remove_tellurics(tspec, telspec)
            else:
                corrspec=tspec
                o2tellscale=0
                o2tellshift=0
                h2otellscale=0
                h2otellshift=0
        else:
            corrspec = tspec

        outpath= os.path.join(str(outbase),str(sntype))
        os.makedirs(outpath, exist_ok=True)
        outfile = os.path.join(outpath, outname)
        z = float(redshift)
        corrspec['wav'] /= (1+z) #de-redshift
        spec_source = 'unknown'
        header = f'{sn_name} data from WISeREP/OSC\n'
        header+='\n'
        header+=f"de-redshifted assuming z={z:.7f}\n"
        header+=f'type = {sntype}\n'
        header+=f'phase = {phase:.3f}\n'
        header+='\n'
        if isest:
            header+="WARNING: fake error spectrum!\n"
        else: 
            header+="\n"
        if unkflag1:
            header+='Max brightness date unknown; taken as discovery date\n'
            if unkflag2:
                header+='Both max brightness date and discovery date are unknown. Skip the event.\n'
        else:
            header+='\n'
        header+='wav flux eflux'
        np.savetxt(outfile, corrspec, header=header)



if __name__ == '__main__':

    inbase = '/Users/beehuynh/Developer/test_suites/sn_spectra_database/data/raw/osc_raw_data_20260325'
    outbase = '/Users/beehuynh/Developer/test_suites/sn_spectra_database/data/processed/'
    dtype =[('name','<U16'),('type','<U11'), ('redshift','<U10'), ('max_date','<U20'),('discovery_date','<U20')]
    sndata = np.loadtxt('SLSNlist.txt', comments='#', dtype=dtype)
    # w = sndata['name'] == '2009jh' 
    # sntype = sndata['type'][w][0]
    # print(f'With w={w}, retrieving sn type:', sntype)
    # print(sndata, sndata.dtype.names)

    # list of files to remove tellurics; use the standardized template names for output
    remtels=['snCSS121015.max.dat','sn2019cqc.p0009.dat','sn2013hx.p0017.dat',
			'snCSS121015.p0053.dat','sn2018jkq.p0015.dat','sn2019cqc.p0010.dat',
			'sn2019xfs.p0029.dat','snCSS121015.p0400.dat','snCSS121015.m0002.dat',
			'sn2019gsp.p0007.dat','sn2013hx.p0000.dat','sn2013hx.p0018.dat',
			'snCSS121015.p0406.dat','snCSS121015.p0052.dat','snCSS121015.p0407.dat',
			'sn2002ic.p0306.dat','sn2002ic.p0016.dat','sn2011km.p0030.dat',
			'sn2019fcg.m0002.dat','sn2012ca.p0112.dat','sn2017eby.p0015.dat',
			'snPTF12efc.p0008.dat','sn2017ifu.p0051.dat','sn2011km.p0064.dat',
			'sn2002ic.p0020.dat','sn2002ic.p0275.dat','sn2002ic.p0357.dat',
			'snASASSN-15og.p0087.dat','sn2016iks.m0074.dat','sn2011km.p0303.dat',
			'sn2005gj.p0042.dat','sn2012ca.p0527.dat','sn2002ic.p0057.dat',
			'sn2012ca.p0495.dat','snPTF12csy.p0159.dat','sn2008S.m0004.dat',
			'snLSQ14pt.p0008.dat','snLSQ14pt.p0007.dat','sn2010jl.p0459.dat',
			'sn2015da.p0104.dat','sn2010jl.p0025.dat','sn2007pk.m0001.dat',
			'sn1997cy.p0410.dat','snOGLE-2013-SN-016.m0023.dat','sn2015da.p0065.dat',
			'sn2015da.m0079.dat','sn2015da.p0608.dat','sn1995G.p0726.dat',
			'sn2015da.m0053.dat','sn1996L.p0060.dat','snOGLE-2013-SN-019.p0000.dat',
			'sn2015da.p0121.dat','sn2010jl.p0492.dat','sn2015da.m0027.dat',
			'sn2010jl.p0145.dat','sn2005db.p0141.dat','sn2010jl.p0072.dat',
			'sn2007pk.p0076.dat','sn2007sv.p0031.dat','snLSQ13zm.p0028.dat',
			'sn2000ch.p3278.dat','snLSQ13zm.p0022.dat','sn2019abn.p0025.dat',
			'sn2007sv.p0022.dat','snOGLE-2013-SN-137.m0004.dat','sn2017jfs.p0009.dat',
			'sn2019abn.p0053.dat','sn2020agp.p0005.dat','sn2014cn.max.dat',
			'sn2013fs.m0001.dat','sn2013fs.max.dat','sniPTF14flu.p0016.dat',
			'sniPTF15crj.m0008.dat','sniPTF14flu.p0017.dat','sn2019vqd.p0002.dat',
			'sniPTF14flu.p0024.dat','snPTF10fqs.max.dat','snPTF10fqs.p0024.dat']
    
    # Load in the telluric spectrum; this can take a bit since the file is quite large
    print("Loading high-resolution telluric spectrum...")
    ts = np.genfromtxt('telspec.dat', names='wav,flux')
    lines=load_lines()
    binnedwav=np.arange(5500,12000,2.5)
    tell=degrade_telluric(ts, binnedwav)

    setup_new_templates(inbase, outbase, sndata, remtels=remtels, telspec=tell)

    # setup_new_templates(inbase, outbase, sndata)
