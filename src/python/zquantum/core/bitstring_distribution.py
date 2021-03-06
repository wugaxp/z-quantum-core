import math
import sys
import warnings
import json
import numpy as np
from .utils import SCHEMA_VERSION, convert_tuples_to_bitstrings
from collections import Counter

def is_non_negative(input_dict):
    """Check if the input dictionary values are non negative.

    Args:
        input_dict (dict): dictionary.

    Returns:
        bool: boolean variable indicating whether dict values are non negative or not.
    """
    return all(value >= 0 for value in input_dict.values())


def is_key_length_fixed(input_dict):
    """Check if the input dictionary keys are same-length.

    Args:
        input_dict (dict): dictionary.

    Returns:
        bool: boolean variable indicating whether dict keys are same-length or not.
    """
    key_length = len(list(input_dict.keys())[0])
    return all(len(key) == key_length for key in input_dict.keys())


def are_keys_binary_strings(input_dict):
    """Check if the input dictionary keys are binary strings.

    Args:
        input_dict (dict): dictionary.

    Returns:
        bool: boolean variable indicating whether dict keys are binary strings or not.
    """
    return all(not any(char not in '10' for char in key) for key in input_dict.keys())


def is_bitstring_distribution(input_dict):
    """Check if the input dictionary is a bitstring distribution, i.e.:
            - keys are same-lenght binary strings,
            - values are non negative.

    Args:
        input_dict (dict): dictionary representing the probability distribution where the keys are bitstrings represented as strings and the values are floats.

    Returns:
        bool: boolean variable indicating whether the bitstring distribution is well defined or not.
    """
    return (is_non_negative(input_dict) and is_key_length_fixed(input_dict) and are_keys_binary_strings(input_dict))


def is_normalized(input_dict):
    """Check if a bitstring distribution is normalized.

    Args:
        bitstring_distribution (dict): dictionary representing the probability distribution where the keys are bitstrings represented as strings and the values are floats.

    Returns:
        bool: boolean variable indicating whether the bitstring distribution is normalized or not.
    """
    norm = sum(input_dict.values())
    return (math.isclose(norm,1))


def normalize_bitstring_distribution(bitstring_distribution):
    """Normalize a bitstring distribution.

    Args:
        bitstring_distribution (dict): dictionary representing the probability distribution where the keys are bitstrings represented as strings and the values are floats.

    Returns:
        dict: dictionary representing the normalized probability distribution where the keys are bitstrings represented as strings and the values are floats.
    """
    norm = sum(bitstring_distribution.values())
    if norm==0:
         raise ValueError('Normalization of BitstringDistribution FAILED: input dict is empty (all zero values).')
    elif 0 < norm < sys.float_info.min:
        raise ValueError('Normalization of BitstringDistribution FAILED: too small values.')
    elif norm == 1:
        return bitstring_distribution
    else:
        for key in bitstring_distribution:
            bitstring_distribution[key]*=1./norm
        return bitstring_distribution


def save_bitstring_distribution(distribution, filename):
    """Save a bistring distribution to a file.

    Args:
        distribution (BitstringDistribution): the bistring distribution
        file (str or file-like object): the name of the file, or a file-like object
    """
    dictionary = {}
    dictionary["bitstring_distribution"] = distribution.distribution_dict
    dictionary["schema"] = SCHEMA_VERSION + "-bitstring-probability-distribution"

    with open(filename, 'w') as f:
        f.write(json.dumps(dictionary, indent=2))


def load_bitstring_distribution(file, many=False):
    """Load an bitstring_distribution from a json file using a schema.

    Arguments:
        file (str): the name of the file
        many (bool): if True, the file is assumend to contain a
            list of objects obeying the schema
    Returns:
        object: a python object loaded from the bitstring_distribution
    """

    if isinstance(file, str):
        with open(file, 'r') as f:
            data = json.load(f)
    else:
        data = json.load(file)
    
    bitstring_distribution = BitstringDistribution(data["bitstring_distribution"])
    return bitstring_distribution
    

def create_bitstring_distribution_from_probability_distribution(prob_distribution):
    """Create a well defined bitstring distribution starting from a probability distribution

    Args:
        probability distribution (np.array): The probabilites of the various states in the wavefunction

    Returns:
        BitstringDistribution : The BitstringDistribution object corresponding to the input measurements.
    """

    # Create dictionary of bitstring tuples as keys with probability as value
    prob_dict = {}
    for state in range(len(prob_distribution)):
        # Convert state to bitstring
        bitstring = format(state, 'b')
        while (len(bitstring) < np.sqrt(len(prob_distribution))):
            bitstring = '0' + bitstring
        # Reverse bitstring
        bitstring = bitstring[::-1]

        # Add to dict
        prob_dict[bitstring] = prob_distribution[state]

    return BitstringDistribution(prob_dict)


