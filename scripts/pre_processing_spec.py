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
from collections import Counter, defaultdict

def setup_new_templates(inbase, outbase, sndata, remtels=None, telspec=None):
    infiles = glob.glob(inbase+"/*")
    lines = load_lines()
    counter_unk = 0
    type_counts = Counter() 
    total_events = 0
    used_filenames = {}

    # /Users/beehuynh/Developer/test_suites/sn_spectra_database/data/raw/osc_raw_data_20260325/2010hy_2010-09-16.dat
    for file in infiles:
        unkflag1 = False     # for 'unknown' max_date, use discovery_date
        unkflag2 = False     # for 'unknown' max_date and discovery_date
        total_events += 1
        filename=file.split("/")[-1]
        parts = filename.split('_')
        sn_name = parts[0]

        sn_version = parts[4] if len(parts) > 4 else '_'
        sn_version = sn_version.split('.')[0]
        
        w = sndata['name'] == sn_name   # sndata from SNlist.txt
        sntype = sndata['type'][w][0]
        if sntype != 'SLSN-I': print(f'{filename} has type {sntype}')
        redshift = sndata['redshift'][w][0]
        maxdate = sndata['max_date'][w][0]
        
        if maxdate == 'unknown':
            maxdate=sndata['discovery_date'][w][0]
            unkflag1=True
            if maxdate == 'unknown':    # both max_date and disdate = unknown
                print(sn_name, maxdate, 'unknown, checking event')
                print(f"Both max_date and discovery_date are unknown for {filename}. Skip the event.")
                counter_unk += 1
                unkflag2=True 
                continue
        if redshift == 'unknown':
            print(f"Redshift is unknown for {filename}. Skip the event.")
            counter_unk += 1
            continue
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
        
        base_outname = f"sn{sn_name}.{ph}"
        extension='.dat'
        if base_outname not in used_filenames:
            outname = base_outname + extension
            used_filenames[base_outname] = 1
        else:
            version_num = used_filenames[base_outname]
            outname = f'{base_outname}_v{version_num:02d}{extension}'
            used_filenames[base_outname] += 1
            print(f'Name collision detected for {sn_name}at phase {ph} => {outname}')


        try:
            tspec, isest = read_spec(file, silence=True)

            if isinstance(tspec, float) or tspec is None:
                print(f'Skipping this file {filename} because failed to load')
                counter_unk += 1
                continue
        except ValueError as e:
            if "B-spline failed to evaluate" in str(e):
                print(f"Error processing {filename}: {e}. Skipping this file.")
                counter_unk += 1
                continue
            else:
                print(f"Unexpected error processing {filename}. Skipping this file.")
                counter_unk += 1
                raise e
            
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
        print('\n\n')
        outpath= os.path.join(str(outbase),str(sntype))
        os.makedirs(outpath, exist_ok=True)
        outfile = os.path.join(outpath, outname)
        z = float(redshift)
        corrspec['wav'] /= (1+z) #de-redshift
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
            header+='Max brightness date: '+maxdate+'\n'
            header+='\n'
        header+='wav flux eflux'
        np.savetxt(outfile, corrspec, header=header)
        type_counts[sntype] += 1
    type_counts_dict = dict(type_counts)
    
    print(f"\nProcessing complete.")
    print(f'Total events processed: {total_events}')
    print(f"Total files excluded: {counter_unk} due to unknown properties or loading errors.")
    print(f"Breakdown of types processed: {type_counts_dict}")
    
def check_for_collisions(inbase, sndata):
    infiles = glob.glob(inbase + "/*")
    # Dictionary to track: {predicted_outname: [list_of_original_files]}
    name_tracker = defaultdict(list)
    
    for file in infiles:
        filename = os.path.basename(file)
        parts = filename.split('_')
        sn_name = parts[0]
        obs_datestr = parts[1]
        
        # Match metadata
        w = sndata['name'] == sn_name
        if not any(w):
            continue
            
        maxdate = sndata['max_date'][w][0]
        if maxdate == 'unknown':
            maxdate = sndata['discovery_date'][w][0]
            if maxdate == 'unknown': continue

        try:
            # Replicate your current naming logic
            maxtime = Time(maxdate, format='isot', scale='utc')
            obstime = Time(obs_datestr, format='isot', scale='utc')
            phase = obstime.jd - maxtime.jd
            
            prefix = 'p' if phase >= 0 else 'm'
            ph = 'max' if phase == 0 else f'{prefix}{abs(round(phase)):04d}'
            
            # This is your current (colliding) naming convention
            predicted_outname = f"sn{sn_name}.{ph}.dat"
            name_tracker[predicted_outname].append(filename)
        except:
            continue

    # Analysis
    collisions = {out: origs for out, origs in name_tracker.items() if len(origs) > 1}
    
    print(f"--- Collision Report ---")
    print(f"Total output names predicted: {len(name_tracker)}")
    print(f"Number of names with collisions: {len(collisions)}")
    
    if collisions:
        print("\nTop 5 Collisions (Output Name -> Original Files):")
        for out, origs in list(collisions.items())[:5]:
            print(f"\n{out}:")
            for o in origs:
                print(f"  - {o}")
                
    return collisions

if __name__ == '__main__':

    inbase = '/Users/beehuynh/Developer/test_suites/sn_spectra_database/data/raw/osc_raw_data_20260406/'
    outbase = '/Users/beehuynh/Developer/test_suites/sn_spectra_database/data/processed2/'
    dtype =[('name','<U25'),('type','<U11'), ('redshift','<U10'), ('max_date','<U20'),('discovery_date','<U20')]
    sndata = np.loadtxt('SNlist_apr30.txt', comments='#', dtype=dtype)
    # print(sndata['name'])
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

    # check_for_collisions(inbase, sndata)
    # setup_new_templates(inbase, outbase, sndata)
