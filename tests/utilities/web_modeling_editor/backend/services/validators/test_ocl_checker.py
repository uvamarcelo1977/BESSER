"""
Tests for semantic OCL syntax warnings in ``check_ocl_constraint``.

The OCL grammar rule ``ID DOUBLECOLON ID`` accepts any
``Enumeration::literal`` pair, so references to enumerations or literals
that do not exist in the domain model parse as syntactically valid.
``check_ocl_constraint`` must surface those references as warnings so the
editor's Syntactic Check reports them instead of silently marking the
constraint valid.
"""

import pytest

from besser.BUML.metamodel.structural import (
    Class,
    Constraint,
    DomainModel,
    Enumeration,
    EnumerationLiteral,
    Property,
)
from besser.utilities.web_modeling_editor.backend.services.validators.ocl_checker import (
    check_ocl_constraint,
)


@pytest.fixture
def enum_model() -> DomainModel:
    """An Employee class with a TCategory enumeration that has no JUNIO literal."""
    tcategory = Enumeration(
        name="TCategory",
        literals={EnumerationLiteral(name="ENERO"), EnumerationLiteral(name="FEBRERO")},
    )
    employee = Class(name="Employee", attributes={Property(name="category", type=tcategory)})
    return DomainModel(name="Company", types={employee, tcategory})


def _make_constraint(expression: str) -> Constraint:
    return Constraint(
        name="c1",
        context=None,
        expression=expression,
        language="OCL",
    )


def test_syntax_error_is_not_a_warning(enum_model):
    constraint = _make_constraint(
        "context Employee inv: self.category = "
    )
    enum_model.constraints = {constraint}
    result = check_ocl_constraint(enum_model)
    assert result["success"] is False
    assert len(result["invalid_constraints"]) == 1
    assert result["warning_constraints"] == []
