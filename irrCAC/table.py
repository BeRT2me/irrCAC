""" Chance-corrected Agreement Coefficient for tabular ratings.

Examples
--------
>>> from irrCAC.datasets import table_cont3x3abstractors
>>> from irrCAC.table import CAC
>>> data = table_cont3x3abstractors()  # doctest: +NORMALIZE_WHITESPACE
>>> print(data)
         Ectopic  AIU  NIU
Ectopic       13    0    0
AIU            0   20    7
NIU            0    4   56

Initialize a CAC object with the data from the contigency table

>>> cont3x3abstractors = CAC(data)
>>> print(cont3x3abstractors.gwet())  # doctest: +NORMALIZE_WHITESPACE
'est': {'coefficient_value': 0.84933,
        'coefficient_name': "Gwet's AC1",
        'confidence_interval': (0.76358, 0.93508),
        'p_value': 0.0,
        'z': 19.65248,
        'se': 0.04322,
        'pa': 0.89,
        'pe': 0.26992},
'weights': array([[1., 0., 0.],
                  [0., 1., 0.],
                  [0., 0., 1.]]),
'categories': ['Ectopic', 'AIU', 'NIU']}

To use weights with the calculations, we pass the type of weights as argument.

>>> cont3x3abstractors_quadratic = CAC(data, weights='quadratic')
>>> print(cont3x3abstractors_quadratic.gwet())  # doctest: +NORMALIZE_WHITESPACE
{'est': {'coefficient_value': 0.94024,
         'coefficient_name': "Gwet's AC2",
         'confidence_interval': (0.90468, 0.97579),
         'p_value': 0.0,
         'z': 52.46802,
         'se': 0.01792,
         'pa': 0.9725,
         'pe': 0.53985},
'weights': array([[1.  , 0.75, 0.  ],
                  [0.75, 1.  , 0.75],
                  [0.  , 0.75, 1.  ]]),
'categories': ['Ectopic', 'AIU', 'NIU']}
"""
import numpy as np
from scipy import stats
from irrCAC.weights import Weights


