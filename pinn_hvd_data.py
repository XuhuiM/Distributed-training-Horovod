import os
import tensorflow as tf
from mpi4py import MPI
import horovod.tensorflow as hvd
import numpy as np
import time
import matplotlib.pyplot as plt

np.random.seed(1234)
tf.set_random_seed(1234)

def hyper_initial(size):
    in_dim = size[0]
    out_dim = size[1]
    std = np.sqrt(2.0/(in_dim + out_dim))
    return tf.Variable(tf.random_normal(shape=size, stddev = std))

def DNN(X, W, b):
    A = X
    L = len(W)
    for i in range(L-1):
        A = tf.tanh(tf.add(tf.matmul(A, W[i]), b[i]))
    Y = tf.add(tf.matmul(A, W[-1]), b[-1])
    return Y

def pdenn(X, W, b):
    u = DNN(X, W, b)
    u_x = tf.gradients(u, X)[0]
    u_xx = tf.gradients(u_x, X)[0]
    f = 4*tf.sin(2*np.pi*X)*np.pi*np.pi

    R = u_xx + f

    return R

if __name__ == '__main__':
    hvd.init()
    config = tf.ConfigProto()
    config.gpu_options.visible_device_list = str(hvd.local_rank())
    config.gpu_options.allow_growth = True
    sess = tf.Session(config=config)
    #saver = tf.train.Saver()

    print ('This is from rank %d'%(hvd.rank()))
    if hvd.rank() == 0:
        N = 51 # Number of trainning data
        x_col = np.linspace(-1, 0, N).reshape((-1, 1))
        x_0 = np.array([-1]).reshape((-1, 1))
        x_1 = np.array([1]).reshape((-1, 1))
        y_0 = -np.sin(2*np.pi*x_0)
        y_1 = -np.sin(2*np.pi*x_1)
    else:
        N = 51 # Number of trainning data
        x_col = np.linspace(0, 1, N).reshape((-1, 1))
        x_0 = np.array([-1]).reshape((-1, 1))
        x_1 = np.array([1]).reshape((-1, 1))
        y_0 = -np.sin(2*np.pi*x_0)
        y_1 = -np.sin(2*np.pi*x_1)

    print('x_col from rank %d'%(hvd.rank()))
    print (x_col)

    layers = [1] + 2*[16] + [1]
    L = len(layers)
    W = [hyper_initial([layers[l-1], layers[l]]) for l in range(1, L)] 
    b = [tf.Variable(tf.zeros([1, layers[l]])) for l in range(1, L)] 
    x_train = tf.placeholder(tf.float32, shape=[None, 1]) 
    x_0_train = tf.placeholder(tf.float32, shape=[None, 1]) 
    y_0_train = tf.placeholder(tf.float32, shape=[None, 1]) 
    x_1_train = tf.placeholder(tf.float32, shape=[None, 1]) 
    y_1_train = tf.placeholder(tf.float32, shape=[None, 1]) 
    y_nn = DNN(x_train, W, b) 
    y_0_nn = DNN(x_0_train, W, b) 
    y_1_nn = DNN(x_1_train, W, b) 
    R_nn = pdenn(x_train, W, b)
    
    loss = tf.reduce_mean(tf.square(R_nn)) + \
           tf.reduce_mean(tf.square(y_0_nn - y_0_train)) + \
           tf.reduce_mean(tf.square(y_1_nn - y_1_train)) 
    lr = 0.001*hvd.size()
    optimizer=tf.train.AdamOptimizer(lr) 
    optimizer=hvd.DistributedOptimizer(optimizer)
    train = optimizer.minimize(loss)

    init = tf.global_variables_initializer()
    sess.run(init) 

    bcast = hvd.broadcast_global_variables(0)
    sess.run(bcast)

    train_dict = {x_train: x_col, x_0_train: x_0, y_0_train: y_0, x_1_train: x_1, y_1_train: y_1}

    Nmax = 30000 # Iteration counter
    start_time = time.perf_counter()
    n = 0
    while n <= Nmax:
        y_pred, train_, loss_ = sess.run([y_nn, train, loss], feed_dict=train_dict)
        n += 1
#       if n%100 == 0:
#           print('rank %d: n = %d, loss = %.3e'%(comm_rank, n, loss_))
    stop_time = time.perf_counter()
    print('Rank: %d, Elapsed time: %f s'%(hvd.rank(), stop_time - start_time))
     
    if hvd.rank() == 0:
        N_plot = 201
        xplot = np.linspace(-1, 1, N_plot).reshape((-1, 1)) 
        y_pred_ = sess.run(y_nn, feed_dict={x_train: xplot})
        filename = 'y_pred_' + str(hvd.rank())
        np.savetxt(filename, y_pred_, fmt='%e')
    else:
        N_plot = 201
        xplot = np.linspace(-1, 1, N_plot).reshape((-1, 1)) 
        y_pred_ = sess.run(y_nn, feed_dict={x_train: xplot})
        filename = 'y_pred_' + str(hvd.rank())
        np.savetxt(filename, y_pred_, fmt='%e')
