from cnns.nnlib.utils.general_utils import ConvType
from cnns.nnlib.utils.general_utils import AttackType
from cnns.nnlib.utils.general_utils import AdversarialType
from cnns.nnlib.utils.general_utils import ConvExecType
from cnns.nnlib.utils.general_utils import CompressType
from cnns.nnlib.utils.general_utils import OptimizerType
from cnns.nnlib.utils.general_utils import SchedulerType
from cnns.nnlib.utils.general_utils import LossType
from cnns.nnlib.utils.general_utils import LossReduction
from cnns.nnlib.utils.general_utils import NetworkType
from cnns.nnlib.utils.general_utils import MemoryType
from cnns.nnlib.utils.general_utils import TensorType
from cnns.nnlib.utils.general_utils import StrideType
from cnns.nnlib.utils.general_utils import PrecisionType
from cnns.nnlib.utils.general_utils import PredictionType
from cnns.nnlib.utils.general_utils import Bool
from cnns.nnlib.utils.general_utils import PolicyType
from cnns.nnlib.utils.general_utils import SVDTransformType
from cnns.nnlib.utils.arguments import Arguments
import argparse


def get_args():
    # Execution parameters.
    args = Arguments()
    parser = argparse.ArgumentParser(description='PyTorch TimeSeries')
    parser.add_argument('--min_batch_size', type=int,
                        default=args.min_batch_size,
                        help=f"input mini batch size for training "
                             f"(default: {args.min_batch_size})")
    parser.add_argument('--test_batch_size', type=int,
                        default=args.test_batch_size,
                        metavar='N',
                        help='input batch size for testing (default: 1000)')
    parser.add_argument('--epochs', type=int, default=args.epochs,
                        metavar='Epochs',
                        help=f"number of epochs to train ("
                             f"default: {args.epochs})")
    parser.add_argument('--learning_rate', type=float,
                        default=args.learning_rate, metavar='LR',
                        help=f'learning rate (default: {args.learning_rate})')
    parser.add_argument('--weight_decay', type=float, default=args.weight_decay,
                        help=f'weight decay (default: {args.weight_decay})')
    parser.add_argument('--momentum', type=float, default=args.momentum,
                        metavar='M',
                        help=f'SGD momentum (default: {args.momentum})')
    parser.add_argument('--use_cuda',
                        default="TRUE" if args.use_cuda else "FALSE",
                        help="use CUDA for training and inference; "
                             "options: " + ",".join(Bool.get_names()))
    parser.add_argument('--seed', type=int, default=args.seed, metavar='S',
                        help='random seed (default: 31)')
    parser.add_argument('--log-interval', type=int, default=args.log_interval,
                        metavar='N',
                        help='how many batches to wait before logging training '
                             'status')
    parser.add_argument("--optimizer_type", default=args.optimizer_type.name,
                        # ADAM_FLOAT16, ADAM, MOMENTUM
                        help="the type of the optimizer, please choose from: " +
                             ",".join(OptimizerType.get_names()))
    parser.add_argument("--scheduler_type", default=args.scheduler_type.name,
                        # StepLR, MultiStepLR, ReduceLROnPlateau, ExponentialLR
                        # CosineAnnealingLR
                        help="the type of the scheduler, please choose from: " +
                             ",".join(SchedulerType.get_names()))
    parser.add_argument("--loss_type", default=args.loss_type.name,
                        # StepLR, MultiStepLR, ReduceLROnPlateau, ExponentialLR
                        # CosineAnnealingLR
                        help="the type of the loss, please choose from: " +
                             ",".join(LossType.get_names()))
    parser.add_argument("--loss_reduction", default=args.loss_reduction.name,
                        help="the type of the loss, please choose from: " +
                             ",".join(LossReduction.get_names()))
    parser.add_argument("--memory_type", default=args.memory_type.name,
                        # "STANDARD", "PINNED"
                        help="the type of the memory used, please choose from: " +
                             ",".join(MemoryType.get_names()))
    parser.add_argument("--workers", default=args.workers, type=int,
                        help="number of workers to fetch data for pytorch data "
                             "loader, 0 means that the data will be "
                             "loaded in the main process")
    parser.add_argument("--model_path",
                        default=args.model_path,
                        # default = "2018-11-07-00-00-27-dataset-50words-preserve-energy-90-test-accuracy-58.46153846153846.model",
                        # default="2018-11-06-21-05-48-dataset-50words-preserve-energy-90-test-accuracy-12.5.model",
                        # default="2018-11-06-21-19-51-dataset-50words-preserve-energy-90-test-accuracy-12.5.model",
                        # no_model
                        # 2018-11-06-21-05-48-dataset-50words-preserve-energy-90-test-accuracy-12.5.model
                        help="The path to a saved model.")
    parser.add_argument("--dataset", default=args.dataset,
                        help="the type of datasets: all, debug, cifar10, mnist.")
    parser.add_argument("--compress_rate", default=args.compress_rate,
                        type=float,
                        help="Percentage of indexes (values) from the back of the "
                             "frequency representation that should be discarded. "
                             "This is the compression in the FFT domain.")
    parser.add_argument('--compress_rates', nargs="+", type=float,
                        default=args.compress_rates,
                        help="Percentage of the high frequency coefficients that "
                             "should be discarded. This is the compression in the "
                             "FFT domain.")
    parser.add_argument('--layers_compress_rates', nargs="+", type=float,
                        default=args.layers_compress_rates,
                        help="Percentage of the high frequency coefficients that "
                             "should be discarded in each of the fft based "
                             "convolution layers. This is the compression in the "
                             "FFT domain. If this is None then the same compress "
                             "rate is used for all the fft based conv layers.")
    parser.add_argument('--preserve_energy', type=float,
                        default=args.preserve_energy)
    parser.add_argument('--preserve_energies', nargs="+", type=float,
                        default=args.preserve_energies,
                        help="How much energy should be preserved in the "
                             "frequency representation of the signal? This "
                             "is the compression in the FFT domain.")
    parser.add_argument("--mem_test",
                        default="TRUE" if args.mem_test else "FALSE",
                        help="is it the memory test; options: " + ",".join(
                            Bool.get_names()))
    parser.add_argument("--is_data_augmentation",
                        default="TRUE" if args.is_data_augmentation else "FALSE",
                        help="should the data augmentation be applied; "
                             "options: " + ",".join(Bool.get_names()))
    parser.add_argument("--is_debug",
                        default="TRUE" if args.is_debug else "FALSE",
                        help="is it the debug mode execution: " + ",".join(
                            Bool.get_names()))
    parser.add_argument("--sample_count_limit", default=args.sample_count_limit,
                        type=int,
                        help="number of samples taken from the dataset "
                             "(0 - inactive)")
    parser.add_argument("--conv_type", default=args.conv_type.name,
                        # "FFT1D", "FFT2D", "STANDARD", "STANDARD2D", "AUTOGRAD",
                        # "SIMPLE_FFT"
                        help="the type of convolution, SPECTRAL_PARAM is with the "
                             "convolutional weights initialized in the spectral "
                             "domain, please choose from: " + ",".join(
                            ConvType.get_names()))
    parser.add_argument("--conv_exec_type",
                        default=args.conv_exec_type.name,
                        help="the type of internal execution of the convolution"
                             "operation, for example: SERIAL: is each data point "
                             "convolved separately with all the filters, all a "
                             "batch of datapoint is convolved with all filters in "
                             "one go; CUDA: the tensor element wise complex "
                             "multiplication is done on CUDA, choose options from: "
                             "" + ",".join(ConvExecType.get_names()))
    parser.add_argument("--compress_type", default=args.compress_type.name,
                        # "STANDARD", "BIG_COEFF", "LOW_COEFF"
                        help="the type of compression to be applied: " + ",".join(
                            CompressType.get_names()))
    parser.add_argument("--network_type", default=args.network_type.name,
                        # "FCNN_STANDARD", "FCNN_SMALL", "LE_NET", "ResNet18"
                        help="the type of network: " + ",".join(
                            NetworkType.get_names()))
    parser.add_argument("--tensor_type", default=args.tensor_type.name,
                        # "FLOAT32", "FLOAT16", "DOUBLE", "INT"
                        help="the tensor data type: " + ",".join(
                            TensorType.get_names()))
    parser.add_argument("--next_power2",
                        default="TRUE" if args.next_power2 else "FALSE",
                        # "TRUE", "FALSE"
                        help="should we extend the input to the length of a power "
                             "of 2 before taking its fft? " + ",".join(
                            Bool.get_names()))
    parser.add_argument("--visualize",
                        default="TRUE" if args.visulize else "FALSE",
                        # "TRUE", "FALSE"
                        help="should we visualize the activations map after each "
                             "of the convolutional layers? " + ",".join(
                            Bool.get_names()))
    parser.add_argument('--static_loss_scale', type=float,
                        default=args.static_loss_scale,
                        help="""Static loss scale, positive power of 2 values can 
                        improve fp16 convergence.""")
    parser.add_argument('--dynamic_loss_scale',
                        default="TRUE" if args.dynamic_loss_scale else "FALSE",
                        help="(bool) Use dynamic loss scaling. "
                             "If supplied, this argument supersedes " +
                             "--static-loss-scale. Options: " + ",".join(
                            Bool.get_names()))
    parser.add_argument('--memory_size', type=float,
                        default=args.memory_size,
                        help="""GPU or CPU memory size in GB.""")
    parser.add_argument("--is_progress_bar",
                        default="TRUE" if args.is_progress_bar else "FALSE",
                        # "TRUE", "FALSE"
                        help="should we show the progress bar after each batch was"
                             "processed in training and testing? " + ",".join(
                            Bool.get_names()))
    parser.add_argument("--log_conv_size",
                        default="TRUE" if args.log_conv_size else "FALSE",
                        # "TRUE", "FALSE"
                        help="should we show log the size of each of the fft based"
                             "conv layers? " + ",".join(Bool.get_names()))
    parser.add_argument("--only_train",
                        default="TRUE" if args.only_train else "FALSE",
                        # "TRUE", "FALSE"
                        help="should we show execute only the train stage without any testing? " + ",".join(
                            Bool.get_names()))
    parser.add_argument("--stride_type", default=args.stride_type.name,
                        # "FLOAT32", "FLOAT16", "DOUBLE", "INT"
                        help="the tensor data type: " + ",".join(
                            StrideType.get_names()))
    parser.add_argument("--is_dev_dataset",
                        default="TRUE" if args.is_dev_dataset else "FALSE",
                        help="is it the dev set extracted from the train set, "
                             "default is {args.is_dev_set}, but choose param from: "
                             "" + ",".join(Bool.get_names()))
    parser.add_argument("--dev_percent", default=args.dev_percent,
                        type=int,
                        help="percent of train set used as the development set"
                             " (range from 0 to 100), 0 - it is inactive,"
                             " default: {args.dev_percent}")
    parser.add_argument("--adam_beta1", default=args.adam_beta1,
                        type=float,
                        help="beta1 value for the ADAM optimizer, default: "
                             "{args.adam_beta1}")
    parser.add_argument("--adam_beta2", default=args.adam_beta2,
                        type=float,
                        help="beta2 value for the ADAM optimizer, default: "
                             "{args.adam_beta1}")
    parser.add_argument("--cuda_block_threads", default=args.cuda_block_threads,
                        type=int,
                        help="Max number of threads for a cuda block.")
    parser.add_argument('--resume', default=args.resume, type=str,
                        metavar='PATH',
                        help='path to the latest checkpoint (default: none '
                             'expressed as an empty string)')
    parser.add_argument('--start_epoch', type=int, default=args.start_epoch,
                        help=f"the epoch number from which to start the training"
                             f"(default: {args.start_epoch})")
    parser.add_argument("--precision_type", default=args.precision_type.name,
                        # "FP16", "FP32", "AMP"
                        help="the precision type: " + ",".join(
                            PrecisionType.get_names()))
    parser.add_argument('--print-freq', '-p', default=10, type=int,
                        metavar='N', help='print frequency (default: 10)')
    parser.add_argument('-e', '--evaluate', dest='evaluate',
                        action='store_true',
                        help='evaluate model on validation set')
    parser.add_argument('--prof', dest='prof', action='store_true',
                        help='Only run 10 iterations for profiling.')
    parser.add_argument('--deterministic', action='store_true')
    parser.add_argument('--sync_bn', action='store_true',
                        help='enabling apex sync BN.')
    parser.add_argument("--local_rank", default=0, type=int)
    parser.add_argument("--gpu", default=0, type=int)
    parser.add_argument("--test_compress_rates",
                        default="TRUE" if args.test_compress_rates else "FALSE",
                        help="should we log to a single file for many compress rates: "
                             "" + ",".join(Bool.get_names()))
    parser.add_argument("--noise_sigma", default=args.noise_sigma,
                        type=float,
                        help=f"how much Gaussian noise to add: "
                             "{args.noise_sigma}")
    parser.add_argument("--noise_sigmas", default=args.noise_sigmas, nargs="+",
                        type=float,
                        help=f"how much Gaussian noise to add: {args.noise_sigmas}")
    parser.add_argument("--noise_epsilon", default=args.noise_epsilon,
                        type=float,
                        help=f"how much uniform noise to add: "
                             f"{args.noise_epsilon}")
    parser.add_argument("--noise_epsilons", default=args.noise_epsilons,
                        type=float,
                        nargs="+",
                        help=f"how much uniform noise to add: "
                             f"{args.noise_epsilons}")
    parser.add_argument("--fft_type", default=args.fft_type,
                        help="the type of fft used: real_fft or complex_fft.")
    parser.add_argument("--imagenet_path", default=args.imagenet_path,
                        help="The path to the imagenet data.")
    parser.add_argument('--distributed',
                        default="FALSE" if args.distributed is False else "TRUE",
                        help="Distributed training: " + ",".join(
                            Bool.get_names()))
    parser.add_argument('--in_channels', type=int,
                        default=args.in_channels,
                        help=f"number of input channels (default): {args.in_channels})")
    parser.add_argument('--values_per_channel',
                        default=args.values_per_channel,
                        type=int,
                        help="we apply the rounding if "
                             "values_per_channel is > 0 "
                             "and input has to be in range [0,1]"
                             "img = 1.0/(values_per_channel - 1) * round((values_per_channel - 1) * img)")
    parser.add_argument('--many_values_per_channel',
                        default=args.many_values_per_channel,
                        nargs="+",
                        type=int,
                        help="We apply many different values of rounding.")
    parser.add_argument("--ucr_path",
                        default=args.ucr_path,
                        help="The path to a UCR dataset.")
    parser.add_argument("--attack_type",
                        default=args.attack_type.name,
                        help="The type of the attack: " + ",".join(
                            AttackType.get_names()))
    parser.add_argument("--adv_type",
                        default=args.adv_type.name,
                        help="The type of the adversarial for robustnes; "
                             "apply the adversarial attack before or after a "
                             "noisy "
                             "channel or do not apply at all: " + ",".join(
                            AdversarialType.get_names()))
    parser.add_argument('--start_epsilon',
                        default=args.start_epsilon, type=int,
                        help="The start epsilon value for the attack.")
    parser.add_argument('--schedule_factor',
                        default=args.schedule_factor, type=float,
                        help="Factor for scheduler.")
    parser.add_argument('--schedule_patience',
                        default=args.schedule_patience, type=int,
                        help="Factor for scheduler.")
    parser.add_argument("--compress_fft_layer", default=args.compress_fft_layer,
                        type=float,
                        help="Only for input images and compression of images"
                             "solely (without any filter compression). "
                             "Percentage of indexes (values) from the back of "
                             "the frequency representation that should be "
                             "discarded. This is the compression in the FFT "
                             "domain.")
    parser.add_argument("--attack_name", default=args.attack_name,
                        help="the name of the attack: either "
                             "CarliniWagnerL2Attack or "
                             "CarliniWagnerL2AttackRoundFFT")
    parser.add_argument("--interpolate",
                        default=args.interpolate,
                        help="The type of interpolation to use: const, exp, lin, log.")
    parser.add_argument("--recover_type",
                        default=args.recover_type,
                        help="The type of interpolation to use: noise, fft, rounding.")
    parser.add_argument('--step_size', type=int, default=args.step_size,
                        metavar='Step size',
                        help=f"number of images to skip for an attack in "
                             f"sequential order (default: {args.step_size})")
    parser.add_argument('--noise_iterations', type=int,
                        default=args.noise_iterations,
                        help=f"number of iterations for the random defense "
                             f"that we that attack is aware of and we use to recover "
                             f"the correct label (default: {args.noise_iterations})")
    parser.add_argument('--many_noise_iterations', type=int, nargs="+",
                        default=args.many_noise_iterations,
                        help=f"many numbers of iterations for "
                             f"the defense that the "
                             f"attacker is aware of "
                             f"(default: {args.many_noise_iterations})")
    parser.add_argument('--recover_iterations', type=int,
                        default=args.recover_iterations,
                        help=f"number of iterations for the defense that the "
                             f"attacker is not aware of (default: {args.recover_iterations})")
    parser.add_argument('--many_recover_iterations', type=int, nargs="+",
                        default=args.many_recover_iterations,
                        help=f"many numbers of iterations for "
                             f"the defense that the "
                             f"attacker is not aware of "
                             f"(default: {args.many_recover_iterations})")
    parser.add_argument('--attack_max_iterations', type=int,
                        default=args.attack_max_iterations,
                        help=f"number of iterations for the attack that the "
                             f" (default: {args.attack_max_iterations})")
    parser.add_argument('--many_attack_iterations', type=int, nargs="+",
                        default=args.many_attack_iterations,
                        help=f"many numbers of iterations for "
                             f"the attacker "
                             f"(default: {args.many_attack_iterations})")
    parser.add_argument("--laplace_epsilon", default=args.laplace_epsilon,
                        type=float,
                        help=f"how much uniform noise to add: "
                             f"{args.laplace_epsilon}")
    parser.add_argument("--laplace_epsilons", default=args.laplace_epsilons,
                        type=float,
                        nargs="+",
                        help=f"how much laplace noise to add: "
                             f"{args.laplace_epsilons}")
    parser.add_argument("--is_DC_shift",
                        default="TRUE" if args.is_DC_shift else "FALSE",
                        help="should we shift the DC component to the center in"
                             "the FFT maps; options: " + ",".join(
                            Bool.get_names()))
    parser.add_argument("--use_foolbox_data",
                        default="TRUE" if args.use_foolbox_data else "FALSE",
                        help="should we use the data from the foolbox "
                             "library" + ",".join(Bool.get_names()))
    parser.add_argument("--svd_compress", default=args.svd_compress,
                        type=float,
                        help=f"svd compress rate: "
                             f"{args.svd_compress}")
    parser.add_argument("--many_svd_compress", default=args.many_svd_compress,
                        type=float,
                        nargs="+",
                        help=f"many svd compression rates: "
                             f"{args.many_svd_compress}")
    parser.add_argument("--rollout_file",
                        default=args.rollout_file,
                        type=str,
                        help=f"The rollout file for deep RL / IL, default: "
                             f"{args.rollout_file}")
    parser.add_argument("--prediction_type",
                        default=args.prediction_type.name,
                        type=str,
                        help=f"Is this classification or regression, "
                             f"default: {args.prediction_type.name}; "
                             f"choose from " + ','.join(
                            PredictionType.get_names()))

    # deeprl
    parser.add_argument('--learn_policy_file',
                        type=str,
                        default=args.learn_policy_file
                        )
    parser.add_argument('--expert_policy_file',
                        type=str,
                        default=args.expert_policy_file
                        )
    parser.add_argument('--env_name',
                        type=str,
                        default=args.env_name
                        )
    parser.add_argument('--render',
                        action='store_true',
                        default=args.render
                        )
    parser.add_argument("--max_timesteps",
                        type=int,
                        default=args.max_timesteps
                        )
    parser.add_argument('--rollouts',
                        type=int,
                        default=args.rollouts,
                        help='Number of expert rollouts / episodes.'
                        )
    parser.add_argument('--hidden_units',
                        type=int,
                        default=args.hidden_units
                        )
    parser.add_argument('--policy_type',
                        type=str,
                        default=args.policy_type.name,
                        help=f"The type of the policy used: {args.policy_type.name}; "
                             f"choose from " + ','.join(PolicyType.get_names())
                        )
    parser.add_argument('--expert_data_dir',
                        type=str,
                        default=args.expert_data_dir)
    parser.add_argument('--verbose',
                        type=bool,
                        default=args.verbose)
    parser.add_argument('--dagger_iterations',
                        type=int,
                        default=args.dagger_iterations,
                        help='Number of iterations for the dagger algorithm.'
                        )
    parser.add_argument('--behave_iterations',
                        type=int,
                        default=args.behave_iterations,
                        help='Number of iterations for the behaviorac clonning algorithm.'
                        )
    parser.add_argument('--pickle_protocol',
                        type=int,
                        default=args.pickle_protocol,
                        help='The number of the pickle protocol (from 1 to 4)',
                        )
    parser.add_argument("--attack_strengths", default=args.attack_strengths,
                        nargs="+",
                        type=float,
                        help=f"how strong the attack should be: "
                             f"{args.attack_strengths}")
    parser.add_argument("--gradient_iters",
                        type=int,
                        default=args.gradient_iters,
                        help='For the CW attack, how many times to accumulate'
                             'the gradients'
                        )
    parser.add_argument("--ensemble",
                        type=int,
                        default=args.ensemble,
                        help='For the RSE defense, how many models in the '
                             'ensemble.')
    parser.add_argument("--attack_confidence",
                        type=float,
                        default=args.attack_confidence,
                        help='Confidence of adversarial examples: a higher value produces adversarials that are further away, but more strongly classified as adversarial.')
    parser.add_argument('--target_class',
                        type=int,
                        default=args.target_class)
    parser.add_argument('--rgb_value', type=int,
                        default=args.noise_iterations,
                        help=f"value to be subtracted from each pixel"
                             f" (default: {args.rgb_value})")
    parser.add_argument('--rgb_values', type=int, nargs="+",
                        default=args.rgb_values,
                        help=f"values to be subtracted from each pixel"
                             f"(default: {args.rgb_values})")
    parser.add_argument("--svd_transform",
                        default=args.svd_transform,
                        type=float,
                        help=f"svd compression rate for input "
                             f"transformation during training and inference: "
                             f"{args.svd_transform}")
    parser.add_argument("--svd_compress_transform",
                        default=args.svd_compress_transform,
                        type=float,
                        nargs="+",
                        help=f"many svd compression rates for input "
                             f"transformations during training and inference: "
                             f"{args.svd_compress_transform}")
    parser.add_argument("--fft_transform",
                        default=args.fft_transform,
                        type=float,
                        help=f"fft compression rate for input "
                             f"transformations during training and inference: "
                             f"{args.fft_transform}")
    parser.add_argument("--fft_compress_transform",
                        default=args.fft_compress_transform,
                        type=float,
                        nargs="+",
                        help=f"many fft compression rates for input "
                             f"transformations during training and inference: "
                             f"{args.fft_compress_transform}")
    parser.add_argument("--svd_transform_type",
                        default=args.svd_transform_type.name,
                        help="The type of SVD transformation / compression "
                             "that should be applied for data pre-processing"
                             " (transformation). " + ",".join(
                            SVDTransformType.get_names()))
    parser.add_argument('--binary_search_steps', type=int,
                        default=args.binary_search_steps,
                        help=f"# of binary search steps in the attacks"
                             f" (default: {args.binary_search_steps})")
    parser.add_argument('--use_set',
                        type=str,
                        default=args.use_set)
    parser.add_argument("--normalize_pytorch",
                        default="TRUE" if args.normalize_pytorch else "FALSE",
                        # "TRUE", "FALSE"
                        help="should we normalize the data pytorch way? " + ",".join(
                            Bool.get_names()))
    parsed_args = parser.parse_args()
    args.set_parsed_args(parsed_args=parsed_args)
    return args
