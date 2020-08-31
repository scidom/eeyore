# %% Power posterior sampling of MLP weights using iris data
#
# Sampling the weights of a multi-layer perceptron (MLP) using the iris data and power posterior algorithm.

# %% Import packages for MCMC simulation and numerical MCMC summaries and diagnostics

import matplotlib.pyplot as plt
import torch

from datetime import timedelta
from timeit import default_timer as timer
from torch.distributions import Normal
from torch.utils.data import DataLoader

from eeyore.constants import loss_functions
from eeyore.datasets import XYDataset
from eeyore.models import mlp
from eeyore.samplers import GAMC
from eeyore.stats import softabs

# %% Avoid issuing memory warning due to number of plots

plt.rcParams.update({'figure.max_open_warning': 0})

# %% Load iris data

iris = XYDataset.from_eeyore('iris', yndmin=1, dtype=torch.float32, yonehot=True)
dataloader = DataLoader(iris, batch_size=len(iris), shuffle=True)

# %% Setup MLP model

# Use torch.float64 to avoid numerical issues associated with eigenvalue computation in softabs
# See https://github.com/pytorch/pytorch/issues/24466

hparams = mlp.Hyperparameters(dims=[4, 3, 3], activations=[torch.sigmoid, None])

model = mlp.MLP(
    loss=loss_functions['multiclass_classification'],
    hparams=hparams,
    dtype=torch.float32
)

model.prior = Normal(
    torch.zeros(model.num_params(), dtype=model.dtype),
    (3 * torch.ones(model.num_params(), dtype=model.dtype)).sqrt()
)

# %% Setup GAMC sampler

per_chain_samplers = [
    ['AM', {
        'l': 0.01, 'b': 2., 'c': 0.025,
        'transform': lambda hessian: softabs(hessian.to(torch.float64), 1000.).to(torch.float32)
    }],
    # ['RAM', {}],
    ['SMMALA', {
        'step': 0.01,
        'transform': lambda hessian: softabs(hessian.to(torch.float64), 1000.).to(torch.float32)
    }]
]

sampler = GAMC(model, per_chain_samplers, theta0=model.prior.sample(), dataloader=dataloader)

# %% Run GAMC sampler

start_time = timer()

sampler.run(num_epochs=11000, num_burnin_epochs=1000, verbose=True, verbose_step=1000)

end_time = timer()
print("Time taken: {}".format(timedelta(seconds=end_time-start_time)))

# %% Import kanga package for visual MCMC summaries

import kanga.plots as ps

# %% Generate kanga ChainArray from eeyore ChainList

chain_array = sampler.get_chain().to_kanga()

# %% Compute acceptance rate

print('Acceptance rate: {}'.format(chain_array.acceptance_rate()))

# %% Compute Monte Carlo mean

print('Monte Carlo mean: {}'.format(chain_array.mean()))

# %% Compute Monte Carlo standard error

print('Monte Carlo standard error: {}'.format(chain_array.mc_se()))

# %% Compute multivariate ESS

print('Multivariate ESS: {}'.format(chain_array.multi_ess()))

# %% Plot traces of simulated Markov chain

for i in range(model.num_params()):
    ps.trace(
        chain_array.get_param(i),
        title=r'Traceplot of $\theta_{{{}}}$'.format(i+1),
        xlabel='Iteration',
        ylabel='Parameter value'
    )

# %% Plot running means of simulated Markov chain

for i in range(model.num_params()):
    ps.running_mean(
        chain_array.get_param(i),
        title=r'Running mean plot of parameter $\theta_{{{}}}$'.format(i+1),
        xlabel='Iteration',
        ylabel='Running mean'
    )

# %% Plot histograms of marginals of simulated Markov chain

for i in range(model.num_params()):    
    ps.hist(
        chain_array.get_param(i),
        bins=30,
        density=True,
        title=r'Histogram of parameter $\theta_{{{}}}$'.format(i+1),
        xlabel='Parameter value',
        ylabel='Parameter relative frequency'
    )