class CAC:
    """ Chance-corrected Agreement Coefficients (CAC) 
    
    The following chance-corrected agreement coefficients (CAC) among 2 raters
    are provided.

    * Brennan-Prediger,
    * Cohen's kappa,
    * Gwet's AC1/AC2,
    * Krippendorff's Alpha,
    * Percent Agreement,
    * Scott's Pi.

    Multiple sets of weights are proposed for computing weighted analyses.
    All of these statistical procedures are described in details in Gwet, K.L.
    (2014,ISBN:978-0970806284): "Handbook of Inter-Rater Reliability,"
    4th edition, Advanced Analytics, LLC.

    Parameters
    ----------
    ratings : DataFrame
        A data frame of ratings where each column represents one rater and
        each row one subject.
    weights : array-like, ndarray, or str, {"identity", "quadratic", "ordinal",\
    "linear", "radical", "ratio", "circular", "bipolar"}
        A mandatory parameter that is either a string variable or a matrix.
        The string describes one of the predefined weights. If this
        parameter is a matrix then it must be a square matrix qxq where q
        is the number of possible categories where a subject can be
        classified. If some of the q possible categories are not used,
        then it is strongly advised to specify the complete list of
        possible categories as a vector in parameter ``categories``.
        Otherwise, the program may not work.
    confidence_level : float, default 0.95
        An optional parameter representing the confidence level associated
        with the confidence interval. Its default value is 0.95.
    N : int, default infinity
        An optional parameter representing the population size (if any).
        It may be used to perform the final population correction to the
        variance. Its default value is infinity.
    digits : int, default 5
        The number of digits to round the results.
    """
    def __init__(
            self,
            ratings,
            weights='identity',
            confidence_level=0.95,
            N=np.inf,
            digits=5):
        weights_choices = (
            "identity", "quadratic", "ordinal", "linear",
            "radical", "ratio", "circular", "bipolar")
        if weights not in weights_choices:
            raise ValueError(f'weights values can be any of {weights_choices}')
        assert 0 < confidence_level <= 0.99,\
            'Confidence level should be in the range (0, 1).'
        self.confidence_level = confidence_level

        if isinstance(weights, str):
            self.weights_name = weights
            weights_functions = Weights(list(range(1, len(ratings) + 1)))
            self.weights_mat = weights_functions[self.weights_name]
        else:
            self.weights_name = 'Custom Weights'
            self.weights_mat = np.asarray(weights)
            if ratings.shape[0] != self.weights_mat.shape[0]:
                raise AttributeError(
                    f'We expect a {ratings.shape[0]}x{ratings.shape[1]}'
                    f' weights matrix but the input matrix is '
                    f'{self.weights_mat.shape[0]}x{self.weights_mat.shape[1]}.'
                )

        if ratings.shape[0] != ratings.shape[1]:
            raise AttributeError(
                'The contingency table should have the same '
                'number of rows and columns.')
        self.ratings = ratings
        self.n = np.sum(ratings.values)
        self.f = self.n / N
        self.q = len(self.ratings)
        self.pa = np.sum(self.ratings.values * self.weights_mat / self.n)
        self.digits = digits
        self.agreement = {
            'est': {
                'coefficient_value': 0,
                'coefficient_name': None,
                'confidence_interval': (0, 0),
                'p_value': 0,
                'z': 0,
                'se': 0,
                'pa': self.pa,
                'pe': 0,
            },
            'weights': self.weights_mat,
            'categories': self.ratings.index.to_list()
        }

    def __str__(self):
        subjects = f'Subjects: {self.n}'
        categories = f'Categories: {self.agreement["categories"]}'
        weights_name = f'Weights: "{self.weights_name}"'
        class_path = f'{CAC.__module__}.{CAC.__name__}'
        _str = f'{class_path} {subjects}, {categories}, {weights_name}'
        return f'<{_str}>'

    def __repr__(self):
        return self.__str__()

    def bp(self):
        """ Brennan-Prediger coefficient for 2 raters.
        """

        tw = np.sum(self.weights_mat)
        pe = tw / pow(self.q, 2)
        bp_coeff = (self.pa - pe) / (1 - pe)
        pkl = self.ratings.values / self.n
        sum1 = 0
        for k in range(self.q):
            for l in range(self.q):
                sum1 += pkl[k, l] * self.weights_mat[k, l]**2
        var_bp = ((1 - self.f) / (self.n * (1 - pe)**2)) * (sum1 - self.pa**2)
        stderr = np.sqrt(var_bp)
        p_value = 2 * (1 - stats.t.cdf(abs(bp_coeff / stderr), self.n - 1))
        lcb, ucb = stats.t.interval(
            alpha=self.confidence_level,
            df=self.n - 1,
            scale=stderr,
            loc=bp_coeff)
        ucb = min(1, ucb)
        self.agreement['est'].update(
            dict(
                coefficient_name='Brennan-Prediger',
                pa=np.round(self.pa, self.digits),
                pe=round(pe, self.digits),
                se=round(stderr, self.digits),
                z=round(bp_coeff / stderr, self.digits),
                coefficient_value=round(bp_coeff, self.digits),
                confidence_interval=(
                    round(lcb, self.digits), round(ucb, self.digits)),
                p_value=round(p_value, self.digits)))
        return self.agreement

    def cohen(self):
        """ Cohen's kappa coefficient for 2 raters.
        
        Cohen's kappa measures the agreement between two raters who each
        classify N subjects into :math:`q` mutually exclusive categories.
        """
        pk_dot = (self.ratings.sum(axis=1) / self.n).values.reshape(-1, 1)
        p_dot_l = (self.ratings.sum(axis=0) / self.n).values.reshape(-1, 1)
        pe = np.sum(self.weights_mat * np.matmul(pk_dot, p_dot_l.T))
        kappa = (self.pa - pe) / (1 - pe)
        pkl = self.ratings.values / self.n
        pb_dot_k = (self.weights_mat * p_dot_l).sum(axis=0)
        pbl_dot = (self.weights_mat * pk_dot).sum(axis=0)
        sum1 = 0
        for k in range(self.q):
            for l in range(self.q):
                sum1 += pkl[k][l] * (
                    self.weights_mat[k][l] - (1 - kappa) *
                    (pb_dot_k[k] + pbl_dot[l]))**2
        var_kappa = ((1 - self.f) / (self.n * (1 - pe)**2)) * (
            sum1 - (self.pa - 2 * (1 - kappa) * pe)**2)
        stderr = np.sqrt(var_kappa)
        p_value = 2 * (1 - stats.t.cdf(abs(kappa / stderr), self.n - 1))
        lcb, ucb = stats.t.interval(
            alpha=self.confidence_level,
            df=self.n - 1,
            scale=stderr,
            loc=kappa)
        ucb = min(1, ucb)
        self.agreement['est'].update(
            dict(
                coefficient_name="Cohen's kappa",
                pa=np.round(self.pa, self.digits),
                pe=np.round(pe, self.digits),
                se=np.round(stderr, self.digits),
                z=np.round(kappa / stderr, self.digits),
                coefficient_value=np.round(kappa, self.digits),
                confidence_interval=(
                    np.round(lcb, self.digits), np.round(ucb, self.digits)),
                p_value=np.round(p_value, self.digits)))
        return self.agreement

    def gwet(self):
        """ Gwet's AC1/AC2 coefficient for 2 raters.

        The AC1 coefficient was suggested by Gwet (2008a) as a paradox-resistant
        alternative to Cohen’s Kappa. The percent chance agreement it is
        defined as the propensity for raters to agree on hard-to-score
        subjects and is calculated by multiplying the probability to agree
        when the rating is random by the probability to select a
        hard-to-score subject.

        The Gwet's AC2 coefficient is the one when using weight for the
        calculation.
        """
        pk_dot = (self.ratings.sum(axis=1) / self.n).values.reshape(-1, 1)
        p_dot_l = (self.ratings.sum(axis=0) / self.n).values.reshape(-1, 1)
        pi_dot_k = (pk_dot + p_dot_l) / 2
        tw = np.sum(self.weights_mat)
        pe = tw * np.sum(pi_dot_k * (1 - pi_dot_k)) / (self.q * (self.q - 1))
        ac1 = (self.pa - pe) / (1 - pe)
        pkl = self.ratings.values / self.n
        sum1 = 0
        for k in range(self.q):
            for l in range(self.q):
                sum1 += float(
                    pkl[k][l] * (
                        self.weights_mat[k][l] - 2 * (1 - ac1) * tw *
                        (1 - (pi_dot_k[k] + pi_dot_k[l]) / 2) /
                        (self.q * (self.q - 1)))**2)
        var_gwet = ((1 - self.f) / (self.n * (1 - pe)**2)) * (
            sum1 - (self.pa - 2 * (1 - ac1) * pe)**2)
        stderr = np.sqrt(var_gwet)
        p_value = 2 * (1 - stats.t.cdf(abs(ac1 / stderr), self.n - 1))
        lcb, ucb = stats.t.interval(
            alpha=self.confidence_level, df=self.n - 1, scale=stderr, loc=ac1)
        ucb = min(1, ucb)
        if np.sum(self.weights_mat) == self.q:
            coeff_name = "Gwet's AC1"
        else:
            coeff_name = "Gwet's AC2"
        self.agreement['est'].update(
            dict(
                coefficient_name=coeff_name,
                pa=np.round(self.pa, self.digits),
                pe=np.round(pe, self.digits),
                se=np.round(stderr, self.digits),
                z=np.round(ac1 / stderr, self.digits),
                coefficient_value=np.round(ac1, self.digits),
                confidence_interval=(
                    np.round(lcb, self.digits), np.round(ucb, self.digits)),
                p_value=np.round(p_value, self.digits)))
        return self.agreement

    def krippendorff(self):
        """ Krippendorff’s Alpha coefficient for 2 raters.

        .. versionadded:: 0.2.0
        """
        epsi = 1 / (2 * self.n)
        pa = (1 - epsi) * self.pa + epsi
        pk_dot = (self.ratings.sum(axis=1) / self.n).values.reshape(-1, 1)
        p_dot_l = (self.ratings.sum(axis=0) / self.n).values.reshape(-1, 1)
        pi_dot_k = (pk_dot + p_dot_l) / 2
        pe = np.sum(self.weights_mat * (pi_dot_k * pi_dot_k.T))
        kripen_coeff = (pa - pe) / (1 - pe)
        pkl = self.ratings.values / self.n
        pb_dot_k = (self.weights_mat * p_dot_l).sum(axis=0)
        pbl_dot = (self.weights_mat * pk_dot).sum(axis=0)
        pbk = (pb_dot_k + pbl_dot) / 2
        kcoeff = (self.pa - pe) / (1 - pe)
        sum1 = 0
        for k in range(self.q):
            for l in range(self.q):
                sum1 += pkl[k][l] * (
                        self.weights_mat[k][l] - (1 - kcoeff) *
                        (pbk[k] + pbk[l]))**2
        var_kripp = ((1 - self.f) / (self.n * (1 - pe)**2)) * (
                sum1 - (self.pa - 2 * (1 - kcoeff) * pe)**2)
        stderr = np.sqrt(var_kripp)
        p_value = 2 * (1 - stats.t.cdf(abs(kripen_coeff / stderr), self.n - 1))
        lcb, ucb = stats.t.interval(
            alpha=self.confidence_level,
            df=self.n - 1,
            scale=stderr,
            loc=kripen_coeff)
        ucb = min(1, ucb)
        self.agreement['est'].update(
            dict(
                coefficient_name="Krippendorff's Alpha",
                pa=np.round(pa, self.digits),
                pe=np.round(pe, self.digits),
                se=np.round(stderr, self.digits),
                z=np.round(kripen_coeff / stderr, self.digits),
                coefficient_value=np.round(kripen_coeff, self.digits),
                confidence_interval=(
                    np.round(lcb, self.digits), np.round(ucb, self.digits)),
                p_value=np.round(p_value, self.digits)))
        return self.agreement

    def pa2(self):
        """ Percent Agreement coefficient for 2 raters.

        .. versionadded:: 0.2.0
        """
        pkl = self.ratings.values / self.n
        sum1 = 0
        for k in range(self.q):
            for l in range(self.q):
                sum1 += pkl[k][l] * self.weights_mat[k][l] ** 2
        var_pa = ((1  -  self.f) / self.n) * (sum1 - self.pa ** 2)
        stderr = np.sqrt(var_pa)
        p_value = 2 * (1 - stats.t.cdf(abs(self.pa / stderr), self.n - 1))
        lcb, ucb = stats.t.interval(
            alpha=self.confidence_level,
            df=self.n - 1,
            scale=stderr,
            loc=self.pa)
        ucb = min(1, ucb)
        self.agreement['est'].update(
            dict(
                coefficient_name="Percent Agreement",
                pa=np.round(self.pa, self.digits),
                pe=0,
                se=np.round(stderr, self.digits),
                z=np.round(self.pa / stderr, self.digits),
                coefficient_value=np.round(self.pa, self.digits),
                confidence_interval=(
                    np.round(lcb, self.digits), np.round(ucb, self.digits)),
                p_value=np.round(p_value, self.digits)))
        return self.agreement

    def scott(self):
        """ Scott’s Pi coefficient for 2 raters.
         
         .. versionadded:: 0.2.0
         """
        pk_dot = (self.ratings.sum(axis=1) / self.n).values.reshape(-1, 1)
        p_dot_l = (self.ratings.sum(axis=0) / self.n).values.reshape(-1, 1)
        pi_dot_k = (pk_dot + p_dot_l) / 2
        pe = np.sum(self.weights_mat * (pi_dot_k * pi_dot_k.T))
        scott = (self.pa - pe) / (1 - pe)
        pkl = self.ratings.values / self.n
        pb_dot_k = (self.weights_mat * p_dot_l).sum(axis=0)
        pbl_dot = (self.weights_mat * pk_dot).sum(axis=0)
        pbk = (pb_dot_k + pbl_dot) / 2
        sum1 = 0
        for k in range(self.q):
            for l in range(self.q):
                sum1 += pkl[k][l] * (
                        self.weights_mat[k][l] - (1 - scott) *
                        (pbk[k] + pbk[l]))**2
        var_scott = ((1 - self.f) / (self.n * (1 - pe)**2)) * (
                sum1 - (self.pa - 2 * (1 - scott) * pe)**2)
        stderr = np.sqrt(var_scott)
        p_value = 2 * (1 - stats.t.cdf(abs(self.pa / stderr), self.n - 1))
        lcb, ucb = stats.t.interval(
            alpha=self.confidence_level,
            df=self.n - 1,
            scale=stderr,
            loc=scott)
        ucb = min(1, ucb)
        self.agreement['est'].update(
            dict(
                coefficient_name="Scott's Pi",
                pa=np.round(self.pa, self.digits),
                pe=0,
                se=np.round(stderr, self.digits),
                z=np.round(scott / stderr, self.digits),
                coefficient_value=np.round(scott, self.digits),
                confidence_interval=(
                    np.round(lcb, self.digits), np.round(ucb, self.digits)),
                p_value=np.round(p_value, self.digits)))
        return self.agreement
