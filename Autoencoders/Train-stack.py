
# coding: utf-8

# In[ ]:

import tensorflow as tf

import numpy as np
import SSAE
reload(SSAE)
import matplotlib.pyplot as plt
import glob
import os
import sys
from scipy import signal
from IPython import display
get_ipython().magic(u'matplotlib inline')


# In[ ]:

sys.path.append('../FileOps/')
import FileIO
import PatchSample


# In[ ]:

def MakePath(ae, iStack, basePath='../train/SSAE/'):
    path = os.path.join(basePath, '%dx%d-xy'%(ae.imgshape[0], ae.imgshape[1]), 
                        'sw-%g-wd-%g-f'%(ae.sparsity[iStack], ae.weight_decay))
    for n in ae.nFeatures[:(iStack+1)]:
        path += '-%d'%n
    
    return path


# In[ ]:

noisyPath = '/home/data0/dufan/CT_images/quater_dose_image/'
normalPath = '/home/data0/dufan/CT_images/full_dose_image/'

normalSet = ['L067', 'L096', 'L109', 'L192', 'L506']

for i in range(len(normalSet)):
    normalSet[i] = os.path.join(normalPath, normalSet[i])


# In[ ]:

samplePath = '../train/sample/%dx%d-xy/'%(imgshape[0], imgshape[1])
nFiles = 10
PatchSample.GenerateTrainingPatchesFromDicomSeq(samplePath, nFiles, 10, 10000, imgshape, normalSet)


# In[ ]:

patches = list()
for iFile in range(nFiles):
    patches.append(PatchSample.RetrieveTrainingPatches(samplePath, iFile))


# In[ ]:

imgshape = [16,16,1]
nFeatures = [1024,1024,1024]
sparsity = [5,5,5]
weight_decay = 0.1
nEpoches = 30
batchsize = 100
ae = SSAE.StackedSparseAutoEncoder(imgshape, nFeatures, sparsity, weight_decay)


# In[ ]:

lastPath = ''
for iStack in range(len(nFeatureMaps)):
    
    tf.reset_default_graph()
    ae.BuildStackedAutoEncoder(iStack)

    update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
    with tf.control_dependencies(update_ops):
        trainer = tf.train.AdamOptimizer(learning_rate=1e-4).minimize(ae.loss_current, var_list=ae.vars_upmost)
    saver = tf.train.Saver(max_to_keep=1000)
    sess = tf.Session(config=tf.ConfigProto(gpu_options=tf.GPUOptions(visible_device_list='3')))
    tf.global_variables_initializer().run(session=sess)

    if lastPath != "":
        var_list = [v for v in ae.vars_encoder + ae.vars_decoder if v not in ae.vars_upmost]
        loader = tf.train.Saver(var_list = var_list)
        loader.restore(sess, os.path.join(lastPath, '%d'%(nEpoches-1)))

    # training
    np.random.seed(0)
    lastPath = MakePath(ae, iStack, basePath='../train/SSAE/1024x3/')
    if not os.path.exists(lastPath):
        os.makedirs(lastPath)
    for epoch in range(nEpoches):
        indFile = range(len(patches))
        np.random.shuffle(indFile)
        
        iIter = 0
        for iFile in indFile:
            normal_imgs = patches[iFile]
            for i in range(0, normal_imgs.shape[0], batchsize):
                normal_batch = normal_imgs[i:i+batchsize,...]

                _, loss_train, loss_s, loss_w, loss_img =                     sess.run([trainer, ae.loss_upmost, ae.loss_sparse, ae.loss_weight, ae.loss_img], 
                             feed_dict={ae.input_data: normal_batch})

                iIter += 1

                if iIter % 100 == 0:
                    sys.__stdout__.write('Stack: %d, Epoch: %d, Iteration: %d, loss = (%f, %f, %f, %f)\n'                                         %(iStack, epoch, iIter, loss_train, loss_s, loss_w, loss_img))

        [decode] = sess.run([ae.decode_datas[-1]], feed_dict = {ae.input_data: normal_batch})

        display.clear_output()
        plt.figure(figsize=[15,6])
        for i in range(5):
            plt.subplot(2, 5, i+1); plt.imshow(normal_batch[i,...,0], 'Greys_r', vmin=-160/500.0, vmax=240/500.0)
            plt.subplot(2, 5, i+6); plt.imshow(decode[i,...,0], 'Greys_r', vmin=-160/500.0, vmax=240/500.0)
        plt.show()
        
        saver.save(sess, os.path.join(lastPath, '%d'%epoch))


# In[ ]:



