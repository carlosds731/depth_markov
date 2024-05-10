import numpy as np
from typing import List


# X_t=\phi X_{t-1}+\epsilon_t
# where \epsilon_t is a sequence of i.i.d. random variables with normal distribution
# with mean 0 and variance sigma^2.


def simulate_ar1_process(
    n_steps: int,
    phi: float,
    sigma: float,
    initial_value: float,
    num_processes: int,
    seed: int = None,
):
    if seed is not None:
        np.random.seed(seed)  # Ensure reproducibility in parallel processing
    # Initialize all processes
    Y = np.zeros((num_processes, n_steps))
    Y[:, 0] = initial_value

    # Generate all noise terms at once
    noise = np.random.normal(0, sigma, size=(num_processes, n_steps - 1))

    # Vectorized computation of the AR(1) process
    for t in range(1, n_steps):
        Y[:, t] = phi * Y[:, t - 1] + noise[:, t - 1]

    return Y


NORMAL_NOISE = "normal"
UNIFORM_NOISE = "uniform"


def simulate_arch_1_process(
    n_steps: int,
    m: callable,
    sigma: callable,
    initial_value: float,
    num_processes: int,
    min_n_step: int | None = None,
    noise: str = NORMAL_NOISE,
    seed: int = None,
) -> List[np.ndarray]:
    """
    Simulates ARCH(1) processes with a specified initial value.

    Args:
    - n_steps (int): Number of steps in each time series.
    - m (callable): Function representing the conditional mean of the process.
    - sigma (callable): Function representing the conditional volatility.
    - initial_value (float): Initial value for each process.
    - num_processes (int): Number of processes to simulate.
    - min_n_step (int | None, optional): Minimum number of steps for each process. If provided,
        the processes will have random lengths between min_n_step and n_steps. Default is None.
    - noise (str, optional): The type of noise to simulate. Can be either 'normal' or 'uniform'.
        Default is 'normal'.
    - seed (int, optional): Random seed for reproducibility. Default is None.

    Returns:
    - List[np.ndarray]: List of simulated ARCH(1) processes, each as a NumPy array.
    """

    if seed is not None:
        np.random.seed(seed)  # Ensure reproducibility in parallel processing

    # Initialize all processes
    Y = np.zeros((num_processes, n_steps))
    Y[:, 0] = initial_value

    # Generate the noise (white noise terms, e_n)
    if noise == NORMAL_NOISE:
        e = np.random.normal(0, 1, size=(num_processes, n_steps - 1))
    elif noise == UNIFORM_NOISE:
        e = np.random.uniform(low=-1, high=1, size=(num_processes, n_steps - 1))

    processes_to_return = list()
    # Simulate the ARCH(1) process iteratively
    for t in range(1, n_steps):
        # Compute the conditional mean and standard deviation
        m_t = m(Y[:, t - 1])
        sigma_t = sigma(Y[:, t - 1])

        # Compute the new values of the series
        Y[:, t] = m_t + sigma_t * e[:, t - 1]

    if min_n_step:
        # Generate random lengths for each process
        process_lengths = (
            np.random.randint(
                low=min_n_step // 10, high=n_steps // 10 + 1, size=num_processes
            )
            * 10
        )
        # Truncate each process to its randomly selected length
        for i in range(num_processes):
            processes_to_return.append(Y[i, : process_lengths[i]])
    else:
        processes_to_return.extend(Y)
    return processes_to_return


