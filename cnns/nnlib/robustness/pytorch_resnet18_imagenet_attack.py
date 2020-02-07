import foolbox
import numpy as np
import torchvision.models as models

import sys

np.random.seed(31)

if not sys.warnoptions:
    import warnings

    # warnings.simplefilter("ignore")

images, labels = foolbox.utils.samples(dataset='imagenet', index=0, batchsize=20,
                                       shape=(224, 224),
                                       data_format='channels_last')
images = np.transpose(images, (0, 3, 1, 2))
images = images / 255

# instantiate the model
resnet18 = models.resnet18(pretrained=True).cuda().eval()  # for CPU, remove cuda()
mean = np.array([0.485, 0.456, 0.406]).reshape((3, 1, 1))
std = np.array([0.229, 0.224, 0.225]).reshape((3, 1, 1))
foolbox_model = foolbox.models.PyTorchModel(resnet18, bounds=(0, 1), num_classes=1000,
                                    preprocessing=(mean, std))

class empty_attack(foolbox.attacks.base.Attack):

    def __call__(self, input_or_adv, label=None, unpack=True, **kwargs):
        return input_or_adv


# attack = foolbox.attacks.FGSM(model)
attack = empty_attack

print("attack_name, correct, counter, correct rate (%)")
attacks = [# empty_attack,
           # foolbox.attacks.SinglePixelAttack(model),
           foolbox.attacks.FGSM(foolbox_model),
           # foolbox.attacks.GradientAttack(model),
           # foolbox.attacks.LinfinityBasicIterativeAttack(
           # model, distance=foolbox.distances.MeanSquaredDistance),
           # foolbox.attacks.GaussianBlurAttack(foolbox_model),
           ]


for attack in attacks:
    correct = 0
    counter = 0
    for i, label in enumerate(labels):
        image = images[i]
        if image is None:
            print("image is None, ", label, " i:", i)
        # image = attack(image, label, epsilons=2, max_epsilon=0.005)
        image_attack = attack(image, label, epsilons=[0.001])
        if image_attack is None:
            image_attack = image
            print("image is None, label:", label, " i:", i)
        predictions = foolbox_model.predictions(image_attack)
        # print(np.argmax(predictions), label)
        if np.argmax(predictions) == label:
            correct += 1
        counter += 1
    print(attack.name(), ",", correct, ",", counter, ",", correct / counter)
