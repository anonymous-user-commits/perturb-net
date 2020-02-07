from cnns.matplotlib_backend import backend

print("backend: ", backend)
from cnns.nnlib.utils.exec_args import get_args
from cnns.nnlib.datasets.cifar import get_cifar
from cnns.nnlib.datasets.imagenet.imagenet_pytorch import load_imagenet
from cnns.nnlib.datasets.imagenet.imagenet_pytorch import imagenet_mean_array
from cnns.nnlib.datasets.imagenet.imagenet_pytorch import imagenet_std_array
from cnns.nnlib.datasets.imagenet.imagenet_pytorch import imagenet_min
from cnns.nnlib.datasets.imagenet.imagenet_pytorch import imagenet_max
import foolbox
from cnns.nnlib.robustness.utils import get_foolbox_model
from cnns.nnlib.robustness.utils import unnormalize
from cnns.nnlib.datasets.cifar import cifar_mean_array
from cnns.nnlib.datasets.cifar import cifar_std_array
import torch
import time
import tables
import numpy as np
import torchvision.models as models


def run(args):
    start = time.time()
    args.sample_count_limit = 0

    if args.dataset == "cifar10":
        train_loader, test_loader, train_dataset, test_dataset = get_cifar(args,
                                                                           args.dataset)

        model_path = "2019-01-14-15-36-20-089354-dataset-cifar10-preserve-energy-100.0-test-accuracy-93.48-compress-rate-0-resnet18.model"
        compress_rate = 0
        fmodel = get_foolbox_model(args, model_path=model_path,
                                   compress_rate=compress_rate)
        mean_array = cifar_mean_array
        std_array = cifar_std_array
        img_size = 32
    elif args.dataset == "imagenet":
        train_loader, test_loader, train_dataset, test_dataset = load_imagenet(
            args)
        # model = models.resnet18(pretrained=True).eval()
        model = models.resnet50(pretrained=True).eval()
        model.to(device=args.device)
        fmodel = foolbox.models.PyTorchModel(model, bounds=(
            imagenet_min, imagenet_max), num_classes=1000)
        mean_array = imagenet_mean_array
        std_array = imagenet_std_array
        img_size = 224

    max_advers_imgs = args.max_advers_imgs
    filename = args.dataset + '_outarray_adverse_2_' + str(max_advers_imgs)

    f = tables.open_file(filename + ".h5", mode='w')
    atom = tables.Float32Atom()

    array_c = f.create_earray(f.root, 'data', atom, (0, 3, img_size, img_size))

    # x = np.random.rand(1, 3, 32, 32)
    # array_c.append(x)
    # array_c.append(np.ones((1, 3,32,32)))
    labels = []

    attack = foolbox.attacks.FGSM(fmodel)
    counter = 0
    for batch_idx, (data, target) in enumerate(test_loader):
        if batch_idx <= -1:
            continue
        if counter >= max_advers_imgs:
            break
        for i, label in enumerate(target):
            if counter >= max_advers_imgs:
                break
            label = label.item()
            image = data[i].numpy()

            # the image has to be classified correctly
            predictions = fmodel.predictions(image)
            predicted_label = np.argmax(predictions)
            if predicted_label == label:
                adv_image = attack(image, label)

                # the attack has to be successful
                if adv_image is not None:
                    counter += 1
                    diff = np.abs(unnormalize(image, mean=mean_array,
                                              std=std_array) - unnormalize(
                        adv_image, mean=mean_array,
                        std=std_array)) * 255
                    print("batch index,", batch_idx, ",i,", i, ",counter,",
                          counter, ",diff < 1.0,", np.all(diff < 1.0),
                          ",diff < 0.5,", np.all(diff < 0.5))
                    image = adv_image

            array_c.append(image[np.newaxis, :])
            labels.append(label)

    f.close()
    print("number of adversarial images: ", counter)

    # f = tables.open_file(filename, mode='r')
    # for i in range(max_advers_imgs):
    #     print(i, f.root.data[i,0,:5,:5], f.root.data[i].shape, type(f.root.data[i]))

    print("labels: ", labels)
    np.save(filename + ".labels", np.array(labels))
    print("timing: ", time.time() - start)


if __name__ == "__main__":
    np.random.seed(31)
    args = get_args()
    # args.dataset = "cifar10"  # "imagenet" or "cifar10"
    args.max_advers_imgs = 2000000
    if torch.cuda.is_available() and args.use_cuda:
        print("cuda is available")
        args.device = torch.device("cuda")
    else:
        print("cuda id not available")
        args.device = torch.device("cpu")

    run(args)
