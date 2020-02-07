#!/usr/bin/env python3
import os
from cnns import matplotlib_backend
import argparse
import torch
import torch.optim as optim
import torch.nn as nn
import torchvision.datasets as dst
import torchvision.transforms as tfs
from cnns.nnlib.pytorch_architecture.vgg import VGG as vgg
from cnns.nnlib.pytorch_architecture.vgg_fft import VGG as vgg_fft
from cnns.nnlib.pytorch_architecture.vgg_perturb import VGG as vgg_perturb
from cnns.nnlib.pytorch_architecture.vgg_perturb_rse import \
    VGG as vgg_perturb_rse
from cnns.nnlib.pytorch_architecture.vgg_perturb_weight import \
    VGG as vgg_perturb_weight
from cnns.nnlib.pytorch_architecture.vgg_perturb_conv_fc import \
    VGG as vgg_perturb_conv_fc
from cnns.nnlib.pytorch_architecture.vgg_perturb_conv_bn import \
    VGG as vgg_perturb_conv_bn
from cnns.nnlib.pytorch_architecture.vgg_perturb_fc_bn import \
    VGG as vgg_perturb_fc_bn
from cnns.nnlib.pytorch_architecture.vgg_perturb_fc import \
    VGG as vgg_perturb_fc
from cnns.nnlib.pytorch_architecture.vgg_perturb_bn import \
    VGG as vgg_perturb_bn
from cnns.nnlib.pytorch_architecture.vgg_rse import VGG as vgg_rse
from cnns.nnlib.pytorch_architecture.vgg_rse_perturb import \
    VGG as vgg_rse_perturb
from cnns.nnlib.pytorch_architecture.vgg_rse_perturb_weights import \
    VGG as vgg_rse_perturb_weights
from cnns.nnlib.pytorch_architecture.vgg_perturb_conv import \
    VGG as vgg_perturb_conv
from cnns.nnlib.pytorch_architecture.vgg_perturb_conv_even import \
    VGG as vgg_perturb_conv_even
from cnns.nnlib.pytorch_architecture.vgg_perturb_conv_every_2nd import \
    VGG as vgg_perturb_conv_every_2nd
from cnns.nnlib.pytorch_architecture.vgg_perturb_conv_every_3rd import \
    VGG as vgg_perturb_conv_every_3rd
from cnns.nnlib.pytorch_architecture.resnext import ResNeXt29_2x64d
from cnns.nnlib.pytorch_architecture.stl10_model_rse import stl10
from torch.utils.data import DataLoader
import time
import sys
from functools import partial
import numpy as np
import torch


def get_data_stats(dataloader):
    count = 0
    sum_avg = 0
    sum_std = 0
    global_min = np.float('inf')
    global_max = np.float('-inf')
    for x, _ in dataloader:
        count += 1
        sum_avg += torch.mean(x)
        sum_std += torch.std(x)
        min = torch.min(x)
        if min < global_min:
            global_min = min
        max = torch.max(x)
        if max > global_max:
            global_max = max
    return sum_avg / count, sum_std / count, global_min, global_max


# train one epoch
def train(dataloader, net, loss_f, optimizer):
    net.train()
    beg = time.time()
    total = 0
    correct = 0
    for x, y in dataloader:
        x, y = x.cuda(), y.cuda()
        optimizer.zero_grad()
        output = net(x)
        lossv = loss_f(output, y)
        lossv.backward()
        optimizer.step()
        correct += y.eq(torch.max(output, 1)[1]).sum().item()
        total += y.numel()
        # print('current accuracy: ', correct/total)
    run_time = time.time() - beg
    return run_time, correct / total


# test and save
def test(dataloader, net, best_acc, opt):
    net.eval()
    total = 0
    correct = 0
    for x, y in dataloader:
        x, y = x.cuda(), y.cuda()
        output = net(x)
        correct += y.eq(torch.max(output, 1)[1]).sum().item()
        total += y.numel()
    acc = correct / total
    if acc > best_acc:
        opt.modelOut = opt.modelOutRoot + '-test-accuracy-' + str(acc)
        torch.save(net.state_dict(), opt.modelOut)
        return acc, acc
    else:
        return acc, best_acc


