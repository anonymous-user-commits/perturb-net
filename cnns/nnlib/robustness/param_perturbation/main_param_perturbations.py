from cnns import matplotlib_backend

print('Using: ', matplotlib_backend.backend)

import matplotlib

print('Using: ', matplotlib.get_backend())

matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as plt

import time
import numpy as np
from cnns.nnlib.utils.exec_args import get_args
import cnns.foolbox.foolbox_2_3_0 as foolbox
from cnns.nnlib.robustness.param_perturbation.utils import \
    get_adv_images_org_images
from cnns.nnlib.robustness.param_perturbation.utils import get_clean_accuracy
from cnns.nnlib.robustness.param_perturbation.utils import get_data_loader
from cnns.nnlib.robustness.param_perturbation.utils import get_fmodel
from cnns.nnlib.robustness.param_perturbation.utils import get_perturbed_fmodel
import sys

delimiter = ';'


def get_attack(args, clean_fmodel):
    if args.target_class > -1:
        criterion = foolbox.criteria.TargetClass(target_class=args.target_class)
        print(f'target class id: {args.target_class}')
        print(
            f'target class name: {args.from_class_idx_to_label[args.target_class]}')
    else:
        criterion = foolbox.criteria.Misclassification()
        print('No target class specified')

    attack = foolbox.attacks.CarliniWagnerL2Attack(
        clean_fmodel, criterion=criterion)
    return attack


def get_adv_data(args, data_loader, attack, perturb_fmodel):
    total_count = 0
    adv_count = 0
    sum_distances = 0
    perturb_count = 0
    success_attacks = 0
    attacks_failed = 0
    err_count = 0

    for batch_idx, (images, labels) in enumerate(data_loader):
        total_count += len(labels)
        images, labels = images.numpy(), labels.numpy()

        adversarials = attack(images, labels,
                              unpack=False,
                              max_iterations=args.attack_max_iterations,
                              binary_search_steps=args.binary_search_steps,
                              initial_const=args.attack_strength,
                              confidence=args.attack_confidence
                              )

        adv_labels = np.asarray(
            [a.adversarial_class for a in adversarials])
        # print('original labels: ', labels)
        # print('adversarial labels: ', adversarial_classes)
        # print('count how many original and adversarial classes agree: ',
        #       np.sum(adversarial_classes == labels))  # will always be 0.0
        adv_count += np.sum(adv_labels == labels)

        # The `Adversarial` objects also provide a `distance` attribute.
        # Note that the distances
        # can be 0 (misclassified without perturbation) and inf (attack failed).
        distances = np.asarray([a.distance.value for a in adversarials])
        distances = np.asarray([distance for distance in distances if
                                distance != 0.0 and distance != np.inf])
        sum_distances += np.sum(distances)
        # print('avg distance: ', sum_distances / total_count)

        attacks_failed += sum(
            adv.distance.value == np.inf for adv in adversarials)
        # print("{} of {} attacks failed".format(attacks_failed, total_count))

        err_count += sum(adv.distance.value == 0 for adv in adversarials)
        # print("{} of {} inputs misclassified without perturbation".format(
        #     err_count, len(adversarials)))

        advs = get_adv_images_org_images(adversarials=adversarials,
                                         images=images)
        perturb_labels = perturb_fmodel.forward(advs).argmax(axis=-1)
        perturb_count += np.sum(perturb_labels == labels)
        # print('adversarial accuracy: ', adv_acc)

    result = np.array([perturb_count,
                       adv_count,
                       sum_distances,
                       attacks_failed,
                       err_count
                       ])
    result /= total_count
    result = np.append(result, total_count)
    return result


def compute(args):
    data_loader = get_data_loader(args)

    clean_fmodel = get_fmodel(args=args)
    get_clean_accuracy(args=args, data_loader=data_loader,
                       clean_fmodel=clean_fmodel)
    attack = get_attack(args, clean_fmodel=clean_fmodel)

    header = ['noise sigma',
              'perturb acc',
              'adv acc',
              'avg distance',
              'attack failure rate',
              'err rate',
              'total count',
              'elapsed time'
              ]
    print(delimiter.join(header))

    for noise_sigma in args.noise_sigmas:
    # for noise_sigma in np.linspace(0.0, 0.05, 30):
    # for noise_sigma in [0.005]:
        start = time.time()
        args.noise_sigma = noise_sigma
        perturb_fmodel = get_perturbed_fmodel(args=args)
        adv_data = get_adv_data(
            args=args, perturb_fmodel=perturb_fmodel, data_loader=data_loader,
            attack=attack)
        elapsed_time = time.time() - start
        adv_data = [args.noise_sigma] + adv_data.tolist() + [elapsed_time]
        adv_data_str = delimiter.join([str(x) for x in adv_data])
        print(adv_data_str)
        sys.stdout.flush()


if __name__ == "__main__":
    start_time = time.time()
    np.random.seed(31)
    # arguments
    args = get_args()
    print('args: ', args.get_str())
    sys.stdout.flush()
    for attack_iterations in args.many_attack_iterations:
        args.attack_max_iterations = attack_iterations
        for attack_strength in args.attack_strengths:
            args.attack_strength = attack_strength

    compute(args)
    print("total elapsed time: ", time.time() - start_time)
