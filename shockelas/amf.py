"""
A module for representing additive and multiplicative functionals of
triangular state space vector systems.

"""

import numpy as np
from .util.utilities import *


# TODO(QBatista):
# - Avoid matrix inversions
# - Precompute kronecker products

class Amf:
    """
    A class for representing additive and multiplicative functionals whose
    additive increment follows:

        Y_{t+1} - Y_{t} = Γ_0 + Γ_1 * X_{1,t} + Γ_2 * X_{2,t}
                          + Γ_3 * (X_{1,t} ⊗ X_{1,t}) + Ψ_0 * W_{t+1}
                          + Ψ_1 * (X_{1,t} ⊗ W_{t+1})
                          + Ψ_2 * (W_{t+1} ⊗ W_{t+1})

    where X_{1,t}, X_{2,t} and W_{t+1} are elements of a triangular state
    vector system.

    Parameters
    ----------
    𝒫 : tuple
        A tuple containing the parameters of the additive increment in the
        following order: Γ_0, Γ_1, Γ_2, Γ_3, Ψ_0, Ψ_1, Ψ_2.

    tri_ss : TriSS
        An instance of a `TriSS` object representing the underlying triangular
        state vector system.

    α_h : ndarray(float, ndim=2), optional(default=None)
        An array representing the shock exposure direction.

    Attributes
    ----------
    𝒫, tri_ss, α_h : See parameters.

    𝒫_t_bar_path, 𝒫_t_tilde_path : list
        Lists containing the values of 𝒫_bar and 𝒫_tilde respectively obtained
        from iterating on the following mappings:

            𝒫_{t}_tilde = 𝒫 + Ɛ_tilde(𝒫_{t-1}_bar)
            𝒫_{t}_bar = Ɛ_bar(𝒫_{t}_tilde)

    References
    ----------

    .. [1] Borovička, Jaroslav & Hansen, Lars Peter, 2014. "Examining
           macroeconomic models through the lens of asset pricing," Journal of
           Econometrics, Elsevier, vol. 183(1), pages 67-90.

    """


    def __init__(self, 𝒫, tri_ss, α_h=None):
        self.𝒫 = 𝒫
        self.tri_ss = tri_ss
        self.α_h = α_h

        self.n, self.k = 𝒫[1].shape[1], 𝒫[4].shape[1]

        𝒫_0_bar = tuple(np.zeros_like(x) for x in 𝒫)
        self.𝒫_t_bar_path = [𝒫_0_bar]
        self.𝒫_t_tilde_path = [None]
        self.Σ_t_tilde_path = [None]
        self.add_Σ_to_path = False

    def Ɛ_bar(self, 𝒫):
        """
        Ɛ_bar mapping (see appendix of reference [1]).

        Parameters
        ----------
        𝒫 : tuple
            A tuple containing the parameters of the additive increment in the
            following order: Γ_0, Γ_1, Γ_2, Γ_3, Ψ_0, Ψ_1, Ψ_2.

        Returns
        ----------
        𝒫_bar : tuple
            A tuple containing the following parameters: Γ_0_bar, Γ_1_bar,
            Γ_2_bar, Γ_3_bar, Ψ_0_bar, Ψ_1_bar, Ψ_2_bar.

        """
        # Unpack parameters
        Γ_0, Γ_1, Γ_2, Γ_3, Ψ_0, Ψ_1, Ψ_2 = 𝒫

        n, k = self.n, self.k

        # Compute 𝒫_bar
        Σ_inv = np.eye(k) - sym(mat(2 * Ψ_2, (k, k)))
        Σ = np.linalg.inv(Σ_inv)
        mat_Ψ_1 = mat(Ψ_1, (k, n))  # μ_1_t

        if self.add_Σ_to_path:
            self.Σ_t_tilde_path.append(Σ)

        Γ_0_bar = Γ_0 - 1 / 2 * np.log(np.linalg.det(Σ_inv)) + \
            1 / 2 * Ψ_0 @ Σ @ Ψ_0.T

        Γ_1_bar = Γ_1 + Ψ_0 @ Σ @ mat_Ψ_1

        Γ_3_bar = Γ_3 + 1 / 2 * vec(mat_Ψ_1.T @ Σ @ mat_Ψ_1).T

        𝒫_bar = (Γ_0_bar, Γ_1_bar, Γ_2, Γ_3_bar, np.array([[0.]]),
                 np.array([[0.]]), np.array([[0.]]))

        return 𝒫_bar

    def Ɛ_tilde(self, 𝒫_bar):
        """
        Ɛ_tilde mapping (see appendix of reference [1]).

        Parameters
        ----------
        𝒫_bar : tuple
            A tuple containing the following parameters: Γ_0_bar, Γ_1_bar,
            Γ_2_bar, Γ_3_bar, Ψ_0_bar, Ψ_1_bar, Ψ_2_bar.

        Returns
        ----------
        𝒫_tilde : tuple
            A tuple containing the following parameters: Γ_0_tilde, Γ_1_tilde,
            Γ_2_tilde, Γ_3_tilde, Ψ_0_tilde, Ψ_1_tilde, Ψ_2_tilde.

        """

        # Unpack parameters
        Θ_10 = self.tri_ss.Θ_10
        Θ_11 = self.tri_ss.Θ_11
        Λ_10 = self.tri_ss.Λ_10
        Θ_20 = self.tri_ss.Θ_20
        Θ_21 = self.tri_ss.Θ_21
        Θ_22 = self.tri_ss.Θ_22
        Θ_23 = self.tri_ss.Θ_23
        Λ_20 = self.tri_ss.Λ_20
        Λ_21 = self.tri_ss.Λ_21
        Λ_22 = self.tri_ss.Λ_22

        n, k = self.n, self.k

        Γ_0_bar, Γ_1_bar, Γ_2_bar, Γ_3_bar, Ψ_0_bar, Ψ_1_bar, Ψ_2_bar = 𝒫_bar

        # Compute 𝒫_tilde
        Γ_0_tilde = Γ_0_bar + Γ_1_bar @ Θ_10 + Γ_2_bar @ Θ_20 + \
            Γ_3_bar @ np.kron(Θ_10, Θ_10)

        Γ_1_tilde = Γ_1_bar @ Θ_11 + Γ_2_bar @ Θ_21 + \
            Γ_3_bar @ (np.kron(Θ_10, Θ_11) + np.kron(Θ_11, Θ_10))

        Γ_2_tilde = Γ_2_bar @ Θ_22

        Γ_3_tilde = Γ_2_bar @ Θ_23 + Γ_3_bar @ np.kron(Θ_11, Θ_11)

        Ψ_0_tilde = Γ_1_bar @ Λ_10 + Γ_2_bar @ Λ_20 + \
            Γ_3_bar @ (np.kron(Θ_10, Λ_10) + np.kron(Λ_10, Θ_10))

        # FIX HERE: Pre-compute
        temp = np.hstack([np.kron(Λ_10, Θ_11[:, [j]]) for j in range(n)])

        Ψ_1_tilde = Γ_2_bar @ Λ_21 + Γ_3_bar @ (np.kron(Θ_11, Λ_10) + temp)

        Ψ_2_tilde = Γ_2_bar @ Λ_22 + Γ_3_bar @ np.kron(Λ_10, Λ_10)

        𝒫_tilde = (Γ_0_tilde, Γ_1_tilde, Γ_2_tilde, Γ_3_tilde, Ψ_0_tilde,
                    Ψ_1_tilde, Ψ_2_tilde)

        return 𝒫_tilde

    def iterate(self, T):
        """
        Add T iterations on the following mapping to 𝒫_t_bar_path and
        𝒫_t_tilde_path:

            𝒫_{t}_tilde = 𝒫 + Ɛ_tilde(𝒫_{t-1}_bar)
            𝒫_{t}_bar = Ɛ_bar(𝒫_{t}_tilde)

        Parameters
        ----------
        T : scalar(int)
            Number of iterations.

        """

        self.add_Σ_to_path = True

        for _ in range(T):
            temp = zip(self.𝒫, self.Ɛ_tilde(self.𝒫_t_bar_path[-1]))

            𝒫_tilde = tuple(x + y for x, y in temp)
            𝒫_bar = self.Ɛ_bar(𝒫_tilde)

            self.𝒫_t_tilde_path.append(𝒫_tilde)
            self.𝒫_t_bar_path.append(𝒫_bar)

        self.add_Σ_to_path = False

    def 𝛆(self, x, t):
        """
        Compute shock elasticity for a given state tuple x and time period t.

        Parameters
        ----------
        x : tuple
            Tuple containing arrays of values for X_{1,t} and X_{2,t}.

        t : scalar(int)
            Time period.

        Returns
        ----------
        𝛆_x_t : scalar(float)
            Shock elasticity.

        """
        x_1, x_2 = x

        T = len(self.𝒫_t_tilde_path) - 1

        if t > T:
            self.iterate(t-T)

        Σ_t_tilde = self.Σ_t_tilde_path[t]  # FIX HERE
        _, _, _, _, Ψ_0, Ψ_1, _ = self.𝒫_t_tilde_path[t]

        μ_0_t = Ψ_0.T
        μ_1_t = mat(Ψ_1, (self.k, self.n))

        if self.α_h is None:
            𝛆_x_t = Σ_t_tilde @ (μ_0_t + μ_1_t @ x_1)
        else:
            𝛆_x_t = self.α_h.T @ Σ_t_tilde @ (μ_0_t + μ_1_t @ x_1)

        return 𝛆_x_t
