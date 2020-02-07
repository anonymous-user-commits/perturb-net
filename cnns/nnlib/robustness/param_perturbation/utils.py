import numpy as np
from cnns.nnlib.datasets.load_data import get_data
import cnns.foolbox.foolbox_2_3_0 as foolbox
from cnns.nnlib.robustness.pytorch_model import get_model
from cnns.nnlib.robustness.utils import gauss_noise_raw
import torch
import time


def get_adv_images(adversarials, images):
    advs = [a.perturbed for a in adversarials]
    advs = [
        p if p is not None else np.full_like(u, np.nan)
        for p, u in zip(advs, images)
    ]
    advs = np.stack(advs)
    return advs


def get_adv_images_org_images(adversarials, images):
    advs = [a.perturbed for a in adversarials]
    advs = [
        adv if adv is not None else image
        for adv, image in zip(advs, images)
    ]
    advs = np.stack(advs)
    return advs


def get_adv_images_org_labels(adversarials, labels):
    advs = [a.perturbed for a in adversarials]
    adv_images = []
    org_labels = []
    for adv, label in zip(advs, labels):
        if adv is not None:
            adv_images.append(adv)
            org_labels.append(label)
    adv_images = np.stack(adv_images)
    return adv_images, org_labels


def get_data_loader(args):
    train_loader, test_loader, train_dataset, test_dataset, limit = get_data(
        args=args)
    if args.use_set == 'test_set':
        data_loader = test_loader
    elif args.use_set == 'train_set':
        data_loader = train_loader
    else:
        raise Exception("Unknown use set: ", args.use_set)
    print(f"Using set: {args.use_set} for source of data to find "
          f"adversarial examples.")
    return data_loader


def perturb_model_params(model, epsilon, min, max):
    params = model.parameters()
    with torch.no_grad():
        for param in params:
            # print(i, param)
            shape = list(param.shape)
            noise = gauss_noise_raw(epsilon=epsilon,
                                    shape=shape, dtype=np.float,
                                    min=min, max=max)
            noise = torch.tensor(noise, dtype=param.dtype, device=param.device)
            param.data += noise
    return model


def get_perturbed_fmodel(args):
    fmodel = get_fmodel(args)
    model = fmodel._model
    perturb_model_params(model, epsilon=args.noise_sigma, min=args.min,
                         max=args.max)
    return fmodel


def get_fmodel(args):
    pytorch_model = get_model(args)
    # preprocessing = dict(mean=args.mean_array,
    #                      std=args.std_array,
    #                      axis=-3)
    fmodel = foolbox.models.PyTorchModel(pytorch_model,
                                         bounds=(args.min, args.max),
                                         channel_axis=1,
                                         device=args.device,
                                         num_classes=args.num_classes,
                                         preprocessing=(0, 1))
    return fmodel


def get_accuracy(fmodel, data_loader):
    total_count = 0
    predict_count = 0

    for batch_idx, (images, labels) in enumerate(data_loader):
        total_count += len(labels)
        images, labels = images.numpy(), labels.numpy()
        # print('labels: ', labels)

        predict_labels = fmodel.forward(images).argmax(axis=-1)
        predict_count += np.sum(predict_labels == labels)
        # print('accuracy: ', predict_count / total_count)
    return predict_count / total_count


def get_clean_accuracy(args, data_loader, clean_fmodel=None):
    start = time.time()
    if clean_fmodel is None:
        clean_fmodel = get_fmodel(args)
    clean_accuracy = get_accuracy(fmodel=clean_fmodel, data_loader=data_loader)
    print(f'clean {args.use_set} accuracy: ', clean_accuracy)
    print('elapsed time: ', time.time() - start)