def create_bitstring_distribution_from_measurements(measurements):
    """Create a well defined bitstring distribution starting from a list of bistrings, resulting from measurements.
    Args:
        measurements (list): List of bitstrings (tuples of integers) representing the outcomes of measurements.
    Returns:
        zquantum.core.bistring_distribution.BitstringDistribution : The BitstringDistribution object corresponding to the input measurements.
    """
    bitstring = convert_tuples_to_bitstrings(measurements)
    bitstring_distribution=dict(Counter(bitstring))
    return BitstringDistribution(bitstring_distribution)


class BitstringDistribution():
    """A probability distribution defined on discrete bitstrings. Normalization is performed by default, unless otherwise specified.

    Args:
        input_dict (dict):  dictionary representing the probability distribution where the keys are bitstrings represented as strings and the values are non-negative floats.

    Attributes:
        bitstring_distribution (dict): dictionary representing the probability distribution where the keys are bitstrings represented as strings and the values are non-negative floats.
    """

    def __init__(self, input_dict, normalize=True):
        if(is_bitstring_distribution(input_dict)): # accept the input dict only if it is a prob distribution
            if(is_normalized(input_dict)):
                self.distribution_dict = input_dict
            else:
                if(normalize==True):
                    self.distribution_dict = normalize_bitstring_distribution(input_dict)
                else:
                    warnings.warn("BitstringDistribution object is not normalized.")
                    self.distribution_dict = input_dict
        else:
            raise RuntimeError("Initialization of BitstringDistribution object FAILED: the input dictionary is not a bitstring probability distribution. Check keys (same-length binary strings) and values (non-negative floats).")

    def __repr__(self):
        output = f'BitstringDistribution(input={self.distribution_dict})'
        return output

    def get_qubits_number(self):
        """Compute how many qubits a bitstring is composed of.

        Returns:
            float: number of qubits in a bitstring (i.e. bitstring length).
        """
        return(len(list(self.distribution_dict.keys())[0])) # already checked in __init__ that all keys have the same length


def compute_clipped_negative_log_likelihood(target_distr, measured_distr, epsilon=1e-9):
    """Compute the value of the clipped negative log likelihood between a target bitstring distribution 
    and a measured bitstring distribution
    See Equation (4) in https://advances.sciencemag.org/content/5/10/eaaw9918?rss=1

    Args:
        target_distr (BitstringDistribution): The target bitstring probability distribution.
        measured_distr (BitstringDistribution): The measured bitstring probability distribution.
        epsilon (float): The small parameter needed to regularize log computation when argument is zero. Default = 1e-9.
    Returns:
        float: The value of the clipped negative log likelihood
    """

    value=0.
    target_keys = target_distr.distribution_dict.keys()
    measured_keys = measured_distr.distribution_dict.keys()
    all_keys = set(target_keys).union(measured_keys)

    for bitstring in all_keys:
        target_bitstring_value = target_distr.distribution_dict.get(bitstring,0)
        measured_bitstring_value = measured_distr.distribution_dict.get(bitstring,0)

        value += target_bitstring_value * math.log(max(epsilon,measured_bitstring_value))

    return -value


def evaluate_distribution_distance(target_distr, measured_distr,
    distance_measure="clipped_log_likelihood", **kwargs):
    """Evaluate the distance between two bitstring distributions - the target distribution and the one predicted (measured) by your model -
       based on the chosen distance measure

       Args:
            target_distr (BitstringDistribution): The target bitstring probability distribution
            measured_distr (BitstringDistribution): The measured bitstring probability distribution
            distance_measure (str): name of the distance measure to be used. 
                Currently implemented: clipped negative log-likelihood.

            Additional parameters can be passed as key word arguments.

       Returns:
            float: The value of the distance metric
    """
    # Check inputs are BitstringDistribution objects
    if not isinstance(target_distr, BitstringDistribution) or not isinstance(measured_distr,BitstringDistribution):
        raise TypeError("Arguments of evaluate_cost_function must be of type BitstringDistribution.")

    # Check inputs are defined on consistent bitstring domains
    if target_distr.get_qubits_number() != measured_distr.get_qubits_number():
        raise RuntimeError('Bitstring Distribution Distance Evaluation FAILED: target and measured distributions are defined on bitstrings of different length.')

    # Check inputs are both normalized (or not normalized)
    if is_normalized(target_distr.distribution_dict) != is_normalized(measured_distr.distribution_dict):
        raise RuntimeError('Bitstring Distribution Distance Evaluation FAILED: one among target and measured distribution is normalized, whereas the other is not.')

    if distance_measure=="clipped_log_likelihood":
        return compute_clipped_negative_log_likelihood(target_distr, measured_distr, **kwargs)
    #elif distance_measure=="something else":
    #remember to initialize cost_function
    else:
        raise RuntimeError('Bitstring Distribution Distance Measure "{}" not implemented.'.format(distance_measure))