def weights_init(initializeNoise, m):
    classname = m.__class__.__name__
    if classname.find('Linear') != -1 or classname.find('LinearNoise') != -1:
        m.weight.data.normal_(0.0, 0.02)
    elif classname.find('Conv') != -1 or classname.find('ConvNoise') != -1:
        m.weight.data.normal_(0.0, initializeNoise)
    elif classname.find('BatchNorm') != -1 and m.affine:
        m.weight.data.normal_(1.0, 0.02)
        m.bias.data.fill_(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='cifar10')
    parser.add_argument('--batchSize', type=int, default=128)
    parser.add_argument('--lr', type=float, default=0.1)
    parser.add_argument('--ngpu', type=int, default=1)
    parser.add_argument('--net', type=str, default='vgg16')
    parser.add_argument('--method', type=str, default="momsgd")
    parser.add_argument('--root', type=str,
                        default="../datasets/cifar-10-batches-py")
    parser.add_argument('--paramNoise', type=float, default=0.0)
    parser.add_argument('--noiseInit', type=float, default=0.2)
    parser.add_argument('--noiseInner', type=float, default=0.1)
    parser.add_argument('--initializeNoise', type=float, default=0.02)
    parser.add_argument('--compress_rate', type=float, default=85.0)
    opt = parser.parse_args()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    opt.modelOutRoot = f"{dir_path}/vgg16/{opt.net}_perturb_{opt.paramNoise}_init_noise_{opt.noiseInit}_inner_noise_{opt.noiseInner}_batch_size_{opt.batchSize}_compress_rate_{opt.compress_rate}.pth"
    opt.root = dir_path + "/" + opt.root
    print(opt)
    # epochs = [80, 60, 40, 20]
    # epochs = [120, 100, 80, 50]
    epochs = [150, 100, 100, 100]
    # epochs = [1, 1, 1]
    net = None
    if opt.net is None:
        print("opt.net must be specified")
        exit(-1)
    elif opt.net == "vgg16":
        net = vgg("VGG16")
    elif opt.net == "vgg16-fft":
        net = vgg_fft("VGG16", compress_rate=opt.compress_rate)
    elif opt.net == "vgg16-perturb":
        net = vgg_perturb("VGG16", param_noise=opt.paramNoise)
    elif opt.net == "vgg16-perturb-weight":
        net = vgg_perturb_weight("VGG16", param_noise=opt.paramNoise)
    elif opt.net == "vgg16-perturb-fc":
        net = vgg_perturb_fc("VGG16", param_noise=opt.paramNoise)
    elif opt.net == "vgg16-perturb-bn":
        net = vgg_perturb_bn("VGG16", param_noise=opt.paramNoise)
    elif opt.net == "vgg16-perturb-conv-fc":
        net = vgg_perturb_conv_fc("VGG16", param_noise=opt.paramNoise)
    elif opt.net == "vgg16-perturb-conv-bn":
        net = vgg_perturb_conv_bn("VGG16", param_noise=opt.paramNoise)
    elif opt.net == "vgg16-perturb-fc-bn":
        net = vgg_perturb_fc_bn("VGG16", param_noise=opt.paramNoise)
    elif opt.net == "vgg16-perturb-rse":
        net = vgg_perturb_rse("VGG16", param_noise=opt.paramNoise)
    elif opt.net == "vgg16-rse":
        net = vgg_rse("VGG16", init_noise=opt.noiseInit,
                      inner_noise=opt.noiseInner)
    elif opt.net == "vgg16-rse-perturb":
        net = vgg_rse_perturb("VGG16", init_noise=opt.noiseInit,
                              inner_noise=opt.noiseInner,
                              param_noise=opt.paramNoise)
    elif opt.net == "vgg16-rse-perturb-weights":
        net = vgg_rse_perturb_weights("VGG16", init_noise=opt.noiseInit,
                                      inner_noise=opt.noiseInner,
                                      param_noise=opt.paramNoise)
    elif opt.net == "vgg16-perturb-conv":
        net = vgg_perturb_conv("VGG16", init_noise=opt.noiseInit,
                               inner_noise=opt.noiseInner)
    elif opt.net == "vgg16-perturb-conv-every-2nd":
        net = vgg_perturb_conv_every_2nd("VGG16", init_noise=opt.noiseInit,
                                         inner_noise=opt.noiseInner)
    elif opt.net == "vgg16-perturb-conv-every-3rd":
        net = vgg_perturb_conv_every_3rd("VGG16", init_noise=opt.noiseInit,
                                         inner_noise=opt.noiseInner)
    elif opt.net == "vgg16-perturb-conv-even":
        net = vgg_perturb_conv_even("VGG16", init_noise=opt.noiseInit,
                                    inner_noise=opt.noiseInner)
    elif opt.net == "resnext":
        net = ResNeXt29_2x64d()
    elif opt.net == "stl10_model":
        net = stl10(32, opt.noiseInit, opt.noiseInner)
    else:
        raise Exception("Invalid opt.net: {}".format(opt.net))

    net = nn.DataParallel(net, device_ids=range(opt.ngpu))
    bound_weights_init = partial(weights_init, opt.initializeNoise)
    net.apply(bound_weights_init)
    net.cuda()
    loss_f = nn.CrossEntropyLoss()
    if opt.dataset == 'cifar10':
        transform_train = tfs.Compose([
            tfs.RandomCrop(32, padding=4),
            tfs.RandomHorizontalFlip(),
            tfs.ToTensor()
        ])

        transform_test = tfs.Compose([
            tfs.ToTensor()
        ])
        data = dst.CIFAR10(opt.root, download=True, train=True,
                           transform=transform_train)
        data_test = dst.CIFAR10(opt.root, download=True, train=False,
                                transform=transform_test)
    elif opt.dataset == 'stl10':
        transform_train = tfs.Compose([
            tfs.RandomCrop(96, padding=4),
            tfs.RandomHorizontalFlip(),
            tfs.ToTensor(),
        ])
        transform_test = tfs.Compose([
            tfs.ToTensor(),
        ])
        data = dst.STL10(opt.root, split='train', download=False,
                         transform=transform_train)
        data_test = dst.STL10(opt.root, split='test', download=False,
                              transform=transform_test)
    else:
        print("Invalid dataset")
        exit(-1)
    assert data, data_test
    dataloader = DataLoader(data, batch_size=opt.batchSize, shuffle=True,
                            num_workers=2)
    dataloader_test = DataLoader(data_test, batch_size=opt.batchSize,
                                 shuffle=False, num_workers=2)

    # train_stats = get_data_stats(dataloader)
    # test_stats = get_data_stats(dataloader_test)
    #
    # print('train_stats: ', train_stats)
    # print('test_stats: ', test_stats)

    accumulate = 0
    best_acc = 0
    total_time = 0
    for epoch in epochs:
        optimizer = optim.SGD(net.parameters(), lr=opt.lr, momentum=.9,
                              weight_decay=5.0e-4)
        for _ in range(epoch):
            accumulate += 1
            run_time, train_acc = train(dataloader, net, loss_f, optimizer)
            test_acc, best_acc = test(dataloader_test, net, best_acc,
                                      opt)
            total_time += run_time
            print(
                '[Epoch={}] Time:{:.2f}, Train: {:.5f}, Test: {:.5f}, Best: {:.5f}'.format(
                    accumulate, total_time, train_acc, test_acc, best_acc))
            sys.stdout.flush()
        # reload best model
        net.load_state_dict(torch.load(opt.modelOut))
        net.cuda()
        opt.lr /= 10


if __name__ == "__main__":
    main()
