import math
from typing import List, Optional


def calculate_mean(values: List[float]) -> float:
    """Calculates the arithmetic mean of a numeric list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def calculate_median(values: List[float]) -> float:
    """Calculates the median value of a numeric list."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
    return float(sorted_vals[mid])


def calculate_std_dev(values: List[float], mean: Optional[float] = None) -> float:
    """Calculates the sample standard deviation (N-1) of a numeric list."""
    n = len(values)
    if n <= 1:
        return 0.0
    if mean is None:
        mean = calculate_mean(values)
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return math.sqrt(variance)


def calculate_percentile(values: List[float], p: float) -> float:
    """
    Calculates the p-th percentile of a numeric list (0 <= p <= 100)
    using linear interpolation.
    """
    if not values:
        return 0.0
    if p < 0:
        p = 0.0
    elif p > 100:
        p = 100.0

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])

    idx = (n - 1) * (p / 100.0)
    low = math.floor(idx)
    high = math.ceil(idx)

    if low == high:
        return float(sorted_vals[int(idx)])

    # Linear interpolation
    d = idx - low
    return sorted_vals[low] * (1.0 - d) + sorted_vals[high] * d


def calculate_iqr_bounds(values: List[float], factor: float = 1.5) -> tuple[float, float, float, float]:
    """
    Calculates Interquartile Range (IQR) parameters.
    Returns: (Q1, Q3, Lower Bound, Upper Bound).
    """
    if not values:
        return 0.0, 0.0, 0.0, 0.0
    q1 = calculate_percentile(values, 25)
    q3 = calculate_percentile(values, 75)
    iqr = q3 - q1
    lower_bound = q1 - (factor * iqr)
    upper_bound = q3 + (factor * iqr)
    return q1, q3, lower_bound, upper_bound


def detect_outliers_iqr(values: List[float], factor: float = 1.5) -> List[bool]:
    """
    Flags outliers using the Interquartile Range (IQR) rule.
    Returns a list of booleans corresponding to outlier status of each element.
    """
    _, _, lower, upper = calculate_iqr_bounds(values, factor)
    return [x < lower or x > upper for x in values]


def detect_outliers_zscore(values: List[float], threshold: float = 3.0) -> List[bool]:
    """
    Flags outliers using the standard Z-score rule.
    Returns a list of booleans indicating if the value resides beyond standard deviations.
    """
    n = len(values)
    if n <= 1:
        return [False] * n
    mean = calculate_mean(values)
    std = calculate_std_dev(values, mean)
    if std == 0.0:
        return [False] * n
    return [abs(x - mean) / std > threshold for x in values]


def calculate_skewness(values: List[float]) -> Optional[float]:
    """Calculates Fisher-Pearson standardized moment coefficient of skewness."""
    n = len(values)
    if n < 3:
        return None
    mean = calculate_mean(values)
    std = calculate_std_dev(values, mean)
    if std == 0.0:
        return 0.0

    m3 = sum((x - mean) ** 3 for x in values) / n
    m2 = sum((x - mean) ** 2 for x in values) / n
    # Fisher-Pearson coefficient
    return m3 / (m2**1.5)


def calculate_kurtosis(values: List[float]) -> Optional[float]:
    """Calculates excess kurtosis (relative to standard normal distribution)."""
    n = len(values)
    if n < 4:
        return None
    mean = calculate_mean(values)
    std = calculate_std_dev(values, mean)
    if std == 0.0:
        return 0.0

    m4 = sum((x - mean) ** 4 for x in values) / n
    m2 = sum((x - mean) ** 2 for x in values) / n
    # Excess kurtosis
    return (m4 / (m2**2)) - 3.0


def calculate_correlation(x: List[float], y: List[float]) -> float:
    """Calculates Pearson correlation coefficient between two variables."""
    n = len(x)
    if n != len(y) or n <= 1:
        return 0.0
    mean_x = calculate_mean(x)
    mean_y = calculate_mean(y)

    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / (n - 1)
    std_x = calculate_std_dev(x, mean_x)
    std_y = calculate_std_dev(y, mean_y)

    if std_x == 0.0 or std_y == 0.0:
        return 0.0

    return cov / (std_x * std_y)


def calculate_correlation_matrix(columns_data: List[List[float]]) -> List[List[float]]:
    """Generates a square Pearson correlation matrix for multiple numeric variables."""
    num_cols = len(columns_data)
    matrix = [[1.0] * num_cols for _ in range(num_cols)]

    for i in range(num_cols):
        for j in range(i + 1, num_cols):
            corr = calculate_correlation(columns_data[i], columns_data[j])
            matrix[i][j] = corr
            matrix[j][i] = corr

    return matrix


def calculate_hhi(exposures: List[float]) -> float:
    """
    Calculates the Herfindahl-Hirschman Index (HHI) for credit concentration.
    HHI ranges from 0 to 10,000 (perfect concentration = 10,000).
    """
    total = sum(exposures)
    if total <= 0:
        return 0.0
    shares = [(val / total) * 100 for val in exposures]
    return sum(s**2 for s in shares)
