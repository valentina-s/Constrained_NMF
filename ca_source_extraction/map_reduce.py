# -*- coding: utf-8 -*-
"""
Function for implementing parallel scalable segmentation of two photon imaging data

Created on Wed Feb 17 14:58:26 2016

@author: agiovann
"""
from ipyparallel import Client
import numpy as np
from sklearn.decomposition import NMF
from scipy.sparse import lil_matrix,coo_matrix
import time
import scipy
 
#%%
def extract_patch_coordinates(d1,d2,rf=7,stride = 5):
    """
    Function that partition the FOV in patches and return the indexed in 2D and 1D (flatten, order='F') formats
    Parameters
    ----------    
    d1,d2: int
        dimensions of the original matrix that will be  divided in patches
    rf: int
        radius of receptive field, corresponds to half the size of the square patch        
    stride: int
        degree of overlap of the patches
    """
    coords_flat=[]
    coords_2d=[]
    for xx in range(stride,d1+stride,2*rf-stride):   
        for yy in range(stride,d2+stride,2*rf-stride):
            coords_x=np.array(range(xx - rf, xx + rf + 1))     
            coords_y=np.array(range(yy - rf, yy + rf + 1))  
            coords_y = coords_y[(coords_y >= 0) & (coords_y < d2)]
            coords_x = coords_x[(coords_x >= 0) & (coords_x < d1)]
            idxs = np.meshgrid( coords_x,coords_y)
            coords_2d.append(idxs)
            coords_ =np.ravel_multi_index(idxs,(d1,d2),order='F')
            coords_flat.append(coords_.flatten())
      
    return coords_flat,coords_2d
#%%
def extract_rois_patch(file_name,d1,d2,rf=5,stride = 5):
    idx_flat,idx_2d=extract_patch_coordinates(d1, d2, rf=rf,stride = stride)
    perctl=95
    n_components=2
    tol=1e-6
    max_iter=5000
    args_in=[]    
    for id_f,id_2d in zip(idx_flat,idx_2d):        
        args_in.append((file_name, id_f,id_2d[0].shape, perctl,n_components,tol,max_iter))
    st=time.time()
    print len(idx_flat)
    try:
        if 1:
            c = Client()   
            dview=c[:]
            file_res = dview.map_sync(nmf_patches, args_in)                         
        else:
            file_res = map(nmf_patches, args_in)                         
    finally:
        dview.results.clear()   
        c.purge_results('all')
        c.purge_everything()
        c.close()
    
    print time.time()-st
    
    A1=lil_matrix((d1*d2,len(file_res)))
    C1=[]
    A2=lil_matrix((d1*d2,len(file_res)))
    C2=[]
    for count,f in enumerate(file_res):
        idx_,flt,ca,d=f
        #flt,ca,_=cse.order_components(coo_matrix(flt),ca)
        A1[idx_,count]=flt[:,0][:,np.newaxis]        
        A2[idx_,count]=flt[:,1][:,np.newaxis]        
        C1.append(ca[0,:])
        C2.append(ca[1,:])
#        pl.imshow(np.reshape(flt[:,0],d,order='F'),vmax=10)
#        pl.pause(.1)
        
        
    return A1,A2,C1,C2
  
#%%    
def cnmf_patches(args_in):
    import numpy as np
    import ca_source_extraction as cse
    
#    file_name, idx_,shapes,p,gSig,K,fudge_fact=args_in
    file_name, idx_,shapes,options=args_in
    
    p=options['temporal_params']['p']
    
    Yr=np.load(file_name,mmap_mode='r')
    Yr=Yr[idx_,:]
    d,T=Yr.shape      
    Y=np.reshape(Yr,(shapes[1],shapes[0],T),order='F')  
    
#    ssub,tsub = options['patch_params']['ssub'],options['patch_params']['tsub']
#    if ssub>1 or tsub>1:
#        Y = cse.initialization.downscale_local_mean(Y,(ssub,ssub,tsub))
     
    [d1,d2,T]=Y.shape