def simulate_arch_1_process_with_shock_anomaly(
    n_steps: int,
    m: callable,
    sigma: callable,
    anomalous_m: callable,
    anomalous_sigma: callable,
    initial_value: float,
    num_processes: int,
    anomaly_percent: float,
    min_n_step: int | None = None,
    noise: str = NORMAL_NOISE,
    seed: int = None,
) -> List[np.ndarray]:
    """
    Simulates ARCH(1) processes with anomalies.

    Args:
    - n_steps (int): Number of steps in each time series.
    - m (callable): Function representing the conditional mean of the process.
    - sigma (callable): Function representing the conditional volatility.
    - initial_value (float): Initial value for each process.
    - num_processes (int): Number of processes to simulate.
    - anomaly_percent (float): Percentage of the trajectory to be anomalous.
    - min_n_step (int | None, optional): Minimum number of steps for each process. If provided,
        the processes will have random lengths between min_n_step and n_steps. Default is None.
    - noise (str, optional): The type of noise to simulate. Can be either 'normal' or 'uniform'.
        Default is 'normal'.
    - seed (int, optional): Random seed for reproducibility. Default is None.

    Returns:
    - List[np.ndarray]: List of simulated ARCH(1) processes with anomalies, each as a NumPy array.
    """

    if seed is not None:
        np.random.seed(seed)  # Ensure reproducibility in parallel processing

    processes_to_return = list()
    for _ in range(num_processes):
        if min_n_step:
            k = np.random.randint(min_n_step, n_steps + 1)
        else:
            k = n_steps

        t = np.random.randint(1, int((1 - anomaly_percent) * k) + 1)

        # Generate the first regular trajectory
        first_trajectory = simulate_arch_1_process(
            n_steps=t,
            m=m,
            sigma=sigma,
            initial_value=initial_value,
            num_processes=1,
            noise=noise,
            seed=seed,
        )[0]

        # Calculate the size of the anomalous trajectory
        anomaly_size = max(1, int(anomaly_percent * k))

        # Generate the anomalous part of the trajectory
        anomalous_trajectory = simulate_arch_1_process(
            n_steps=anomaly_size,
            m=anomalous_m,
            sigma=anomalous_sigma,
            initial_value=first_trajectory[-1],
            num_processes=1,
            noise=noise,
            seed=seed,
        )[0]

        # Generate the second regular trajectory
        second_trajectory = simulate_arch_1_process(
            n_steps=n_steps - len(first_trajectory) - len(anomalous_trajectory),
            m=m,
            sigma=sigma,
            initial_value=anomalous_trajectory[-1],
            num_processes=1,
            noise=noise,
            seed=seed,
        )[0]

        # Combine the trajectories
        combined_trajectory = np.concatenate(
            (first_trajectory, anomalous_trajectory, second_trajectory)
        )
        processes_to_return.append(combined_trajectory)

    return processes_to_return


def simulate_reflective_random_walk(n_steps: int, num_processes: int, seed: int = None):
    if seed is not None:
        np.random.seed(seed)  # Set the seed for reproducibility

    upper_bound = 1
    lower_bound = -1

    # Initialize the array to store the walks
    Y = np.zeros((num_processes, n_steps))  # Include the initial position

    # Generate all steps at once for all processes
    all_steps = np.random.uniform(
        low=lower_bound, high=upper_bound, size=(num_processes, n_steps - 1)
    )

    for i in range(num_processes):
        position = 0
        for j in range(n_steps - 1):
            new_position = position + all_steps[i, j]
            if new_position > upper_bound:
                excess = new_position - upper_bound
                position = upper_bound - excess  # Rebound at the upper boundary
            elif new_position < lower_bound:
                excess = lower_bound - new_position
                position = lower_bound + excess  # Rebound at the lower boundary
            else:
                position = new_position
            Y[i, j + 1] = position  # Store the position after the step

    return Y


def simulate_positive_recurrent_modulated_random_walk(
    n_steps: int, num_processes: int, seed: int = None
):
    if seed is not None:
        np.random.seed(seed)  # Set the seed for reproducibility

    # Initialize the array to store the walks
    Y = np.zeros((num_processes, n_steps))  # Include the initial position

    # Generate all steps at once for all processes
    # using -Y+1 where Y is exponential with expectation 2.
    # This guarantees that the increments of the random walk have infinite
    # left tail, negative expectation (-1) but that they also take positive values.
    all_steps = (
        -np.random.exponential(scale=0.5, size=(num_processes, n_steps - 1)) + 1.5
    )

    for i in range(num_processes):
        position = 0
        for j in range(n_steps - 1):
            # Subtract a constant to make the expectation negative
            new_position = position + all_steps[i, j]
            Y[i, j + 1] = max(new_position, 0)

    return Y
