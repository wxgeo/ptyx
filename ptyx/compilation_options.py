from ast import literal_eval
from dataclasses import dataclass, field
from typing import Literal, Any, get_origin
from argparse import Namespace


@dataclass(kw_only=True, frozen=True)
class CompilationOptions:
    filenames: list[str] = field(default_factory=list)
    number_of_documents: int = 1
    names_list: list[str] = field(default_factory=list)
    remove: bool = False
    debug: bool = False
    quiet: bool = False
    start: int = 1
    cat: bool = False
    compress: bool = False
    reorder_pages: Literal["brochure", "brochure-reversed", ""] = ""
    set_number_of_pages: int = 0
    same_number_of_pages: bool = False
    same_number_of_pages_compact: bool = False
    no_correction: bool = False
    no_pdf: bool = False
    view: bool = False
    generate_batch_for_windows_printing: bool = False
    cpu_cores: int = 0
    context: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, options: Namespace) -> "CompilationOptions":
        kwargs = vars(options)

        # -------------------------
        # Handle `--context` option
        # -------------------------
        context = {}
        for keyval in kwargs.pop("context", "").split(";"):
            if keyval.strip():
                key, val = keyval.split("=", 1)
                key = key.strip()
                if not str.isidentifier(key):
                    raise NameError(f"{key} is not a valid variable name.")
                context[key] = literal_eval(val)
        kwargs["context"] = context

        # -------------------
        # Test types validity
        # -------------------
        for key, value in cls.__dataclass_fields__.items():
            # Get the required type of the attribute.
            type_ = get_origin(value.type)
            if type_ is None:
                type_ = value.type
            # Test for conformity
            if type_ == Literal:
                assert kwargs[key] in value.type.__args__, kwargs[key]
            else:
                assert isinstance(type_, type), (key, repr(type_))
                assert isinstance(kwargs[key], type_), (key, repr(kwargs[key]), repr(type_))

        # -------------------------------------
        # Test that all options are recognized
        # -------------------------------------
        unknown_options = set(kwargs) - set(cls.__dataclass_fields__)
        assert not unknown_options, (
            f"Unknown options: {', '.join(unknown_options)}."
            " Maybe the class `CompilationOptions` should be updated?"
        )

        unfilled_options = set(cls.__dataclass_fields__) - set(kwargs)
        if unfilled_options:
            print(
                f"Warning: unfilled options: {', '.join(unknown_options)}."
                " Maybe the class `CompilationOptions` should be updated?"
            )

        # if "fixed_number_of_pages" in kwargs:
        #     kwargs["pages"] = kwargs["fixed_number_of_pages"]
        #     kwargs["fixed_number_of_pages"] = True
        # else:
        #     kwargs["fixed_number_of_pages"] = False

        return cls(**kwargs)


DEFAULT_OPTIONS = CompilationOptions()