#    pl.imshow(np.mean(Y,axis=-1))
#    pl.pause(.1)
#    import pdb
#    pdb.set_trace()
#    options = cse.utilities.CNMFSetParms(Y,p=p,gSig=gSig,K=K)
    options['spatial_params']['d2']=d1
    options['spatial_params']['d1']=d2
    options['spatial_params']['backend']='single_thread'
    options['temporal_params']['backend']='single_thread'
    
    Yr,sn,g=cse.pre_processing.preprocess_data(Yr,**options['preprocess_params'])
    Ain, Cin, b_in, f_in, center=cse.initialization.initialize_components(Y, **options['init_params']) 
                                                       
    print options
    A,b,Cin = cse.spatial.update_spatial_components(Yr, Cin, f_in, Ain, sn=sn, **options['spatial_params'])  
    options['temporal_params']['p'] = 0 # set this to zero for fast updating without deconvolution
    
    C,f,S,bl,c1,neurons_sn,g,YrA = cse.temporal.update_temporal_components(Yr,A,b,Cin,f_in,bl=None,c1=None,sn=None,g=None,**options['temporal_params'])
    
    A_m,C_m,nr_m,merged_ROIs,S_m,bl_m,c1_m,sn_m,g_m=cse.merging.merge_components(Yr,A,b,C,f,S,sn,options['temporal_params'], options['spatial_params'], bl=bl, c1=c1, sn=neurons_sn, g=g, thr=0.8, fast_merge = True)
    
    A2,b2,C2 = cse.spatial.update_spatial_components(Yr, C_m, f, A_m, sn=sn, **options['spatial_params'])
    options['temporal_params']['p'] = p # set it back to original value to perform full deconvolution
    C2,f2,S2,bl2,c12,neurons_sn2,g21,YrA = cse.temporal.update_temporal_components(Yr,A2,b2,C2,f,bl=None,c1=None,sn=None,g=None,**options['temporal_params'])
    
    Y=[]
    Yr=[]
    
    return idx_,shapes,A2,b2,C2,f2,S2,bl2,c12,neurons_sn2,g21,sn,options

#%%
def run_CNMF_patches(file_name, shape, options, rf=16, stride = 4, n_processes=2, backend='single_thread'):
    """
    Function that runs CNMF in patches, either in parallel or sequentiually, and return the result for each. It requires that ipyparallel is running
        
    Parameters
    ----------        
    file_name: string
        full path to an npy file (2D, pixels x time) containing the movie        
        
    shape: tuple of thre elements
        dimensions of the original movie across y, x, and time 
    
    options:
        dictionary containing all the parameters for the various algorithms
    
    rf: int 
        half-size of the square patch in pixel
    
    stride: int
        amount of overlap between patches
        
    backend: string
        'ipyparallel' or 'single_thread'
    
    
    Returns
    -------
    A_tot:
    
    C_tot:
    
    sn_tot:
    
    optional_outputs:    
    """
    (d1,d2,T)=shape
    d=d1*d2
    K=options['init_params']['K']
    
    idx_flat,idx_2d=extract_patch_coordinates(d1, d2, rf=rf, stride = stride)
    
    args_in=[]    
    for id_f,id_2d in zip(idx_flat[:],idx_2d[:]):        
        args_in.append((file_name, id_f,id_2d[0].shape, options))

    print len(idx_flat)

    st=time.time()        
    
    if backend is 'ipyparallel':

        try:

            c = Client()   
            dview=c[:n_processes]
            file_res = dview.map_sync(cnmf_patches, args_in)        

        finally:
            
            dview.results.clear()   
            c.purge_results('all')
            c.purge_everything()
            c.close()                   

    elif backend is 'single_thread':

        file_res = map(cnmf_patches, args_in)                         

    else:
        raise Exception('Backend unknown')
            
      
    print time.time()-st
    
    
    # extract the values from the output of mapped computation
    num_patches=len(file_res)
    
    A_tot=scipy.sparse.csc_matrix((d,K*num_patches))
    C_tot=np.zeros((K*num_patches,T))
    sn_tot=np.zeros((d1*d2))
    b_tot=[]
    f_tot=[]
    bl_tot=[]
    c1_tot=[]
    neurons_sn_tot=[]
    g_tot=[]    
    idx_tot=[];
    shapes_tot=[]    
    id_patch_tot=[]
    
    count=0  
    patch_id=0

    print 'Transforming patches into full matrix'
    
    for idx_,shapes,A,b,C,f,S,bl,c1,neurons_sn,g,sn,_ in file_res:
    
        sn_tot[idx_]=sn
        b_tot.append(b)
        f_tot.append(f)
        bl_tot.append(bl)
        c1_tot.append(c1)
        neurons_sn_tot.append(neurons_sn)
        g_tot.append(g)
        idx_tot.append(idx_)
        shapes_tot.append(shapes)
        
        for ii in range(np.shape(A)[-1]):            
            new_comp=A.tocsc()[:,ii]/np.sqrt(np.sum(np.array(A.tocsc()[:,ii].todense())**2))
            if new_comp.sum()>0:
                A_tot[idx_,count]=new_comp
                C_tot[count,:]=C[ii,:]   
                id_patch_tot.append(patch_id)
                count+=1
        
        patch_id+=1      

    A_tot=A_tot[:,:count]
    C_tot=C_tot[:count,:]  
    
    optional_outputs=dict()
    optional_outputs['b_tot']=b_tot
    optional_outputs['f_tot']=f_tot
    optional_outputs['bl_tot']=bl_tot
    optional_outputs['c1_tot']=c1_tot
    optional_outputs['neurons_sn_tot']=neurons_sn_tot
    optional_outputs['g_tot']=g_tot
    optional_outputs['idx_tot']=idx_tot
    optional_outputs['shapes_tot']=shapes_tot
    optional_outputs['id_patch_tot']= id_patch_tot
    
    return A_tot,C_tot,sn_tot, optional_outputs


