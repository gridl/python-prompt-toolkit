import six
from typing import Union, Any, Callable, List, Tuple, Iterable
from typing_extensions import Protocol

__all__ = [
    'StyleAndTextTuples',
    'MagicFormattedText',
    'AnyFormattedText',
    'to_formatted_text',
    'is_formatted_text',
    'Template',
    'merge_formatted_text',
    'FormattedText',
]

# List of (style, text) tuples.
StyleAndTextTuples = List[Tuple[str, str]]
StyleAndTextTuplesWithMouseHandlers = List[Union[Tuple[str, str], Tuple[str, str, Callable]]]


class MagicFormattedText(Protocol):
    """
    Any object that implements ``__pt_formatted_text__`` represents formatted
    text.
    """
    def __pt_formatted_text__(self) -> 'AnyFormattedText':
        ...


AnyFormattedText = Union[
    str,
    MagicFormattedText,
    StyleAndTextTuples,
    Callable[[], 'AnyFormattedText']
]


def to_formatted_text(value: AnyFormattedText, style: str = '',
                      auto_convert: bool = False):
    """
    Convert the given value (which can be formatted text) into a list of text
    fragments. (Which is the canonical form of formatted text.) The outcome is
    always a `FormattedText` instance, which is a list of (style, text) tuples.

    It can take an `HTML` object, a plain text string, or anything that
    implements `__pt_formatted_text__`.

    :param style: An additional style string which is applied to all text
        fragments.
    :param auto_convert: If `True`, also accept other types, and convert them
        to a string first.
    """
    if value is None:
        result = []
    elif isinstance(value, str):
        result = [('', value)]
    elif isinstance(value, list):
        if len(value):
            assert isinstance(value[0][0], str), \
                'Expecting string, got: %r' % (value[0][0], )
            assert isinstance(value[0][1], str), \
                'Expecting string, got: %r' % (value[0][1], )

        result = value
    elif hasattr(value, '__pt_formatted_text__'):
        result = value.__pt_formatted_text__()
    elif callable(value):
        return to_formatted_text(value(), style=style)
    elif auto_convert:
        result = [('', '{}'.format(value))]
    else:
        raise ValueError('No formatted text. Expecting a unicode object, '
                         'HTML, ANSI or a FormattedText instance. Got %r' % value)

    # Apply extra style.
    if style:
        try:
            result = [(style + ' ' + k, v) for k, v in result]
        except ValueError:
            # Too many values to unpack:
            #     If the above failed, try the slower version (almost twice as
            #     slow) which supports multiple items. This is used in the
            #     `to_formatted_text` call in `FormattedTextControl` which also
            #     accepts (style, text, mouse_handler) tuples.
            result = [(style + ' ' + item[0], ) + item[1:] for item in result]

    # Make sure the result is wrapped in a `FormattedText`. Among other
    # reasons, this is important for `print_formatted_text` to work correctly
    # and distinguish between lists and formatted text.
    if isinstance(result, FormattedText):
        return result
    else:
        return FormattedText(result)


def is_formatted_text(value: Any) -> bool:
    """
    Check whether the input is valid formatted text (for use in assert
    statements).
    In case of a callable, it doesn't check the return type.
    """
    if callable(value):
        return True
    if isinstance(value, (str, list)):
        return True
    if hasattr(value, '__pt_formatted_text__'):
        return True
    return False


class FormattedText(StyleAndTextTuplesWithMouseHandlers):
    """
    A list of ``(style, text)`` tuples.

    (In some situations, this can also be ``(style, text, mouse_handler)``
    tuples.)
    """
    def __pt_formatted_text__(self) -> AnyFormattedText:
        return self

    def __repr__(self) -> str:
        return 'FormattedText(%s)' % (
            super(FormattedText, self).__repr__())


class Template:
    """
    Template for string interpolation with formatted text.

    Example::

        Template(' ... {} ... ').format(HTML(...))

    :param text: Plain text.
    """
    def __init__(self, text: str) -> None:
        assert '{0}' not in text
        self.text = text

    def format(self, *values: AnyFormattedText) -> AnyFormattedText:
        def get_result():
            # Split the template in parts.
            parts = self.text.split('{}')
            assert len(parts) - 1 == len(values)

            result = FormattedText()
            for part, val in zip(parts, values):
                result.append(('', part))
                result.extend(to_formatted_text(val))
            result.append(('', parts[-1]))
            return result
        return get_result


def merge_formatted_text(items: Iterable[AnyFormattedText]) -> AnyFormattedText:
    """
    Merge (Concatenate) several pieces of formatted text together.
    """
    def _merge_formatted_text():
        result = FormattedText()
        for i in items:
            result.extend(to_formatted_text(i))
        return result

    return _merge_formatted_text