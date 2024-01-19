from __future__ import annotations

from typing import Iterable, Callable, Any
import warnings
from ...compat import Number
import re

FORMATTER = Callable[
    [
        Any,
    ],
    str,
]


def formatter(
    items: Iterable[tuple[str, Number]],
    as_ratio: bool = True,
    single_denominator: bool = False,
    product_fmt: str = " * ",
    division_fmt: str = " / ",
    power_fmt: str = "{} ** {}",
    parentheses_fmt: str = "({0})",
    exp_call: FORMATTER = "{:n}".format,
    sort: bool = True,
) -> str:
    """Format a list of (name, exponent) pairs.

    Parameters
    ----------
    items : list
        a list of (name, exponent) pairs.
    as_ratio : bool, optional
        True to display as ratio, False as negative powers. (Default value = True)
    single_denominator : bool, optional
        all with terms with negative exponents are
        collected together. (Default value = False)
    product_fmt : str
        the format used for multiplication. (Default value = " * ")
    division_fmt : str
        the format used for division. (Default value = " / ")
    power_fmt : str
        the format used for exponentiation. (Default value = "{} ** {}")
    parentheses_fmt : str
        the format used for parenthesis. (Default value = "({0})")
    exp_call : callable
         (Default value = lambda x: f"{x:n}")
    sort : bool, optional
        True to sort the formatted units alphabetically (Default value = True)

    Returns
    -------
    str
        the formula as a string.

    """

    if sort:
        items = sorted(items)
    else:
        items = tuple(items)

    if not items:
        return ""

    if as_ratio:
        fun = lambda x: exp_call(abs(x))
    else:
        fun = exp_call

    pos_terms, neg_terms = [], []

    for key, value in items:
        if value == 1:
            pos_terms.append(key)
        elif value > 0:
            pos_terms.append(power_fmt.format(key, fun(value)))
        elif value == -1 and as_ratio:
            neg_terms.append(key)
        else:
            neg_terms.append(power_fmt.format(key, fun(value)))

    if not as_ratio:
        # Show as Product: positive * negative terms ** -1
        return _join(product_fmt, pos_terms + neg_terms)

    # Show as Ratio: positive terms / negative terms
    pos_ret = _join(product_fmt, pos_terms) or "1"

    if not neg_terms:
        return pos_ret

    if single_denominator:
        neg_ret = _join(product_fmt, neg_terms)
        if len(neg_terms) > 1:
            neg_ret = parentheses_fmt.format(neg_ret)
    else:
        neg_ret = _join(division_fmt, neg_terms)

    return _join(division_fmt, [pos_ret, neg_ret])


# Extract just the type from the specification mini-language: see
# http://docs.python.org/2/library/string.html#format-specification-mini-language
# We also add uS for uncertainties.
_BASIC_TYPES = frozenset("bcdeEfFgGnosxX%uS")


def _parse_spec(spec: str) -> str:
    # TODO: provisional
    from ...formatting import _FORMATTERS

    result = ""
    for ch in reversed(spec):
        if ch == "~" or ch in _BASIC_TYPES:
            continue
        elif ch in list(_FORMATTERS.keys()) + ["~"]:
            if result:
                raise ValueError("expected ':' after format specifier")
            else:
                result = ch
        elif ch.isalpha():
            raise ValueError("Unknown conversion specified " + ch)
        else:
            break
    return result


__JOIN_REG_EXP = re.compile(r"{\d*}")


def _join(fmt: str, iterable: Iterable[Any]) -> str:
    """Join an iterable with the format specified in fmt.

    The format can be specified in two ways:
    - PEP3101 format with two replacement fields (eg. '{} * {}')
    - The concatenating string (eg. ' * ')

    Parameters
    ----------
    fmt : str

    iterable :


    Returns
    -------
    str

    """
    if not iterable:
        return ""
    if not __JOIN_REG_EXP.search(fmt):
        return fmt.join(iterable)
    miter = iter(iterable)
    first = next(miter)
    for val in miter:
        ret = fmt.format(first, val)
        first = ret
    return first


_PRETTY_EXPONENTS = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def _pretty_fmt_exponent(num: Number) -> str:
    """Format an number into a pretty printed exponent.

    Parameters
    ----------
    num : int

    Returns
    -------
    str

    """
    # unicode dot operator (U+22C5) looks like a superscript decimal
    ret = f"{num:n}".replace("-", "⁻").replace(".", "\u22C5")
    for n in range(10):
        ret = ret.replace(str(n), _PRETTY_EXPONENTS[n])
    return ret


def extract_custom_flags(spec: str) -> str:
    import re

    if not spec:
        return ""

    # TODO: provisional
    from ...formatting import _FORMATTERS

    # sort by length, with longer items first
    known_flags = sorted(_FORMATTERS.keys(), key=len, reverse=True)

    flag_re = re.compile("(" + "|".join(known_flags + ["~"]) + ")")
    custom_flags = flag_re.findall(spec)

    return "".join(custom_flags)


def remove_custom_flags(spec: str) -> str:
    # TODO: provisional
    from ...formatting import _FORMATTERS

    for flag in sorted(_FORMATTERS.keys(), key=len, reverse=True) + ["~"]:
        if flag:
            spec = spec.replace(flag, "")
    return spec


def split_format(
    spec: str, default: str, separate_format_defaults: bool = True
) -> tuple[str, str]:
    mspec = remove_custom_flags(spec)
    uspec = extract_custom_flags(spec)

    default_mspec = remove_custom_flags(default)
    default_uspec = extract_custom_flags(default)

    if separate_format_defaults in (False, None):
        # should we warn always or only if there was no explicit choice?
        # Given that we want to eventually remove the flag again, I'd say yes?
        if spec and separate_format_defaults is None:
            if not uspec and default_uspec:
                warnings.warn(
                    (
                        "The given format spec does not contain a unit formatter."
                        " Falling back to the builtin defaults, but in the future"
                        " the unit formatter specified in the `default_format`"
                        " attribute will be used instead."
                    ),
                    DeprecationWarning,
                )
            if not mspec and default_mspec:
                warnings.warn(
                    (
                        "The given format spec does not contain a magnitude formatter."
                        " Falling back to the builtin defaults, but in the future"
                        " the magnitude formatter specified in the `default_format`"
                        " attribute will be used instead."
                    ),
                    DeprecationWarning,
                )
        elif not spec:
            mspec, uspec = default_mspec, default_uspec
    else:
        mspec = mspec or default_mspec
        uspec = uspec or default_uspec

    return mspec, uspec


def join_mu(joint_fstring: str, mstr: str, ustr: str) -> str:
    if ustr.startswith("1 / "):
        return joint_fstring.format(mstr, ustr[2:])
    return joint_fstring.format(mstr, ustr)
