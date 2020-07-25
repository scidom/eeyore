# %% Sampling from a bivariate normal density via AM

# %% Import packages

import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats
import seaborn as sns
import torch

from torch.distributions import MultivariateNormal
# from torch.distributions import Normal
from torch.utils.data import DataLoader

from eeyore.datasets import EmptyXYDataset
from eeyore.models import Density
from eeyore.samplers import AM
from eeyore.stats import softabs

# %% Set up unnormalized target density

# Use torch.float64 to avoid numerical issues associated with eigenvalue computation in softabs
# See https://github.com/pytorch/pytorch/issues/24466

# Using manually defined log_pdf function

# def log_pdf(theta, x, y):
#     return -0.5*torch.sum(theta**2)

# Using log_pdf function based on Normal torch distribution

# pdf = Normal(torch.zeros(2), torch.ones(2))

# def log_pdf(theta, x, y):
#     return torch.sum(pdf.log_prob(theta))

# Using log_pdf function based on MultivariateNormal torch distribution

pdf = MultivariateNormal(torch.zeros(2), covariance_matrix=torch.eye(2))

def log_pdf(theta, x, y):
    return pdf.log_prob(theta)

density = Density(log_pdf, 2, dtype=torch.float32)

# %% Setup AM sampler

# softabs is used for avoiding issues with Cholesky decomposition
# See https://github.com/pytorch/pytorch/issues/24466
# Relevant functions :np.linalg.eig(), torch.eig() and torch.symeig() 
# If operations are carried out in torch.float64, Cholesky fails
# The solution is to use torch.float32 throught, and convert to torch.float64 only in softabs

sampler = AM(
    density,
    theta0=torch.tensor([-1, 1], dtype=torch.float32),
    dataloader=DataLoader(EmptyXYDataset()),
    transform=lambda hessian: softabs(hessian.to(torch.float64), 1000.).to(torch.float32)
)

# %% Run AM sampler

sampler.run(num_epochs=11000, num_burnin_epochs=1000)

# %% Compute acceptance rate

print('Acceptance rate: {}'.format(sampler.get_chain().acceptance_rate()))

# %% Compute Monte Carlo mean

print('Monte Carlo mean: {}'.format(sampler.get_chain().mean()))

# %% Plot traces of simulated Markov chain

for i in range(density.num_params()):
    chain = sampler.get_sample(i)
    plt.figure()
    sns.lineplot(range(len(chain)), chain)
    plt.xlabel('Iteration')
    plt.ylabel('Parameter value')
    plt.title(r'Traceplot of parameter $\theta_{}$'.format(i+1))

# %% Plot histograms of marginals of simulated Markov chain

x_hist_range = np.linspace(-4, 4, 100)

for i in range(density.num_params()):
    plt.figure()
    plot = sns.distplot(sampler.get_sample(i), hist=False, color='blue', label='Simulated')
    plot.set_xlabel('Parameter value')
    plot.set_ylabel('Relative frequency')
    plot.set_title(r'Traceplot of parameter $\theta_{}$'.format(i+1))
    sns.lineplot(x_hist_range, stats.norm.pdf(x_hist_range, 0, 1), color='red', label='Target')
    plot.legend()

# %% Plot scatter of simulated Markov chain

x_contour_range, y_contour_range = np.mgrid[-5:5:.01, -5:5:.01]

contour_grid = np.empty(x_contour_range.shape+(2,))
contour_grid[:, :, 0] = x_contour_range
contour_grid[:, :, 1] = y_contour_range

target = stats.multivariate_normal([0., 0.], [[1., 0.], [0., 1.]])

plt.scatter(x=sampler.get_sample(0), y=sampler.get_sample(1), marker='+')
plt.contour(x_contour_range, y_contour_range, target.pdf(contour_grid), cmap='copper')
plt.title('Countours of target and scatterplot of simulated chain');
