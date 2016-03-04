import ca_source_extraction as cse
import numpy.testing as npt

def test_demo():
    #%%
    try:
    #    %load_ext autoreload
    #    %autoreload 2
        print 1
    except:
        print 'NOT IPYTHON'

    import matplotlib as mpl

    from matplotlib import pyplot as plt
    #plt.ion()

    import sys
    import numpy as np
    import ca_source_extraction as cse

    #sys.path.append('../SPGL1_python_port')
    #%
    from time import time
    from scipy.sparse import coo_matrix
    import tifffile
    import subprocess
    import time as tm
    from time import time
    import pylab as pl
    import psutil



    n_processes = np.maximum(psutil.cpu_count() - 2,1) # roughly number of cores on your machine minus 1
    n_processes = 1
    #print 'using ' + str(n_processes) + ' processes'
    p=2 # order of the AR model (in general 1 or 2)

    #%% start cluster for efficient computation
    print "Stopping  cluster to avoid unnencessary use of memory...."
    sys.stdout.flush()
    cse.utilities.stop_server()

    #%% LOAD MOVIE AND MAKE DIMENSIONS COMPATIBLE WITH CNMF
    reload=0
    filename='movies/demoMovie.tif'
    t = tifffile.TiffFile(filename)
    Yr = t.asarray().astype(dtype=np.float32)
    Yr = np.transpose(Yr,(1,2,0))
    d1,d2,T=Yr.shape
    Yr=np.reshape(Yr,(d1*d2,T),order='F')
    #np.save('Y',Y)
    np.save('Yr',Yr)
    #Y=np.load('Y.npy',mmap_mode='r')
    Yr = np.load('Yr.npy',mmap_mode='r')
    Y = np.reshape(Yr,(d1,d2,T),order='F')
    Cn = cse.utilities.local_correlations(Y)
    #n_pixels_per_process=d1*d2/n_processes # how to subdivide the work among processes

    #%%
    options = cse.utilities.CNMFSetParms(Y,p=p,gSig=[4,4],K=30)
    cse.utilities.start_server(options['spatial_params']['n_processes'])

    #%% PREPROCESS DATA AND INITIALIZE COMPONENTS
    t1 = time()
    Yr,sn,g=cse.pre_processing.preprocess_data(Yr,**options['preprocess_params'])
    Atmp, Ctmp, b_in, f_in, center=cse.initialization.initialize_components(Y, **options['init_params'])
    print time() - t1
    plt.show(block = False)



    #%% Refine manually component by clicking on neurons
    refine_components=False
    if refine_components:
        Ain,Cin = cse.utilities.manually_refine_components(Y,options['init_params']['gSig'],coo_matrix(Atmp),Ctmp,Cn,thr=0.9)
    else:
        Ain,Cin = Atmp, Ctmp


    #%% UPDATE SPATIAL COMPONENTS
    A,b,Cin = cse.spatial.update_spatial_components(Yr, Cin, f_in, Ain, sn=sn, **options['spatial_params'])

    #%% update_temporal_components
    options['temporal_params']['p'] = 0 # set this to zero for fast updating without deconvolution
    C,f,S,bl,c1,neurons_sn,g,YrA = cse.temporal.update_temporal_components(Yr,A,b,Cin,f_in,bl=None,c1=None,sn=None,g=None,**options['temporal_params'])

    print(np.sum(np.abs(C)))

    #%% merge components corresponding to the same neuron
    A_m,C_m,nr_m,merged_ROIs,S_m,bl_m,c1_m,sn_m,g_m=cse.merging.merge_components(Yr,A,b,C,f,S,sn,options['temporal_params'], options['spatial_params'], bl=bl, c1=c1, sn=neurons_sn, g=g, thr=0.8, mx=50, fast_merge = True)

    print(np.sum(np.abs(C_m)))



    cse.utilities.stop_server()

    npt.assert_allclose(np.sum(np.abs(C_m)),46893045.1187)
